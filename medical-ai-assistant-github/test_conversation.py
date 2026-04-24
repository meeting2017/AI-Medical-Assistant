#!/usr/bin/env python3
"""
测试会话管理器的连续对话功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.memory.conversation import conversation_manager

def test_continuous_conversation():
    """测试连续对话功能"""
    print("=== 测试连续对话功能 ===")
    
    # 测试会话 ID
    session_id = "test_session_continuous"
    
    # 步骤 1: 清空会话
    print("1. 清空会话...")
    conversation_manager.clear_session(session_id)
    
    # 步骤 2: 第一次对话
    print("2. 第一次对话: 你好我叫六科技")
    conversation_manager.add_message(session_id, "user", "你好我叫六科技")
    conversation_manager.add_message(session_id, "assistant", "您好，六科技！很高兴为您服务。")
    
    # 步骤 3: 第二次对话
    print("3. 第二次对话: 你知道我叫什么吗")
    conversation_manager.add_message(session_id, "user", "你知道我叫什么吗")
    conversation_manager.add_message(session_id, "assistant", "您好，六科技！我当然记得您的名字。")
    
    # 步骤 4: 第三次对话
    print("4. 第三次对话: 我有点头疼怎么解决")
    conversation_manager.add_message(session_id, "user", "我有点头疼怎么解决")
    conversation_manager.add_message(session_id, "assistant", "您好，六科技！关于头疼，建议您...")
    
    # 步骤 5: 第四次对话
    print("5. 第四次对话: 还有点恶心")
    conversation_manager.add_message(session_id, "user", "还有点恶心")
    conversation_manager.add_message(session_id, "assistant", "了解了，六科技！头疼伴随恶心可能是...")
    
    # 步骤 6: 读取完整历史
    print("6. 读取完整历史...")
    history = conversation_manager.get_history(session_id)
    
    print("\n=== 完整对话历史 ===")
    for i, msg in enumerate(history):
        role = "用户" if msg["role"] == "user" else "助手"
        print(f"{i+1}. {role}: {msg['content']}")
    
    # 步骤 7: 模拟重启后读取历史
    print("\n=== 模拟重启后读取历史 ===")
    # 创建新的会话管理器实例模拟重启
    from app.memory.conversation import ConversationManager
    new_manager = ConversationManager()
    restart_history = new_manager.get_history(session_id)
    
    print("重启后读取的历史:")
    for i, msg in enumerate(restart_history):
        role = "用户" if msg["role"] == "user" else "助手"
        print(f"{i+1}. {role}: {msg['content']}")
    
    # 验证历史是否一致
    if history == restart_history:
        print("\n✅ 测试通过：重启后历史保持一致")
    else:
        print("\n❌ 测试失败：重启后历史不一致")
    
    # 清理测试数据
    conversation_manager.clear_session(session_id)
    print("\n测试完成，已清理测试数据")

if __name__ == "__main__":
    test_continuous_conversation()
