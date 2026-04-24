#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
娴嬭瘯棰勭害淇濆瓨鍜岃幏鍙栧姛鑳?"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from app.appointment.register_service import register_service
from app.state import MedicalState
from app.appointment.register_agent import RegisterAgent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_save_and_get_appointment():
    """娴嬭瘯淇濆瓨鍜岃幏鍙栭绾﹀姛鑳?""
    print("=== 娴嬭瘯棰勭害淇濆瓨鍜岃幏鍙栧姛鑳?===")
    
    # 浣跨敤涓€涓祴璇曚細璇滻D
    test_session_id = "test_user_001"
    test_appointments_file = Path("sessions") / f"{test_session_id}_appointments.json"
    if test_appointments_file.exists():
        test_appointments_file.unlink()
    
    # 鍑嗗棰勭害鏁版嵁
    appointment_data = {
        "patient_name": "寮犱笁",
        "phone": "13800000000",
        "department": {"name": "鍐呯"},
        "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),  # 鏄庡ぉ
        "time": "14:00-15:00",  # 涓嬪崍涓ょ偣
        "doctor": "寮犲尰鐢?
    }
    
    print(f"鍑嗗淇濆瓨棰勭害鏁版嵁: {appointment_data}")
    
    # 淇濆瓨棰勭害
    save_result = register_service.save_appointment(test_session_id, appointment_data)
    print(f"淇濆瓨缁撴灉: {save_result}")
    
    if save_result["success"]:
        print("鉁?棰勭害淇濆瓨鎴愬姛")
        
        # 鑾峰彇棰勭害
        appointments = register_service.get_appointments(test_session_id)
        print(f"鑾峰彇鍒扮殑棰勭害鏁伴噺: {len(appointments)}")
        
        if appointments:
            print("鉁?鎴愬姛鑾峰彇棰勭害:")
            for apt in appointments:
                print(f"  - 棰勭害鍙? {apt['id']}")
                print(f"  - 濮撳悕: {apt['patient_name']}")
                print(f"  - 鎵嬫満: {apt['phone']}")
                print(f"  - 绉戝: {apt['department']}")
                print(f"  - 鏃ユ湡: {apt['date']}")
                print(f"  - 鏃堕棿: {apt['time']}")
                print(f"  - 鐘舵€? {apt['status']}")
                print(f"  - 鍒涘缓鏃堕棿: {apt['created_at']}")
        else:
            print("鉁?鏈兘鑾峰彇鍒伴绾?)
    else:
        print(f"鉁?棰勭害淇濆瓨澶辫触: {save_result.get('message')}")
    
    # 妫€鏌essions鐩綍鍜屾枃浠?    sessions_dir = Path("sessions")
    if sessions_dir.exists():
        print(f"\nsessions鐩綍瀛樺湪锛屽寘鍚枃浠?")
        for file in sessions_dir.iterdir():
            print(f"  - {file.name}")
            
        # 妫€鏌ョ壒瀹氱殑棰勭害鏂囦欢
        appointment_file = sessions_dir / f"{test_session_id}_appointments.json"
        if appointment_file.exists():
            print(f"\n{appointment_file.name} 鏂囦欢瀛樺湪")
            with open(appointment_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                print(f"鏂囦欢鍐呭: {content}")
        else:
            print(f"\n{appointment_file.name} 鏂囦欢涓嶅瓨鍦?)
    else:
        print("\nsessions鐩綍涓嶅瓨鍦?)


def test_register_agent_flow():
    """娴嬭瘯瀹屾暣鐨勬敞鍐屼唬鐞嗘祦绋?""
    print("\n=== 娴嬭瘯瀹屾暣娉ㄥ唽浠ｇ悊娴佺▼ ===")
    
    # 鍒涘缓鐘舵€佸璞?    state = MedicalState({
        "messages": ["甯垜鎸傛槑澶╀笅鍗堜袱鐐圭殑鍐呯鐨勫彿"],
        "intent": "INT-03",  # 棰勭害鎰忓浘
        "conversation_id": "test_user_002"
    })
    test_appointments_file = Path("sessions") / "test_user_002_appointments.json"
    if test_appointments_file.exists():
        test_appointments_file.unlink()
    
    # 鍒涘缓娉ㄥ唽浠ｇ悊
    agent = RegisterAgent()
    
    # 妯℃嫙鐢ㄦ埛浜や簰娴佺▼
    print("姝ラ1: 寮€濮嬮绾?)
    state = agent.start_registration(state)
    print(f"绯荤粺鎻愮ず: {state['final_answer']}")
    
    # 鐢ㄦ埛杈撳叆濮撳悕
    print("\n姝ラ2: 杈撳叆濮撳悕")
    state["messages"].append("寮犱笁")
    state["appointment_data"]["patient_name"] = "寮犱笁"
    state["appointment_step"] = "phone"
    state["final_answer"] = "璇锋彁渚涙偍鐨勬墜鏈哄彿锛?1浣嶆暟瀛楋級"
    print(f"绯荤粺鎻愮ず: {state['final_answer']}")
    
    # 鐢ㄦ埛杈撳叆鎵嬫満鍙?    print("\n姝ラ3: 杈撳叆鎵嬫満鍙?)
    state["messages"].append("13800000000")
    state["appointment_data"]["phone"] = "13800000000"
    state["appointment_step"] = "department"
    print("绯荤粺鎻愮ず: 璇烽€夋嫨鎮ㄨ鎸傚彿鐨勭瀹?)
    
    # 鐢ㄦ埛閫夋嫨绉戝
    print("\n姝ラ4: 閫夋嫨绉戝")
    state["messages"].append("鍐呯")
    from app.appointment.mock_data import get_departments
    departments = get_departments()
    for dept in departments:
        if dept['name'] == '鍐呯':
            state["appointment_data"]["department"] = dept
            break
    state["appointment_step"] = "date"
    print("绯荤粺鎻愮ず: 璇烽€夋嫨鎮ㄨ棰勭害鐨勬棩鏈?)
    
    # 鐢ㄦ埛閫夋嫨鏃ユ湡
    print("\n姝ラ5: 閫夋嫨鏃ユ湡")
    tomorrow = datetime.now() + timedelta(days=2)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    state["messages"].append("鏄庡ぉ")
    state["appointment_data"]["date"] = tomorrow_str
    state["appointment_step"] = "time"
    print("绯荤粺鎻愮ず: 璇烽€夋嫨鎮ㄨ棰勭害鐨勬椂闂存")
    
    # 鐢ㄦ埛閫夋嫨鏃堕棿
    print("\n姝ラ6: 閫夋嫨鏃堕棿")
    state["messages"].append("涓嬪崍涓ょ偣")
    state["appointment_data"]["time"] = "15:00-16:00"
    state["appointment_step"] = "confirm"
    print(f"绯荤粺鎻愮ず: {agent._generate_confirmation(state['appointment_data'])}")
    
    # 鐢ㄦ埛纭棰勭害
    print("\n姝ラ7: 纭棰勭害")
    state["messages"].append("纭")
    # 杩欓噷妯℃嫙璋冪敤run鏂规硶鐨勭‘璁ら儴鍒?    save_result = agent.register_service.save_appointment(
        state.get("conversation_id", "default"),
        state["appointment_data"]
    )
    
    if save_result.get("success", False):
        appointment = save_result.get("appointment", {})
        state["final_answer"] = f"棰勭害鎴愬姛锛佸彲鍦?鎴戠殑棰勭害'涓煡鐪媆n\n棰勭害淇℃伅锛歕n鈥?濮撳悕锛歿appointment.get('patient_name', '')}\n鈥?鎵嬫満鍙凤細{appointment.get('phone', '')}\n鈥?绉戝锛歿appointment.get('department', '')}\n鈥?鍖荤敓锛歿appointment.get('doctor', '')}\n鈥?鏃ユ湡锛歿appointment.get('date', '')}\n鈥?鏃堕棿锛歿appointment.get('time', '')}\n\n棰勭害鍙凤細{appointment.get('id', '')}"
        state["appointment_info"] = save_result
        print(f"绯荤粺鎻愮ず: {state['final_answer']}")
        
        # 楠岃瘉棰勭害鏄惁宸蹭繚瀛?        saved_appointments = agent.register_service.get_appointments(state.get("conversation_id", "default"))
        print(f"楠岃瘉: 璇ヤ細璇濈幇鍦ㄦ湁 {len(saved_appointments)} 鏉￠绾﹁褰?)
    else:
        print(f"棰勭害澶辫触: {save_result.get('message', '鏈煡閿欒')}")


if __name__ == "__main__":
    test_save_and_get_appointment()
    test_register_agent_flow()
    
    print("\n=== 娴嬭瘯瀹屾垚 ===")
    print("濡傛灉娴嬭瘯鏄剧ず棰勭害淇濆瓨鎴愬姛浣?鎴戠殑棰勭害'涓湅涓嶅埌锛?)
    print("鍙兘鏄墠绔樉绀烘垨浼氳瘽ID涓嶅尮閰嶇殑闂銆?)

