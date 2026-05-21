# transformer imports
from sentence_transformers import SentenceTransformer

# python imports
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any
from dotenv import load_dotenv
import asyncio
import json
import ast
import os
import re

# openai imports
from openai import AsyncOpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
os.environ["OPENAI_API_KEY"]=OPENAI_API_KEY

openai_client = AsyncOpenAI()

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Phase3 Consolidators
def safe_parse(text):
    if isinstance(text, dict):
        return text

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return ast.literal_eval(text)


def repair_and_parse_json(raw_text: str) -> Any:
    """
    Attempt to repair common LLM JSON formatting issues:
    - Single quotes instead of double quotes
    - Markdown ```json fences
    - Stray `json` tokens
    - Trailing commas
    - Extra text before/after JSON

    Returns:
        Parsed Python object (dict / list)

    Raises:
        ValueError if JSON cannot be repaired
    """

    text = raw_text

    # Remove markdown code fences
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```", "", text).strip()

    # Remove stray standalone 'json' tokens
    text = re.sub(r"\bjson\b", "", text, flags=re.IGNORECASE).strip()

    # Extract the JSON object/array only
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object or array found in output")

    text = match.group(1)

    # Remove trailing commas (JSON illegal)
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # json_text = json.loads(ast.literal_eval(json.dumps(text)))
    json_text = safe_parse(text)

    try:
        return json_text
    except json.JSONDecodeError as e:
        raise ValueError(
            f"JSON repair failed.\n"
            f"Original output:\n{raw_text}\n\n"
            f"Repaired attempt:\n{text}\n\n"
            f"Error: {e}"
        )
        

async def _call_llm(prompt: str, slm=False) -> Dict:
    """Call LLM with TPM-aware model fallback"""
    try:
        await asyncio.sleep(3)

        prompt += "\n\nRespond in JSON format."

        if slm:
            models = [
                "llama-3.3-70b-versatile",    # primary
                "openai/gpt-oss-20b",         # fallback 1
                "gpt-4o"         # fallback 2 (heaviest, last resort)
            ]
        else:
            models = [
                "gpt-4o",    # primary 
                "openai/gpt-oss-20b",         # fallback 1
            ]

        last_error = None

        for model in models:
            try:
                if "gpt-4o" == model:
                    response = await openai_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )

                content = response.choices[0].message.content
                return content

            except Exception as e:
                last_error = e
                err = str(e).lower()

                if any(k in err for k in ["tpm", "rate limit", "429", "tokens per minute"]):
                    print(f"TPM error on {model}, switching model...")
                    await asyncio.sleep(2)
                    continue
                else:
                    raise 

        raise last_error

    except Exception as e:
        print(f"- LLM call failed: {e}")
        return {}
    
async def extract_topics(
    query: str,
    max_topics: int = 10
) -> Dict:

    prompt = f"""
You are an expert semantic decomposition system.

Your task is to analyze the user's query across TWO dimensions:

1. SEMANTIC TOPICS — the distinct subject-matter concepts
2. INTENT DIMENSIONS — the action or deliverable the user needs

USER QUERY:
{query}

RULES FOR TOPICS:
- Extract distinct semantic concepts
- Focus on information needs
- Avoid paraphrases of each other
- Avoid generic wording
- Each topic = DIFFERENT information

RULES FOR INTENT DIMENSIONS:
- Identify what the user needs to DO or PRODUCE
- Think about persona (who is asking?)
- Think about format (battlecard, script, questions, framework?)
- Think about use-case (sales call, email, meeting prep?)
- These are equally important as topics

EXAMPLE for a sales battlecard query:
topics:
  - engineering time cost
  - maintenance burden
  - opportunity cost
  - ROI proof points
  - scalability risks
  - technical debt

intent_dimensions:
  - discovery questions to ask prospects
  - verbal objection response script
  - cost quantification framework
  - competitive proof points
  - risk exposure framing

    "intent_dimensions examples":
    - case study narrative structure        # ← catches "present this as"
    - trigger moment documentation          # ← catches "triggered upsell"
    - champion stakeholder identification   # ← catches "stakeholder feedback"
    - growth story arc for prospects        # ← catches "growth case study"
    
OUTPUT JSON:
{{
    "topics": ["topic1", "topic2"],
    "intent_dimensions": ["intent1", "intent2"]
}}
"""

    result = await _call_llm(prompt)
    result = repair_and_parse_json(result)

    topics = [
        str(t).strip()
        for t in result.get("topics", [])
        if str(t).strip()
    ]

    intent_dimensions = [
        str(i).strip()
        for i in result.get("intent_dimensions", [])
        if str(i).strip()
    ]

    return {
        "topics": list(dict.fromkeys(topics)),
        "intent_dimensions": list(dict.fromkeys(intent_dimensions))
    }


# =========================================================
# STEP 2 — GENERATE SUBQUERIES IN TWO PASSES
# =========================================================
# FIX: Previously generated all queries in one pass, which
# caused the LLM to over-index on subject-matter and ignore
# persona-specific action queries.
#
# Now runs TWO separate passes:
#   Pass A — knowledge/evidence queries (what do we know?)
#   Pass B — action/persona queries (what does the user do?)
#
# This guarantees coverage of both dimensions.
# =========================================================

async def generate_knowledge_queries(
    query: str,
    topics: List[str],
    max_queries: int = 8
) -> List[str]:
    """Pass A — retrieves evidence, data, proof points, research."""

    topics_text = "\n".join([f"- {t}" for t in topics])

    prompt = f"""
You are an expert enterprise research assistant.

PRIMARY USER QUERY:
{query}

SEMANTIC TOPICS:
{topics_text}

TASK:
Generate HIGH-QUALITY natural language research subqueries
that will retrieve EVIDENCE, DATA, and PROOF POINTS.

Each query should retrieve meaningfully DIFFERENT evidence.
Do NOT generate queries that overlap with each other.

GOOD EXAMPLES:
- How much engineering time does an internal build typically consume?
- What hidden maintenance costs emerge after a custom tool launches?
- Why do internally built tools struggle to scale beyond initial scope?
- What is the typical ROI gap between vendor solutions and custom builds?
- How does technical debt accumulate in custom internal software?

BAD EXAMPLES (too similar to each other — pick ONE not both):
- Hidden costs of building software in-house
- Operational costs of in-house software development   ← same thing

MAX QUERIES: {max_queries}

OUTPUT JSON:
{{
    "queries": ["query1", "query2"]
}}
"""

    result = await _call_llm(prompt)
    result = repair_and_parse_json(result)

    queries = [
        str(q).strip()
        for q in result.get("queries", [])
        if str(q).strip()
    ]
    return list(dict.fromkeys(queries))


async def generate_action_queries(
    query: str,
    intent_dimensions: List[str],
    max_queries: int = 7
) -> List[str]:
    """Pass B — retrieves scripts, frameworks, talk tracks, questions."""

    intents_text = "\n".join([f"- {d}" for d in intent_dimensions])

    prompt = f"""
You are an expert enterprise sales enablement assistant.

PRIMARY USER QUERY:
{query}

INTENT DIMENSIONS (what the user needs to do or produce):
{intents_text}

TASK:
Generate HIGH-QUALITY natural language subqueries that will
retrieve ACTION-ORIENTED content — scripts, frameworks,
questions to ask, talk tracks, objection handlers.

Think from the perspective of the PERSONA in the query.
What would they search for to prepare for this situation?

GOOD EXAMPLES:
- What questions should a sales rep ask to make a prospect quantify their build cost?
- How should an AE respond verbally when a prospect says they will build in-house?
- What is a framework for helping prospects calculate total cost of ownership of a build?
- What discovery questions expose underestimated costs in an in-house development plan?
- How do top sales reps reframe a build vs buy conversation toward long-term risk?

BAD EXAMPLES:
- build vs buy analysis
- software ROI metrics

MAX QUERIES: {max_queries}

OUTPUT JSON:
{{
    "queries": ["query1", "query2"]
}}
"""

    result = await _call_llm(prompt)
    result = repair_and_parse_json(result)

    queries = [
        str(q).strip()
        for q in result.get("queries", [])
        if str(q).strip()
    ]
    return list(dict.fromkeys(queries))


# =========================================================
# STEP 3 — SEMANTIC DEDUPLICATION
# =========================================================
# FIX: Lowered default threshold from 0.84 → 0.80 to catch
# near-paraphrases like "hidden costs" vs "operational costs"
# that were slipping through before.
# Also runs dedup WITHIN each pass before merging, then
# a final dedup across the combined set.
# =========================================================

def deduplicate_queries(
    queries: List[str],
    threshold: float = 0.80   # tighter than before (was 0.84)
) -> List[str]:

    if len(queries) <= 1:
        return queries

    embeddings = embedding_model.encode(
        queries,
        normalize_embeddings=True
    )

    keep = []
    removed = set()

    for i, q in enumerate(queries):

        if i in removed:
            continue

        keep.append(q)

        similarities = cosine_similarity(
            [embeddings[i]],
            embeddings
        )[0]

        for j, sim in enumerate(similarities):
            if i == j:
                continue
            if sim >= threshold:
                removed.add(j)

    return keep


# FINAL PIPELINE
async def generate_nl_subqueries(
    query: str,
    target_count: int = 7,
    max_topics: int = 10,
):

    # -----------------------------------------
    # STEP 1 — TOPIC + INTENT EXTRACTION
    # -----------------------------------------

    extraction = await extract_topics(
        query=query,
        max_topics=max_topics
    )

    topics = extraction["topics"]
    intent_dimensions = extraction["intent_dimensions"]

    # Scale per-pass budgets proportionally to target_count so the LLM
    # never generates far more queries than needed.
    max_knowledge_queries = 8 # max(3, round(target_count * 0.7))
    max_action_queries    = 7 # max(2, round(target_count * 0.6))

    # -----------------------------------------
    # STEP 2A — KNOWLEDGE QUERIES (evidence)
    # -----------------------------------------

    knowledge_queries = await generate_knowledge_queries(
        query=query,
        topics=topics,
        max_queries=max_knowledge_queries
    )
    knowledge_queries = deduplicate_queries(knowledge_queries, threshold=0.80)

    # -----------------------------------------
    # STEP 2B — ACTION QUERIES (persona-aware)
    # -----------------------------------------

    action_queries = await generate_action_queries(
        query=query,
        intent_dimensions=intent_dimensions,
        max_queries=max_action_queries
    )
    action_queries = deduplicate_queries(action_queries, threshold=0.80)

    # -----------------------------------------
    # STEP 3 — MERGE + FINAL DEDUP ACROSS BOTH
    # -----------------------------------------
    # Action queries go first — preserved over generic knowledge ones
    # when similarity conflict arises.

    all_queries = action_queries + knowledge_queries
    final_queries = deduplicate_queries_smart(
        all_queries,
        target_count=target_count
    )
    # Hard cap: dedup binary search may overshoot when queries are very diverse
    final_queries = final_queries[:target_count]

    # Score each subquery by cosine similarity to the original query
    if final_queries:
        query_emb = embedding_model.encode([query], normalize_embeddings=True)
        sub_embs = embedding_model.encode(final_queries, normalize_embeddings=True)
        sims = cosine_similarity(query_emb, sub_embs)[0]
        payload = sorted(
            [{"question": q, "priority": float(s)} for q, s in zip(final_queries, sims)],
            key=lambda x: -x["priority"]
        )
    else:
        payload = []

    return payload


def deduplicate_queries_smart(
    queries: List[str],
    target_count: int = 10,        # how many you want at the end
    min_threshold: float = 0.70,   # never remove below this similarity
    max_threshold: float = 0.85    # always remove above this similarity
) -> List[str]:
    """
    Dynamically adjusts threshold to hit target_count
    instead of using a fixed cutoff that over/under removes.
    """
    if len(queries) <= target_count:
        return queries

    embeddings = embedding_model.encode(queries, normalize_embeddings=True)

    # Binary search for the right threshold
    lo, hi = min_threshold, max_threshold

    for _ in range(10):  # 10 iterations is enough
        mid = (lo + hi) / 2
        result = _apply_threshold(queries, embeddings, mid)

        if len(result) > target_count:
            hi = mid   # too many kept → be stricter
        elif len(result) < target_count:
            lo = mid   # too few kept → be looser
        else:
            return result

    # Return closest to target
    return _apply_threshold(queries, embeddings, (lo + hi) / 2)


def _apply_threshold(queries, embeddings, threshold):
    keep = []
    removed = set()
    for i, q in enumerate(queries):
        if i in removed:
            continue
        keep.append(q)
        sims = cosine_similarity([embeddings[i]], embeddings)[0]
        for j, sim in enumerate(sims):
            if i != j and sim >= threshold:
                removed.add(j)
    return keep

