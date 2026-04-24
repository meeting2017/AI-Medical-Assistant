from typing import TypedDict, List, Optional, Dict, Any
from enum import Enum

class IntentType(str, Enum):
    SYMPTOM_INQUIRY = "INT-01"
    KNOWLEDGE_QUERY = "INT-02"
    APPOINTMENT = "INT-03"
    HEALTH_ADVICE = "INT-04"
    MEDICATION_INFO = "INT-05"
    GENERAL_CHAT = "INT-06"

class RiskLevel(str, Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class MedicalState(TypedDict):
    messages: List[str]
    dialogue_history: Optional[List[Dict[str, str]]]
    intent: Optional[str]
    intent_confidence: Optional[float]
    symptom_info: Optional[Dict[str, Any]]
    knowledge_context: Optional[List[Any]]
    risk_level: Optional[str]
    final_answer: Optional[str]
    appointment_info: Optional[Dict[str, Any]]
    conversation_id: Optional[str]
    timestamp: Optional[str]

def create_initial_state(
    user_message: str,
    history: List[str] = None,
    history_records: List[Dict[str, str]] = None
) -> MedicalState:
    from datetime import datetime
    import uuid
    
    if history:
        # 如果提供了历史消息，直接使用历史消息
        # 注意：历史消息已经包含了用户的最新消息
        messages = history.copy()
    else:
        # 否则只使用当前消息
        messages = [user_message] if user_message else []
    
    return MedicalState(
        messages=messages,
        dialogue_history=history_records or [],
        intent=None,
        intent_confidence=None,
        symptom_info=None,
        knowledge_context=None,
        risk_level=None,
        final_answer=None,
        appointment_info=None,
        conversation_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat()
    )
