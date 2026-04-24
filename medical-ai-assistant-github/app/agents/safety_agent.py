from typing import Dict, Any
import json
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import SAFETY_AGENT_PROMPT
from app.utils.risk_keywords import check_risk_level
from app.utils.logger import logger

class SafetyAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = SAFETY_AGENT_PROMPT
    
    def run(self, state: MedicalState) -> MedicalState:
        user_input = state["messages"][-1] if state["messages"] else ""
        medical_response = ""
        
        if state.get("knowledge_context"):
            for item in state["knowledge_context"]:
                if isinstance(item, dict):
                    if "answer" in item:
                        medical_response += item["answer"] + "\n"
                    elif "summary" in item:
                        medical_response += item["summary"] + "\n"
        
        initial_risk_level = check_risk_level(user_input)
        
        # 白名单：自报姓名不属于高风险
        if "我叫" in user_input or "我的名字是" in user_input:
            initial_risk_level = "LOW"
        
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({
                "user_input": user_input,
                "medical_response": medical_response,
                "initial_risk_level": initial_risk_level
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
            
            risk_level = result.get("risk_level", "SAFE")
            
            if risk_level == "HIGH":
                state["risk_level"] = "HIGH"
            elif risk_level == "MEDIUM":
                state["risk_level"] = "MEDIUM"
            elif risk_level == "LOW":
                state["risk_level"] = "LOW"
            else:
                state["risk_level"] = "SAFE"
            
            safety_info = {
                "risk_level": state["risk_level"],
                "risk_factors": result.get("risk_factors", []),
                "warnings": result.get("warnings", []),
                "disclaimer": result.get("disclaimer", ""),
                "requires_medical_attention": result.get("requires_medical_attention", False),
                "emergency_action": result.get("emergency_action", "")
            }
            
            if not state.get("knowledge_context"):
                state["knowledge_context"] = []
            state["knowledge_context"].append(safety_info)
            
            logger.info(f"Safety assessment completed: {state['risk_level']}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse safety response: {e}")
            state["risk_level"] = initial_risk_level
            safety_info = {
                "risk_level": state["risk_level"],
                "risk_factors": [],
                "warnings": [],
                "disclaimer": "本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有不适，请及时就医。紧急情况请立即拨打120急救电话或前往最近的医院急诊。",
                "requires_medical_attention": state["risk_level"] != "SAFE",
                "emergency_action": ""
            }
            if not state.get("knowledge_context"):
                state["knowledge_context"] = []
            state["knowledge_context"].append(safety_info)
        except Exception as e:
            logger.error(f"Error in safety agent: {e}")
            state["risk_level"] = initial_risk_level
            safety_info = {
                "risk_level": state["risk_level"],
                "risk_factors": [],
                "warnings": [],
                "disclaimer": "本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有不适，请及时就医。紧急情况请立即拨打120急救电话或前往最近的医院急诊。",
                "requires_medical_attention": state["risk_level"] != "SAFE",
                "emergency_action": ""
            }
            if not state.get("knowledge_context"):
                state["knowledge_context"] = []
            state["knowledge_context"].append(safety_info)
        
        return state