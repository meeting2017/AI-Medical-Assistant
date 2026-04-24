from typing import Dict, Any
import json
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import SYMPTOM_AGENT_PROMPT
from app.utils.logger import logger

class SymptomAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = SYMPTOM_AGENT_PROMPT
    
    def run(self, state: MedicalState) -> MedicalState:
        user_input = state["messages"][-1] if state["messages"] else ""
        
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"user_input": user_input})
            
            response_text = response.content.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            state["symptom_info"] = {
                "symptoms": result.get("symptoms", []),
                "duration": result.get("duration", ""),
                "severity": result.get("severity", "中等"),
                "affected_areas": result.get("affected_areas", []),
                "additional_info": result.get("additional_info", ""),
                "preliminary_assessment": result.get("preliminary_assessment", ""),
                "recommendations": result.get("recommendations", [])
            }
            
            logger.info(f"Symptom analysis completed: {len(state['symptom_info']['symptoms'])} symptoms identified")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse symptom response: {e}")
            state["symptom_info"] = {
                "symptoms": [],
                "duration": "",
                "severity": "中等",
                "affected_areas": [],
                "additional_info": "",
                "preliminary_assessment": "",
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"Error in symptom agent: {e}")
            state["symptom_info"] = {
                "symptoms": [],
                "duration": "",
                "severity": "中等",
                "affected_areas": [],
                "additional_info": "",
                "preliminary_assessment": "",
                "recommendations": []
            }
        
        return state