from typing import Dict, Any, List, Optional
from app.appointment.schedule_service import schedule_service
from app.appointment.mock_data import get_doctors_by_department, get_doctor
from app.utils.logger import logger
import json
import os
from pathlib import Path
import datetime

class RegisterService:
    def __init__(self):
        self.schedule_service = schedule_service
        self.appointment_state = {}

    @staticmethod
    def _extract_doctor_name(doctor: Any) -> str:
        """Normalize doctor field to a displayable name."""
        if isinstance(doctor, dict):
            return doctor.get("name", "张医生")
        if isinstance(doctor, str) and doctor.strip():
            return doctor
        return "张医生"    
    def start_registration(self, conversation_id: str) -> Dict[str, Any]:
        self.appointment_state[conversation_id] = {
            "step": "department",
            "data": {}
        }
        departments = self.schedule_service.get_all_departments()
        
        dept_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
        
        return {
            "message": f"好的，我来帮您预约挂号。\n\n请选择您要挂号的科室：\n{dept_list}\n\n请告诉我您想挂哪个科室？",
            "step": "department",
            "options": [dept["name"] for dept in departments]
        }
    
    def process_input(self, conversation_id: str, user_input: str) -> Dict[str, Any]:
        if conversation_id not in self.appointment_state:
            return self.start_registration(conversation_id)
        
        state = self.appointment_state[conversation_id]
        step = state["step"]
        
        if step == "department":
            return self._process_department(conversation_id, user_input)
        elif step == "doctor":
            return self._process_doctor(conversation_id, user_input)
        elif step == "date":
            return self._process_date(conversation_id, user_input)
        elif step == "time":
            return self._process_time(conversation_id, user_input)
        elif step == "confirm":
            return self._process_confirm(conversation_id, user_input)
        else:
            return self.start_registration(conversation_id)
    
    def _process_department(self, conversation_id: str, user_input: str) -> Dict[str, Any]:
        state = self.appointment_state[conversation_id]
        department = self.schedule_service.get_department_by_name(user_input)
        
        if not department:
            return {
                "message": f"抱歉，没有找到科室：{user_input}。请重新选择科室。",
                "step": "department"
            }
        
        state["data"]["department"] = department
        state["step"] = "doctor"
        
        doctors = self.schedule_service.get_doctors_for_department(department["name"])
        
        if not doctors:
            return {
                "message": f"抱歉，{department['name']}暂时没有医生坐诊。请选择其他科室。",
                "step": "department"
            }
        
        doctor_list = "\n".join([f"• {doc['name']}（{doc['title']}，{doc['specialty']}）" for doc in doctors])
        
        return {
            "message": f"好的，您选择了{department['name']}。\n\n请选择医生：\n{doctor_list}\n\n请告诉我您想预约哪位医生？",
            "step": "doctor",
            "options": [doc["name"] for doc in doctors]
        }
    
    def _process_doctor(self, conversation_id: str, user_input: str) -> Dict[str, Any]:
        state = self.appointment_state[conversation_id]
        doctor = self.schedule_service.get_doctor_by_name(user_input)
        
        if not doctor:
            return {
                "message": f"抱歉，没有找到医生：{user_input}。请重新选择医生。",
                "step": "doctor"
            }
        
        state["data"]["doctor"] = doctor
        state["step"] = "date"
        
        dates = self.schedule_service.get_available_dates()
        date_list = "\n".join([f"• {date}" for date in dates])
        
        return {
            "message": f"好的，您选择了{doctor['name']}医生（{doctor['title']}）。\n\n请选择预约日期：\n{date_list}\n\n请告诉我您想预约哪一天？",
            "step": "date",
            "options": dates
        }
    
    def _process_date(self, conversation_id: str, user_input: str) -> Dict[str, Any]:
        state = self.appointment_state[conversation_id]
        
        state["data"]["date"] = user_input
        state["step"] = "time"
        
        doctor_name = state["data"]["doctor"]["name"]
        slots = self.schedule_service.get_available_time_slots(doctor_name, user_input)
        
        if not slots:
            return {
                "message": f"抱歉，{doctor_name}医生在{user_input}没有可预约的时间段。请选择其他日期。",
                "step": "date"
            }
        
        slot_list = "\n".join([f"• {slot['time']}" for slot in slots])
        state["data"]["available_slots"] = slots
        
        return {
            "message": f"好的，您选择了{user_input}。\n\n请选择预约时间段：\n{slot_list}\n\n请告诉我您想预约哪个时间段？",
            "step": "time",
            "options": [slot["time"] for slot in slots]
        }
    
    def _process_time(self, conversation_id: str, user_input: str) -> Dict[str, Any]:
        state = self.appointment_state[conversation_id]
        
        selected_slot = None
        for slot in state["data"]["available_slots"]:
            if user_input in slot["time"]:
                selected_slot = slot
                break
        
        if not selected_slot:
            return {
                "message": f"抱歉，没有找到时间段：{user_input}。请重新选择时间段。",
                "step": "time"
            }
        
        state["data"]["time_slot"] = selected_slot
        state["step"] = "confirm"
        
        summary = self._generate_summary(state["data"])
        
        return {
            "message": f"{summary}\n\n请确认以上信息是否正确？\n回复「确认」完成预约，或回复「取消」重新开始。",
            "step": "confirm",
            "options": ["确认", "取消"]
        }
    
    def _process_confirm(self, conversation_id: str, user_input: str) -> Dict[str, Any]:
        state = self.appointment_state[conversation_id]
        
        if "确认" not in user_input and "是" not in user_input:
            return self.start_registration(conversation_id)
        
        appointment_data = {
            "patient_name": state["data"].get("patient_name", "患者"),
            "doctor_id": state["data"]["doctor"]["id"],
            "date": state["data"]["date"],
            "time_slot": state["data"]["time_slot"]["id"],
            "contact_info": state["data"].get("contact_info", "未提供"),
            "symptoms": state["data"].get("symptoms", "")
        }
        
        result = self.schedule_service.book_appointment(appointment_data)
        
        if result["success"]:
            del self.appointment_state[conversation_id]
            return {
                "message": result["message"],
                "step": "completed",
                "appointment": result["appointment"]
            }
        else:
            return {
                "message": f"预约失败：{result['message']}",
                "step": "confirm"
            }
    
    def _generate_summary(self, data: Dict[str, Any]) -> str:
        summary = "请确认您的预约信息：\n\n"
        summary += f"科室：{data['department']['name']}\n"
        summary += f"医生：{data['doctor']['name']}（{data['doctor']['title']}）\n"
        summary += f"日期：{data['date']}\n"
        summary += f"时间：{data['time_slot']['time']}\n"
        return summary
    
    def reset_registration(self, conversation_id: str):
        if conversation_id in self.appointment_state:
            del self.appointment_state[conversation_id]
    
    def create_appointment(self, conversation_id: str, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建预约"""
        try:
            # 生成预约数据
            appointment = {
                "patient_name": appointment_data.get("patient_name", ""),
                "phone": appointment_data.get("phone", ""),
                "department": appointment_data.get("department", {}).get("name", ""),
                "doctor": "张医生",
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "time": "09:00-10:00",
                "status": "confirmed"
            }
            
            logger.info(f"Created appointment: {appointment}")
            
            return {
                "success": True,
                "appointment": appointment,
                "message": "预约成功"
            }
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return {
                "success": False,
                "message": "预约失败"
            }
    
    def check_duplicate_appointment(self, session_id: str, date: str, time: str) -> bool:
        """检查是否存在重复预约（同一session_id + 同一日期 + 同一时间段）"""
        try:
            # 预约文件路径
            sessions_dir = Path("sessions")
            appointment_file = sessions_dir / f"{session_id}_appointments.json"
            
            # 读取预约
            if not appointment_file.exists():
                return False
            
            with open(appointment_file, 'r', encoding='utf-8') as f:
                appointments = json.load(f)
                for appointment in appointments:
                    appointment["doctor"] = self._extract_doctor_name(appointment.get("doctor"))            
            # 检查是否存在重复预约（已确认的预约）
            for apt in appointments:
                if (apt["date"] == date and 
                    apt["time"] == time and 
                    apt["status"] == "confirmed"):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking duplicate appointment: {e}")
            return False
    
    def save_appointment(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存预约到文件"""
        try:
            # 检查重复预约
            date = data.get("date", "")
            time = data.get("time", "")
            
            if self.check_duplicate_appointment(session_id, date, time):
                return {
                    "success": False,
                    "message": "该时间段已被预约，请选择其他时间"
                }
            
            # 创建sessions目录
            sessions_dir = Path("sessions")
            sessions_dir.mkdir(exist_ok=True)
            
            # 预约文件路径
            appointment_file = sessions_dir / f"{session_id}_appointments.json"
            
            # 读取现有预约
            existing_appointments = []
            if appointment_file.exists():
                try:
                    with open(appointment_file, 'r', encoding='utf-8') as f:
                        existing_appointments = json.load(f)
                    for appointment in existing_appointments:
                        appointment["doctor"] = self._extract_doctor_name(appointment.get("doctor"))
                except:
                    existing_appointments = []
            
            # 生成预约ID
            appointment_id = f"APT{len(existing_appointments) + 1:04d}"
            
            # 添加新预约
            appointment = {
                "id": appointment_id,
                "patient_name": data.get("patient_name", ""),
                "phone": data.get("phone", ""),
                "department": data.get("department", {}).get("name", "") if isinstance(data.get("department"), dict) else data.get("department", ""),
                "doctor": self._extract_doctor_name(data.get("doctor")),
                "date": data.get("date", ""),
                "time": data.get("time", ""),
                "status": "confirmed",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            existing_appointments.append(appointment)
            
            # 保存到文件
            with open(appointment_file, 'w', encoding='utf-8') as f:
                json.dump(existing_appointments, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved appointment for session {session_id}: {appointment_id}")
            
            return {
                "success": True,
                "appointment": appointment,
                "message": "预约已保存"
            }
        except Exception as e:
            logger.error(f"Error saving appointment: {e}")
            return {
                "success": False,
                "message": "保存预约失败"
            }
    
    def get_appointments(self, session_id: str) -> List[Dict[str, Any]]:
        """获取指定session的所有预约（按时间倒序）"""
        try:
            # 预约文件路径
            sessions_dir = Path("sessions")
            appointment_file = sessions_dir / f"{session_id}_appointments.json"
            
            # 读取预约
            if appointment_file.exists():
                with open(appointment_file, 'r', encoding='utf-8') as f:
                    appointments = json.load(f)
                for appointment in appointments:
                    appointment["doctor"] = self._extract_doctor_name(appointment.get("doctor"))
                # 按创建时间倒序排列（最新的在前）
                appointments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return appointments
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            return []
    
    def cancel_appointment(self, session_id: str, appointment_id: str) -> Dict[str, Any]:
        """取消指定预约"""
        try:
            # 预约文件路径
            sessions_dir = Path("sessions")
            appointment_file = sessions_dir / f"{session_id}_appointments.json"
            
            # 读取预约
            if not appointment_file.exists():
                return {
                    "success": False,
                    "message": "预约记录不存在"
                }
            
            with open(appointment_file, 'r', encoding='utf-8') as f:
                appointments = json.load(f)
                for appointment in appointments:
                    appointment["doctor"] = self._extract_doctor_name(appointment.get("doctor"))            
            # 查找并取消预约
            found = False
            for apt in appointments:
                if apt["id"] == appointment_id:
                    apt["status"] = "cancelled"
                    apt["cancelled_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    found = True
                    break
            
            if not found:
                return {
                    "success": False,
                    "message": "预约记录不存在"
                }
            
            # 保存更新后的预约
            with open(appointment_file, 'w', encoding='utf-8') as f:
                json.dump(appointments, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cancelled appointment {appointment_id} for session {session_id}")
            
            return {
                "success": True,
                "message": "预约已成功取消"
            }
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return {
                "success": False,
                "message": "取消预约失败"
            }

register_service = RegisterService()
