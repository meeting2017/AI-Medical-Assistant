import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from app.state import MedicalState, create_initial_state
from app.workflow import workflow
from app.memory.conversation import conversation_manager
from app.llm.llm_factory import llm_factory
from app.rag.retriever import medical_retriever
from app.config.settings import settings
from app.utils.logger import logger

def _looks_like_appointment_continuation(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return False

    # 明确预约流程关键词
    appointment_keywords = [
        "预约", "挂号", "取消预约", "我的预约", "看医生", "科室", "医生", "日期", "时间", "时段",
        "确认", "是", "好的", "继续"
    ]
    if any(k in text for k in appointment_keywords):
        return True

    # 11位手机号
    digits_only = "".join(ch for ch in text if ch.isdigit())
    if len(digits_only) == 11:
        return True

    # 常见日期/时间表达
    date_time_keywords = [
        "今天", "明天", "后天", "大后天", "上午", "下午", "晚上", "早上",
        "点", "号", "-", ":"
    ]
    if any(k in text for k in date_time_keywords):
        return True

    # 2-4位纯中文，常见于“姓名”回复
    chinese_only = "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    if chinese_only and len(chinese_only) == len(text.replace(" ", "")) and 2 <= len(chinese_only) <= 4:
        return True

    return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API started with JSON file memory")
    warmup_task = None
    if settings.RAG_WARMUP_BACKGROUND:
        async def _warmup():
            try:
                await asyncio.to_thread(medical_retriever.warmup, settings.RAG_WARMUP_LOAD_RERANKER)
                logger.info("RAG background warmup completed")
            except Exception as e:
                logger.warning(f"RAG background warmup failed: {e}")
        warmup_task = asyncio.create_task(_warmup())
    try:
        yield
    finally:
        if warmup_task and not warmup_task.done():
            warmup_task.cancel()
        logger.info("API shutdown")

app = FastAPI(
    title="智能医疗助手 API",
    description="基于 LangChain + LangGraph 的多智能体医疗助手。",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StreamingChatResponse:
    def __init__(self, state: Dict[str, Any], session_id: str):
        self.state = state
        self.session_id = session_id
    
    async def __call__(self, scope, receive, send):
        try:
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/event-stream"),
                    (b"cache-control", b"no-cache"),
                    (b"connection", b"keep-alive"),
                ],
            })
            
            result = await asyncio.to_thread(workflow.invoke, self.state)
            
            response_data = {
                "answer": result.get("final_answer", ""),
                "intent": result.get("intent", ""),
                "risk_level": result.get("risk_level", "SAFE"),
                "sources": self._extract_sources(result),
                "disclaimer": self._extract_disclaimer(result)
            }
            
            # Save assistant response
            if result.get("final_answer"):
                conversation_manager.add_message(
                    self.session_id,
                    "assistant",
                    result["final_answer"]
                )
            
            await send({
                "type": "http.response.body",
                "body": f"data: {json.dumps(response_data)}\n\n".encode(),
                "more_body": False,
            })
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_data = {"error": str(e)}
            await send({
                "type": "http.response.body",
                "body": f"data: {json.dumps(error_data)}\n\n".encode(),
                "more_body": False,
            })
    
    def _extract_sources(self, result: Dict[str, Any]) -> List[str]:
        sources = []
        if result.get("knowledge_context"):
            for item in result["knowledge_context"]:
                if isinstance(item, str) and "【医学知识" in item:
                    sources.append(item[:100] + "...")
        return sources
    
    def _extract_disclaimer(self, result: Dict[str, Any]) -> str:
        if result.get("knowledge_context"):
            for item in result["knowledge_context"]:
                if isinstance(item, dict) and "disclaimer" in item:
                    return item["disclaimer"]
        return "本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。"

