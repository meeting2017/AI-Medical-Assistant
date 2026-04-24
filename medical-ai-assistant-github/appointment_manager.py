#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
预约管理工具
用于管理预约科室和取消预约操作
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from app.appointment.register_service import register_service
from app.appointment.mock_data import get_departments, get_doctors_by_department


def list_appointments(session_id):
    """列出指定会话的所有预约"""
    print(f"\n=== 会话 {session_id} 的预约列表 ===")
    appointments = register_service.get_appointments(session_id)
    
    if not appointments:
        print("没有找到预约记录")
        return
    
    for apt in appointments:
        status_text = "已预约" if apt["status"] == "confirmed" else "已取消"
        print(f"\n预约号: {apt['id']}")
        print(f"姓名: {apt['patient_name']}")
        print(f"手机号: {apt['phone']}")
        print(f"科室: {apt['department']}")
        print(f"医生: {apt['doctor']}")
        print(f"日期: {apt['date']}")
        print(f"时间: {apt['time']}")
        print(f"状态: {status_text}")
        print(f"创建时间: {apt['created_at']}")
        if apt.get('cancelled_at'):
            print(f"取消时间: {apt['cancelled_at']}")


def cancel_appointment(session_id, appointment_id):
    """取消指定预约"""
    print(f"\n=== 取消预约 {appointment_id} ===")
    result = register_service.cancel_appointment(session_id, appointment_id)
    
    if result.get("success", False):
        print(f"成功: {result.get('message')}")
    else:
        print(f"失败: {result.get('message')}")


def list_departments():
    """列出所有科室"""
    print("\n=== 科室列表 ===")
    departments = get_departments()
    
    for dept in departments:
        print(f"\n科室ID: {dept['id']}")
        print(f"科室名称: {dept['name']}")
        print(f"科室描述: {dept['description']}")
        
        # 列出该科室的医生
        doctors = get_doctors_by_department(dept['id'])
        if doctors:
            print("\n  医生列表:")
            for doc in doctors:
                print(f"  - {doc['name']} ({doc['title']}, {doc['specialty']})")


def check_session_files():
    """检查会话文件"""
    sessions_dir = Path("sessions")
    print("\n=== 会话文件检查 ===")
    
    if not sessions_dir.exists():
        print("sessions目录不存在")
        return
    
    files = list(sessions_dir.iterdir())
    if not files:
        print("sessions目录为空")
        return
    
    print(f"找到 {len(files)} 个会话文件:")
    for file in files:
        print(f"- {file.name}")
        
        # 尝试读取文件内容
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                print(f"  包含 {len(content)} 条预约记录")
        except Exception as e:
            print(f"  读取失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="预约管理工具")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出预约命令
    list_parser = subparsers.add_parser("list", help="列出预约")
    list_parser.add_argument("session_id", help="会话ID")
    
    # 取消预约命令
    cancel_parser = subparsers.add_parser("cancel", help="取消预约")
    cancel_parser.add_argument("session_id", help="会话ID")
    cancel_parser.add_argument("appointment_id", help="预约号")
    
    # 列出科室命令
    dept_parser = subparsers.add_parser("departments", help="列出所有科室")
    
    # 检查会话文件命令
    check_parser = subparsers.add_parser("check", help="检查会话文件")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_appointments(args.session_id)
    elif args.command == "cancel":
        cancel_appointment(args.session_id, args.appointment_id)
    elif args.command == "departments":
        list_departments()
    elif args.command == "check":
        check_session_files()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
