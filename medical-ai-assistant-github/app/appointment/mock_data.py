from typing import List, Dict, Any
from datetime import datetime, timedelta

DEPARTMENTS = [
    {"id": "D001", "name": "内科", "description": "诊治各种内科疾病"},
    {"id": "D002", "name": "外科", "description": "诊治各种外科疾病"},
    {"id": "D003", "name": "儿科", "description": "诊治儿童疾病"},
    {"id": "D004", "name": "妇产科", "description": "诊治妇产科疾病"},
    {"id": "D005", "name": "眼科", "description": "诊治眼科疾病"},
    {"id": "D006", "name": "耳鼻喉科", "description": "诊治耳鼻喉疾病"},
    {"id": "D007", "name": "口腔科", "description": "诊治口腔疾病"},
    {"id": "D008", "name": "皮肤科", "description": "诊治皮肤疾病"},
    {"id": "D009", "name": "神经科", "description": "诊治神经系统疾病"},
    {"id": "D010", "name": "心血管科", "description": "诊治心血管疾病"}
]

DOCTORS = [
    {"id": "DR001", "name": "张医生", "department": "D001", "title": "主任医师", "specialty": "消化内科"},
    {"id": "DR002", "name": "李医生", "department": "D001", "title": "副主任医师", "specialty": "呼吸内科"},
    {"id": "DR003", "name": "王医生", "department": "D002", "title": "主任医师", "specialty": "普外科"},
    {"id": "DR004", "name": "赵医生", "department": "D002", "title": "副主任医师", "specialty": "骨科"},
    {"id": "DR005", "name": "陈医生", "department": "D003", "title": "主任医师", "specialty": "小儿内科"},
    {"id": "DR006", "name": "刘医生", "department": "D004", "title": "副主任医师", "specialty": "产科"},
    {"id": "DR007", "name": "孙医生", "department": "D005", "title": "主任医师", "specialty": "眼科疾病"},
    {"id": "DR008", "name": "周医生", "department": "D006", "title": "副主任医师", "specialty": "耳鼻喉疾病"},
    {"id": "DR009", "name": "吴医生", "department": "D007", "title": "主任医师", "specialty": "口腔疾病"},
    {"id": "DR010", "name": "郑医生", "department": "D008", "title": "副主任医师", "specialty": "皮肤疾病"},
    {"id": "DR011", "name": "冯医生", "department": "D009", "title": "主任医师", "specialty": "神经内科"},
    {"id": "DR012", "name": "韩医生", "department": "D010", "title": "副主任医师", "specialty": "心血管疾病"}
]

TIME_SLOTS = [
    {"id": "T001", "period": "上午", "time": "08:00-09:00"},
    {"id": "T002", "period": "上午", "time": "09:00-10:00"},
    {"id": "T003", "period": "上午", "time": "10:00-11:00"},
    {"id": "T004", "period": "上午", "time": "11:00-12:00"},
    {"id": "T005", "period": "下午", "time": "14:00-15:00"},
    {"id": "T006", "period": "下午", "time": "15:00-16:00"},
    {"id": "T007", "period": "下午", "time": "16:00-17:00"},
    {"id": "T008", "period": "下午", "time": "17:00-18:00"}
]

# 动态生成未来7天的日期
def generate_dates():
    today = datetime.now()
    dates = []
    for i in range(7):
        date = today + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return dates

DATES = generate_dates()

APPOINTMENTS = []

def get_departments() -> List[Dict[str, Any]]:
    return DEPARTMENTS

def get_doctors_by_department(department_id: str) -> List[Dict[str, Any]]:
    return [doc for doc in DOCTORS if doc["department"] == department_id]

def get_doctor(doctor_id: str) -> Dict[str, Any]:
    for doc in DOCTORS:
        if doc["id"] == doctor_id:
            return doc
    return None

def get_time_slots() -> List[Dict[str, Any]]:
    return TIME_SLOTS

def get_dates() -> List[str]:
    return generate_dates()

def get_available_slots(doctor_id: str, date: str) -> List[Dict[str, Any]]:
    booked_slots = [apt["time_slot"] for apt in APPOINTMENTS 
                    if apt["doctor_id"] == doctor_id and apt["date"] == date]
    return [slot for slot in TIME_SLOTS if slot["id"] not in booked_slots]

def create_appointment(appointment: Dict[str, Any]) -> Dict[str, Any]:
    appointment["id"] = f"APT{len(APPOINTMENTS) + 1:04d}"
    appointment["status"] = "confirmed"
    APPOINTMENTS.append(appointment)
    return appointment

def get_appointments(patient_name: str = None) -> List[Dict[str, Any]]:
    if patient_name:
        return [apt for apt in APPOINTMENTS if apt["patient_name"] == patient_name]
    return APPOINTMENTS

def cancel_appointment(appointment_id: str) -> bool:
    for apt in APPOINTMENTS:
        if apt["id"] == appointment_id:
            apt["status"] = "cancelled"
            return True
    return False