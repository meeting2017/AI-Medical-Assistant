import hashlib
import json
import os
from pathlib import Path
from typing import List

from langchain_community.docstore.document import Document
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import settings
from app.utils.logger import logger


class VectorStore:
    def __init__(self):
        self.embeddings = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", "：", ".", "!", "?", ";", ":", "，", ",", " ", ""],
        )
        self.vectorstore = None
        self._initialized = False
        self._faiss_docs_cache: List[Document] = []

    def _build_embeddings(self):
        provider = settings.EMBEDDING_PROVIDER.lower()

        if provider == "huggingface":
            try:
                from langchain_huggingface import HuggingFaceEmbeddings

                logger.info(f"Using HuggingFace embeddings model: {settings.EMBEDDING_MODEL}")
                return HuggingFaceEmbeddings(
                    model_name=settings.EMBEDDING_MODEL,
                    model_kwargs={"device": settings.EMBEDDING_DEVICE},
                    encode_kwargs={"normalize_embeddings": True},
                )
            except Exception as e:
                logger.warning(f"Failed to load langchain-huggingface embeddings ({settings.EMBEDDING_MODEL}): {e}")
                logger.warning("Falling back to API embeddings")

        if settings.API_PROVIDER.lower() == "dashscope":
            return OpenAIEmbeddings(
                model=settings.DASHSCOPE_EMBEDDING_MODEL,
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_API_BASE,
                tiktoken_enabled=False,
                check_embedding_ctx_length=False,
            )

        return OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
        )

    def _initialize_vectorstore(self):
        if self.embeddings is None:
            self.embeddings = self._build_embeddings()
        if settings.VECTOR_DB_TYPE.lower() == "chroma":
            self._init_chroma()
        else:
            self._init_faiss()
        self._initialized = True

    def _ensure_initialized(self):
        if not self._initialized:
            self._initialize_vectorstore()

    def ensure_initialized(self):
        self._ensure_initialized()

    def _get_faiss_cache_path(self) -> Path:
        return Path(settings.FAISS_DOCSTORE_CACHE_FILE)

    def _get_faiss_signature_path(self) -> Path:
        return Path(settings.FAISS_SIGNATURE_FILE)

    def _compute_files_sha256(self, files: List[Path]) -> str:
        digest = hashlib.sha256()
        for file_path in files:
            if not file_path.exists():
                continue
            digest.update(file_path.name.encode("utf-8"))
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
        return digest.hexdigest()

    def _faiss_files(self) -> List[Path]:
        base = Path(settings.FAISS_INDEX_PATH)
        return [base / "index.faiss", base / "index.pkl", self._get_faiss_cache_path()]

    def _save_faiss_signature(self):
        try:
            sig_path = self._get_faiss_signature_path()
            sig_path.parent.mkdir(parents=True, exist_ok=True)
            sig_path.write_text(self._compute_files_sha256(self._faiss_files()), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save FAISS signature: {e}")

    def _verify_faiss_signature(self) -> bool:
        sig_path = self._get_faiss_signature_path()
        if not sig_path.exists():
            return settings.FAISS_TRUST_LEGACY_INDEX
        try:
            saved = sig_path.read_text(encoding="utf-8").strip()
            current = self._compute_files_sha256(self._faiss_files())
            return bool(saved) and saved == current
        except Exception as e:
            logger.warning(f"Failed to verify FAISS signature: {e}")
            return False

    def _save_faiss_docs_cache(self):
        try:
            cache_path = self._get_faiss_cache_path()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                for doc in self._faiss_docs_cache:
                    f.write(
                        json.dumps(
                            {"page_content": doc.page_content, "metadata": doc.metadata},
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
        except Exception as e:
            logger.warning(f"Failed to save FAISS docs cache: {e}")

    def _load_faiss_docs_cache(self):
        self._faiss_docs_cache = []
        cache_path = self._get_faiss_cache_path()
        if not cache_path.exists():
            return
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    self._faiss_docs_cache.append(
                        Document(page_content=row.get("page_content", ""), metadata=row.get("metadata", {}))
                    )
        except Exception as e:
            logger.warning(f"Failed to load FAISS docs cache: {e}")
            self._faiss_docs_cache = []

    def _init_faiss(self):
        index_path = settings.FAISS_INDEX_PATH
        if os.path.exists(index_path):
            if not self._verify_faiss_signature():
                logger.warning("FAISS signature check failed or missing, skip loading existing index")
                self.vectorstore = None
                self._faiss_docs_cache = []
                return
            try:
                self.vectorstore = FAISS.load_local(
                    index_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                if not self._is_faiss_dimension_compatible():
                    logger.warning("FAISS index dimension is incompatible with current embedding model, rebuilding index")
                    self.vectorstore = None
                    self._faiss_docs_cache = []
                    return
                self._load_faiss_docs_cache()
                logger.info(f"Loaded existing FAISS index from {index_path}")
            except Exception as e:
                logger.warning(f"Failed to load FAISS index: {e}, creating new one")
                self.vectorstore = None
                self._faiss_docs_cache = []
        else:
            self.vectorstore = None
            self._faiss_docs_cache = []

    def _is_faiss_dimension_compatible(self) -> bool:
        if self.vectorstore is None:
            return True
        try:
            sample_vec = self.embeddings.embed_query("test dimension")
            emb_dim = len(sample_vec)
            index_dim = getattr(self.vectorstore.index, "d", emb_dim)
            return emb_dim == index_dim
        except Exception as e:
            logger.warning(f"Failed to validate FAISS dimension compatibility: {e}")
            return True

    def _init_chroma(self):
        persist_dir = settings.CHROMA_PERSIST_DIR
        if os.path.exists(persist_dir):
            try:
                self.vectorstore = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=self.embeddings,
                )
                logger.info(f"Loaded existing Chroma DB from {persist_dir}")
            except Exception as e:
                logger.warning(f"Failed to load Chroma DB: {e}, creating new one")
                self.vectorstore = None
        else:
            self.vectorstore = None

    def load_documents(self, file_path: str) -> List[Document]:
        documents: List[Document] = []
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.suffix.lower() == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(Document(page_content=content, metadata={"source": file_path_obj.name}))
            elif file_path_obj.suffix.lower() == ".pdf":
                try:
                    from pypdf import PdfReader

                    reader = PdfReader(file_path)
                    for i, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text.strip():
                            documents.append(
                                Document(
                                    page_content=text,
                                    metadata={"source": file_path_obj.name, "page": i + 1},
                                )
                            )
                except ImportError:
                    logger.error("pypdf not installed. Install with: pip install pypdf")
            logger.info(f"Loaded {len(documents)} documents from {file_path}")
        except Exception as e:
            logger.error(f"Error loading documents from {file_path}: {e}")
        return documents

    def add_documents(self, documents: List[Document]):
        self._ensure_initialized()
        if not documents:
            logger.warning("No documents to add")
            return

        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Split documents into {len(chunks)} chunks")

        if self.vectorstore is None:
            if settings.VECTOR_DB_TYPE.lower() == "chroma":
                self.vectorstore = Chroma.from_documents(
                    chunks,
                    self.embeddings,
                    persist_directory=settings.CHROMA_PERSIST_DIR,
                )
            else:
                self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
                self.vectorstore.save_local(settings.FAISS_INDEX_PATH)
                self._faiss_docs_cache = list(chunks)
                self._save_faiss_docs_cache()
                self._save_faiss_signature()
        else:
            self.vectorstore.add_documents(chunks)
            if settings.VECTOR_DB_TYPE.lower() == "faiss":
                self.vectorstore.save_local(settings.FAISS_INDEX_PATH)
                self._faiss_docs_cache.extend(chunks)
                self._save_faiss_docs_cache()
                self._save_faiss_signature()

        logger.info(f"Added {len(chunks)} chunks to vector store")

    def similarity_search(self, query: str, k: int = None) -> List[Document]:
        self._ensure_initialized()
        if self.vectorstore is None:
            logger.warning("Vector store not initialized")
            return []

        k = k or settings.TOP_K_RETRIEVAL
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            logger.info(f"Found {len(results)} similar documents for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []

    def similarity_search_with_score(self, query: str, k: int = None):
        self._ensure_initialized()
        if self.vectorstore is None:
            logger.warning("Vector store not initialized")
            return []

        k = k or settings.TOP_K_RETRIEVAL
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            logger.info(f"Found {len(results)} similar documents with scores for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error during similarity search with score: {e}")
            return []

    def max_marginal_relevance_search(self, query: str, k: int = None, fetch_k: int = None):
        self._ensure_initialized()
        if self.vectorstore is None:
            logger.warning("Vector store not initialized")
            return []

        k = k or settings.TOP_K_RETRIEVAL
        fetch_k = fetch_k or settings.MMR_FETCH_K
        try:
            return self.vectorstore.max_marginal_relevance_search(
                query, k=k, fetch_k=fetch_k, lambda_mult=settings.MMR_LAMBDA
            )
        except Exception as e:
            logger.error(f"Error during MMR search: {e}")
            return []

    def has_data(self) -> bool:
        self._ensure_initialized()
        if self.vectorstore is None:
            return False
        try:
            if settings.VECTOR_DB_TYPE.lower() == "chroma":
                raw = self.vectorstore.get(limit=1)
                ids = raw.get("ids", []) or []
                return len(ids) > 0
            return getattr(self.vectorstore.index, "ntotal", 0) > 0
        except Exception:
            return False

    def get_all_documents(self) -> List[Document]:
        self._ensure_initialized()
        if self.vectorstore is None:
            return []

        try:
            if settings.VECTOR_DB_TYPE.lower() == "chroma":
                raw = self.vectorstore.get(include=["documents", "metadatas"])
                docs = raw.get("documents", []) or []
                metadatas = raw.get("metadatas", []) or []
                return [
                    Document(page_content=doc or "", metadata=meta or {})
                    for doc, meta in zip(docs, metadatas)
                    if doc
                ]
            return list(self._faiss_docs_cache)
        except Exception as e:
            logger.error(f"Error reading all documents from vector store: {e}")
            return []

    def delete_vectorstore(self):
        if settings.VECTOR_DB_TYPE.lower() == "chroma":
            import shutil

            if os.path.exists(settings.CHROMA_PERSIST_DIR):
                shutil.rmtree(settings.CHROMA_PERSIST_DIR)
                logger.info(f"Deleted Chroma DB at {settings.CHROMA_PERSIST_DIR}")
        else:
            import shutil

            if os.path.exists(settings.FAISS_INDEX_PATH):
                shutil.rmtree(settings.FAISS_INDEX_PATH)
                logger.info(f"Deleted FAISS index at {settings.FAISS_INDEX_PATH}")
            cache_path = self._get_faiss_cache_path()
            if cache_path.exists():
                cache_path.unlink()
            sig_path = self._get_faiss_signature_path()
            if sig_path.exists():
                sig_path.unlink()
            self._faiss_docs_cache = []
        self.vectorstore = None
        self._initialized = False


vector_store = VectorStore()
