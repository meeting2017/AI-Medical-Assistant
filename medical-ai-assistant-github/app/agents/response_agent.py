from typing import Dict, Any
import json
import re
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import RESPONSE_AGENT_PROMPT
from app.utils.logger import logger

class ResponseAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = RESPONSE_AGENT_PROMPT
    
    def run(self, state: MedicalState) -> MedicalState:
        user_input = state["messages"][-1] if state["messages"] else ""
        dialogue_history = state.get("dialogue_history") or []
        # 构建完整的对话历史（优先使用结构化角色历史）
        if dialogue_history:
            conversation_history = "\n".join(
                [f"{'用户' if msg.get('role') == 'user' else '助手'}: {msg.get('content', '')}" for msg in dialogue_history]
            )
        else:
            # 向后兼容：旧状态仍可能只有 messages
            conversation_history = "\n".join([f"用户: {msg}" if i % 2 == 0 else f"助手: {msg}" for i, msg in enumerate(state["messages"])])
        known_user_name = self._extract_user_name(dialogue_history, state.get("messages", []))
        
        analysis_result = ""
        safety_assessment = ""
        
        if state.get("knowledge_context"):
            for item in state["knowledge_context"]:
                if isinstance(item, dict):
                    if "summary" in item:
                        analysis_result += json.dumps(item, ensure_ascii=False) + "\n"
                    elif "risk_level" in item:
                        safety_assessment = json.dumps(item, ensure_ascii=False)
        
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({
                "user_input": user_input,
                "conversation_history": conversation_history,
                "known_user_name": known_user_name or "未提供",
                "analysis_result": analysis_result,
                "safety_assessment": safety_assessment
            })
            
            response_text = response.content.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)

            greeting = result.get("greeting", "")
            # 兜底：未识别到用户自报姓名时，强制使用通用称呼，避免模型臆造名字
            if not known_user_name:
                greeting = "您好！"
            else:
                if not greeting or "您好" not in greeting:
                    greeting = f"{known_user_name}，您好！"
            
            final_answer = f"{greeting}\n\n"
            final_answer += f"{result.get('main_response', '')}\n\n"
            
            if result.get('key_points'):
                final_answer += "关键要点：\n"
                for point in result['key_points']:
                    final_answer += f"• {point}\n"
                final_answer += "\n"
            
            if result.get('recommendations'):
                final_answer += "建议：\n"
                for rec in result['recommendations']:
                    final_answer += f"• {rec}\n"
                final_answer += "\n"
            
            final_answer += f"{result.get('closing', '')}\n\n"
            final_answer += f"⚠️ {result.get('disclaimer', '')}"
            
            state["final_answer"] = final_answer
            
            logger.info(f"Response generated successfully")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response: {e}")
            state["final_answer"] = f"您好，我收到了您的问题：{user_input}\n\n"
            state["final_answer"] += "很抱歉，我在生成回复时遇到了一些问题。不过请放心，我仍然可以为您提供帮助。\n\n"
            state["final_answer"] += "建议：\n"
            state["final_answer"] += "• 如果您有紧急的医疗问题，请立即拨打120急救电话\n"
            state["final_answer"] += "• 您可以尝试重新描述您的问题\n"
            state["final_answer"] += "• 如需预约挂号，请告诉我您的需求\n\n"
            state["final_answer"] += "⚠️ 本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有不适，请及时就医。"
        except Exception as e:
            logger.error(f"Error in response agent: {e}")
            state["final_answer"] = f"您好，我收到了您的问题：{user_input}\n\n"
            state["final_answer"] += "很抱歉，我在生成回复时遇到了一些问题。不过请放心，我仍然可以为您提供帮助。\n\n"
            state["final_answer"] += "建议：\n"
            state["final_answer"] += "• 如果您有紧急的医疗问题，请立即拨打120急救电话\n"
            state["final_answer"] += "• 您可以尝试重新描述您的问题\n"
            state["final_answer"] += "• 如需预约挂号，请告诉我您的需求\n\n"
            state["final_answer"] += "⚠️ 本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有不适，请及时就医。"
        
        return state

    def _extract_user_name(self, dialogue_history: list[dict], messages: list[str]) -> str:
        """
        仅从用户消息中提取明确自报姓名，避免臆造称呼。
        当前状态中消息按 [user, assistant, user, assistant, ...] 交替存储。
        """
        patterns = [
            r"(?:我叫|我是|我的名字是|叫我)\s*([A-Za-z0-9\u4e00-\u9fa5·]{2,16})",
            r"^(?:你好|您好)[，,\s]*我是\s*([A-Za-z0-9\u4e00-\u9fa5·]{2,16})"
        ]

        if dialogue_history:
            user_messages = [
                msg.get("content", "")
                for msg in dialogue_history
                if isinstance(msg, dict) and msg.get("role") == "user"
            ]
        else:
            user_messages = [msg for idx, msg in enumerate(messages) if idx % 2 == 0 and isinstance(msg, str)]
        for msg in reversed(user_messages):
            for pat in patterns:
                m = re.search(pat, msg)
                if m:
                    name = m.group(1).strip("，。,.!！？ ")
                    if name:
                        return name
        return ""
