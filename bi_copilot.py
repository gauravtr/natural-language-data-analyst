"""
bi_copilot.py  —  LLM-powered BI Copilot
Primary LLM : Groq  (FREE — 14,400 req/day, 30 req/min — 10x Gemini free tier)
Fallback LLM: Gemini (if Groq also fails)

Why Groq:
  • Completely free, no credit card needed
  • 14,400 requests/day vs Gemini's ~1,500
  • Llama 3.3-70B produces excellent SQL
  • Same API cost optimisations as before

API tokens per query:
  Cached question  → 0 calls
  New question     → 1 call  (~500 input + ~150 output tokens)
  SQL needs fixing → +1 call
  Everything else  → local (explanations, chart selection, suggestions)
"""

import os
import re
import json
import time
import hashlib
import datetime
from collections import deque

import duckdb
import pandas as pd
import sqlglot
import yaml
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# LLM CLIENT SETUP  —  Groq primary, Gemini fallback
# ─────────────────────────────────────────────────────────────────────────────

GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Groq model chain (tried in order on quota errors)
# All are free-tier; Llama 3.3-70B is best for SQL
GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # best SQL quality
    "llama-3.1-8b-instant",      # fastest, lighter
    "gemma2-9b-it",              # Google's model on Groq infra
    "mixtral-8x7b-32768",        # large context window
]

# Gemini fallback chain
GEMINI_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]

DB_PATH        = os.getenv("DB_PATH", "bi_copilot.duckdb")
GLOSSARY_PATH  = "glossary.yaml"
SQL_CACHE_PATH = "sql_cache.json"

_groq_model_idx   = 0
_gemini_model_idx = 0

# ── Initialise clients (only if keys present) ─────────────────────────────────
_groq_client   = None
_gemini_ready  = False

try:
    if GROQ_API_KEY:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
        print("✓ Groq client ready")
    else:
        print("⚠ GROQ_API_KEY not set — will fall back to Gemini")
except ImportError:
    print("⚠ groq package not installed. Run: pip install groq")

try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_ready = True
        print("✓ Gemini client ready (fallback)")
    else:
        print("⚠ GEMINI_API_KEY not set")
except ImportError:
    print("⚠ google-generativeai not installed")

if not _groq_client and not _gemini_ready:
    raise ValueError(
        "No LLM available.\n"
        "Add at least one key to your .env file:\n"
        "  GROQ_API_KEY=gsk_...    (free at console.groq.com)\n"
        "  GEMINI_API_KEY=AIza...  (free at aistudio.google.com)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMITER
# ─────────────────────────────────────────────────────────────────────────────
_CALL_LOG: deque = deque(maxlen=25)   # Groq allows 30/min — stay under
_RATE_WINDOW     = 60


def _rate_limit_wait() -> None:
    if len(_CALL_LOG) < 25:
        return
    elapsed = time.time() - _CALL_LOG[0]
    if elapsed < _RATE_WINDOW:
        time.sleep(_RATE_WINDOW - elapsed + 1)


# ─────────────────────────────────────────────────────────────────────────────
# GROQ CALL
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(system_instruction: str, user_message: str, max_tokens: int = 400) -> str:
    global _groq_model_idx
    if not _groq_client:
        raise RuntimeError("Groq client not initialised")

    models_tried = 0
    while models_tried < len(GROQ_MODELS):
        model = GROQ_MODELS[_groq_model_idx]
        try:
            resp = _groq_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",  "content": system_instruction},
                    {"role": "user",    "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=0,
            )
            _CALL_LOG.append(time.time())
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e).lower()
            is_quota = any(k in err for k in ("quota", "429", "rate", "exhausted", "limit"))
            if is_quota or "404" in err or "not found" in err:
                _groq_model_idx = (_groq_model_idx + 1) % len(GROQ_MODELS)
                models_tried += 1
                continue
            raise RuntimeError(f"Groq error: {e}") from e

    raise RuntimeError("All Groq models quota-exhausted")


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI CALL  (fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini(system_instruction: str, user_message: str, max_tokens: int = 400) -> str:
    global _gemini_model_idx
    if not _gemini_ready:
        raise RuntimeError("Gemini client not initialised")

    models_tried = 0
    while models_tried < len(GEMINI_MODELS):
        model_name = GEMINI_MODELS[_gemini_model_idx]
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens, temperature=0.0
                ),
            )
            resp = model.generate_content(user_message)
            _CALL_LOG.append(time.time())
            return resp.text.strip()
        except Exception as e:
            err = str(e).lower()
            is_quota = any(k in err for k in ("quota", "429", "resource_exhausted", "rate"))
            if is_quota or "not found" in err or "404" in err:
                _gemini_model_idx = (_gemini_model_idx + 1) % len(GEMINI_MODELS)
                models_tried += 1
                continue
            raise RuntimeError(f"Gemini error: {e}") from e

    raise RuntimeError("All Gemini models quota-exhausted")


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED CALL  —  Groq first, Gemini fallback, clear error if both fail
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(system_instruction: str, user_message: str, max_tokens: int = 400) -> str:
    """
    Try Groq first (most generous free tier).
    If Groq fails or is unavailable, fall back to Gemini.
    """
    _rate_limit_wait()

    # Try Groq
    if _groq_client:
        try:
            return _call_groq(system_instruction, user_message, max_tokens)
        except RuntimeError as e:
            if "quota-exhausted" not in str(e).lower() and "not initialised" not in str(e).lower():
                raise  # real error, not a quota issue — propagate
            # Groq quota exhausted → fall through to Gemini
            print(f"Groq quota hit, falling back to Gemini. ({e})")

    # Try Gemini
    if _gemini_ready:
        try:
            return _call_gemini(system_instruction, user_message, max_tokens)
        except RuntimeError as e:
            if "quota-exhausted" not in str(e).lower():
                raise

    raise RuntimeError(
        "All LLM providers are quota-exhausted.\n\n"
        "Options:\n"
        "  1. Wait 60 seconds (per-minute quota resets)\n"
        "  2. Create a new FREE Groq key at console.groq.com\n"
        "     → Groq gives 14,400 req/day vs Gemini's ~1,500\n"
        "  3. Create a new Gemini key in a NEW Google Cloud project\n"
        "     at console.cloud.google.com (separate quota per project)\n\n"
        "Both keys are completely free — no credit card needed."
    )


