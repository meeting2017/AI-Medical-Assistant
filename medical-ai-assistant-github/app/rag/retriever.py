import math
import re
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from langchain_community.docstore.document import Document
from app.rag.vector_store import vector_store
from app.config.settings import settings
from app.utils.logger import logger

class MedicalRetriever:
    def __init__(self):
        self.vector_store = vector_store
        self.reranker = None
        self._reranker_loaded = False
        self._knowledge_bootstrapped = False
        self._bm25_cache = None
        self._bm25_cache_key = None

    def _init_reranker(self):
        if not settings.RERANKER_ENABLED:
            return None
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker model: {settings.RERANKER_MODEL}")
            return CrossEncoder(settings.RERANKER_MODEL)
        except Exception as e:
            logger.warning(f"Reranker initialization failed: {e}")
            return None

    def _get_reranker(self):
        if self._reranker_loaded:
            return self.reranker
        self.reranker = self._init_reranker()
        self._reranker_loaded = True
        return self.reranker

    def _ensure_knowledge_base(self):
        if self._knowledge_bootstrapped:
            return
        try:
            if self.vector_store.has_data():
                self._knowledge_bootstrapped = True
                return

            docs_dir = Path(settings.MEDICAL_DOCS_DIR)
            if docs_dir.exists():
                for doc_file in docs_dir.glob("*.txt"):
                    documents = self.vector_store.load_documents(str(doc_file))
                    if documents:
                        self.vector_store.add_documents(documents)
                logger.info("RAG knowledge base bootstrapped on first retrieval")
            self._knowledge_bootstrapped = True
        except Exception as e:
            logger.warning(f"Knowledge base bootstrap failed: {e}")

    def _tokenize_text(self, text: str) -> List[str]:
        if not text:
            return []
        # 英文按词，中文优先按词（jieba），缺失时退化为按字
        en_tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        zh_text = "".join([ch for ch in text if "\u4e00" <= ch <= "\u9fff"])
        if not zh_text:
            return en_tokens
        try:
            import jieba
            zh_tokens = [tok.strip() for tok in jieba.lcut(zh_text) if tok.strip()]
        except Exception:
            zh_tokens = [ch for ch in zh_text]
        return en_tokens + zh_tokens

    def _doc_key(self, doc: Document) -> str:
        source = doc.metadata.get("source", "")
        page = doc.metadata.get("page", "")
        return f"{source}|{page}|{doc.page_content[:120]}"

    def _normalize_vector_score(self, raw_score: float) -> float:
        # 相似度检索统一成越大越好（FAISS/Chroma 原生分值通常是距离，越小越好）
        score = max(float(raw_score), 0.0)
        return 1.0 / (1.0 + score)

    def _vector_candidates(self, query: str, fetch_k: int) -> List[Tuple[Document, float]]:
        raw = self.vector_store.similarity_search_with_score(query, k=fetch_k)
        return [(doc, self._normalize_vector_score(score)) for doc, score in raw]

    def _bm25_candidates(self, query: str, docs: List[Document], fetch_k: int) -> List[Tuple[Document, float]]:
        if not docs:
            return []
        try:
            from rank_bm25 import BM25Okapi
        except Exception as e:
            logger.warning(f"rank_bm25 unavailable, skip BM25: {e}")
            return []

        cache_key = (len(docs), sum(len(d.page_content) for d in docs))
        if self._bm25_cache is None or self._bm25_cache_key != cache_key:
            tokenized_docs = [self._tokenize_text(d.page_content) for d in docs]
            self._bm25_cache = BM25Okapi(tokenized_docs)
            self._bm25_cache_key = cache_key

        bm25 = self._bm25_cache
        scores = bm25.get_scores(self._tokenize_text(query))

        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)
        top = indexed[:fetch_k]
        max_score = max([s for _, s in top], default=0.0)
        if max_score <= 0:
            return [(docs[idx], 0.0) for idx, _ in top]
        return [(docs[idx], float(s / max_score)) for idx, s in top]

    def _hybrid_merge(self, vector_items: List[Tuple[Document, float]], bm25_items: List[Tuple[Document, float]]) -> List[Tuple[Document, float]]:
        merged: Dict[str, Dict[str, Any]] = {}

        for doc, score in vector_items:
            key = self._doc_key(doc)
            if key not in merged:
                merged[key] = {"doc": doc, "vector": 0.0, "bm25": 0.0}
            merged[key]["vector"] = max(merged[key]["vector"], score)

        for doc, score in bm25_items:
            key = self._doc_key(doc)
            if key not in merged:
                merged[key] = {"doc": doc, "vector": 0.0, "bm25": 0.0}
            merged[key]["bm25"] = max(merged[key]["bm25"], score)

        v_w = settings.HYBRID_VECTOR_WEIGHT
        b_w = settings.HYBRID_BM25_WEIGHT
        fused = []
        for row in merged.values():
            final_score = row["vector"] * v_w + row["bm25"] * b_w
            fused.append((row["doc"], final_score))

        fused.sort(key=lambda x: x[1], reverse=True)
        return fused

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _apply_mmr(self, query: str, docs_with_scores: List[Tuple[Document, float]], top_k: int) -> List[Tuple[Document, float]]:
        if (
            not settings.MMR_ENABLED
            or len(docs_with_scores) <= top_k
            or len(docs_with_scores) < settings.MMR_MIN_CANDIDATES
        ):
            return docs_with_scores[:top_k]

        docs = [d for d, _ in docs_with_scores]
        texts = [d.page_content for d in docs]

        try:
            self.vector_store.ensure_initialized()
            query_emb = self.vector_store.embeddings.embed_query(query)
            doc_embs = self.vector_store.embeddings.embed_documents(texts)
        except Exception as e:
            logger.warning(f"MMR embedding failed, fallback to score ranking: {e}")
            return docs_with_scores[:top_k]

        lambda_mult = settings.MMR_LAMBDA
        selected_idx: List[int] = []
        candidate_idx = list(range(len(docs)))

        while candidate_idx and len(selected_idx) < top_k:
            best_idx = None
            best_score = -1e9

            for idx in candidate_idx:
                sim_to_query = self._cosine(query_emb, doc_embs[idx])
                if not selected_idx:
                    mmr_score = sim_to_query
                else:
                    max_sim_selected = max(self._cosine(doc_embs[idx], doc_embs[s]) for s in selected_idx)
                    mmr_score = lambda_mult * sim_to_query - (1.0 - lambda_mult) * max_sim_selected

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is None:
                break
            selected_idx.append(best_idx)
            candidate_idx.remove(best_idx)

        selected = [(docs[idx], docs_with_scores[idx][1]) for idx in selected_idx]
        return selected

    def _apply_rerank(self, query: str, docs_with_scores: List[Tuple[Document, float]], top_k: int) -> List[Tuple[Document, float]]:
        reranker = self._get_reranker()
        if (
            not reranker
            or not docs_with_scores
            or len(docs_with_scores) < settings.RERANK_MIN_CANDIDATES
        ):
            return docs_with_scores[:top_k]

        try:
            candidates = docs_with_scores[: settings.MAX_RERANK_CANDIDATES]
            pairs = [(query, doc.page_content) for doc, _ in candidates]
            rerank_scores = reranker.predict(pairs)
            enriched = []
            for (doc, base_score), rr in zip(candidates, rerank_scores):
                final_score = 0.2 * base_score + 0.8 * float(rr)
                enriched.append((doc, final_score))
            enriched.sort(key=lambda x: x[1], reverse=True)
            return enriched[:top_k]
        except Exception as e:
            logger.warning(f"Rerank failed, fallback to pre-rerank order: {e}")
            return docs_with_scores[:top_k]
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[str]:
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        top_k = top_k or settings.TOP_K_RETRIEVAL
        
        try:
            self._ensure_knowledge_base()
            fetch_k = max(top_k * settings.HYBRID_CANDIDATE_MULTIPLIER, settings.MMR_FETCH_K)
            if settings.ENABLE_LOW_LATENCY_RETRIEVAL:
                fetch_k = min(fetch_k, settings.FAST_FETCH_K_CAP)

            vector_items = self._vector_candidates(query, fetch_k)
            if settings.RETRIEVAL_MODE.lower() == "hybrid":
                all_docs = self.vector_store.get_all_documents()
                bm25_items = self._bm25_candidates(query, all_docs, fetch_k)
                merged = self._hybrid_merge(vector_items, bm25_items)
            else:
                merged = vector_items

            mmr_selected = self._apply_mmr(query, merged, top_k=max(top_k * 3, top_k))
            final_items = self._apply_rerank(query, mmr_selected, top_k=top_k)

            contexts = [doc.page_content for doc, _ in final_items]
            logger.info(f"Retrieved {len(contexts)} contexts for query")
            return contexts
        except Exception as e:
            logger.error(f"Error retrieving contexts: {e}")
            return []
    
    def retrieve_with_metadata(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        top_k = top_k or settings.TOP_K_RETRIEVAL
        
        try:
            self._ensure_knowledge_base()
            fetch_k = max(top_k * settings.HYBRID_CANDIDATE_MULTIPLIER, settings.MMR_FETCH_K)
            if settings.ENABLE_LOW_LATENCY_RETRIEVAL:
                fetch_k = min(fetch_k, settings.FAST_FETCH_K_CAP)

            vector_items = self._vector_candidates(query, fetch_k)
            if settings.RETRIEVAL_MODE.lower() == "hybrid":
                all_docs = self.vector_store.get_all_documents()
                bm25_items = self._bm25_candidates(query, all_docs, fetch_k)
                merged = self._hybrid_merge(vector_items, bm25_items)
            else:
                merged = vector_items

            mmr_selected = self._apply_mmr(query, merged, top_k=max(top_k * 3, top_k))
            results = self._apply_rerank(query, mmr_selected, top_k=top_k)

            contexts = []
            for doc, score in results:
                contexts.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            logger.info(f"Retrieved {len(contexts)} contexts with metadata for query")
            return contexts
        except Exception as e:
            logger.error(f"Error retrieving contexts with metadata: {e}")
            return []
    
    def retrieve_by_source(self, query: str, source: str, top_k: Optional[int] = None) -> List[str]:
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []
        
        top_k = top_k or settings.TOP_K_RETRIEVAL
        
        try:
            all_results = self.retrieve_with_metadata(query, top_k=top_k * 3)
            filtered_results = [
                item for item in all_results
                if item["metadata"].get("source") == source
            ]
            contexts = [item["content"] for item in filtered_results[:top_k]]
            logger.info(f"Retrieved {len(contexts)} contexts from source '{source}'")
            return contexts
        except Exception as e:
            logger.error(f"Error retrieving contexts by source: {e}")
            return []
    
    def format_contexts(self, contexts: List[str]) -> str:
        if not contexts:
            return "未找到相关的医学知识。"
        
        formatted = "\n\n".join([f"【医学知识 {i+1}】\n{ctx}" for i, ctx in enumerate(contexts)])
        return formatted
    
    def get_relevant_knowledge(self, query: str, top_k: Optional[int] = None) -> str:
        contexts = self.retrieve(query, top_k)
        return self.format_contexts(contexts)

    def warmup(self, preload_reranker: bool = False):
        self._ensure_knowledge_base()
        self.vector_store.ensure_initialized()
        if preload_reranker and settings.RERANKER_ENABLED:
            self._get_reranker()

medical_retriever = MedicalRetriever()
