# fastapi imports
from fastapi import APIRouter, HTTPException

# python imports
from dotenv import load_dotenv
from typing import Dict, Any
import warnings
import asyncio
import uuid
import os

# local imports
from src.core.models import EvaluatorRequest, EvaluatorResponse
from src.core.logger import AIBuilderEvalLogger
from src.core.utils import get_miki_answers_async # get_miki_answers
from src.config import confy

warnings.filterwarnings("ignore")
load_dotenv()

JOB_STORE: Dict[str, Dict[str, Any]] = {}

# Initialize logger
logger = AIBuilderEvalLogger(name=__name__, log_level=confy.log_level)

# Fast API initialization
eval_router = APIRouter()
# asset_builder/evaluate

# @eval_router.post("/", response_model=EvaluatorResponse)
# async def start_evaluator(req: EvaluatorRequest):
#     try:
#         results_map = await asyncio.to_thread(
#             get_miki_answers,
#             req.query,
#             req.k,
#             req.tenant,
#         )

#         return EvaluatorResponse(
#             query=req.query,
#             results_map=results_map,
#         )
#     except Exception as exc:
#         logger.error(f"Failed to fetch related sub-queries: {exc}")
#         raise HTTPException(
#             status_code=500,
#             detail="Unable to fetch related sub-queries for the query.",
#         ) from exc

async def run_pipeline(job_id: str, req: EvaluatorRequest):
    try:
        JOB_STORE[job_id].update({
            "status": "running",
            "progress": 10,
            "message": "Embedding query..."
        })

        # Step 1
        await asyncio.sleep(1)

        JOB_STORE[job_id].update({
            "progress": 30,
            "message": "Retrieving sub-queries..."
        })

        # Step 2
        await asyncio.sleep(1)

        JOB_STORE[job_id].update({
            "progress": 60,
            "message": "Calling MIKI..."
        })

        # results_map = await asyncio.to_thread(
        #     get_miki_answers,
        #     req.query,
        #     req.k,
        #     req.tenant,
        # )
        results_map, scores_map = await get_miki_answers_async(
            req.query,
            req.k,
            req.tenant,
            max_concurrency=5
        )

        JOB_STORE[job_id].update({
            "progress": 90,
            "message": "Aggregating results...",
            "results_map": results_map,
            "scores_map": scores_map,
        })

        JOB_STORE[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Done"
        })

    except Exception as e:
        JOB_STORE[job_id].update({
            "status": "failed",
            "error": str(e)
        })

# async def run_pipeline(job_id: str, req: EvaluatorRequest):
#     try:
#         # STEP 1
#         JOB_STORE[job_id].update({
#             "status": "running",
#             "progress": 10,
#             "message": "Embedding query..."
#         })
#         await asyncio.sleep(1)

#         # STEP 2
#         JOB_STORE[job_id].update({
#             "progress": 30,
#             "message": "Retrieving sub-queries..."
#         })
#         await asyncio.sleep(1)

#         # STEP 3
#         JOB_STORE[job_id].update({
#             "progress": 60,
#             "message": "Calling MIKI..."
#         })
#         await asyncio.sleep(1)

#         # ─────────────────────────────────────────
#         # 🧪 DUMMY RESULTS (instead of real call)
#         # ─────────────────────────────────────────
#         query = req.query

#         dummy_results = {
#             f"{query}~What are key differentiators vs DocuSign?":
#                 "Strong workflow automation, better contract lifecycle visibility, and deep CRM integrations.",

#             f"{query}~Why do customers switch from DocuSign?":
#                 "Customers often cite pricing, limited customization, and lack of analytics as reasons.",

#             f"{query}~What industries prefer Ironclad?":
#                 "Technology, SaaS, and high-growth startups prefer flexible contract lifecycle tools.",

#             f"{query}~What are common objections?":
#                 "Implementation effort and change management are common objections during evaluation.",

#             f"{query}~How does it compare on pricing?":
#                 "Typically positioned as value-driven vs enterprise-heavy pricing models."
#         }

#         # ─────────────────────────────────────────
#         # OPTIONAL: simulate streaming results
#         # ─────────────────────────────────────────
#         partial_results = {}
#         total = len(dummy_results)

#         for i, (k, v) in enumerate(dummy_results.items(), start=1):
#             partial_results[k] = v

#             JOB_STORE[job_id].update({
#                 "progress": 60 + int((i / total) * 30),  # 60 → 90
#                 "message": f"Processing result {i}/{total}...",
#                 "results_map": partial_results
#             })

#             await asyncio.sleep(0.5)

#         # FINAL STEP
#         JOB_STORE[job_id].update({
#             "status": "completed",
#             "progress": 100,
#             "message": "Done",
#             "results_map": dummy_results
#         })

#     except Exception as e:
#         JOB_STORE[job_id].update({
#             "status": "failed",
#             "progress": 100,
#             "message": "Failed",
#             "error": str(e)
#         })

@eval_router.post("/")
async def start_evaluator(req: EvaluatorRequest):
    job_id = str(uuid.uuid4())

    JOB_STORE[job_id] = {
        "status": "started",
        "progress": 0,
        "message": "Initializing...",
        "results_map": None,
        "error": None,
    }

    asyncio.create_task(run_pipeline(job_id, req))

    return {"job_id": job_id}

@eval_router.get("/{job_id}")
async def get_status(job_id: str):
    job = JOB_STORE.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
