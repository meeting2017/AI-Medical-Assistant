from typing import Dict, Any
import json
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import KNOWLEDGE_AGENT_PROMPT
from app.rag.retriever import medical_retriever
from app.utils.logger import logger

class KnowledgeAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = KNOWLEDGE_AGENT_PROMPT
        self.retriever = medical_retriever
    
    def run(self, state: MedicalState) -> MedicalState:
        user_input = state["messages"][-1] if state["messages"] else ""
        
        try:
            knowledge_context = self.retriever.get_relevant_knowledge(user_input)
            state["knowledge_context"] = [knowledge_context]
            
            chain = self.prompt | self.llm
            response = chain.invoke({
                "query": user_input,
                "knowledge_context": knowledge_context
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
            
            state["knowledge_context"].append({
                "answer": result.get("answer", ""),
                "key_points": result.get("key_points", []),
                "references": result.get("references", []),
                "related_topics": result.get("related_topics", []),
                "confidence": result.get("confidence", 0.0)
            })
            
            logger.info(f"Knowledge retrieval completed: {len(state['knowledge_context'])} contexts")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse knowledge response: {e}")
            if not state["knowledge_context"]:
                state["knowledge_context"] = []
        except Exception as e:
            logger.error(f"Error in knowledge agent: {e}")
            if not state["knowledge_context"]:
                state["knowledge_context"] = []
        
        return state