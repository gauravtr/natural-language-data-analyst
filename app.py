"""
app.py  —  BI Copilot Streamlit UI (universal dataset version)

New in this version:
  • Upload any CSV / Excel / JSON — works instantly
  • See data preview and schema after upload
  • Auto-generated starter questions per dataset
  • Multi-table support (upload several files, join them)
  • Switch between demo data and your own data anytime
  • Delete individual tables without resetting everything

Run: streamlit run app.py
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from bi_copilot import BICopilot

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BI Copilot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    if "copilot" not in st.session_state:
        st.session_state.copilot             = BICopilot()   # empty in-memory DB
        st.session_state.messages            = []
        st.session_state.table_info          = []            # list of load_file() dicts
        st.session_state.suggested_questions = []
        st.session_state.data_mode           = "none"        # "none" | "demo" | "upload"
        st.session_state.processed_files     = set()         # tracks already-loaded uploads

_init_state()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def render_chart(df: pd.DataFrame, chart_type: str, title: str = "") -> None:
    if df.empty:
        st.info("Query returned no rows.")
        return
    cols = df.columns.tolist()
    try:
        kw = dict(title=title)
        if chart_type == "line" and len(cols) >= 2:
            fig = px.line(df, x=cols[0], y=cols[1], markers=True, **kw)
        elif chart_type == "bar" and len(cols) >= 2:
            fig = px.bar(df, x=cols[0], y=cols[1],
                         color=cols[0],
                         color_discrete_sequence=px.colors.qualitative.Pastel, **kw)
        elif chart_type == "scatter" and len(cols) >= 2:
            fig = px.scatter(df, x=cols[0], y=cols[1], **kw)
        elif chart_type == "pie" and len(cols) >= 2:
            fig = px.pie(df, names=cols[0], values=cols[1], **kw)
        else:
            st.dataframe(df, use_container_width=True)
            return
        fig.update_layout(showlegend=False, margin=dict(t=40, l=0, r=0, b=0), height=380)
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.dataframe(df, use_container_width=True)


def _load_demo() -> None:
    """Switch to the bundled Northwind demo database."""
    import os
    if not os.path.exists("bi_copilot.duckdb"):
        st.error("Demo database not found. Run `python setup_db.py` first.")
        return
    st.session_state.copilot             = BICopilot(db_path="bi_copilot.duckdb")
    st.session_state.messages            = []
    st.session_state.table_info          = []
    st.session_state.suggested_questions = st.session_state.copilot.suggest_questions()
    st.session_state.data_mode           = "demo"
    st.session_state.processed_files     = set()
    st.rerun()


def _reset_to_empty() -> None:
    """Drop all uploaded tables and start fresh."""
    st.session_state.copilot.reset_to_empty()
    st.session_state.messages            = []
    st.session_state.table_info          = []
    st.session_state.suggested_questions = []
    st.session_state.data_mode           = "none"
    st.session_state.processed_files     = set()
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 BI Copilot")
    st.caption("Ask any business question in plain English.")
    st.divider()

    # ── Data source ──────────────────────────────────────────────────────────
    st.markdown("### Data source")

    # Currently loaded tables
    if st.session_state.table_info:
        st.markdown("**Loaded tables:**")
        for info in st.session_state.table_info:
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.markdown(
                    f"📄 **{info['table_name']}**  \n"
                    f"<span style='font-size:11px;color:gray'>"
                    f"{info['rows']:,} rows · {len(info['columns'])} cols</span>",
                    unsafe_allow_html=True,
                )
            with col_b:
                if st.button("✕", key=f"drop_{info['table_name']}", help="Remove this table"):
                    st.session_state.copilot.drop_table(info["table_name"])
                    st.session_state.table_info = [
                        t for t in st.session_state.table_info
                        if t["table_name"] != info["table_name"]
                    ]
                    st.session_state.messages            = []
                    st.session_state.suggested_questions = (
                        st.session_state.copilot.suggest_questions()
                    )
                    if not st.session_state.table_info:
                        st.session_state.data_mode = "none"
                    st.rerun()
        st.markdown("")

    # Upload widget
    uploaded_files = st.file_uploader(
        "Upload CSV, Excel, or JSON",
        type=["csv", "xlsx", "xls", "json", "tsv"],
        accept_multiple_files=True,
        help="Each file becomes a separate queryable table. Upload multiple files to join them.",
    )

    if uploaded_files:
        for file in uploaded_files:
            file_id = f"{file.name}_{file.size}"
            if file_id not in st.session_state.processed_files:
                # First upload — switch copilot to in-memory if currently on demo
                if st.session_state.data_mode == "demo":
                    st.session_state.copilot = BICopilot()
                    st.session_state.messages = []
                    st.session_state.table_info = []

                with st.spinner(f"Loading {file.name}…"):
                    try:
                        info = st.session_state.copilot.load_file(file)
                        st.session_state.table_info.append(info)
                        st.session_state.processed_files.add(file_id)
                        st.session_state.data_mode           = "upload"
                        st.session_state.messages            = []
                        st.session_state.suggested_questions = (
                            st.session_state.copilot.suggest_questions()
                        )
                        st.success(f"✓ {info['table_name']} loaded ({info['rows']:,} rows)")
                    except Exception as e:
                        st.error(f"Error loading {file.name}: {e}")

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Use demo data", use_container_width=True,
                     help="Load the built-in Northwind e-commerce dataset"):
            _load_demo()
    with col2:
        if st.button("Reset all", use_container_width=True, type="secondary",
                     help="Remove all tables and start fresh"):
            _reset_to_empty()

    st.divider()

    # ── Suggested / example questions ─────────────────────────────────────────
    if st.session_state.suggested_questions:
        st.markdown("### Suggested questions")
        for q in st.session_state.suggested_questions:
            if st.button(q, use_container_width=True, key=f"sq_{q[:40]}"):
                st.session_state["pending_query"] = q
    elif st.session_state.data_mode == "demo":
        st.markdown("### Try these")
        demo_qs = [
            "Which product category had the highest revenue last year?",
            "Show me monthly revenue for 2023",
            "Who are the top 5 customers by total spend?",
            "Which country has the highest average order value?",
            "Which employee closed the most orders this year?",
        ]
        for q in demo_qs:
            if st.button(q, use_container_width=True, key=f"dq_{q[:40]}"):
                st.session_state["pending_query"] = q

    st.divider()
    if st.button("🗑 Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.copilot.history.clear()
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────

# ── Welcome screen (no data loaded) ──────────────────────────────────────────
if st.session_state.data_mode == "none":
    st.markdown("# Welcome to BI Copilot")
    st.markdown(
        "Ask any business question in plain English — the system writes the SQL, "
        "runs it, and shows you a chart with an explanation."
    )
    st.markdown("---")

    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        st.markdown("### 📂 Upload your own data")
        st.markdown(
            "Drag a file into the sidebar uploader. Supported formats:"
        )
        st.markdown(
            "- **CSV** — any comma-separated file\n"
            "- **Excel** (.xlsx / .xls) — first sheet is loaded\n"
            "- **JSON** — array of objects or records\n"
            "- **TSV** — tab-separated values\n\n"
            "You can upload **multiple files** — each becomes a separate table "
            "you can ask questions across."
        )

    with col_b:
        st.markdown("### 🛍 Or try the demo dataset")
        st.markdown(
            "Click **Use demo data** in the sidebar to load a pre-built "
            "Northwind-style e-commerce database with 6 tables: "
            "customers, orders, products, employees, categories, and order_details."
        )
        if st.button("Load demo data now →", type="primary"):
            _load_demo()

    st.stop()


# ── Data preview (shown right after upload, before any chat) ─────────────────
if st.session_state.table_info and not st.session_state.messages:
    st.markdown("### Data loaded — here's a preview")

    if len(st.session_state.table_info) == 1:
        info = st.session_state.table_info[0]
        st.markdown(
            f"**Table: `{info['table_name']}`** — "
            f"{info['rows']:,} rows, {len(info['columns'])} columns"
        )
        with st.expander("📋 Column names and types", expanded=True):
            dtype_df = pd.DataFrame([
                {"Column": col, "Type": info["dtypes"].get(col, "—")}
                for col in info["columns"]
            ])
            st.dataframe(dtype_df, use_container_width=True, hide_index=True)
        st.markdown("**First 5 rows:**")
        st.dataframe(info["preview"], use_container_width=True, hide_index=True)
    else:
        tabs = st.tabs([f"📄 {info['table_name']}" for info in st.session_state.table_info])
        for tab, info in zip(tabs, st.session_state.table_info):
            with tab:
                st.markdown(f"{info['rows']:,} rows · {len(info['columns'])} columns")
                with st.expander("Column names and types"):
                    dtype_df = pd.DataFrame([
                        {"Column": col, "Type": info["dtypes"].get(col, "—")}
                        for col in info["columns"]
                    ])
                    st.dataframe(dtype_df, use_container_width=True, hide_index=True)
                st.dataframe(info["preview"], use_container_width=True, hide_index=True)

    if st.session_state.suggested_questions:
        st.markdown("### Starter questions for your data")
        st.caption("Click any question to run it, or type your own below.")
        qs = st.session_state.suggested_questions
        cols = st.columns(min(len(qs), 2))
        for i, q in enumerate(qs):
            with cols[i % 2]:
                if st.button(q, use_container_width=True, key=f"pq_{i}"):
                    st.session_state["pending_query"] = q
                    st.rerun()

    st.markdown("---")


# ── Chat replay ───────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.write(msg["content"])
        elif msg.get("result_type") == "result":
            st.write(msg["explanation"])
            render_chart(msg["dataframe"], msg["chart_type"])
            label = "View generated SQL"
            if msg.get("attempts", 1) > 1:
                label += f"  _(auto-fixed in {msg['attempts']} attempts)_"
            with st.expander(label):
                st.code(msg["sql"], language="sql")
                if msg.get("glossary_used"):
                    terms = ", ".join(e.split(":")[0] for e in msg["glossary_used"])
                    st.caption(f"Business terms resolved: {terms}")
        elif msg.get("result_type") == "clarification":
            st.info(f"🤔 {msg['content']}")
        else:
            st.error(msg.get("content", "Unknown error"))


# ── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask a question about your data…")

# Handle sidebar button clicks (suggested questions)
if not prompt and "pending_query" in st.session_state:
    prompt = st.session_state.pop("pending_query")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = st.session_state.copilot.query(prompt)

        if result["type"] == "no_data":
            st.warning(result["error"])
            st.session_state.messages.append({
                "role": "assistant", "content": result["error"], "result_type": "error"
            })

        elif result["type"] == "clarification":
            msg = f"I need a bit more detail: **{result['question']}**"
            st.info(msg)
            st.session_state.messages.append({
                "role": "assistant", "content": msg, "result_type": "clarification"
            })

        elif result["type"] == "error":
            st.error(result["error"])
            st.session_state.messages.append({
                "role": "assistant", "content": result["error"], "result_type": "error"
            })

        else:
            st.write(result["explanation"])
            render_chart(result["dataframe"], result["chart_type"], title=prompt)

            label = "View generated SQL"
            if result["attempts"] > 1:
                label += f"  _(auto-fixed in {result['attempts']} attempts)_"
            with st.expander(label):
                st.code(result["sql"], language="sql")
                if result["glossary_used"]:
                    terms = ", ".join(e.split(":")[0] for e in result["glossary_used"])
                    st.caption(f"Business terms resolved: {terms}")

            st.session_state.messages.append({
                "role":          "assistant",
                "explanation":   result["explanation"],
                "dataframe":     result["dataframe"],
                "chart_type":    result["chart_type"],
                "sql":           result["sql"],
                "attempts":      result["attempts"],
                "glossary_used": result["glossary_used"],
                "result_type":   "result",
            })

    st.rerun()