@app.get("/")
async def root():
    return JSONResponse(
        content={
            "service": "medical-ai-assistant-api",
            "status": "ok",
            "api_base": "http://127.0.0.1:8000",
            "docs": "http://127.0.0.1:8000/docs",
            "frontend_dev": "http://127.0.0.1:5173"
        }
    )

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id", None)
        
        if not message:
            return JSONResponse(status_code=400, content={"error": "Message is required"})
        
        if not session_id:
            return JSONResponse(status_code=400, content={"error": "Session ID is required"})
        
        # Add user message to history
        conversation_manager.add_message(session_id, "user", message)

        # Get updated history
        updated_history = conversation_manager.get_history(session_id)

        # Build state with complete history
        history_messages = [msg["content"] for msg in updated_history]
        state = create_initial_state(
            message,
            history=history_messages,
            history_records=updated_history
        )
        state["conversation_id"] = session_id

        # 恢复预约状态
        saved_appointment_state = conversation_manager.get_appointment_state(session_id)
        if saved_appointment_state.get("appointment_step"):
            state["appointment_step"] = saved_appointment_state["appointment_step"]
            state["appointment_data"] = saved_appointment_state.get("appointment_data", {})

        async def event_generator():
            # 先发送开始事件
            yield f"data: {json.dumps({'type': 'start'})}\n\n"

            # 检查是否已经在预约流程中或意图为预约挂号
            from app.appointment.register_agent import register_agent

            # 保存可能存在的预约状态，因为 workflow.invoke 可能不包含它
            has_appointment_step = "appointment_step" in state
            saved_step = state.get("appointment_step")
            saved_data = state.get("appointment_data", {})

            # 执行工作流获取意图
            result = await asyncio.to_thread(workflow.invoke, state)

            # 恢复预约状态
            if has_appointment_step:
                result["appointment_step"] = saved_step
                result["appointment_data"] = saved_data

            # 检查意图是否为预约挂号
            is_appointment_intent = result.get("intent") == "INT-03"
            is_cancel_appointment_intent = result.get("intent") == "INT-07"
            in_progress_step = bool(saved_step)
            is_continuation_input = _looks_like_appointment_continuation(message)
            topic_switched = in_progress_step and (not is_appointment_intent) and (not is_cancel_appointment_intent) and (not is_continuation_input)

            # 如果用户在预约过程中突然转移话题，结束预约上下文，避免继续追问手机号/姓名
            if topic_switched:
                conversation_manager.clear_appointment_state(session_id)
                result.pop("appointment_step", None)
                result.pop("appointment_data", None)
                logger.info(
                    f"Topic switched detected, exit appointment flow. session_id={session_id}, intent={result.get('intent')}"
                )

            # 仅在明确是预约/取消，或预约流程中的有效续聊输入时，才进入 RegisterAgent
            # 也需要检查用户是否在回复"确认"来确认预约
            user_confirming = message and ("确认" in message or "是" in message)
            should_use_register_agent = (
                is_appointment_intent
                or is_cancel_appointment_intent
                or user_confirming
                or (in_progress_step and is_continuation_input)
            )

            if should_use_register_agent:
                # 调用 RegisterAgent
                appointment_result = register_agent.run(result)
                result = appointment_result

                # 保存预约状态
                step = result.get("appointment_step")
                data_to_save = result.get("appointment_data", {})

                if step and data_to_save:
                    conversation_manager.save_appointment_state(
                        session_id,
                        step,
                        data_to_save
                    )
                elif step is None:
                    conversation_manager.clear_appointment_state(session_id)
            
            # Add assistant response to history
            if result.get("final_answer"):
                conversation_manager.add_message(
                    session_id,
                    "assistant",
                    result["final_answer"]
                )

            # Stream output must preserve original text exactly
            if result.get("final_answer"):
                answer = result["final_answer"]
                chunk_buffer = []
                flush_chars = 12
                flush_on = {'\n', '\u3002', '\uff01', '\uff1f', '\uff0c', ',', '.', ';', '\uff1b', ':', '\uff1a'}

                for char in answer:
                    chunk_buffer.append(char)
                    if len(chunk_buffer) >= flush_chars or char in flush_on:
                        data = json.dumps({"type": "message", "content": "".join(chunk_buffer)})
                        yield f"data: {data}\n\n"
                        chunk_buffer = []
                        await asyncio.sleep(0.02)

                if chunk_buffer:
                    data = json.dumps({"type": "message", "content": "".join(chunk_buffer)})
                    yield f"data: {data}\n\n"

            # 构建最终响应数据
            response_data = {
                "type": "complete",
                "answer": result.get("final_answer", ""),
                "intent": result.get("intent", ""),
                "risk_level": result.get("risk_level", "SAFE"),
                "sources": [],
                "disclaimer": "",
                "session_id": session_id,
                "appointment_step": result.get("appointment_step", ""),
                "appointment_data": result.get("appointment_data", {}),
                "dates": result.get("dates", []),
                "time_slots": result.get("time_slots", []),
                "appointments": result.get("appointments", []),
                "topic_switched": topic_switched,
                "topic_switch_notice": "已为您暂停预约流程，如需继续请说“继续预约”。" if topic_switched else ""
            }

            if result.get("knowledge_context"):
                for item in result["knowledge_context"]:
                    if isinstance(item, str) and "【医学知识" in item:
                        response_data["sources"].append(item[:100] + "...")
                    elif isinstance(item, dict) and "disclaimer" in item:
                        response_data["disclaimer"] = item["disclaimer"]

            if not response_data["disclaimer"]:
                response_data["disclaimer"] = "本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。"
            
            # 发送完成事件
            yield f"data: {json.dumps(response_data)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        # 即使出错也要返回友好的流式响应
        async def error_generator():
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            error_message = "很抱歉，我在处理您的请求时遇到了一些情况。不过请放心，我仍然可以为您提供帮助。"
            for char in error_message:
                data = json.dumps({"type": "message", "content": char})
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.05)
            data = json.dumps({"type": "message", "content": "\n\n"})
            yield f"data: {data}\n\n"
            advice = "建议您：\n• 尝试重新描述您的症状\n• 确保网络连接稳定\n• 如需紧急帮助，请立即联系医疗专业人士"
            for char in advice:
                data = json.dumps({"type": "message", "content": char})
                yield f"data: {data}\n\n"
                await asyncio.sleep(0.03)
            data = json.dumps({"type": "message", "content": "\n\n⚠️ 本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有不适，请及时就医。"})
            yield f"data: {data}\n\n"
            complete_data = json.dumps({
                "type": "complete",
                "answer": "",
                "intent": "",
                "risk_level": "SAFE",
                "sources": [],
                "disclaimer": "本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有不适，请及时就医。",
                "session_id": ""
            })
            yield f"data: {complete_data}\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream"
        )

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """获取会话历史"""
    try:
        history = conversation_manager.get_history(session_id)
        return JSONResponse(content={
            "full_history": history,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return JSONResponse(content={
            "full_history": [],
            "session_id": session_id
        })

@app.post("/chat/stream")
async def chat_stream(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id", None)
        
        if not message:
            return JSONResponse(status_code=400, content={"error": "Message is required"})
        
        if not session_id:
            return JSONResponse(status_code=400, content={"error": "Session ID is required"})
        
        # Add user message to history
        conversation_manager.add_message(session_id, "user", message)
        
        # Get updated history
        updated_history = conversation_manager.get_history(session_id)
        
        # Build state with complete history
        history_messages = [msg["content"] for msg in updated_history]
        state = create_initial_state(
            message,
            history=history_messages,
            history_records=updated_history
        )
        state["conversation_id"] = session_id
        
        return StreamingResponse(
            StreamingChatResponse(state, session_id), 
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Stream error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.post("/clear")
async def clear_session(request: Request):
    try:
        data = await request.json()
        session_id = data.get("session_id", None)
        
        if not session_id:
            return JSONResponse(status_code=400, content={"error": "Session ID is required"})
        
        conversation_manager.clear_session(session_id)
        
        return JSONResponse(content={"message": "Session cleared", "session_id": session_id})
        
    except Exception as e:
        logger.error(f"Clear session error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.post("/appointment")
async def appointment(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id", None)
        
        if not session_id:
            return JSONResponse(status_code=400, content={"error": "Session ID is required"})
        
        from app.appointment.register_agent import register_agent
        
        state = create_initial_state(message)
        state["conversation_id"] = session_id
        
        result = register_agent.run(state)
        
        # Add assistant response to history
        if result.get("final_answer"):
            conversation_manager.add_message(
                session_id,
                "assistant",
                result["final_answer"]
            )
        
        return JSONResponse(content={"answer": result.get("final_answer", ""), "appointment_info": result.get("appointment_info", {})})
        
    except Exception as e:
        logger.error(f"Appointment error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.get("/my-appointments")
async def get_my_appointments(request: Request):
    """获取当前session的所有预约"""
    try:
        session_id = request.query_params.get("session_id")
        
        if not session_id:
            return JSONResponse(status_code=400, content={"error": "Session ID is required"})
        
        from app.appointment.register_service import register_service
        
        appointments = register_service.get_appointments(session_id)
        
        return JSONResponse(content={
            "appointments": appointments,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Get appointments error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.post("/cancel-appointment")
async def cancel_appointment(request: Request):
    """取消指定预约"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        appointment_id = data.get("appointment_id")
        
        if not session_id:
            return JSONResponse(status_code=400, content={"error": "Session ID is required"})
        
        if not appointment_id:
            return JSONResponse(status_code=400, content={"error": "Appointment ID is required"})
        
        from app.appointment.register_service import register_service
        
        result = register_service.cancel_appointment(session_id, appointment_id)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Cancel appointment error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.post("/save-appointment")
async def save_appointment(request: Request):
    """直接保存预约"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        appointment_data = data.get("appointment_data")
        
        if not session_id:
            return JSONResponse(status_code=400, content={"success": False, "message": "Session ID is required"})
        
        if not appointment_data:
            return JSONResponse(status_code=400, content={"success": False, "message": "Appointment data is required"})
        
        from app.appointment.register_service import register_service
        
        # 调用保存预约方法
        result = register_service.save_appointment(session_id, appointment_data)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Save appointment error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": "保存预约失败"})

@app.post("/model/switch")
async def switch_model(request: Request):
    try:
        data = await request.json()
        model = data.get("model", "")
        
        if model:
            from app.config.settings import settings
            settings.OPENAI_MODEL = model
            llm_factory.reset_llm()
            
        return JSONResponse(content={"message": f"Model switched to {model}"})
        
    except Exception as e:
        logger.error(f"Switch model error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

if __name__ == "__main__":
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    logger.info(f"API entrypoint: http://{host}:{port}")
    uvicorn.run("app.api:app", host=host, port=port, reload=True)
