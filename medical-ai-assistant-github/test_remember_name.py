#!/usr/bin/env python3
"""
测试记住用户姓名功能
"""

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.memory.conversation import conversation_manager
from app.state import create_initial_state
from app.workflow import workflow

def test_remember_name():
    """测试记住用户姓名功能"""
    print("=== 测试记住用户姓名功能 ===")
    
    # 测试会话 ID
    session_id = "test_session_remember_name"
    
    # 步骤 1: 清空会话
    print("1. 清空会话...")
    conversation_manager.clear_session(session_id)
    
    # 步骤 2: 第一次对话 - 自报姓名
    print("2. 第一次对话: 你好我叫六科技")
    user_message = "你好我叫六科技"
    
    # 添加用户消息到历史
    conversation_manager.add_message(session_id, "user", user_message)
    
    # 构建状态
    history = conversation_manager.get_history(session_id)
    history_messages = [msg["content"] for msg in history]
    state = create_initial_state(user_message, history=history_messages)
    state["conversation_id"] = session_id
    
    # 执行工作流
    result = workflow.invoke(state)
    
    # 添加助手回复到历史
    if result.get("final_answer"):
        conversation_manager.add_message(session_id, "assistant", result["final_answer"])
        print(f"   助手回复: {result['final_answer'][:100]}...")
    
    # 步骤 3: 第二次对话 - 询问名字
    print("3. 第二次对话: 你知道我叫什么吗")
    user_message = "你知道我叫什么吗"
    
    # 添加用户消息到历史
    conversation_manager.add_message(session_id, "user", user_message)
    
    # 构建状态
    history = conversation_manager.get_history(session_id)
    history_messages = [msg["content"] for msg in history]
    state = create_initial_state(user_message, history=history_messages)
    state["conversation_id"] = session_id
    
    # 执行工作流
    result = workflow.invoke(state)
    
    # 添加助手回复到历史
    if result.get("final_answer"):
        conversation_manager.add_message(session_id, "assistant", result["final_answer"])
        print(f"   助手回复: {result['final_answer'][:100]}...")
        
        # 验证是否记得名字
        if "六科技" in result["final_answer"]:
            print("   ✅ 测试通过：助手记得用户名字")
        else:
            print("   ❌ 测试失败：助手不记得用户名字")
    
    # 步骤 4: 第三次对话 - 医疗问题
    print("4. 第三次对话: 我有点头疼")
    user_message = "我有点头疼"
    
    # 添加用户消息到历史
    conversation_manager.add_message(session_id, "user", user_message)
    
    # 构建状态
    history = conversation_manager.get_history(session_id)
    history_messages = [msg["content"] for msg in history]
    state = create_initial_state(user_message, history=history_messages)
    state["conversation_id"] = session_id
    
    # 执行工作流
    result = workflow.invoke(state)
    
    # 添加助手回复到历史
    if result.get("final_answer"):
        conversation_manager.add_message(session_id, "assistant", result["final_answer"])
        print(f"   助手回复: {result['final_answer'][:100]}...")
        
        # 验证是否使用名字称呼
        if "六科技" in result["final_answer"]:
            print("   ✅ 测试通过：助手使用用户名字称呼")
        else:
            print("   ❌ 测试失败：助手没有使用用户名字称呼")
    
    # 步骤 5: 模拟重启后测试
    print("5. 模拟重启后测试: 你叫我什么")
    # 创建新的会话管理器实例模拟重启
    from app.memory.conversation import ConversationManager
    new_manager = ConversationManager()
    
    # 获取历史
    history = new_manager.get_history(session_id)
    
    # 新的用户消息
    user_message = "你叫我什么"
    
    # 添加用户消息到历史
    new_manager.add_message(session_id, "user", user_message)
    
    # 构建状态
    history_messages = [msg["content"] for msg in new_manager.get_history(session_id)]
    state = create_initial_state(user_message, history=history_messages)
    state["conversation_id"] = session_id
    
    # 执行工作流
    result = workflow.invoke(state)
    
    # 添加助手回复到历史
    if result.get("final_answer"):
        new_manager.add_message(session_id, "assistant", result["final_answer"])
        print(f"   助手回复: {result['final_answer'][:100]}...")
        
        # 验证是否记得名字
        if "六科技" in result["final_answer"]:
            print("   ✅ 测试通过：重启后助手仍然记得用户名字")
        else:
            print("   ❌ 测试失败：重启后助手不记得用户名字")
    
    # 清理测试数据
    conversation_manager.clear_session(session_id)
    print("\n测试完成，已清理测试数据")

if __name__ == "__main__":
    test_remember_name()
