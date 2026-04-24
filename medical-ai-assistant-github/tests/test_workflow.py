import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.state import create_initial_state
from app.workflow import workflow

def test_workflow():
    print("Testing Medical AI Assistant Workflow...")
    print("=" * 60)
    
    test_cases = [
        "我最近头痛，还有点恶心",
        "什么是高血压？",
        "我想预约挂号",
        "保持健康有什么建议？"
    ]
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {user_input}")
        print("-" * 60)
        
        state = create_initial_state(user_input)
        
        try:
            result = workflow.invoke(state)
            
            print(f"Intent: {result.get('intent')}")
            print(f"Risk Level: {result.get('risk_level')}")
            print(f"Response: {result.get('final_answer', 'No response')[:200]}...")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print()
    
    print("=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    test_workflow()