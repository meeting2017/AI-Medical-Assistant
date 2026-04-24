from typing import Dict, Any
import json
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import INTENT_PROMPT
from app.utils.logger import logger

class IntentAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = INTENT_PROMPT
    
    def run(self, state: MedicalState) -> MedicalState:
        user_input = state["messages"][-1] if state["messages"] else ""

        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"user_input": user_input})
            
            response_text = response.content
            response_text = response_text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            state["intent"] = result.get("intent")
            state["intent_confidence"] = result.get("confidence", 0.0)
            
            logger.info(f"Intent recognized: {state['intent']} (confidence: {state['intent_confidence']})")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent response: {e}")
            state["intent"] = "INT-06"
            state["intent_confidence"] = 0.5
        except Exception as e:
            logger.error(f"Error in intent agent: {e}")
            state["intent"] = "INT-06"
            state["intent_confidence"] = 0.5
        
        return state
