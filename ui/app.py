"""
AI Builder — Evaluator console (Streamlit)

✔ Real backend progress
✔ Job polling
✔ Preview modal (fixed, scrollable)
✔ Export options
"""

from __future__ import annotations

from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from typing import Any
import requests
import logging
import time
import html
import os
from datetime import datetime

import streamlit as st

# ── Logging ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ── ENV ─────────────────────────────────────────────────
DEFAULT_INGEST_URL = os.getenv(
    "INGEST_API_URL",
    "http://127.0.0.1:8000/asset_builder/evaluate/",
)
API_USERNAME = os.getenv("API_USERNAME", "").strip()
API_PASSWORD = os.getenv("API_PASSWORD", "").strip()

# ── PAGE ────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Asset Builder · Evaluator Console",
    layout="wide",
)

# ── SESSION ─────────────────────────────────────────────
def _init_session():
    st.session_state.setdefault("last_response", None)
    st.session_state.setdefault("last_duration_ms", None)
    st.session_state.setdefault("show_preview", False)

_init_session()

# ── AUTH ────────────────────────────────────────────────
def _api_auth():
    if API_USERNAME and API_PASSWORD:
        return HTTPBasicAuth(API_USERNAME, API_PASSWORD)
    return None

# ── API ─────────────────────────────────────────────────
def start_job(url, query, k, tenant):
    resp = requests.post(
        url.rstrip("/") + "/",
        json={"query": query, "k": k, "tenant": tenant},
        timeout=600,
        auth=_api_auth(),
    )
    resp.raise_for_status()
    return resp.json()["job_id"]


def get_status(url, job_id):
    resp = requests.get(
        f"{url.rstrip('/')}/{job_id}",
        timeout=600,
        auth=_api_auth(),
    )
    resp.raise_for_status()
    return resp.json()


def parse_results_map(primary, results_map):
    prefix = primary + "~"
    rows = []
    for k, v in results_map.items():
        sub = k[len(prefix):] if k.startswith(prefix) else k
        rows.append({"sub_query": sub, "doc": v})
    return rows

# ── PIPELINE ────────────────────────────────────────────
def run_pipeline(url, query, k, tenant):

    progress = st.progress(0)
    status = st.empty()

    job_id = start_job(url, query, k, tenant)
    status.info(f"Job started: {job_id}")

    t0 = time.perf_counter()

    while True:
        job = get_status(url, job_id)

        progress.progress(job.get("progress", 0) / 100)
        status.markdown(f"**{job.get('message','')}**")

        if job["status"] == "completed":
            return {
                "query": query,
                "results_map": job["results_map"],
                "_duration_ms": (time.perf_counter() - t0) * 1000,
            }

        if job["status"] == "failed":
            raise Exception(job.get("error"))

        time.sleep(5)

# ── AUTHENTICATION LOGIC ────────────────────────────────
def check_password():
    """Returns True if the user has the correct password."""
    if st.session_state.get("password_correct"):
        return True

    # Login UI
    st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style='font-size: 2.5rem;'>🔐 AI Asset Builder</h1>
            <p style="color: #666; font-size: 1.1rem;">Secure Content Evaluator Access Control</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_gate"):
            # We use keys to ensure state persistence
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pw")
            submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            
            if submit:
                # Matches credentials from your ENV variables
                if username == API_USERNAME and password == API_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
    return False

# ── 1. DIALOG DEFINITION (Outside the function) ───────────────────
@st.dialog("📄 Full Report Preview", width="large")
def show_full_preview(rows):
    """Displays a scrollable modal with all sub-query results."""
    content_html = ""
    for idx, r in enumerate(rows):
        content_html += f"<div style='margin-bottom:20px;'><h3 style='color:#1f77b4;'>{html.escape(r['sub_query'])}</h3>"
        content_html += f"<div style='background:#f8f9fa; padding:15px; border-radius:5px; border-left:4px solid #1f77b4; white-space:pre-wrap; font-family:monospace; font-size:0.9rem;'>{html.escape(r['doc'])}</div></div>"
        if idx < len(rows) - 1: 
            content_html += "<hr style='margin:25px 0; border:0; border-top:1px dashed #ccc;'/>"

    st.markdown(f'<div style="height:600px; overflow-y:auto; padding-right:10px;">{content_html}</div>', unsafe_allow_html=True)
    if st.button("Close Preview", use_container_width=True):
        st.session_state.show_preview = False
        st.rerun()