def get_active_provider() -> str:
    """Return which LLM is currently being used (for UI display)."""
    if _groq_client:
        return f"Groq / {GROQ_MODELS[_groq_model_idx]}"
    if _gemini_ready:
        return f"Gemini / {GEMINI_MODELS[_gemini_model_idx]}"
    return "none"


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTENT SQL CACHE  —  repeated questions cost ZERO API calls
# ─────────────────────────────────────────────────────────────────────────────

def _load_sql_cache() -> dict:
    if os.path.exists(SQL_CACHE_PATH):
        try:
            with open(SQL_CACHE_PATH) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_sql_cache(cache: dict) -> None:
    try:
        with open(SQL_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=1)
    except Exception:
        pass


def _cache_key(query: str, schema_str: str) -> str:
    norm        = re.sub(r"\s+", " ", query.lower().strip())
    schema_hash = hashlib.md5(schema_str.encode()).hexdigest()[:10]
    return f"{schema_hash}::{norm}"


_SQL_CACHE = _load_sql_cache()


# ─────────────────────────────────────────────────────────────────────────────
# FILE LOADING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clean_col_names(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict = {}
    new_cols   = []
    for col in df.columns:
        c = re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip()).lower().strip("_") or "col"
        if c in seen:
            seen[c] += 1
            c = f"{c}_{seen[c]}"
        else:
            seen[c] = 0
        new_cols.append(c)
    df.columns = new_cols
    return df


def _table_name_from_filename(filename: str) -> str:
    base = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"[^a-zA-Z0-9]+", "_", base).lower().strip("_") or "uploaded_table"


# ─────────────────────────────────────────────────────────────────────────────
# 1. SCHEMA RETRIEVAL + COMPACT SERIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def get_schema(conn: duckdb.DuckDBPyConnection) -> dict:
    schema = {}
    try:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='main' AND table_type='BASE TABLE'"
        ).fetchdf()["table_name"].tolist()
    except Exception:
        return {}
    for table in tables:
        try:
            cols_df = conn.execute(f'DESCRIBE "{table}"').fetchdf()
        except Exception:
            continue
        columns = []
        for _, row in cols_df.iterrows():
            col_name, col_type = row["column_name"], row["column_type"]
            sample = None
            if any(t in col_type.upper() for t in ("DATE", "TIME", "VARCHAR")):
                try:
                    r = conn.execute(
                        f'SELECT "{col_name}" FROM "{table}" WHERE "{col_name}" IS NOT NULL LIMIT 1'
                    ).fetchone()
                    sample = str(r[0])[:20] if r else None
                except Exception:
                    pass
            columns.append({"name": col_name, "type": col_type, "sample": sample})
        schema[table] = {"columns": columns}
    return schema


