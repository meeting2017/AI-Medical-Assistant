from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta
import re
from app.state import MedicalState
from app.llm.llm_factory import llm_factory
from app.llm.prompts import REGISTER_PROMPT, APPOINTMENT_PROMPT
from app.appointment.register_service import register_service
from app.appointment.mock_data import get_departments, get_time_slots, get_dates, get_doctors_by_department
from app.utils.logger import logger

class RegisterAgent:
    def __init__(self):
        self.llm = llm_factory.get_llm()
        self.prompt = REGISTER_PROMPT
        self.register_service = register_service

    @staticmethod
    def _doctor_name(doctor: Any) -> str:
        if isinstance(doctor, dict):
            return doctor.get("name", "张医生")
        if isinstance(doctor, str) and doctor.strip():
            return doctor
        return "张医生"
    def extract_name_and_phone(self, user_input: str) -> tuple:
        """从用户输入中提取姓名和手机号"""
        name = None
        phone = None

        phone_patterns = [
            r'1[3-9]\d{9}',
            r'手机号[是为：:\s]*(\d{11})',
            r'手机[是为：:\s]*(\d{11})',
            r'电话[是为：:\s]*(\d{11})',
            r'联系[是为：:\s]*(\d{11})',
            r'[（(](\d{11})[）)]',
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, user_input)
            if phone_match:
                phone = phone_match.group(1) if phone_match.lastindex else phone_match.group(0)
                if len(phone) == 11:
                    break

        name_patterns = [
            r'姓名[是为：:]\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'叫\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'名叫\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'患者[是为：:]\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'病人[是为：:]\s*([^\s，,。！!？?（）\(\)\-]+)',
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, user_input)
            if name_match:
                name = name_match.group(1)
                break

        if not name:
            cleaned_input = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', user_input)
            chinese_chars = re.findall(r'[\u4e00-\u9fa5]{2,4}', cleaned_input)
            excluded_patterns = [
                r'手机', r'电话', r'预约', r'挂号', r'内科', r'外科', r'儿科', r'妇产科',
                r'眼科', r'耳鼻喉', r'口腔', r'皮肤', r'神经', r'心血管',
                r'明天', r'今天', r'昨天', r'后天', r'下午', r'上午', r'早上',
                r'两点', r'三点', r'四点', r'五点', r'六点', r'七点', r'八点',
                r'帮我', r'我要', r'我想', r'请帮', r'患者', r'病人', r'姓名',
            ]
            for chars in chinese_chars:
                if len(chars) < 2:
                    continue
                if any(re.search(pat, chars) for pat in excluded_patterns):
                    continue
                name = chars
                break

        return name, phone

    def parse_natural_language_appointment(self, user_input: str) -> Optional[Dict[str, Any]]:
        """解析自然语言预约表达，如'帮我挂明天下午两点的内科'"""
        result = {}

        departments = get_departments()
        for dept in departments:
            if dept['name'] in user_input or dept['name'][:-1] in user_input:
                result['department'] = dept
                break

        date = self.parse_date(user_input)
        if date:
            result['date'] = date

        time = self.parse_time_slot(user_input)
        if time:
            result['time'] = time

        phone_patterns = [
            r'1[3-9]\d{9}',
            r'手机号[是为：:\s]*(\d{11})',
            r'手机[是为：:\s]*(\d{11})',
            r'电话[是为：:\s]*(\d{11})',
            r'联系[是为：:\s]*(\d{11})',
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, user_input)
            if phone_match:
                phone = phone_match.group(1) if phone_match.lastindex else phone_match.group(0)
                if len(phone) == 11:
                    result['phone'] = phone
                    break

        name_patterns = [
            r'姓名[是为：:]\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'叫\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'名叫\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'患者[是为：:]\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'病人[是为：:]\s*([^\s，,。！!？?（）\(\)\-]+)',
            r'^([\u4e00-\u9fa5]{2,4})[\s（）\(\)\-]',
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, user_input)
            if name_match:
                result['name'] = name_match.group(1)
                break

        if 'name' not in result:
            chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', user_input)
            for chars in chinese_chars:
                if 2 <= len(chars) <= 4 and chars not in ['内科', '外科', '儿科', '妇产科', '眼科', '耳鼻喉科', '口腔科', '皮肤科', '神经科', '心血管科', '明天下午', '今天', '明天', '后天', '昨天', '帮我', '我要', '我想', '请帮我', '预约', '挂号']:
                    result['name'] = chars
                    break

        return result if result else None

    def parse_date(self, user_input: str) -> Optional[str]:
        """解析日期输入"""
        dates = get_dates()

        date_patterns = [
            (r'(\d{4})[年-](\d{1,2})[月-](\d{1,2})[日号]?', '%Y-%m-%d'),
            (r'(\d{1,2})[月-](\d{1,2})[日号]?', None),
        ]

        for pattern, date_format in date_patterns:
            match = re.search(pattern, user_input)
            if match:
                if date_format:
                    try:
                        date_str = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
                        if date_str in dates:
                            return date_str
                    except:
                        pass
                else:
                    try:
                        month, day = int(match.group(1)), int(match.group(2))
                        today = datetime.now()
                        year = today.year
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        for d in dates:
                            if d.endswith(f"-{month:02d}-{day:02d}"):
                                return d
                    except:
                        pass

        for date in dates:
            if date in user_input:
                return date

        try:
            day_match = re.search(r'(\d+)号', user_input)
            if day_match:
                day = int(day_match.group(1))
                for date in dates:
                    if int(date.split('-')[2]) == day:
                        return date
        except:
            pass

        today = datetime.now().date()
        if "明天" in user_input or "明日" in user_input:
            tomorrow = today + timedelta(days=1)
            tomorrow_str = tomorrow.strftime("%Y-%m-%d")
            for d in dates:
                if d.startswith(tomorrow.strftime("%Y-%m-%d")):
                    return d
            if tomorrow_str in dates:
                return tomorrow_str
        elif "后天" in user_input:
            day_after = today + timedelta(days=2)
            day_after_str = day_after.strftime("%Y-%m-%d")
            for d in dates:
                if d.startswith(day_after.strftime("%Y-%m-%d")):
                    return d
            if day_after_str in dates:
                return day_after_str
        elif "大后天" in user_input:
            day_after = today + timedelta(days=3)
            day_after_str = day_after.strftime("%Y-%m-%d")
            for d in dates:
                if d.startswith(day_after.strftime("%Y-%m-%d")):
                    return d
            if day_after_str in dates:
                return day_after_str
        elif "今天" in user_input or "当日" in user_input:
            today_str = today.strftime("%Y-%m-%d")
            for d in dates:
                if d.startswith(today.strftime("%Y-%m-%d")):
                    return d
            if today_str in dates:
                return today_str
        elif "昨天" in user_input:
            yesterday = today - timedelta(days=1)
            yesterday_str = yesterday.strftime("%Y-%m-%d")
            for d in dates:
                if d.startswith(yesterday.strftime("%Y-%m-%d")):
                    return d
            if yesterday_str in dates:
                return yesterday_str

        return None

    def parse_time_slot(self, user_input: str) -> Optional[str]:
        """解析时间段输入"""
        time_slots = get_time_slots()

        for slot in time_slots:
            if slot["time"] in user_input:
                return slot["time"]

        time_mapping = {
            "8点": "08:00-09:00",
            "9点": "09:00-10:00",
            "10点": "10:00-11:00",
            "11点": "11:00-12:00",
            "12点": "11:00-12:00",
            "13点": "14:00-15:00",
            "14点": "14:00-15:00",
            "15点": "15:00-16:00",
            "16点": "16:00-17:00",
            "17点": "17:00-18:00",
            "18点": "17:00-18:00",
            "下午两点": "14:00-15:00",
            "下午三点": "15:00-16:00",
            "下午四点": "16:00-17:00",
            "下午五点": "17:00-18:00",
            "下午六点": "17:00-18:00",
            "上午八点": "08:00-09:00",
            "上午九点": "09:00-10:00",
            "上午十点": "10:00-11:00",
            "上午十一点": "11:00-12:00",
            "上午": "09:00-10:00",
            "下午": "14:00-15:00",
            "中午": "11:00-12:00",
            "早上": "08:00-09:00",
            " morning ": "09:00-10:00",
            " afternoon ": "14:00-15:00",
            "两点": "14:00-15:00",
            "三点": "15:00-16:00",
            "四点": "16:00-17:00",
            "五点": "17:00-18:00",
            "六点": "17:00-18:00",
            "两点半": "14:00-15:00",
            "三点半": "15:00-16:00",
            "四点半": "16:00-17:00",
            "五点半": "17:00-18:00",
            "六点半": "17:00-18:00",
        }

        sorted_keys = sorted(time_mapping.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key in user_input:
                return time_mapping[key]

        return None

    def parse_cancel_request(self, user_input: str) -> Optional[Dict[str, Any]]:
        """解析取消预约请求"""
        result = {}

        date = self.parse_date(user_input)
        if date:
            result['date'] = date

        departments = get_departments()
        for dept in departments:
            if dept['name'] in user_input or dept['name'][:-1] in user_input:
                result['department'] = dept['name']
                break

        apt_id_patterns = [
            r'预约号[是为：:\s]*([A-Z0-9]{6,})',
            r'号[是为：:\s]*([A-Z0-9]{6,})',
            r'APT\d+',
            r'[A-Z]{2,}\d{4,}',
        ]
        for pattern in apt_id_patterns:
            apt_id_match = re.search(pattern, user_input, re.IGNORECASE)
            if apt_id_match:
                result['appointment_id'] = apt_id_match.group().upper()
                break

        time_patterns = [
            r'((?:上午|下午|早上|晚上)\s*\d{1,2}[点时许])',
            r'(\d{1,2}[点时许]\d{0,2}分?)',
        ]
        for pattern in time_patterns:
            time_match = re.search(pattern, user_input)
            if time_match:
                result['time_desc'] = time_match.group()
                break

        return result if result else None

    def run(self, state: MedicalState) -> MedicalState:
        user_input = state["messages"][-1] if state["messages"] else ""
        conversation_id = state.get("conversation_id", "default")
        intent = state.get("intent", "")

        appointment_keywords = ["预约", "挂号", "想看", "要挂号", "帮挂号", "挂个号", "挂", "帮我挂", "看医生"]
        is_appointment_request = any(keyword in user_input for keyword in appointment_keywords)

        if user_input and ("查看预约" in user_input or "我的预约" in user_input or "查看我的预约" in user_input):
            appointments = self.register_service.get_appointments(conversation_id)
            if appointments:
                appointment_list = "您的预约记录：\n\n"
                for apt in appointments:
                    status_text = "已预约" if apt["status"] == "confirmed" else "已取消"
                    appointment_list += f"• 预约号：{apt['id']}\n  姓名：{apt['patient_name']}\n  科室：{apt['department']}\n  医生：{self._doctor_name(apt.get('doctor'))}\n  日期：{apt['date']}\n  时间：{apt['time']}\n  状态：{status_text}\n\n"
                state["final_answer"] = appointment_list
                state["appointments"] = appointments
            else:
                state["final_answer"] = "您暂时没有预约记录。"
                state["appointments"] = []
            return state

        if intent == "INT-07" or (user_input and "取消预约" in user_input):
            parsed = self.parse_cancel_request(user_input)

            if parsed and 'appointment_id' in parsed:
                apt_id = parsed['appointment_id']
                cancel_result = self.register_service.cancel_appointment(conversation_id, apt_id)
                if cancel_result.get("success", False):
                    state["final_answer"] = cancel_result.get("message", "预约已成功取消")
                    appointments = self.register_service.get_appointments(conversation_id)
                    state["appointments"] = appointments
                else:
                    state["final_answer"] = cancel_result.get("message", "取消预约失败")
            else:
                appointments = self.register_service.get_appointments(conversation_id)
                if appointments:
                    confirm_appointments = [apt for apt in appointments if apt["status"] == "confirmed"]
                    if len(confirm_appointments) == 1:
                        apt_id = confirm_appointments[0]['id']
                        cancel_result = self.register_service.cancel_appointment(conversation_id, apt_id)
                        if cancel_result.get("success", False):
                            state["final_answer"] = f"已为您取消 {confirm_appointments[0]['date']} {confirm_appointments[0]['time']} 的预约"
                            appointments = self.register_service.get_appointments(conversation_id)
                            state["appointments"] = appointments
                        else:
                            state["final_answer"] = cancel_result.get("message", "取消预约失败")
                    elif len(confirm_appointments) > 1:
                        appointment_list = "请告诉我想取消哪个预约（可以回复预约号或日期时间）：\n\n"
                        for apt in confirm_appointments:
                            appointment_list += f"• 预约号：{apt['id']}\n  科室：{apt['department']}\n  日期：{apt['date']}\n  时间：{apt['time']}\n\n"
                        state["final_answer"] = appointment_list
                    else:
                        state["final_answer"] = "您暂时没有可取消的预约记录。"
                else:
                    state["final_answer"] = "您暂时没有可取消的预约记录。"
            return state

        if is_appointment_request and "appointment_step" not in state:
            parsed_info = self.parse_natural_language_appointment(user_input)

            if parsed_info:
                state["appointment_data"] = {}
                missing_fields = []

                if 'name' not in parsed_info:
                    missing_fields.append("姓名")
                else:
                    state["appointment_data"]["patient_name"] = parsed_info['name']

                if 'phone' not in parsed_info:
                    missing_fields.append("手机号")
                else:
                    state["appointment_data"]["phone"] = parsed_info['phone']

                if 'department' not in parsed_info:
                    missing_fields.append("科室")
                else:
                    state["appointment_data"]["department"] = parsed_info['department']

                if 'date' not in parsed_info:
                    missing_fields.append("日期")
                else:
                    state["appointment_data"]["date"] = parsed_info['date']

                if 'time' not in parsed_info:
                    missing_fields.append("时间段")
                else:
                    state["appointment_data"]["time"] = parsed_info['time']

                if not missing_fields:
                    department_id = state["appointment_data"]["department"]["id"]
                    doctors = get_doctors_by_department(department_id)
                    if doctors:
                        state["appointment_data"]["doctor"] = doctors[0]
                    else:
                        state["appointment_data"]["doctor"] = {"name": "张医生"}

                    state["appointment_step"] = "confirm"
                    state["final_answer"] = self._generate_confirmation(state["appointment_data"])
                    return state
                else:
                    missing_str = "、".join(missing_fields)
                    state["final_answer"] = f"好的，我来帮您预约挂号。请您提供以下信息：\n\n缺少的信息：{missing_str}\n\n请告诉我您的{missing_str[0]}（如果已经提供部分信息，请一并告诉我）"
                    state["appointment_step"] = "name"
                    return state
            else:
                state["appointment_data"] = {}
                state["appointment_step"] = "name"
                state["final_answer"] = "好的，我来帮您预约挂号。请告诉我您的姓名"
                return state

        if "appointment_data" not in state:
            state["appointment_data"] = {}

        if "appointment_step" not in state:
            state["appointment_step"] = "name"
        
        try:
            step = state["appointment_step"]
            appointment_data = state["appointment_data"]

            if step == "name":
                user_input_stripped = user_input.strip() if user_input else ""

                if user_input_stripped and ("确认" in user_input_stripped or "是" in user_input_stripped):
                    if "department" in appointment_data and "date" in appointment_data and "time" in appointment_data:
                        state["appointment_step"] = "confirm"
                        department_id = appointment_data["department"]["id"]
                        doctors = get_doctors_by_department(department_id)
                        if doctors:
                            appointment_data["doctor"] = doctors[0]
                        else:
                            appointment_data["doctor"] = {"name": "张医生"}
                elif user_input_stripped:
                    name, phone = self.extract_name_and_phone(user_input)

                    if phone:
                        appointment_data["phone"] = phone
                    if name:
                        appointment_data["patient_name"] = name

                    if name and phone:
                        if "department" in appointment_data and "date" in appointment_data and "time" in appointment_data:
                            state["appointment_step"] = "confirm"
                            department_id = appointment_data["department"]["id"]
                            doctors = get_doctors_by_department(department_id)
                            if doctors:
                                appointment_data["doctor"] = doctors[0]
                            else:
                                appointment_data["doctor"] = {"name": "张医生"}
                            state["final_answer"] = self._generate_confirmation(appointment_data)
                        elif "department" not in appointment_data:
                            state["appointment_step"] = "department"
                            departments = get_departments()
                            department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                            state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
                        elif "date" not in appointment_data:
                            state["appointment_step"] = "date"
                            dates = get_dates()
                            date_list = "\n".join([f"• {date}" for date in dates])
                            state["final_answer"] = f"请选择您要预约的日期：\n{date_list}"
                        elif "time" not in appointment_data:
                            state["appointment_step"] = "time"
                            time_slots = get_time_slots()
                            time_list = "\n".join([f"• {slot['time']}" for slot in time_slots])
                            state["final_answer"] = f"请选择您要预约的时间段：\n{time_list}"
                        else:
                            state["appointment_step"] = "confirm"
                            department_id = appointment_data["department"]["id"]
                            doctors = get_doctors_by_department(department_id)
                            if doctors:
                                appointment_data["doctor"] = doctors[0]
                            else:
                                appointment_data["doctor"] = {"name": "张医生"}
                            state["final_answer"] = self._generate_confirmation(appointment_data)
                    elif phone:
                        if "patient_name" not in appointment_data:
                            state["appointment_step"] = "name_confirm"
                            state["final_answer"] = "请告诉我您的姓名"
                        elif "department" not in appointment_data:
                            state["appointment_step"] = "department"
                            departments = get_departments()
                            department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                            state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
                        else:
                            state["appointment_step"] = "department"
                            departments = get_departments()
                            department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                            state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
                    elif name:
                        if "phone" not in appointment_data:
                            state["appointment_step"] = "phone"
                            state["final_answer"] = "请提供您的手机号（11位数字）"
                        elif "department" not in appointment_data:
                            state["appointment_step"] = "department"
                            departments = get_departments()
                            department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                            state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
                        else:
                            state["appointment_step"] = "department"
                            departments = get_departments()
                            department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                            state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
                    else:
                        state["final_answer"] = "请告诉我您的姓名"
                else:
                    state["final_answer"] = "请告诉我您的姓名"

            elif step == "name_confirm":
                user_input_stripped = user_input.strip() if user_input else ""
                if user_input_stripped:
                    appointment_data["patient_name"] = user_input_stripped
                    state["appointment_step"] = "confirm"
                    department_id = appointment_data["department"]["id"]
                    doctors = get_doctors_by_department(department_id)
                    if doctors:
                        appointment_data["doctor"] = doctors[0]
                    else:
                        appointment_data["doctor"] = {"name": "张医生"}
                    state["final_answer"] = self._generate_confirmation(appointment_data)
                else:
                    state["final_answer"] = "请告诉我您的姓名"
            
            elif step == "phone":
                # 第二步：收集手机号
                if user_input and user_input.strip():
                    phone = user_input.strip()
                    # 验证手机号格式
                    if len(phone) == 11 and phone.isdigit():
                        appointment_data["phone"] = phone
                        state["appointment_step"] = "department"
                        # 生成科室列表
                        departments = get_departments()
                        department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                        state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
                    else:
                        state["final_answer"] = "请提供有效的11位数字手机号"
                else:
                    state["final_answer"] = "请提供您的手机号（11位数字）"
            
            elif step == "department":
                # 第三步：选择科室
                if user_input and user_input.strip():
                    department_name = user_input.strip()
                    # 查找科室
                    departments = get_departments()
                    selected_dept = None
                    for dept in departments:
                        if dept['name'] == department_name:
                            selected_dept = dept
                            break
                    
                    if selected_dept:
                        appointment_data["department"] = selected_dept
                        state["appointment_step"] = "date"
                        # 生成日期列表
                        dates = get_dates()
                        date_list = "\n".join([f"• {date}" for date in dates])
                        state["final_answer"] = f"请选择您要预约的日期：\n{date_list}"
                    else:
                        departments = get_departments()
                        department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                        state["final_answer"] = f"请从以下科室中选择：\n{department_list}"
                else:
                    departments = get_departments()
                    department_list = "\n".join([f"• {dept['name']}: {dept['description']}" for dept in departments])
                    state["final_answer"] = f"请选择您要挂号的科室：\n{department_list}"
            
            elif step == "date":
                # 第四步：选择日期
                if user_input and user_input.strip():
                    parsed_date = self.parse_date(user_input)
                    if parsed_date:
                        appointment_data["date"] = parsed_date
                        state["appointment_step"] = "time"
                        # 生成时间段列表
                        time_slots = get_time_slots()
                        time_list = "\n".join([f"• {slot['time']}" for slot in time_slots])
                        state["final_answer"] = f"请选择您要预约的时间段：\n{time_list}"
                        # 添加时间段选项到状态，供前端使用
                        state["time_slots"] = [slot["time"] for slot in time_slots]
                    else:
                        dates = get_dates()
                        date_list = "\n".join([f"• {date}" for date in dates])
                        state["final_answer"] = f"请从以下日期中选择：\n{date_list}"
                        # 添加日期选项到状态，供前端使用
                        state["dates"] = dates
                else:
                    dates = get_dates()
                    date_list = "\n".join([f"• {date}" for date in dates])
                    state["final_answer"] = f"请选择您要预约的日期：\n{date_list}"
                    # 添加日期选项到状态，供前端使用
                    state["dates"] = dates
            
            elif step == "time":
                # 第五步：选择时间段
                if user_input and user_input.strip():
                    parsed_time = self.parse_time_slot(user_input)
                    if parsed_time:
                        appointment_data["time"] = parsed_time
                        state["appointment_step"] = "confirm"
                        # 选择医生（默认选择对应科室的第一个医生）
                        department_id = appointment_data["department"]["id"]
                        doctors = get_doctors_by_department(department_id)
                        if doctors:
                            appointment_data["doctor"] = doctors[0]
                        else:
                            appointment_data["doctor"] = {"name": "张医生"}
                        # 生成确认信息
                        state["final_answer"] = self._generate_confirmation(appointment_data)
                    else:
                        time_slots = get_time_slots()
                        time_list = "\n".join([f"• {slot['time']}" for slot in time_slots])
                        state["final_answer"] = f"请从以下时间段中选择：\n{time_list}"
                else:
                    time_slots = get_time_slots()
                    time_list = "\n".join([f"• {slot['time']}" for slot in time_slots])
                    state["final_answer"] = f"请选择您要预约的时间段：\n{time_list}"
            
            elif step == "confirm":
                # 第六步：确认预约
                if user_input and ("确认" in user_input or "是" in user_input):
                    # 调用服务保存预约
                    save_result = self.register_service.save_appointment(
                        conversation_id,
                        appointment_data
                    )

                    if save_result.get("success", False):
                        appointment = save_result.get("appointment", {})
                        # 预约成功后，更新状态中的预约列表
                        appointments = self.register_service.get_appointments(conversation_id)
                        state["appointments"] = appointments
                        state["final_answer"] = f"预约成功！可在'我的预约'中查看\n\n预约信息：\n• 姓名：{appointment.get('patient_name', '')}\n• 手机号：{appointment.get('phone', '')}\n• 科室：{appointment.get('department', '')}\n• 医生：{self._doctor_name(appointment.get('doctor'))}\n• 日期：{appointment.get('date', '')}\n• 时间：{appointment.get('time', '')}\n\n预约号：{appointment.get('id', '')}"
                        state["appointment_info"] = save_result
                        # 保存最后一次预约信息
                        state["last_appointment_id"] = appointment.get("id", "")
                        # 清除预约状态，避免影响后续对话
                        state["appointment_step"] = None
                        state["appointment_data"] = {}
                    else:
                        # 保存失败（可能是重复预约）
                        state["final_answer"] = save_result.get("message", "预约失败，请稍后重试")
                        state["appointment_step"] = "date"
                else:
                    state["final_answer"] = "预约已取消。如果您需要重新预约，请告诉我。"
                    state["appointment_step"] = "name"
                    state["appointment_data"] = {}
            
            logger.info(f"Appointment step: {state['appointment_step']}, data: {state['appointment_data']}")
            
        except Exception as e:
            logger.error(f"Error in register agent: {e}")
            state["final_answer"] = "预约过程中出现问题，请稍后重试"
            state["appointment_data"] = {}
            state["appointment_step"] = "name"
        
        return state
    
    def _generate_confirmation(self, appointment_data: Dict[str, Any]) -> str:
        """生成预约确认信息"""
        name = appointment_data.get("patient_name", "")
        phone = appointment_data.get("phone", "")
        department = appointment_data.get("department", {})
        dept_name = department.get("name", "")
        date = appointment_data.get("date", "")
        time = appointment_data.get("time", "")
        doctor_name = self._doctor_name(appointment_data.get("doctor"))
        
        confirmation = f"\n预约确认信息：\n"
        confirmation += f"姓名：{name}\n"
        confirmation += f"手机号：{phone}\n"
        confirmation += f"科室：{dept_name}\n"
        confirmation += f"日期：{date}\n"
        confirmation += f"时间：{time}\n"
        confirmation += f"医生：{doctor_name}\n\n"
        confirmation += "请确认以上信息是否正确？回复‘确认’完成预约，或回复其他内容取消预约。"
        
        return confirmation
    
    def start_registration(self, state: MedicalState) -> MedicalState:
        """开始预约流程"""
        state["appointment_data"] = {}
        state["appointment_step"] = "name"
        state["final_answer"] = "请告诉我您的姓名"
        logger.info("Started registration process")
        return state
    
    def reset_registration(self, conversation_id: str):
        """重置预约流程"""
        self.register_service.reset_registration(conversation_id)

register_agent = RegisterAgent()