# ── 2. RENDER RESULTS FUNCTION ────────────────────────────────────
def render_results(data, duration):
    # Header Toolbar
    head_col1, head_col2, head_col3 = st.columns([4, 1, 1])
    with head_col1:
        st.markdown(f"""
        <div style="
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            background: #f0f4ff;
            border: 1px solid #d6e0ff;
            font-size: 13px;
            color: #1f4ed8;
            font-weight: 500;
            margin-bottom: 10px;
        ">
            ⏱️ {duration/1000:.2f}s
        </div>
        """, unsafe_allow_html=True)
    with head_col2:
        if st.button("↺ New Search", use_container_width=True):
            st.session_state.last_response = None
            st.rerun()
    with head_col3:
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            st.session_state["password_correct"] = False
            st.session_state.last_response = None
            st.rerun()

    # Data Preparation
    primary = data["query"]
    rows = parse_results_map(primary, data["results_map"])

    if not rows:
        st.warning("No results found.")
        return

    # Define full_report early to avoid NameError
    full_report = "\n\n---\n\n".join([f"## {r['sub_query']}\n\n{r['doc']}" for r in rows])
    
    # ── MODAL TRIGGER ──
    # We check the state here; if True, show dialog then immediately reset state
    if st.session_state.get("show_preview"):
        show_full_preview(rows)
        st.session_state.show_preview = False

    # Layout
    nav, content = st.columns([1, 2.5])

    # ── LEFT PANEL ─────────────────────────
    with nav:
        st.markdown("##### 📍 Sub-Queries")
        # Added a unique key to prevent reset on interaction
        selected = st.radio(
            "Sub Queries",
            [r["sub_query"] for r in rows],
            label_visibility="collapsed",
            key="sub_query_selector" 
        )
        st.divider()
        if st.button("👁️ Preview All Results", use_container_width=True):
            st.session_state.show_preview = True
            st.rerun()

    # ── RIGHT PANEL ────────────────────────
    with content:
        # Get the row matching the radio selection
        row = next(r for r in rows if r["sub_query"] == selected)
        
        st.markdown(f"#### {selected}")
        st.markdown(
            f"""
            <div style="padding:20px; border:1px solid #e6e9ef; background-color:white; border-radius:10px; height:450px; overflow:auto; box-shadow: inset 0 0 5px rgba(0,0,0,0.05); font-family: 'Source Code Pro', monospace;">
            {html.escape(row["doc"])}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("") 
        with st.container(border=True):
            st.markdown("##### 📦 Export Action Center")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = selected[:40].replace(" ", "_")

            col_batch, col_single = st.columns(2)
            with col_batch:
                st.caption("FULL JOB EXPORTS")
                st.download_button("📄 All Docs (.txt)", "\n\n---\n\n".join(r["doc"] for r in rows), file_name=f"all_docs_{ts}.txt", use_container_width=True)
                st.download_button("📑 Formatted Report", full_report, file_name=f"report_{ts}.txt", use_container_width=True)

            with col_single:
                st.caption("CURRENT SELECTION")
                st.download_button("📥 Download Selection", f"QUERY: {selected}\n\n{row['doc']}", file_name=f"selected_{safe}.txt", use_container_width=True)
                st.download_button("📝 Raw Text Only", row["doc"], file_name=f"raw_{safe}.txt", use_container_width=True)
# ── MAIN ────────────────────────────────────────────────
def main():
    if not check_password():
        st.stop()

    # Header section with title and Logout integrated in the main page
    title_col, logout_col = st.columns([5, 1])
    with title_col:
        st.markdown("""
            <style>
            .main-title { font-size: 2.2rem; font-weight: 700; color: #1E1E1E; }
            .sub-text { color: #666; margin-bottom: 2rem; }
            </style>
            <div class="main-title">AI Builder - Evaluator Console</div>
        """, unsafe_allow_html=True)

    # Show logout ONLY on starter page (no results yet)
    if not st.session_state.last_response:
        with logout_col:
            if st.button("🚪 Logout", key="top_logout", use_container_width=True):
                st.session_state["password_correct"] = False
                st.session_state.last_response = None
                st.rerun()

    if st.session_state.last_response:
        render_results(st.session_state.last_response, st.session_state.last_duration_ms)
    
    else:
        st.markdown("<div class='sub-text'>Ready for a new intelligence query.</div>", unsafe_allow_html=True)
        
        with st.expander("⚙️ Connection Settings", expanded=False):
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a: url = st.text_input("API URL", DEFAULT_INGEST_URL)
            with col_b: tenant = st.text_input("Tenant", "ironclad")
            with col_c: k = st.number_input("Top K", 1, 100, 10)

        with st.form("query_form", clear_on_submit=False):
            st.markdown("### 🔍 Search Query")
            query = st.text_area("Request:", placeholder="e.g. Find all clauses related to termination...", label_visibility="collapsed", height=150)
            col_btn, col_info = st.columns([1, 4])
            with col_btn:
                submit_button = st.form_submit_button("🚀 Run Query", use_container_width=True, type="primary")
            with col_info:
                st.caption("Tip: Press **Ctrl + Enter** to run instantly.")

        if submit_button:
            if not query.strip():
                st.warning("Please enter a query.")
                return
            try:
                with st.status("Processing Pipeline...", expanded=True) as status_box:
                    data = run_pipeline(url, query, k, tenant)
                    status_box.update(label="Query Complete!", state="complete", expanded=False)
                
                st.session_state.last_response = data
                st.session_state.last_duration_ms = data.pop("_duration_ms")
                st.rerun() 
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()