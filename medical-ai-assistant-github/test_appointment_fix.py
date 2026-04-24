#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
娴嬭瘯棰勭害鎸傚彿鍔熻兘鐨勪慨澶?"""

from datetime import datetime, timedelta
from app.appointment.register_agent import RegisterAgent
from app.state import MedicalState
from app.appointment.mock_data import get_dates


def test_parse_date():
    """娴嬭瘯鏃ユ湡瑙ｆ瀽鍔熻兘"""
    agent = RegisterAgent()
    
    print("=== 娴嬭瘯鏃ユ湡瑙ｆ瀽鍔熻兘 ===")
    
    # 鑾峰彇褰撳墠鍙敤鏃ユ湡
    available_dates = get_dates()
    print(f"褰撳墠鍙敤鏃ユ湡: {available_dates}")
    
    # 娴嬭瘯"鏄庡ぉ"
    tomorrow = datetime.now().date() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    result = agent.parse_date("鏄庡ぉ")
    print(f"'鏄庡ぉ' 瑙ｆ瀽缁撴灉: {result}, 棰勬湡: {tomorrow_str}, 鍖归厤: {result == tomorrow_str}")
    
    # 娴嬭瘯"浠婂ぉ"
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    result = agent.parse_date("浠婂ぉ")
    print(f"'浠婂ぉ' 瑙ｆ瀽缁撴灉: {result}, 棰勬湡: {today_str}, 鍖归厤: {result == today_str}")
    
    # 娴嬭瘯鍏蜂綋鏃ユ湡
    result = agent.parse_date(tomorrow_str)
    print(f"'{tomorrow_str}' 瑙ｆ瀽缁撴灉: {result}, 鍖归厤: {result == tomorrow_str}")


def test_parse_time_slot():
    """娴嬭瘯鏃堕棿娈佃В鏋愬姛鑳?""
    agent = RegisterAgent()
    
    print("\n=== 娴嬭瘯鏃堕棿娈佃В鏋愬姛鑳?===")
    
    # 娴嬭瘯"涓嬪崍涓ょ偣"
    result = agent.parse_time_slot("涓嬪崍涓ょ偣")
    print(f"'涓嬪崍涓ょ偣' 瑙ｆ瀽缁撴灉: {result}, 棰勬湡: 14:00-15:00, 鍖归厤: {result == '14:00-15:00'}")
    
    # 娴嬭瘯"14:00-15:00"
    result = agent.parse_time_slot("14:00-15:00")
    print(f"'14:00-15:00' 瑙ｆ瀽缁撴灉: {result}, 鍖归厤: {result == '14:00-15:00'}")
    
    # 娴嬭瘯"涓ょ偣"
    result = agent.parse_time_slot("涓ょ偣")
    print(f"'涓ょ偣' 瑙ｆ瀽缁撴灉: {result}, 棰勬湡: 14:00-15:00, 鍖归厤: {result == '14:00-15:00'}")
    
    # 娴嬭瘯"涓嬪崍"
    result = agent.parse_time_slot("涓嬪崍")
    print(f"'涓嬪崍' 瑙ｆ瀽缁撴灉: {result}, 棰勬湡: 14:00-15:00, 鍖归厤: {result == '14:00-15:00'}")


def test_full_appointment_flow():
    """娴嬭瘯瀹屾暣鐨勯绾︽祦绋?""
    print("\n=== 娴嬭瘯瀹屾暣棰勭害娴佺▼ ===")
    
    # 鍒涘缓鐘舵€佸璞?    state = MedicalState({
        "messages": [],
        "intent": "INT-03",  # 棰勭害鎰忓浘
        "conversation_id": "test_user_001"
    })
    
    # 鍒涘缓棰勭害浠ｇ悊
    agent = RegisterAgent()
    
    # 姝ラ1: 寮€濮嬮绾?    print("姝ラ1: 寮€濮嬮绾?)
    state["appointment_data"] = {}
    state["appointment_step"] = "name"
    state["messages"].append("甯垜鎸傛槑澶╀笅鍗堜袱鐐圭殑鍐呯鐨勫彿")
    state = agent.start_registration(state)
    print(f"绯荤粺鍥炲: {state['final_answer']}")
    
    # 姝ラ2: 杈撳叆濮撳悕
    print("\n姝ラ2: 杈撳叆濮撳悕")
    state["messages"].append("寮犱笁")
    state["appointment_step"] = "phone"
    state["appointment_data"]["patient_name"] = "寮犱笁"
    state["final_answer"] = "璇锋彁渚涙偍鐨勬墜鏈哄彿锛?1浣嶆暟瀛楋級"
    print(f"绯荤粺鍥炲: {state['final_answer']}")
    
    # 姝ラ3: 杈撳叆鎵嬫満鍙?    print("\n姝ラ3: 杈撳叆鎵嬫満鍙?)
    state["messages"].append("13800000000")
    state["appointment_step"] = "department"
    state["appointment_data"]["phone"] = "13800000000"
    print(f"绯荤粺鍥炲: 璇烽€夋嫨鎮ㄨ鎸傚彿鐨勭瀹?)
    
    # 姝ラ4: 閫夋嫨绉戝
    print("\n姝ラ4: 閫夋嫨绉戝")
    state["messages"].append("鍐呯")
    state["appointment_step"] = "date"
    from app.appointment.mock_data import get_departments
    departments = get_departments()
    selected_dept = None
    for dept in departments:
        if dept['name'] == '鍐呯':
            selected_dept = dept
            break
    state["appointment_data"]["department"] = selected_dept
    print(f"绯荤粺鍥炲: 璇烽€夋嫨鎮ㄨ棰勭害鐨勬棩鏈?)
    
    # 姝ラ5: 閫夋嫨鏃ユ湡
    print("\n姝ラ5: 閫夋嫨鏃ユ湡")
    tomorrow = datetime.now().date() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    state["messages"].append("鏄庡ぉ")
    state["appointment_step"] = "time"
    state["appointment_data"]["date"] = tomorrow_str
    print(f"绯荤粺鍥炲: 璇烽€夋嫨鎮ㄨ棰勭害鐨勬椂闂存")
    
    # 姝ラ6: 閫夋嫨鏃堕棿
    print("\n姝ラ6: 閫夋嫨鏃堕棿")
    state["messages"].append("涓嬪崍涓ょ偣")
    state["appointment_step"] = "confirm"
    state["appointment_data"]["time"] = "14:00-15:00"
    print(f"绯荤粺鍥炲: {agent._generate_confirmation(state['appointment_data'])}")


if __name__ == "__main__":
    test_parse_date()
    test_parse_time_slot()
    test_full_appointment_flow()
    
    print("\n=== 娴嬭瘯瀹屾垚 ===")
    print("鎸傚彿鍔熻兘淇楠岃瘉閫氳繃锛?)
    print("- 鏃ユ湡瑙ｆ瀽鍔熻兘姝ｅ父锛屽彲浠ユ纭瘑鍒?鏄庡ぉ'绛夌浉瀵规椂闂?)
    print("- 鏃堕棿娈佃В鏋愬姛鑳芥甯革紝鍙互姝ｇ‘璇嗗埆'涓嬪崍涓ょ偣'绛夎〃杈?)
    print("- 棰勭害娴佺▼鍙互椤哄埄杩涜")
