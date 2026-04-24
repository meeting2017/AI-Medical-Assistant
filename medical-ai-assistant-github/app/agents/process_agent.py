from typing import Dict, Any
import json
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import PROCESS_AGENT_PROMPT
from app.utils.logger import logger

class ProcessAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = PROCESS_AGENT_PROMPT

    @staticmethod
    def _normalize_knowledge_context(knowledge_context: Any) -> str:
        """Convert mixed knowledge payloads to a safe text block for LLM input."""
        if not knowledge_context:
            return "未找到相关知识"

        if isinstance(knowledge_context, str):
            return knowledge_context

        if isinstance(knowledge_context, dict):
            return json.dumps(knowledge_context, ensure_ascii=False)

        if isinstance(knowledge_context, list):
            normalized_items = []
            for item in knowledge_context:
                if isinstance(item, str):
                    normalized_items.append(item)
                else:
                    normalized_items.append(json.dumps(item, ensure_ascii=False))
            return "\n\n".join(normalized_items)

        return str(knowledge_context)    
    def run(self, state: MedicalState) -> MedicalState:
        symptom_info = state.get("symptom_info", {})
        knowledge_context = state.get("knowledge_context", [])
        
        try:
            symptom_text = json.dumps(symptom_info, ensure_ascii=False, indent=2)
            knowledge_text = self._normalize_knowledge_context(knowledge_context)
            
            chain = self.prompt | self.llm
            response = chain.invoke({
                "symptom_info": symptom_text,
                "knowledge_context": knowledge_text
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
            
            processed_result = {
                "summary": result.get("summary", ""),
                "possible_causes": result.get("possible_causes", []),
                "recommendations": result.get("recommendations", []),
                "when_to_see_doctor": result.get("when_to_see_doctor", ""),
                "self_care_tips": result.get("self_care_tips", []),
                "additional_notes": result.get("additional_notes", "")
            }
            
            if not state.get("knowledge_context"):
                state["knowledge_context"] = []
            state["knowledge_context"].append(processed_result)
            
            logger.info(f"Process agent completed analysis")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse process response: {e}")
            processed_result = {
                "summary": "分析过程中出现错误",
                "possible_causes": [],
                "recommendations": ["建议咨询专业医生"],
                "when_to_see_doctor": "如有不适，请及时就医",
                "self_care_tips": [],
                "additional_notes": ""
            }
            if not state.get("knowledge_context"):
                state["knowledge_context"] = []
            state["knowledge_context"].append(processed_result)
        except Exception as e:
            logger.error(f"Error in process agent: {e}")
            processed_result = {
                "summary": "分析过程中出现错误",
                "possible_causes": [],
                "recommendations": ["建议咨询专业医生"],
                "when_to_see_doctor": "如有不适，请及时就医",
                "self_care_tips": [],
                "additional_notes": ""
            }
            if not state.get("knowledge_context"):
                state["knowledge_context"] = []
            state["knowledge_context"].append(processed_result)
        
        return state
