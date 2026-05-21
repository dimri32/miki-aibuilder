# python imports
from typing import List, Optional, Dict, Any, Tuple, Set
from requests.auth import HTTPBasicAuth
from functools import lru_cache
from threading import Lock
import numpy as np
import requests
import aiohttp
import asyncio
import base64
import json
import time
import os

# openai imports
from openai import OpenAI

# # trasnformer imports
# from sentence_transformers import SentenceTransformer

# local imports
# from src.core.database import CustomEmbedding, AstraIndex
from src.core.nl_query_generator import generate_nl_subqueries
from src.core.logger import AIBuilderEvalLogger
from src.config import confy

logger = AIBuilderEvalLogger(name=__name__, log_level=confy.log_level)

# Prevent double-load races if multiple threads hit the first encode at once
_EMBEDDER_LOCK = Lock()

# hf_custom_model = SentenceTransformer(
#     confy.EMBEDDING_MODEL_ID,
#     truncate_dim=confy.DIM,
#     token=confy.EMBEEDING_HF_TOKEN
# ) # small variant
# hf_custom_embedding = CustomEmbedding(hf_custom_model)

# astra_index = AstraIndex(
#     token=confy.ASTRAV_DB_APPLICATION_TOKEN,
#     api_endpoint=confy.ASTRAV_DB_API_ENDPOINT,
#     keyspace=confy.keyspace,
#     model=hf_custom_embedding,
#     collection_name=confy.ASTRAV_VECTOR_COLLECTION
# )