def serialize_schema_compact(schema: dict) -> str:
    """Compact one-liner per table — 70% fewer tokens than CREATE TABLE blocks."""
    if not schema:
        return "(no tables)"
    lines = []
    for tname, meta in schema.items():
        cols = []
        for c in meta["columns"]:
            t = (c["type"].replace("INTEGER","INT").replace("VARCHAR","TXT")
                          .replace("DOUBLE","FLT").replace("DECIMAL","DEC")
                          .replace("BOOLEAN","BOOL").replace("BIGINT","INT"))
            entry = f"{c['name']}:{t}"
            if c.get("sample"):
                entry += f"({c['sample']})"
            cols.append(entry)
        lines.append(f'"{tname}"[{", ".join(cols)}]')
    return "\n".join(lines)


def _relevant_tables(schema: dict, query: str) -> dict:
    """Send only matching tables to reduce input tokens on large schemas."""
    if len(schema) <= 3:
        return schema
    q = query.lower()
    relevant = {
        t: m for t, m in schema.items()
        if t.lower() in q or t.lower().rstrip("s") in q
        or any(c["name"].lower() in q for c in m["columns"] if len(c["name"]) > 3)
    }
    return relevant if relevant else schema


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUSINESS GLOSSARY
# ─────────────────────────────────────────────────────────────────────────────

