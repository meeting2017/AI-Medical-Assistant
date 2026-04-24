import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from app.config.settings import settings
from app.utils.logger import logger


class ConversationManager:
    def __init__(self):
        self.session_dir = Path(settings.SESSION_DIR)
        self.session_ttl_days = settings.SESSION_TTL_DAYS
        self._ensure_session_dir()
        self._clean_expired_sessions()
    
    def _ensure_session_dir(self):
        """确保会话目录存在"""
        if not self.session_dir.exists():
            try:
                self.session_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created session directory: {self.session_dir}")
            except Exception as e:
                logger.error(f"Failed to create session directory: {e}")
    
    def _clean_expired_sessions(self):
        """清理过期的会话文件"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.session_ttl_days)
            for session_file in self.session_dir.glob("*.json"):
                try:
                    # 检查文件修改时间
                    file_mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        session_file.unlink()
                        logger.info(f"Deleted expired session file: {session_file}")
                except Exception as e:
                    logger.warning(f"Error checking session file {session_file}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning expired sessions: {e}")
    
    def _get_session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.session_dir / f"{session_id}.json"
    
    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取会话历史"""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return []

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("messages", [])
                return []
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading session file {session_file}: {e}")
            return []

    def get_appointment_state(self, session_id: str) -> Dict[str, Any]:
        """获取预约状态"""
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return {}

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {
                        "appointment_step": data.get("appointment_step"),
                        "appointment_data": data.get("appointment_data", {})
                    }
                return {}
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading session file {session_file}: {e}")
            return {}

    def save_appointment_state(self, session_id: str, appointment_step: str, appointment_data: Dict[str, Any]) -> bool:
        """保存预约状态"""
        try:
            session_file = self._get_session_file(session_id)
            data = {}

            if session_file.exists():
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if not isinstance(data, dict):
                            data = {"messages": data}
                except (json.JSONDecodeError, Exception):
                    data = {}

            data["appointment_step"] = appointment_step
            data["appointment_data"] = appointment_data

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved appointment state for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving appointment state for session {session_id}: {e}")
            return False

    def clear_appointment_state(self, session_id: str) -> bool:
        """清除预约状态"""
        try:
            session_file = self._get_session_file(session_id)

            if not session_file.exists():
                return True

            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.pop("appointment_step", None)
                        data.pop("appointment_data", None)
            except (json.JSONDecodeError, Exception):
                data = {}

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Cleared appointment state for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing appointment state for session {session_id}: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """添加消息到会话历史"""
        try:
            session_file = self._get_session_file(session_id)
            data = {}

            if session_file.exists():
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, dict):
                            data = existing_data
                        else:
                            data = {"messages": existing_data}
                except (json.JSONDecodeError, Exception):
                    data = {}

            if "messages" not in data:
                data["messages"] = []

            data["messages"].append(
                {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
            )

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Added message to session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            return False
    
    def clear_session(self, session_id: str) -> bool:
        """清空会话历史"""
        try:
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                session_file.unlink()
                logger.info(f"Cleared session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {e}")
            return False


# 全局会话管理器实例
conversation_manager = ConversationManager()