class TinyVectorIndex:
    def __init__(self, dim: int, snap_path: Optional[str] = None):
        self.dim = dim
        self.snap_path = snap_path
        self._keys: List[str] = []      # template_hash (or full redis key)
        self._meta: List[Dict[str, Any]] = []
        self._E = np.zeros((0, dim), np.float32)  # normalized vectors
        self._dirty = False
        self._lock = Lock()
    def _normalize(self, v: np.ndarray) -> np.ndarray:
        v = v.astype(np.float32, copy=False)
        v /= (np.linalg.norm(v) + 1e-12)
        return v
    def upsert(self, key: str, vec: np.ndarray, meta: Dict[str, Any]):
        vec = self._normalize(vec)
        with self._lock:
            if key in self._keys:
                i = self._keys.index(key)
                self._E[i] = vec
                self._meta[i] = meta
            else:
                self._keys.append(key)
                if self._E.shape[0] == 0:
                    self._E = vec.reshape(1, -1)
                else:
                    self._E = np.vstack([self._E, vec.reshape(1, -1)])
                self._meta.append(meta)
            self._dirty = True
    def search(self, q: np.ndarray, k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
        if self._E.shape[0] == 0:
            return []
        q = self._normalize(q).reshape(1, -1)        # (1, D)
        sims = (self._E @ q.T).ravel()               # cosine similarity
        k = min(k, sims.shape[0])
        top = np.argpartition(-sims, k-1)[:k]
        top = top[np.argsort(-sims[top])]
        out = []
        print(" Search sims:", top)
        for i in top:
            meta = dict(self._meta[i])
            meta["id"] = self._keys[i]
            out.append((float(sims[i]), meta))
        return out


    # optional persistence (fast warm start)
    def save(self):
        if not self.snap_path or not self._dirty:
            return
        tmp = self.snap_path + ".tmp"
        if not tmp.endswith(".npz"):
            tmp = tmp + ".npz"
        np.savez_compressed(
            tmp,
            E=self._E,
            keys=np.array(self._keys, dtype=object),
            meta=np.array(self._meta, dtype=object),
            dim=self.dim
        )
        os.replace(tmp, self.snap_path)  # works on Linux/Win/macOS
        self._dirty = False

    def load(self):
        """Load vectors + metadata from .npz snapshot"""
        if not self.snap_path:
            return
        path = self.snap_path
        if not os.path.exists(path):
            print(f"[TinyVectorIndex] No snapshot at {path}, starting empty.")
            return
        try:
            z = np.load(path, allow_pickle=True)
            self._E = z["E"].astype(np.float32)
            self._keys = list(z["keys"])
            self._meta = list(z["meta"])
            self.dim = int(z["dim"])
            self._dirty = False
            print(f"[TinyVectorIndex] ✅ Loaded {len(self._keys)} vectors from {path}")
        except Exception as e:
            print(f"[TinyVectorIndex] ⚠️ Failed to load snapshot: {e}")


@lru_cache(maxsize=1)
def _get_embedder() -> OpenAI:
    """
    Return a process-wide Mixbread client (cached).
    """
    with _EMBEDDER_LOCK:
        t0 = time.time()
        print(f"[Embedder] 🔧 Initializing Mixbread client for embeddings '{confy.MIXBREAD_EMBED_MODEL}' ...")
        
        # Get Mixbread credentials from environment
        mixbread_url = os.getenv("MIXBREAD_URL","https://miki-mxbai-embed-large-v1-miki-prod-8000-ed0bfc.ci.aviso.com")
        mixbread_username = os.getenv("MIXBREAD_USERNAME",'miki-mxbread')
        mixbread_password = os.getenv("MIXBREAD_PASSWORD",'Aviso@321')
        
        if not all([mixbread_url, mixbread_username, mixbread_password]):
            raise RuntimeError("Missing Mixbread credentials in environment variables")
        
        # Create basic auth header
        basic = base64.b64encode(f"{mixbread_username}:{mixbread_password}".encode()).decode()
        
        # Initialize OpenAI client with Mixbread endpoint
        client = OpenAI(
            base_url=f"{mixbread_url}/v1",
            api_key="dummy",  # required by SDK, ignored by TEI
            default_headers={"Authorization": f"Basic {basic}"}
        )
        
        print(f"[Embedder] ✅ Mixbread client ready in {(time.time()-t0)*1000:.1f}ms")
        return client

def _encode(text: str) -> np.ndarray:
    """
    Encode one string using Mixbread embeddings (L2-normalized float32).
    """
    client = _get_embedder()
    t1 = time.time()
    resp = client.embeddings.create(model=confy.MIXBREAD_EMBED_MODEL, input=[text])
    vec = np.asarray(resp.data[0].embedding, dtype=np.float32)
    # L2 normalize for COSINE distance usage in Redis
    norm = np.linalg.norm(vec) + 1e-12
    out = (vec / norm).astype(np.float32)
    print(f"[Embedder] ⏱️ Encode took {(time.time()-t1)*1000:.1f}ms")
    return out
    
def _prewarm():
    if confy.PREWARM_EMBEDDER:
        try:
            # Triggers client init + a tiny embed call at import/startup
            _ = _encode("warmup")
            print("[Embedder] 🔥 Prewarm complete")
        except Exception as e:
            print(f"[Embedder] ⚠️ Prewarm failed: {e}")

def _generate_embedding(text: str) -> np.ndarray:
    # Uses the process-wide singleton embedder; no per-instance model state
    return _encode(text)

def parse_hits(hits: List[Tuple[float, Dict[str, Any]]]) -> List[Dict[str, str]]:
    results = []
    
    for score, meta in hits:
        results.append({
            "category": "",
            "subcategory": "",
            "question": meta.get("query_text", ""),
            "priority": score,
        })
        
    return results

def parse_topic_dict(topic_dict: Dict[str, Dict[str, List[Dict]]]) -> List[Dict]:
    topic_dict = topic_dict.get("result", {})
    sections = []
    
    for header, sub_area_dict in topic_dict.items():
        for sub_area, question_sets in sub_area_dict.items():
            question_sets = [
                {
                    "question": question_sets.get("question", ""),
                    "context": question_sets.get("detailedText", "")
                }
            ]
            
            section = {
                'header': header,
                'sub_area': sub_area,
                'questions': question_sets,
                'question_count': len(question_sets)
            }
            sections.append(section)
    return sections

def safe_parse(text):
    if isinstance(text, dict):
        return text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import ast
        return ast.literal_eval(text)
          
_tiny_index = TinyVectorIndex(
    dim=confy.MIXBREAD_EMBED_DIM,
    snap_path= "vec_index_mixbread.npz"
)

async def get_questions_from_primary_query(primary_query: str, k: int = 10) -> List[str]:
    """
    Given a primary query:
    - Generates embedding
    - Searches index
    - Parses hits
    - Returns unique list of questions
    """

    # Step 1: Generate embedding
    qvec = _generate_embedding(primary_query)

    # Step 2: Load index (safe to call multiple times if internally cached)
    _tiny_index.load()

    # Step 3: Search
    hits = _tiny_index.search(qvec, k=k)

    # Step 4: Parse results
    flattened_payload = parse_hits(hits)

    # Step 5: Extract unique questions
    questions: Set[str] = set()

    for item in flattened_payload:
        q = item.get("question")
        if q:
            questions.add(q.strip())

    return list(questions)

# async def _fetch_docs(sub_query: str, top_k: int, min_similarity: float):
#     try:
#         docs = astra_index.search_content_threshold(
#             query=sub_query,
#             top_k=top_k,
#             min_similarity=min_similarity
#         )
#         return sub_query, docs or []
#     except Exception as e:
#         print(f"[ERROR] {sub_query}: {e}")
#         return sub_query, []

# async def get_relevant_docs_parallel(
#     sub_queries: List[str],
#     top_k: int = 5,
#     min_similarity: float = 0.7
# ) -> Dict[str, List[Dict[str, Any]]]:
#     """
#     Parallel version for faster retrieval.
#     """

#     tasks = [
#         _fetch_docs(q, top_k, min_similarity)
#         for q in sub_queries
#     ]

#     results = await asyncio.gather(*tasks)

#     return {query: docs for query, docs in results}


# def get_miki_answers(
#     primary_query: str,
#     k: int = 10,
#     tenant: str = "ironclad"
# ) -> Dict[str, str]:
#     """
#     End-to-end pipeline:
#     1. Embed primary query
#     2. Retrieve top-k similar queries
#     3. Call MIKI for each
#     4. Return results_map[query] = detailed_text
#     """

#     # ── Step 1: Embed + Search ─────────────────────────
#     qvec = _generate_embedding(primary_query)

#     _tiny_index.load()
#     hits = _tiny_index.search(qvec, k=k)

#     # ── Step 2: Parse hits ─────────────────────────────
#     def parse_hits(hits: List[Tuple[float, Dict[str, Any]]]):
#         results = []
#         for score, meta in hits:
#             results.append({
#                 "question": meta.get("query_text", ""),
#                 "priority": score,
#             })
#         return results

#     payload = parse_hits(hits)

#     # ── Step 3: Setup API ──────────────────────────────
#     API_URL = confy.MIKI_API_URL 
#     API_USERNAME = confy.MIKI_API_USERNAME
#     API_PASSWORD = confy.MIKI_API_PASSWORD

#     auth = HTTPBasicAuth(API_USERNAME, API_PASSWORD)

#     results_map: Dict[str, str] = {}

#     time.sleep(1)
#     # ── Step 4: Loop through queries ───────────────────
#     for item in payload:
#         query = item.get("question")
#         if not query:
#             continue

#         print("Constructed query for MIKI:", query)

#         query_payload = {
#             "sender": f"123test {tenant}.com 9b351668-31a9-4bec-9d81-2f133a8f2b1a",
#             "message": query,
#             "metadata": {
#                 "node": "Global#Global"
#             }
#         }

#         try:
#             response = requests.post(
#                 API_URL,
#                 auth=auth,
#                 json=query_payload,
#                 timeout=180
#             )
#             response.raise_for_status()

#             response_data = response.json()
#             custom_response = response_data[0].get("custom", [])

#             detailed_text = ""

#             # ── Extract detailedText ───────────────────
#             for item in custom_response:
#                 if item.get("type") == "brief-text" and "message" in item:
#                     message = item["message"]
#                     detailed_text = message.get("detailedText", "")  # ✅ key part

#             # fallback (optional)
#             if not detailed_text:
#                 detailed_text = str(custom_response)

#             results_map[query] = detailed_text

#         except Exception as e:
#             print(f"Error for query: {query} → {str(e)}")
#             results_map[query] = f"ERROR: {str(e)}"

#     return results_map

async def fetch_miki_response(session, url, auth, query, tenant, semaphore):
    query_payload = {
        "sender": f"123test {tenant}.com 9b351668-31a9-4bec-9d81-2f133a8f2b1a",
        "message": query,
        "metadata": {
            "node": "Global#Global"
        }
    }

    async with semaphore:  # concurrency control

        start_time = time.perf_counter()

        # START LOG
        logger.info(f"[MIKI_CALL_START] query='{query}'")

        try:
            async with session.post(
                url,
                json=query_payload,
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:

                response.raise_for_status()
                response_data = await response.json()

                custom_response = response_data[0].get("custom", [])
                detailed_text = ""

                for item in custom_response:
                    if item.get("type") == "brief-text" and "message" in item:
                        detailed_text = item["message"].get("detailedText", "")

                duration_ms = (time.perf_counter() - start_time) * 1000

                if not detailed_text:
                    raw_preview = str(response_data)[:300]
                    logger.warning(
                        f"[MIKI_NO_CONTENT] query='{query}' duration_ms={duration_ms:.2f} "
                        f"raw={raw_preview}"
                    )
                    return query, None

                logger.info(
                    f"[MIKI_CALL_SUCCESS] query='{query}' "
                    f"duration_ms={duration_ms:.2f}"
                )
                return query, detailed_text

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[MIKI_CALL_ERROR] query='{query}' "
                f"duration_ms={duration_ms:.2f} error={str(e)}"
            )
            return query, None
        
async def get_miki_answers_async(
    primary_query: str,
    k: int = 10,
    tenant: str = "ironclad",
    max_concurrency: int = 5,
    workflow_id: str = ""
):

    payload = await generate_nl_subqueries(primary_query, target_count=k)
    payload = payload[:k]  # hard cap — never fire more MIKI calls than requested

    # Preserve priority scores keyed by question text before MIKI calls
    scores_map: Dict[str, float] = {
        item["question"]: item["priority"]
        for item in payload if item.get("question")
    }

    # ── Step 2: Setup API ──────────────────────────────
    API_URL = confy.MIKI_API_URL
    auth = aiohttp.BasicAuth(
        confy.MIKI_API_USERNAME,
        confy.MIKI_API_PASSWORD
    )

    semaphore = asyncio.Semaphore(max_concurrency)  # ✅ key addition

    # ── Step 3: Parallel Calls ─────────────────────────
    async with aiohttp.ClientSession() as session:

        tasks = [
            fetch_miki_response(
                session,
                API_URL,
                auth,
                item["question"],
                tenant,
                semaphore
            )
            for item in payload if item.get("question")
        ]

        responses = await asyncio.gather(*tasks)

    # ── Step 4: Aggregate — drop skipped / errored responses ──────────
    results_map = {query: result for query, result in responses if result}

    return results_map, scores_map