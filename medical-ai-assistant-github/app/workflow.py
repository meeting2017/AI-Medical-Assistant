from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from app.state import MedicalState
from app.agents import (
    IntentAgent,
    SymptomAgent,
    KnowledgeAgent,
    ProcessAgent,
    SafetyAgent,
    ResponseAgent
)
from app.appointment.register_agent import register_agent
from app.rag.vector_store import vector_store
from app.config.settings import settings
from app.utils.logger import logger

class Workflow:
    def __init__(self):
        self.intent_agent = IntentAgent()
        self.symptom_agent = SymptomAgent()
        self.knowledge_agent = KnowledgeAgent()
        self.process_agent = ProcessAgent()
        self.safety_agent = SafetyAgent()
        self.response_agent = ResponseAgent()
        self.register_agent = register_agent
        
        if settings.RAG_PRELOAD_ON_STARTUP:
            self._initialize_vectorstore()
        else:
            logger.info("Skip RAG preload on startup (lazy-load enabled)")
        self.graph = self._build_graph()
    
    def _initialize_vectorstore(self):
        from pathlib import Path
        docs_dir = Path("./app/rag/medical_docs")
        if docs_dir.exists():
            try:
                if vector_store.has_data():
                    logger.info("Vector store already contains data, skip re-indexing medical docs")
                    return
                for doc_file in docs_dir.glob("*.txt"):
                    documents = vector_store.load_documents(str(doc_file))
                    if documents:
                        vector_store.add_documents(documents)
                logger.info("Vector store initialized with medical documents")
            except Exception as e:
                logger.warning(f"Vector store initialization skipped: {e}")
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(MedicalState)
        
        workflow.add_node("intent", self.intent_agent.run)
        workflow.add_node("symptom", self.symptom_agent.run)
        workflow.add_node("knowledge", self.knowledge_agent.run)
        workflow.add_node("process", self.process_agent.run)
        workflow.add_node("safety", self.safety_agent.run)
        workflow.add_node("response", self.response_agent.run)
        workflow.add_node("appointment", self.register_agent.run)
        
        workflow.set_entry_point("intent")
        
        workflow.add_conditional_edges(
            "intent",
            self.route_by_intent,
            {
                "INT-01": "symptom",
                "INT-02": "knowledge",
                "INT-03": "appointment",
                "INT-04": "knowledge",
                "INT-05": "knowledge",
                # 闲聊走快速路径，减少不必要的检索/处理链路
                "INT-06": "response",
                "INT-07": "appointment"
            }
        )
        
        workflow.add_edge("symptom", "knowledge")
        workflow.add_edge("knowledge", "process")
        workflow.add_edge("process", "safety")
        workflow.add_edge("safety", "response")
        workflow.add_edge("response", END)
        workflow.add_edge("appointment", END)
        
        return workflow.compile()
    
    def route_by_intent(self, state: MedicalState) -> Literal["INT-01", "INT-02", "INT-03", "INT-04", "INT-05", "INT-06", "INT-07"]:
        intent = state.get("intent", "INT-06")
        logger.info(f"Routing by intent: {intent}")
        return intent
    
    def invoke(self, state: MedicalState) -> MedicalState:
        try:
            result = self.graph.invoke(state)
            logger.info("Workflow completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in workflow: {e}")
            state["final_answer"] = "抱歉，系统出现了一些问题。请稍后再试。"
            return state
    
    def stream(self, state: MedicalState):
        try:
            for event in self.graph.stream(state):
                for node_name, node_output in event.items():
                    logger.info(f"Node {node_name} completed")
                    yield node_name, node_output
        except Exception as e:
            logger.error(f"Error in workflow stream: {e}")
            yield "error", {"error": str(e)}

workflow = Workflow()
