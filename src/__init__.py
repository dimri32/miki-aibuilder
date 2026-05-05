# fastapi imports
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

# python imports
from contextlib import asynccontextmanager
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# local imports
from src.apps.ingest_routes import eval_router
from src.apps.health import health_router
from src.config import confy

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is Starting....")

    yield
    print("Server is stopping...")


version = confy.model_version

app = FastAPI(
    title="AI Asset Builder Service",
    description="A FastAPI to Evaluate Content Generation Responses",
    version=version,
    lifespan=lifespan
)
# FastAPI
# START
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# END

app.include_router(eval_router, prefix="/asset_builder/evaluate", tags=["AI Asset Builder"])
app.include_router(health_router, prefix="/asset_builder/health", tags=["Health"])