def load_glossary(path: str = GLOSSARY_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_relevant_glossary_entries(query: str, glossary: dict) -> list:
    q = query.lower()
    return [
        f"{term}={str(expr).strip()}"
        for term, expr in glossary.items()
        if term.replace("_", " ") in q or term in q
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 3. SQL GENERATION  — 1 LLM call, SQL only (minimal tokens)
# ─────────────────────────────────────────────────────────────────────────────

def generate_sql(user_query: str, schema_compact: str, glossary_entries: list, history: deque) -> str:
    parts = [
        "DuckDB SQL expert. Return ONLY a SELECT query. No markdown. No explanation.",
        f"Today: {datetime.date.today().isoformat()}",
        f"Schema:\n{schema_compact}",
    ]
    if glossary_entries:
        parts.append("Defs: " + "; ".join(glossary_entries))
    if history:
        h = history[-1]
        parts.append(f"Prev Q: {h['query']}")
    parts.append('Rules: quote tables "like_this"; alias aggregates AS name; SELECT only.')

    raw = call_llm("\n".join(parts), user_query, max_tokens=350)
    return re.sub(r"```(?:sql)?\s*", "", raw).strip().rstrip("`").strip()


def fix_sql(original_sql: str, error: str, schema_compact: str) -> str:
    raw = call_llm(
        f"Fix this DuckDB SQL. Return ONLY the corrected SQL.\nSchema:\n{schema_compact}",
        f"SQL:\n{original_sql}\nError: {error[:200]}",
        max_tokens=350,
    )
    return re.sub(r"```(?:sql)?\s*", "", raw).strip().rstrip("`").strip()


# ─────────────────────────────────────────────────────────────────────────────
# 4. SQL VALIDATOR  (local — zero API)
# ─────────────────────────────────────────────────────────────────────────────

_FORBIDDEN = {"INSERT","UPDATE","DELETE","DROP","CREATE","ALTER","TRUNCATE","GRANT","REVOKE"}


def validate_sql(sql: str) -> dict:
    if not sql.strip():
        return {"valid": False, "error": "Empty SQL."}
    for kw in _FORBIDDEN:
        if re.search(rf"\b{kw}\b", sql.upper()):
            return {"valid": False, "error": f"Forbidden: '{kw}'."}
    try:
        sqlglot.parse_one(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as e:
        return {"valid": False, "error": f"Syntax error: {str(e)[:200]}"}
    return {"valid": True, "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# 5. SELF-HEALING EXECUTOR
# ─────────────────────────────────────────────────────────────────────────────

def execute_with_healing(sql, conn, schema_compact, max_attempts=3):
    current_sql = sql
    for attempt in range(1, max_attempts + 1):
        try:
            return conn.execute(current_sql).fetchdf(), current_sql, attempt
        except Exception as e:
            if attempt == max_attempts:
                raise RuntimeError(f"SQL failed after {max_attempts} attempts: {e}") from e
            current_sql = fix_sql(current_sql, str(e), schema_compact)
    raise RuntimeError("Unexpected loop exit")


# ─────────────────────────────────────────────────────────────────────────────
# 6. CHART AUTO-SELECTOR  (local — zero API)
# ─────────────────────────────────────────────────────────────────────────────

def pick_chart_type(df: pd.DataFrame) -> str:
    if df.empty or len(df.columns) == 0:
        return "table"
    has_dt = any(
        "datetime" in str(d).lower() or pd.api.types.is_datetime64_any_dtype(df[c])
        for c, d in zip(df.columns, df.dtypes)
    )
    n_cats = sum(pd.api.types.is_string_dtype(df[c]) for c in df.columns)
    n_nums = sum(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns)
    n_rows, n_cols = len(df), len(df.columns)

    if has_dt and n_nums >= 1:                                  return "line"
    if n_cols == 1:                                             return "table"
    if n_cats == 1 and n_nums == 1:
        col2 = df.columns[1].lower()
        if n_rows <= 8 and any(w in col2 for w in ("pct","percent","share","ratio")):
            return "pie"
        return "bar" if n_rows <= 15 else "line"
    if n_cats == 0 and n_nums == 2:                             return "scatter"
    if n_cats >= 1 and n_nums >= 1 and n_rows <= 30:           return "bar"
    if n_cols > 4:                                              return "table"
    return "bar"


# ─────────────────────────────────────────────────────────────────────────────
# 7. LOCAL EXPLAINER  (zero API — templates from DataFrame)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(v) -> str:
    if isinstance(v, float): return f"{v:,.2f}".rstrip("0").rstrip(".")
    if isinstance(v, int):   return f"{v:,}"
    return str(v)


def local_explain(query: str, df: pd.DataFrame) -> str:
    if df.empty:
        return "The query returned no results."
    n_rows, n_cols = len(df), len(df.columns)
    cols = df.columns.tolist()

    if n_rows == 1 and n_cols == 1:
        return f"**{_fmt(df.iloc[0, 0])}** — {cols[0].replace('_', ' ')}."

    if n_rows == 1:
        pairs = ", ".join(
            f"{c.replace('_',' ')}: **{_fmt(df.iloc[0][c])}**" for c in cols[:4]
        )
        return f"{pairs}."

    if n_cols == 2 and pd.api.types.is_numeric_dtype(df[cols[1]]):
        top = df.iloc[0]
        return (
            f"**{top[cols[0]]}** has the highest {cols[1].replace('_',' ')} "
            f"at **{_fmt(top[cols[1]])}** out of {n_rows} results."
        )

    return (
        f"Returned **{n_rows:,} rows** — "
        f"columns: {', '.join(c.replace('_',' ') for c in cols[:5])}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. LOCAL QUESTION SUGGESTIONS  (zero API — from column types)
# ─────────────────────────────────────────────────────────────────────────────

def local_suggest_questions(schema: dict) -> list:
    questions = []
    for tname, meta in schema.items():
        num_cols  = [c["name"] for c in meta["columns"]
                     if any(t in c["type"].upper() for t in ("INT","DEC","FLT","FLOAT","DOUBLE","BIGINT"))]
        cat_cols  = [c["name"] for c in meta["columns"]
                     if any(t in c["type"].upper() for t in ("VARCHAR","TXT","TEXT"))]
        date_cols = [c["name"] for c in meta["columns"]
                     if "DATE" in c["type"].upper() or "TIME" in c["type"].upper()]
        nice = lambda s: s.replace("_", " ")

        if num_cols and cat_cols:
            questions.append(f"Which {nice(cat_cols[0])} has the highest {nice(num_cols[0])}?")
        if date_cols and num_cols:
            questions.append(f"Show {nice(num_cols[0])} trend over time")
        if cat_cols:
            questions.append(f"How many records per {nice(cat_cols[0])}?")
        if num_cols:
            questions.append(f"What is the average {nice(num_cols[0])}?")
        if len(num_cols) >= 2:
            questions.append(f"Top 10 rows by {nice(num_cols[0])}")
        if len(questions) >= 5:
            break

    seen, out = set(), []
    for q in questions:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out[:5]


# ─────────────────────────────────────────────────────────────────────────────
# 9. BICopilot  —  main class
# ─────────────────────────────────────────────────────────────────────────────

class BICopilot:
    def __init__(self, db_path=None, glossary_path=GLOSSARY_PATH, history_size=3):
        if db_path and os.path.exists(db_path):
            self.conn = duckdb.connect(db_path)
        else:
            self.conn = duckdb.connect(":memory:")

        self.glossary      = load_glossary(glossary_path)
        self.schema        = get_schema(self.conn)
        self.schema_str    = serialize_schema_compact(self.schema)
        self.history       = deque(maxlen=history_size)
        self.loaded_tables = []
        self.last_cache_hit = False
        print(f"BICopilot ready  |  provider: {get_active_provider()}")

    # ── File management ───────────────────────────────────────────────────────

    def load_file(self, file_obj, table_name=None) -> dict:
        filename = getattr(file_obj, "name", "upload")
        ext      = os.path.splitext(filename)[1].lower()

        if ext == ".csv":
            df = pd.read_csv(file_obj)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_obj)
        elif ext == ".json":
            try:
                df = pd.read_json(file_obj)
            except Exception:
                data = json.load(file_obj)
                df   = pd.json_normalize(data) if isinstance(data, dict) else pd.DataFrame(data)
        elif ext in (".tsv", ".txt"):
            df = pd.read_csv(file_obj, sep="\t")
        else:
            raise ValueError(f"Unsupported: '{ext}'. Use .csv .xlsx .xls .json .tsv")

        if df.empty:
            raise RuntimeError(f"'{filename}' is empty.")

        if not table_name:
            table_name = _table_name_from_filename(filename)
        if table_name in {"information_schema", "main", "pg_catalog"}:
            table_name = f"upload_{table_name}"

        df = _clean_col_names(df)
        self.conn.register("_tmp_upload", df)
        self.conn.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM _tmp_upload')
        self.conn.unregister("_tmp_upload")

        if table_name not in self.loaded_tables:
            self.loaded_tables.append(table_name)
        self.refresh_schema()
        self.history.clear()

        return {
            "table_name": table_name,
            "rows":       len(df),
            "columns":    list(df.columns),
            "dtypes":     {c: str(t) for c, t in zip(df.columns, df.dtypes)},
            "preview":    df.head(5),
        }

    def drop_table(self, table_name: str) -> None:
        self.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        if table_name in self.loaded_tables:
            self.loaded_tables.remove(table_name)
        self.refresh_schema()
        self.history.clear()

    def reset_to_empty(self) -> None:
        for t in list(self.loaded_tables):
            try:
                self.conn.execute(f'DROP TABLE IF EXISTS "{t}"')
            except Exception:
                pass
        self.loaded_tables.clear()
        self.history.clear()
        self.refresh_schema()

    def refresh_schema(self) -> None:
        self.schema     = get_schema(self.conn)
        self.schema_str = serialize_schema_compact(self.schema)

    def suggest_questions(self) -> list:
        return local_suggest_questions(self.schema)

    # ── Main query pipeline ───────────────────────────────────────────────────

    def query(self, user_query: str) -> dict:
        if not self.schema:
            return {"type": "no_data", "query": user_query,
                    "error": "No data loaded. Upload a file or click 'Use demo data'."}

        self.last_cache_hit = False

        # ── Cache check (ZERO API on hit) ─────────────────────────────────────
        key        = _cache_key(user_query, self.schema_str)
        cached_sql = _SQL_CACHE.get(key)
        if cached_sql:
            try:
                df = self.conn.execute(cached_sql).fetchdf()
                self.last_cache_hit = True
                self.history.append({"query": user_query, "sql": cached_sql})
                return {
                    "type": "result", "query": user_query, "sql": cached_sql,
                    "dataframe": df, "chart_type": pick_chart_type(df),
                    "explanation": local_explain(user_query, df),
                    "attempts": 0, "glossary_used": [], "from_cache": True,
                }
            except Exception:
                _SQL_CACHE.pop(key, None)

        # ── Trim schema + glossary ────────────────────────────────────────────
        rel_schema       = _relevant_tables(self.schema, user_query)
        schema_compact   = serialize_schema_compact(rel_schema)
        glossary_entries = get_relevant_glossary_entries(user_query, self.glossary)

        # ── 1 API call: SQL generation ────────────────────────────────────────
        try:
            sql = generate_sql(user_query, schema_compact, glossary_entries, self.history)
        except RuntimeError as e:
            return {"type": "error", "query": user_query, "error": str(e)}

        # ── Validate locally ──────────────────────────────────────────────────
        val = validate_sql(sql)
        if not val["valid"]:
            try:
                sql = fix_sql(sql, val["error"], schema_compact)
            except RuntimeError as e:
                return {"type": "error", "query": user_query, "error": str(e)}

        # ── Execute with self-healing ─────────────────────────────────────────
        try:
            df, final_sql, attempts = execute_with_healing(sql, self.conn, schema_compact)
        except RuntimeError as e:
            return {"type": "error", "query": user_query, "error": str(e)}

        # ── Cache the successful SQL ──────────────────────────────────────────
        _SQL_CACHE[key] = final_sql
        _save_sql_cache(_SQL_CACHE)

        self.history.append({"query": user_query, "sql": final_sql})

        return {
            "type":          "result",
            "query":         user_query,
            "sql":           final_sql,
            "dataframe":     df,
            "chart_type":    pick_chart_type(df),
            "explanation":   local_explain(user_query, df),
            "attempts":      attempts,
            "glossary_used": glossary_entries,
            "from_cache":    False,
        }