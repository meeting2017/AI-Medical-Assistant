from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from app.config.settings import settings
from app.utils.logger import logger

class LLMFactory:
    _instance = None
    _llm = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_llm(self) -> BaseChatModel:
        if self._llm is None:
            provider = settings.API_PROVIDER.lower()
            
            if provider == "dashscope":
                # 使用阿里云 DashScope API
                self._llm = ChatOpenAI(
                    model=settings.DASHSCOPE_MODEL,
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                    api_key=settings.DASHSCOPE_API_KEY,
                    base_url=settings.DASHSCOPE_API_BASE,
                    timeout=settings.RESPONSE_TIMEOUT
                )
                logger.info(f"LLM initialized with DashScope model: {settings.DASHSCOPE_MODEL}")
            else:
                # 使用 OpenAI API（默认）
                self._llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    temperature=settings.TEMPERATURE,
                    max_tokens=settings.MAX_TOKENS,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_API_BASE,
                    timeout=settings.RESPONSE_TIMEOUT
                )
                logger.info(f"LLM initialized with OpenAI model: {settings.OPENAI_MODEL}")
        
        return self._llm
    
    def reset_llm(self):
        self._llm = None

llm_factory = LLMFactory()