import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI API 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # 阿里云 DashScope API 配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_API_BASE: str = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen-turbo")
    DASHSCOPE_EMBEDDING_MODEL: str = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v2")
    
    # API 提供商选择
    API_PROVIDER: str = os.getenv("API_PROVIDER", "openai")
    
    # 通用配置
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
    
    VECTOR_DB_TYPE: str = os.getenv("VECTOR_DB_TYPE", "faiss")
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
    
    # Embedding 配置
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "huggingface")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")
    
    # 切片配置（中文医疗文本推荐较小切片 + 稳定重叠）
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "420"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "80"))
    
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "3"))
    
    # 检索配置
    RETRIEVAL_MODE: str = os.getenv("RETRIEVAL_MODE", "hybrid")  # vector | hybrid
    HYBRID_CANDIDATE_MULTIPLIER: int = int(os.getenv("HYBRID_CANDIDATE_MULTIPLIER", "6"))
    HYBRID_VECTOR_WEIGHT: float = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.55"))
    HYBRID_BM25_WEIGHT: float = float(os.getenv("HYBRID_BM25_WEIGHT", "0.45"))
    
    MMR_ENABLED: bool = os.getenv("MMR_ENABLED", "true").lower() == "true"
    MMR_LAMBDA: float = float(os.getenv("MMR_LAMBDA", "0.65"))
    MMR_FETCH_K: int = int(os.getenv("MMR_FETCH_K", "20"))
    
    RERANKER_ENABLED: bool = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    RERANK_MIN_CANDIDATES: int = int(os.getenv("RERANK_MIN_CANDIDATES", "8"))
    MAX_RERANK_CANDIDATES: int = int(os.getenv("MAX_RERANK_CANDIDATES", "12"))
    
    # 启动优化：默认不在启动时预加载 RAG（改为首个检索请求懒加载）
    RAG_PRELOAD_ON_STARTUP: bool = os.getenv("RAG_PRELOAD_ON_STARTUP", "false").lower() == "true"
    RAG_WARMUP_BACKGROUND: bool = os.getenv("RAG_WARMUP_BACKGROUND", "true").lower() == "true"
    RAG_WARMUP_LOAD_RERANKER: bool = os.getenv("RAG_WARMUP_LOAD_RERANKER", "false").lower() == "true"

    # 低延迟检索优化
    ENABLE_LOW_LATENCY_RETRIEVAL: bool = os.getenv("ENABLE_LOW_LATENCY_RETRIEVAL", "true").lower() == "true"
    FAST_FETCH_K_CAP: int = int(os.getenv("FAST_FETCH_K_CAP", "12"))
    MMR_MIN_CANDIDATES: int = int(os.getenv("MMR_MIN_CANDIDATES", "10"))

    # FAISS sidecar 文档缓存与签名（提升安全性与可维护性）
    FAISS_DOCSTORE_CACHE_FILE: str = os.getenv("FAISS_DOCSTORE_CACHE_FILE", "./faiss_index/docs_cache.jsonl")
    FAISS_SIGNATURE_FILE: str = os.getenv("FAISS_SIGNATURE_FILE", "./faiss_index/signature.sha256")
    FAISS_TRUST_LEGACY_INDEX: bool = os.getenv("FAISS_TRUST_LEGACY_INDEX", "false").lower() == "true"
    
    MAX_CONVERSATION_HISTORY: int = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MEDICAL_DOCS_DIR: str = os.path.join(BASE_DIR, "rag", "medical_docs")
    
    RESPONSE_TIMEOUT: int = int(os.getenv("RESPONSE_TIMEOUT", "5"))
    
    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "604800"))  # 7 days in seconds
    REDIS_CONNECT_TIMEOUT: float = 5.0
    REDIS_RETRY_COUNT: int = 3
    
    # Session file storage
    SESSION_DIR: str = os.getenv("SESSION_DIR", "sessions")
    SESSION_TTL_DAYS: int = int(os.getenv("SESSION_TTL_DAYS", "7"))

settings = Settings()
