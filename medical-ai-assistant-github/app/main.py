import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.state import create_initial_state
from app.workflow import workflow
from app.memory.conversation import conversation_manager
from app.utils.logger import logger
from app.config.settings import settings

class MedicalAIAssistant:
    def __init__(self):
        self.workflow = workflow
        self.conversation_manager = conversation_manager
        self.current_conversation = None
    
    def process_message(self, user_message: str, conversation_id: str = None) -> str:
        if not user_message or not user_message.strip():
            return "请输入您的问题或需求。"
        
        if conversation_id is None:
            self.current_conversation = self.conversation_manager.create_conversation()
            conversation_id = self.current_conversation.conversation_id
        else:
            self.current_conversation = self.conversation_manager.get_conversation(conversation_id)
            if self.current_conversation is None:
                self.current_conversation = self.conversation_manager.create_conversation(conversation_id)
        
        self.current_conversation.add_message("user", user_message)
        
        state = create_initial_state(user_message)
        state["conversation_id"] = conversation_id
        
        try:
            result = self.workflow.invoke(state)
            final_answer = result.get("final_answer", "抱歉，我无法理解您的问题。请重新描述。")
            
            self.current_conversation.add_message("assistant", final_answer)
            
            logger.info(f"Processed message for conversation {conversation_id}")
            
            return final_answer
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_message = "抱歉，系统出现了一些问题。请稍后再试。"
            self.current_conversation.add_message("assistant", error_message)
            return error_message
    
    def start_conversation(self) -> str:
        self.current_conversation = self.conversation_manager.create_conversation()
        welcome_message = """您好！我是您的智能医疗助手。

我可以为您提供以下服务：
• 症状咨询：描述您的症状，我会为您提供专业的分析和建议
• 医学知识：询问疾病、药物、健康知识等问题
• 预约挂号：帮您预约医院的医生
• 健康建议：提供健康生活方式的建议

请告诉我您需要什么帮助？

⚠️ 重要提示：本系统提供的医疗信息仅供参考，不能替代专业医生的诊断和治疗。如有紧急情况，请立即拨打120急救电话。"""
        
        self.current_conversation.add_message("assistant", welcome_message)
        return welcome_message
    
    def get_conversation_history(self, conversation_id: str = None) -> str:
        if conversation_id:
            conv = self.conversation_manager.get_conversation(conversation_id)
            if conv:
                return conv.get_conversation_history()
        elif self.current_conversation:
            return self.current_conversation.get_conversation_history()
        return "暂无对话历史"
    
    def reset_conversation(self):
        if self.current_conversation:
            self.conversation_manager.delete_conversation(self.current_conversation.conversation_id)
            self.current_conversation = None
        logger.info("Conversation reset")

def main():
    print("=" * 60)
    print("智能医疗助手系统")
    print("基于 LangChain + LangGraph 的多智能体医疗助手")
    print("=" * 60)
    print()
    
    assistant = MedicalAIAssistant()
    
    print(assistant.start_conversation())
    print()
    
    conversation_id = assistant.current_conversation.conversation_id
    
    while True:
        try:
            user_input = input("您: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["退出", "exit", "quit", "bye"]:
                print("\n感谢使用智能医疗助手！祝您身体健康！")
                break
            
            if user_input.lower() in ["历史", "history"]:
                print("\n" + assistant.get_conversation_history() + "\n")
                continue
            
            if user_input.lower() in ["重置", "reset", "清空", "clear"]:
                assistant.reset_conversation()
                print("\n" + assistant.start_conversation() + "\n")
                continue
            
            print("\n助手: ", end="", flush=True)
            response = assistant.process_message(user_input, conversation_id)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n感谢使用智能医疗助手！祝您身体健康！")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\n抱歉，出现了一些问题：{e}\n")

if __name__ == "__main__":
    main()