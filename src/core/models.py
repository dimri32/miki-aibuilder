# python imports    
from pydantic import BaseModel, Field

# local imports
from src.core.logger import AIBuilderEvalLogger
from src.config import confy

# Initialize logger
logger = AIBuilderEvalLogger(name=__name__, log_level=confy.log_level)

class EvaluatorRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Primary query text")
    k: int = Field(10, ge=1, le=50, description="Max related sub-queries to return")
    tenant: str = Field(
        default="ironclad",
        min_length=1,
        description="Tenant id used in MIKI sender metadata (e.g. ironclad)",
    )


class EvaluatorResponse(BaseModel):
    query: str
    results_map: dict[str, str]