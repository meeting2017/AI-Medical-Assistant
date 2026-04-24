from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.appointment.mock_data import (
    get_departments,
    get_doctors_by_department,
    get_doctor,
    get_time_slots,
    get_available_slots,
    create_appointment,
    get_appointments,
    cancel_appointment
)
from app.utils.logger import logger

class ScheduleService:
    def __init__(self):
        pass
    
    def get_all_departments(self) -> List[Dict[str, Any]]:
        departments = get_departments()
        logger.info(f"Retrieved {len(departments)} departments")
        return departments
    
    def get_department_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        departments = get_departments()
        for dept in departments:
            if name in dept["name"]:
                return dept
        return None
    
    def get_doctors_for_department(self, department_name: str) -> List[Dict[str, Any]]:
        dept = self.get_department_by_name(department_name)
        if not dept:
            logger.warning(f"Department not found: {department_name}")
            return []
        
        doctors = get_doctors_by_department(dept["id"])
        logger.info(f"Retrieved {len(doctors)} doctors for {department_name}")
        return doctors
    
    def get_doctor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        from app.appointment.mock_data import DOCTORS
        for doc in DOCTORS:
            if name in doc["name"]:
                return doc
        return None
    
    def get_available_dates(self, days: int = 7) -> List[str]:
        today = datetime.now()
        dates = []
        for i in range(days):
            date = today + timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        logger.info(f"Retrieved {len(dates)} available dates")
        return dates
    
    def get_available_time_slots(self, doctor_name: str, date: str) -> List[Dict[str, Any]]:
        doctor = self.get_doctor_by_name(doctor_name)
        if not doctor:
            logger.warning(f"Doctor not found: {doctor_name}")
            return []
        
        slots = get_available_slots(doctor["id"], date)
        logger.info(f"Retrieved {len(slots)} available slots for {doctor_name} on {date}")
        return slots
    
    def book_appointment(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["patient_name", "doctor_id", "date", "time_slot", "contact_info"]
        
        for field in required_fields:
            if field not in appointment_data:
                logger.error(f"Missing required field: {field}")
                return {"success": False, "message": f"缺少必要信息：{field}"}
        
        doctor = get_doctor(appointment_data["doctor_id"])
        if not doctor:
            logger.error(f"Doctor not found: {appointment_data['doctor_id']}")
            return {"success": False, "message": "医生信息不存在"}
        
        available_slots = get_available_slots(appointment_data["doctor_id"], appointment_data["date"])
        slot_ids = [slot["id"] for slot in available_slots]
        
        if appointment_data["time_slot"] not in slot_ids:
            logger.warning(f"Time slot not available: {appointment_data['time_slot']}")
            return {"success": False, "message": "该时间段已被预约"}
        
        appointment = create_appointment(appointment_data)
        logger.info(f"Appointment created: {appointment['id']}")
        
        return {
            "success": True,
            "appointment": appointment,
            "message": f"预约成功！预约号：{appointment['id']}"
        }
    
    def cancel_appointment(self, appointment_id: str) -> Dict[str, Any]:
        success = cancel_appointment(appointment_id)
        if success:
            logger.info(f"Appointment cancelled: {appointment_id}")
            return {"success": True, "message": "预约已取消"}
        else:
            logger.warning(f"Appointment not found: {appointment_id}")
            return {"success": False, "message": "预约信息不存在"}
    
    def get_patient_appointments(self, patient_name: str) -> List[Dict[str, Any]]:
        appointments = get_appointments(patient_name)
        logger.info(f"Retrieved {len(appointments)} appointments for {patient_name}")
        return appointments

schedule_service = ScheduleService()