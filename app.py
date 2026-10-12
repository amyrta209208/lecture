from __future__ import annotations

import base64
import html
import json
import math
import mimetypes
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from supabase import create_client
except Exception:  # Supabase is optional for local-only mode.
    create_client = None

APP_DIR = Path(__file__).parent.resolve()
ASSET_DIR = APP_DIR / "assets"
DATA_DIR = APP_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "wonderbook.sqlite3"
HERO_IMAGE = ASSET_DIR / "hero.png"
PATH_IMAGE = ASSET_DIR / "hijra_path.png"

st.set_page_config(
    page_title="Start the Hijra | Wonderbook",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


SUPABASE_URL = get_setting("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_setting("SUPABASE_SERVICE_KEY")
EDITOR_PASSWORD = get_setting("EDITOR_PASSWORD")
REMOTE_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY and create_client)


CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700;800&display=swap');
:root { --ink:#5e4225; --ink-soft:#8a714c; --cream:#fff9e9; --gold:#d7a343; --gold-dark:#9b6229; --leaf:#7d8c67; --line:#e8d7af; }
.stApp { background: radial-gradient(circle at 10% 2%, #fff9eb 0, #f5edcf 38%, #e8e0bc 100%); color:var(--ink); }
.block-container { max-width: 1450px; padding-top: 1.15rem; padding-bottom: 3rem; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
h1,h2,h3,h4 { font-family:'Playfair Display',Georgia,serif !important; color:#654621; }
section[data-testid="stSidebar"] { background:#f8f0d9; border-right:1px solid #dfc58e; }
.stButton > button { border-radius:999px; border:1px solid #d9b56f; background:linear-gradient(180deg,#ffeab0,#f2cb72); color:#694321; font-weight:700; box-shadow:0 3px 0 #d5a65b; min-height:2.7rem; }
.stButton > button:hover { border-color:#bc873f; color:#523216; box-shadow:0 4px 0 #bd8745; transform:translateY(-1px); }
.stButton > button:focus:not(:active) { outline:3px solid #b2bc82; }
.stTextInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"] > div,.stNumberInput input { border-radius:12px; border-color:#dcc89c; background:#fffdf4; }
[data-testid="stFileUploader"] section { background:#fffaf0; border:1px dashed #c9a260; border-radius:16px; }
[data-testid="stMetric"] { background:#fff9e9; border:1px solid #e8d7af; padding:12px 16px; border-radius:18px; }
.wb-eyebrow { text-transform:uppercase; letter-spacing:.18em; font-size:.72rem; font-weight:700; color:#ab7a31; margin-bottom:.5rem; }
.wb-subtitle { color:#7e6848; font-size:1.05rem; }
.wb-hero { background-size:cover; background-position:center; border:2px solid #d7ad5b; border-radius:28px; overflow:hidden; min-height:270px; padding:30px; box-shadow:0 9px 0 rgba(185,135,59,.16); display:flex; flex-direction:column; justify-content:flex-end; }
.wb-hero h1 { font-family:'Playfair Display',Georgia,serif !important; line-height:1.05; font-size:clamp(2.15rem,4vw,4rem); margin:0; max-width:720px; color:#674719; text-shadow:0 1px 10px rgba(255,250,227,.55); }
.wb-hero p { color:#775f3d; font-size:1.12rem; margin:.65rem 0 0; max-width:520px; }
.wb-section { background:rgba(255,251,238,.78); border:1px solid #e5d4a7; padding:18px 20px; border-radius:22px; margin:12px 0; }
.wb-map-shell { position:relative; margin:10px 0 22px; border:2px solid #d9b46c; border-radius:20px; overflow:hidden; box-shadow:0 7px 0 rgba(185,135,59,.14); }
.wb-map-image { width:100%; height:auto; display:block; }
.wb-map-marker { position:absolute; z-index:2; transform:translate(-50%,-50%); display:flex; flex-direction:column; align-items:center; gap:4px; text-decoration:none !important; color:#5c4125 !important; max-width:130px; }
.wb-map-marker .thumb-wrap { position:relative; width:clamp(48px,6vw,78px); height:clamp(48px,6vw,78px); border:5px solid #fff7e3; border-radius:50%; padding:2px; background:linear-gradient(140deg,#fffdf0,#d8b269); box-shadow:0 4px 0 #ba8d4a,0 8px 16px #624b2529; transition:transform .2s ease; }
.wb-map-marker:hover .thumb-wrap { transform:scale(1.08) rotate(-2deg); }
.wb-map-marker img { width:100%; height:100%; display:block; object-fit:cover; border-radius:50%; }
.wb-map-marker .label { background:#fff8e6; border:1px solid #d8b56e; border-radius:9px; padding:4px 8px; font-size:clamp(.6rem,.9vw,.8rem); line-height:1.1; font-weight:800; text-align:center; white-space:normal; max-width:130px; box-shadow:0 2px 0 #d4ae67; }
.wb-map-marker .score { position:absolute; top:-7px; right:-17px; background:#557a49; color:white; font-weight:800; font-size:.65rem; border:2px solid #fff5d8; border-radius:999px; padding:4px 6px; box-shadow:0 2px 4px #563d2033; }
.wb-map-marker .quiz-flag { background:#818866; color:white; position:absolute; top:-5px; left:75%; font-size:.58rem; font-weight:800; padding:3px 6px; border:2px solid #fff6dd; border-radius:999px; }
.wb-quiz-meter { position:sticky; top:5rem; min-height:260px; background:rgba(255,249,229,.85); border:1px solid #e4cb90; border-radius:18px; padding:12px 8px; display:flex; flex-direction:column; align-items:center; gap:10px; }
.wb-meter-track { width:17px; height:220px; background:#e7d9b7; border:2px solid #fff2d0; border-radius:999px; position:relative; overflow:hidden; box-shadow:inset 0 2px 6px #684a221b; }
.wb-meter-fill { position:absolute; bottom:0; left:0; right:0; border-radius:999px; background:linear-gradient(0deg,#6e8c50,#f5c95e); transition:height .45s ease; }
.wb-meter-label { writing-mode:vertical-rl; transform:rotate(180deg); text-transform:uppercase; letter-spacing:.15em; font-size:.65rem; color:#8c703d; font-weight:800; }
.wb-meter-number { font-weight:800; color:#715027; font-size:.85rem; }
.wb-note { font-size:.86rem; color:#8a7352; }
.wb-success { position:relative; overflow:hidden; padding:14px; border-radius:16px; border:1px solid #d2b66d; background:linear-gradient(140deg,#fff7d7,#edf2d5); text-align:center; color:#48643e; font-weight:800; animation:wbPop .35s ease-out; }
.wb-success:before,.wb-success:after { content:'✦  ✧  ✦'; position:absolute; color:#d8a83d; letter-spacing:10px; animation:wbSpark 1.3s ease-out infinite; opacity:.85; }
.wb-success:before { left:6px; top:5px; } .wb-success:after { right:0; bottom:3px; animation-delay:.3s; }
@keyframes wbPop { 0%{transform:scale(.96);opacity:.2} 70%{transform:scale(1.025)} 100%{transform:scale(1);opacity:1} }
@keyframes wbSpark { 0%{transform:translateY(4px);opacity:0} 35%{opacity:1} 100%{transform:translateY(-7px);opacity:0} }
.wb-bad { padding:13px; border-radius:14px; background:#fff0df; border:1px solid #e8bb89; color:#975c33; font-weight:700; }
.wb-footer { margin-top:2.2rem; padding-top:1rem; border-top:1px solid #e2cf9f; color:#947b52; font-size:.78rem; }
@media (max-width:700px) { .wb-hero{padding:19px;min-height:250px;border-radius:20px}.wb-map-marker .label{max-width:74px}.wb-map-marker .quiz-flag{display:none}.block-container{padding-left:.7rem;padding-right:.7rem} }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_ext(filename: str) -> str:
    suffix = Path(filename or "upload.bin").suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
        return ".bin"
    return suffix


def file_bytes(uploaded) -> bytes:
    uploaded.seek(0)
    return uploaded.read()


def data_uri(path: Path) -> str:
    raw = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


class WonderbookStore:
    def __init__(self):
        self.remote = REMOTE_ENABLED
        self.client = None
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        if self.remote:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            except Exception as exc:
                st.error(f"Could not connect to Supabase: {exc}")
                self.remote = False
        if not self.remote:
            self._init_local_db()

    def _connect(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_local_db(self):
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
                published INTEGER DEFAULT 1, items_json TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS attempts (
                id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL, image_id TEXT NOT NULL,
                viewer_id TEXT NOT NULL, correct INTEGER NOT NULL, total INTEGER NOT NULL,
                percentage REAL NOT NULL, created_at TEXT NOT NULL
            )""")
            conn.commit()

    def list_lessons(self, include_unpublished: bool = False) -> list[dict[str, Any]]:
        if self.remote:
            query = self.client.table("wonderbook_lessons").select("*").order("updated_at", desc=True)
            if not include_unpublished:
                query = query.eq("published", True)
            rows = query.execute().data or []
            return [self._lesson_from_row(row) for row in rows]
        with self._connect() as conn:
            if include_unpublished:
                rows = conn.execute("SELECT * FROM lessons ORDER BY updated_at DESC").fetchall()
            else:
                rows = conn.execute("SELECT * FROM lessons WHERE published=1 ORDER BY updated_at DESC").fetchall()
        return [
            {"id": r["id"], "title": r["title"], "description": r["description"],
             "published": bool(r["published"]), "items": json.loads(r["items_json"]), "updated_at": r["updated_at"]}
            for r in rows
        ]

    @staticmethod
    def _lesson_from_row(row: dict[str, Any]) -> dict[str, Any]:
        items = row.get("items", [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = []
        return {"id": row["id"], "title": row.get("title", "Untitled lesson"),
                "description": row.get("description", ""), "published": bool(row.get("published", True)),
                "items": items or [], "updated_at": row.get("updated_at", "")}

    def get_lesson(self, lesson_id: str, include_unpublished: bool = True) -> dict[str, Any] | None:
        if not lesson_id:
            return None
        if self.remote:
            query = self.client.table("wonderbook_lessons").select("*").eq("id", lesson_id).limit(1)
            rows = query.execute().data or []
            if not rows:
                return None
            lesson = self._lesson_from_row(rows[0])
            if not include_unpublished and not lesson["published"]:
                return None
            return lesson
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        if row is None or (not include_unpublished and not bool(row["published"])):
            return None
        return {"id": row["id"], "title": row["title"], "description": row["description"],
                "published": bool(row["published"]), "items": json.loads(row["items_json"]), "updated_at": row["updated_at"]}

    def save_lesson(self, lesson: dict[str, Any]) -> None:
        lesson["updated_at"] = utc_now()
        if self.remote:
            payload = {"id": lesson["id"], "title": lesson["title"], "description": lesson.get("description", ""),
                       "published": bool(lesson.get("published", True)), "items": lesson.get("items", []),
                       "updated_at": lesson["updated_at"]}
            self.client.table("wonderbook_lessons").upsert(payload).execute()
            return
        with self._connect() as conn:
            conn.execute("""INSERT INTO lessons(id,title,description,published,items_json,updated_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,
                description=excluded.description,published=excluded.published,
                items_json=excluded.items_json,updated_at=excluded.updated_at""",
                (lesson["id"], lesson["title"], lesson.get("description", ""), int(bool(lesson.get("published", True))),
                 json.dumps(lesson.get("items", []), ensure_ascii=False), lesson["updated_at"]))
            conn.commit()

    def delete_lesson(self, lesson_id: str) -> None:
        if self.remote:
            self.client.table("wonderbook_lessons").delete().eq("id", lesson_id).execute()
        else:
            with self._connect() as conn:
                conn.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))
                conn.execute("DELETE FROM attempts WHERE lesson_id=?", (lesson_id,))
                conn.commit()

    def save_media(self, lesson_id: str, uploaded, kind: str) -> str:
        ext = safe_ext(uploaded.name)
        content_type = getattr(uploaded, "type", None) or mimetypes.guess_type(uploaded.name)[0] or "application/octet-stream"
        return self.save_media_bytes(lesson_id, uploaded.name, file_bytes(uploaded), kind, content_type)

    def save_media_bytes(self, lesson_id: str, filename: str, raw: bytes, kind: str, content_type: str | None = None) -> str:
        ext = safe_ext(filename)
        media_id = uuid.uuid4().hex
        content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if self.remote:
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)[:90] or f"file{ext}"
            storage_path = f"{lesson_id}/{kind}/{media_id}_{safe_name}"
            self.client.storage.from_("wonderbook-media").upload(
                storage_path, raw,
                file_options={"content-type": content_type, "cache-control": "3600", "upsert": "true"},
            )
            public = self.client.storage.from_("wonderbook-media").get_public_url(storage_path)
            if isinstance(public, dict):
                public = public.get("publicUrl") or public.get("publicURL") or public.get("data", {}).get("publicUrl")
            return str(public)
        filename_out = f"{media_id}{ext}"
        (MEDIA_DIR / filename_out).write_bytes(raw)
        return f"data/media/{filename_out}"

    def record_attempt(self, attempt: dict[str, Any]) -> None:
        attempt["created_at"] = utc_now()
        if self.remote:
            self.client.table("wonderbook_attempts").insert(attempt).execute()
        else:
            with self._connect() as conn:
                conn.execute("""INSERT INTO attempts(id,lesson_id,image_id,viewer_id,correct,total,percentage,created_at)
                    VALUES(?,?,?,?,?,?,?,?)""", (attempt["id"], attempt["lesson_id"], attempt["image_id"], attempt["viewer_id"],
                    attempt["correct"], attempt["total"], attempt["percentage"], attempt["created_at"]))
                conn.commit()

    def attempts_for(self, lesson_id: str, viewer_id: str) -> list[dict[str, Any]]:
        if self.remote:
            rows = self.client.table("wonderbook_attempts").select("*").eq("lesson_id", lesson_id).eq("viewer_id", viewer_id).order("created_at").execute().data or []
            return rows
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM attempts WHERE lesson_id=? AND viewer_id=? ORDER BY created_at", (lesson_id, viewer_id)).fetchall()
        return [dict(r) for r in rows]

    def upload_public_url(self, reference: str) -> str:
        if reference.startswith("http://") or reference.startswith("https://") or reference.startswith("data:"):
            return reference
        path = Path(reference)
        if not path.is_absolute():
            path = APP_DIR / path
        if path.exists():
            return data_uri(path)
        return ""

    def media_for_streamlit(self, reference: str) -> str | bytes | None:
        if not reference:
            return None
        if reference.startswith("http://") or reference.startswith("https://"):
            return reference
        path = Path(reference)
        if not path.is_absolute():
            path = APP_DIR / path
        return str(path) if path.exists() else None


@st.cache_resource
def get_store() -> WonderbookStore:
    return WonderbookStore()

store = get_store()


def lesson_score(lesson: dict[str, Any], viewer_id: str) -> dict[str, Any] | None:
    attempts = store.attempts_for(lesson["id"], viewer_id)
    latest_by_image: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        latest_by_image[attempt["image_id"]] = attempt
    if not latest_by_image:
        return None
    total = sum(int(a.get("total", 0)) for a in latest_by_image.values())
    correct = sum(int(a.get("correct", 0)) for a in latest_by_image.values())
    if total <= 0:
        return None
    return {"correct": correct, "total": total, "percentage": round(100 * correct / total), "images_completed": len(latest_by_image)}


def image_score(lesson: dict[str, Any], image_id: str, viewer_id: str) -> int | None:
    attempts = store.attempts_for(lesson["id"], viewer_id)
    filtered = [a for a in attempts if a.get("image_id") == image_id]
    if not filtered:
        return None
    latest = filtered[-1]
    return int(round(float(latest.get("percentage", 0))))


def question_count(lesson: dict[str, Any]) -> int:
    return sum(len(item.get("quiz", [])) for item in lesson.get("items", []))


def html_image(reference: str) -> str:
    uri = store.upload_public_url(reference)
    return html.escape(uri, quote=True)


def render_path_map(lessons: list[dict[str, Any]], viewer_id: str) -> None:
    path_uri = html.escape(data_uri(PATH_IMAGE), quote=True)
    markers = []
    count = len(lessons)
    for index, lesson in enumerate(lessons):
        if count == 1:
            left = 50
        else:
            left = 7 + (86 * index / (count - 1))
        # Keep markers loosely aligned to the meandering dotted trail.
        top = 46 + 15 * math.sin(index * 1.48 - 0.5)
        top = min(67, max(30, top))
        items = lesson.get("items", [])
        if items:
            image_ref = items[0].get("image_url", "")
            thumb = html_image(image_ref)
        else:
            thumb = html.escape(data_uri(HERO_IMAGE), quote=True)
        title = html.escape(lesson.get("title", "Untitled lesson"))
        lesson_id = html.escape(lesson["id"], quote=True)
        score = lesson_score(lesson, viewer_id)
        score_html = f'<span class="score">{score["percentage"]}%</span>' if score else ""
        has_quiz = any(item.get("quiz") for item in items)
        quiz_html = '<span class="quiz-flag">QUIZ</span>' if has_quiz else ""
        markers.append(f"""<a class="wb-map-marker" style="left:{left:.3f}%;top:{top:.3f}%;" href="?open_lesson={lesson_id}" aria-label="Open {title}">
          <span class="thumb-wrap"><img src="{thumb}" alt="" loading="lazy">{score_html}{quiz_html}</span>
          <span class="label">{title}</span></a>""")
    map_html = f"""<div class="wb-map-shell"><img class="wb-map-image" src="{path_uri}" alt="A sunlit golden path through mountains">
    {''.join(markers)}</div>"""
    st.markdown(map_html, unsafe_allow_html=True)


def update_page(page: str):
    st.query_params.clear()
    st.session_state.page = page
    if page != "present":
        st.session_state.active_lesson_id = None


def open_present(lesson_id: str):
    st.session_state.page = "present"
    st.session_state.active_lesson_id = lesson_id
    st.session_state.present_index = 0
    st.session_state.quiz_open = False
    st.query_params.clear()


def get_editor_unlocked() -> bool:
    expected = EDITOR_PASSWORD
    if st.session_state.get("editor_unlocked", False):
        return True
    if not expected:
        st.error("Editing is locked until you configure EDITOR_PASSWORD in .streamlit/secrets.toml (local) or the Streamlit Cloud Secrets settings (hosted).")
        return False
    with st.form("editor_login"):
        entered = st.text_input("Editor password", type="password")
        unlock = st.form_submit_button("Unlock lesson editor")
    if unlock:
        if entered == expected:
            st.session_state.editor_unlocked = True
            st.success("Editor unlocked for this session.")
        else:
            st.error("That password did not match.")
    return bool(st.session_state.get("editor_unlocked", False))


def save_and_refresh(lesson: dict[str, Any], message: str = "Saved."):
    store.save_lesson(lesson)
    st.success(message)
    st.rerun()


def render_home():
    hero_uri = html.escape(data_uri(HERO_IMAGE), quote=True)
    st.markdown(f"""<div class="wb-hero" style="background-image:linear-gradient(90deg,rgba(255,250,233,.91) 0%,rgba(255,250,233,.60) 39%,rgba(255,250,233,.02) 72%),url('{hero_uri}')">
      <div class="wb-eyebrow">Open a book. Find a world.</div><h1>Every lesson brings<br>you closer to Allah</h1><p>Learn about your deen.</p>
    </div>""", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("▶  Start the Hijra  ↗", type="primary", use_container_width=True, key="start_hijra"):
            update_page("map")
            st.rerun()
    with c2:
        st.markdown('<p class="wb-subtitle" style="padding-top:12px">Follow the golden path, explore your lessons, and collect what you learn along the way.</p>', unsafe_allow_html=True)
    all_published = store.list_lessons(False)
    if all_published:
        st.markdown("### Your storybook shelf")
        cols = st.columns(min(3, len(all_published)))
        for i, lesson in enumerate(all_published[:6]):
            with cols[i % len(cols)]:
                with st.container(border=True):
                    if lesson.get("items"):
                        media = store.media_for_streamlit(lesson["items"][0].get("image_url", ""))
                        if media:
                            st.image(media, use_container_width=True)
                    st.markdown(f"#### {html.escape(lesson['title'])}")
                    st.caption(f"{len(lesson.get('items', []))} pictures · {question_count(lesson)} quiz questions")
                    if st.button("Open story", key=f"home_open_{lesson['id']}", use_container_width=True):
                        open_present(lesson["id"])
                        st.rerun()
    if not REMOTE_ENABLED:
        st.markdown('<div class="wb-footer">Local library mode · lessons are stored on this computer/server. Add Supabase storage before hosting if everyone should see the same shared lesson library.</div>', unsafe_allow_html=True)


def render_map(viewer_id: str):
    st.markdown('<div class="wb-eyebrow">Your learning journey</div><h1 style="margin-bottom:0">Your Hijra Path</h1><p class="wb-subtitle">Choose a landmark to open its story. Quiz badges remember your progress in this session.</p>', unsafe_allow_html=True)
    lessons = store.list_lessons(False)
    if not lessons:
        st.info("Your path is waiting for its first lesson. Open **Manage lessons** to add pictures and publish a story.")
        if st.button("Manage lessons"):
            update_page("manage")
            st.rerun()
        return
    render_path_map(lessons, viewer_id)
    st.markdown("### Choose a story")
    cols = st.columns(min(3, len(lessons)))
    for index, lesson in enumerate(lessons):
        with cols[index % len(cols)]:
            with st.container(border=True):
                if lesson.get("items"):
                    image = store.media_for_streamlit(lesson["items"][0].get("image_url", ""))
                    if image:
                        st.image(image, use_container_width=True)
                score = lesson_score(lesson, viewer_id)
                st.markdown(f"#### {html.escape(lesson['title'])}")
                st.caption(f"{len(lesson.get('items', []))} pictures · {question_count(lesson)} questions")
                if score:
                    st.metric("Your quiz score", f"{score['percentage']}%", f"{score['correct']} / {score['total']} correct")
                if st.button("Open this story", key=f"map_open_{lesson['id']}", use_container_width=True):
                    open_present(lesson["id"])
                    st.rerun()


def active_image(lesson: dict[str, Any]) -> tuple[int, dict[str, Any]] | tuple[None, None]:
    items = lesson.get("items", [])
    if not items:
        return None, None
    idx = int(st.session_state.get("present_index", 0))
    idx = max(0, min(idx, len(items) - 1))
    st.session_state.present_index = idx
    return idx, items[idx]


def render_meter(percent: int, caption: str = "Path energy"):
    percent = max(0, min(100, int(percent)))
    st.markdown(f"""<div class="wb-quiz-meter"><div class="wb-meter-label">{html.escape(caption)}</div>
      <div class="wb-meter-track"><div class="wb-meter-fill" style="height:{percent}%"></div></div>
      <div class="wb-meter-number">{percent}%</div></div>""", unsafe_allow_html=True)


@st.dialog("A little picture quiz", width="large")
def quiz_dialog(lesson: dict[str, Any], item: dict[str, Any], viewer_id: str):
    questions = item.get("quiz", [])
    run = st.session_state.get("quiz_run") or {}
    if not questions:
        st.markdown("There is no quiz for this picture yet. The lesson editor can add multiple question types to any image.")
        if st.button("Close quiz", use_container_width=True):
            st.session_state.quiz_open = False
            st.rerun()
        return
    if run.get("finished"):
        total = len(questions)
        correct = int(run.get("correct", 0))
        pct = round(100 * correct / total) if total else 0
        st.markdown(f"<div class='wb-success'>✨ Story complete! You answered {correct} of {total} correctly — {pct}% ✨</div>", unsafe_allow_html=True)
        st.progress(pct / 100, text=f"Final score: {pct}%")
        if st.button("Return to the picture", type="primary", use_container_width=True):
            st.session_state.quiz_open = False
            st.session_state.quiz_run = None
            st.rerun()
        return
    qidx = int(run.get("index", 0))
    if qidx >= len(questions):
        qidx = len(questions) - 1
        run["index"] = qidx
    question = questions[qidx]
    col_question, col_progress = st.columns([5, 1])
    with col_question:
        st.caption(f"{lesson['title']} · Picture {int(st.session_state.get('present_index', 0)) + 1} · Question {qidx + 1} of {len(questions)}")
        st.markdown(f"### {html.escape(question.get('prompt', 'Your question'))}")
        answered = run.get("answered")
        if answered is None:
            with st.form(f"quiz_answer_{lesson['id']}_{item['id']}_{qidx}"):
                qtype = question.get("type", "mcq")
                if qtype == "mcq":
                    choices = question.get("choices", ["A", "B", "C", "D"])
                    response = st.radio("Choose one answer", choices, index=None, key=f"ans_mcq_{qidx}")
                elif qtype == "tf":
                    response = st.radio("Choose your answer", ["True", "False"], index=None, key=f"ans_tf_{qidx}")
                else:
                    response = st.text_input("Your answer", key=f"ans_short_{qidx}")
                submitted = st.form_submit_button("Check my answer ✨", use_container_width=True)
            if submitted:
                qtype = question.get("type", "mcq")
                if response is None or (isinstance(response, str) and not response.strip()):
                    st.warning("Choose or write an answer first.")
                else:
                    if qtype == "mcq":
                        correct_answer = question.get("answer", 0)
                        if isinstance(correct_answer, int):
                            expected = question.get("choices", [])[correct_answer] if 0 <= correct_answer < len(question.get("choices", [])) else ""
                        else:
                            expected = str(correct_answer)
                        is_correct = str(response).strip().casefold() == str(expected).strip().casefold()
                    elif qtype == "tf":
                        expected = bool(question.get("answer", True))
                        is_correct = (response == "True") == expected
                    else:
                        accepted = question.get("answers", [])
                        if isinstance(accepted, str):
                            accepted = [x.strip() for x in accepted.split("|") if x.strip()]
                        expected = accepted[0] if accepted else ""
                        is_correct = str(response).strip().casefold() in {str(a).strip().casefold() for a in accepted}
                    run["answered"] = bool(is_correct)
                    run["answers"].append({"question_id": question.get("id", str(qidx)), "correct": bool(is_correct)})
                    run["correct"] = int(run.get("correct", 0)) + int(is_correct)
                    # The right-side presenter meter responds to every answer: correct fills, wrong drains.
                    step = max(100 / len(questions), 8)
                    old_energy = float(run.get("energy", 50))
                    run["energy"] = max(0, min(100, old_energy + step if is_correct else old_energy - step))
                    run["last_expected"] = expected
                    st.session_state.quiz_run = run
                    st.rerun()
        else:
            if answered:
                st.markdown('<div class="wb-success">✦ Correct! Wonderful work! ✦</div>', unsafe_allow_html=True)
                st.markdown("<div style='text-align:center;font-size:1.2rem;letter-spacing:12px;color:#d5a63b;animation:wbSpark 1.3s ease-out infinite'>✦ ✧ ✦ ✧ ✦</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="wb-bad">Not quite — keep exploring. You can learn from this one.</div>', unsafe_allow_html=True)
                st.caption(f"Answer: {run.get('last_expected', 'See lesson notes')}")
            if qidx + 1 < len(questions):
                if st.button("Next question  →", type="primary", use_container_width=True):
                    run["index"] = qidx + 1
                    run["answered"] = None
                    st.session_state.quiz_run = run
                    st.rerun()
            else:
                if st.button("Finish quiz", type="primary", use_container_width=True):
                    total = len(questions)
                    correct = int(run.get("correct", 0))
                    pct = round(100 * correct / total) if total else 0
                    store.record_attempt({"id": uuid.uuid4().hex, "lesson_id": lesson["id"], "image_id": item["id"],
                                          "viewer_id": viewer_id, "correct": correct, "total": total, "percentage": pct})
                    run["finished"] = True
                    run["percentage"] = pct
                    run["energy"] = pct
                    st.session_state.path_energy = pct
                    st.session_state.quiz_run = run
                    st.rerun()
    with col_progress:
        pct = round(100 * int(run.get("correct", 0)) / len(questions)) if questions else 0
        st.markdown(f"<div class='wb-quiz-meter' style='min-height:220px'><div class='wb-meter-label'>Quiz score</div><div class='wb-meter-track' style='height:170px'><div class='wb-meter-fill' style='height:{pct}%'></div></div><div class='wb-meter-number'>{pct}%</div></div>", unsafe_allow_html=True)


def render_present(viewer_id: str):
    lesson_id = st.session_state.get("active_lesson_id")
    lesson = store.get_lesson(lesson_id, include_unpublished=False) if lesson_id else None
    if not lesson:
        st.warning("That lesson is not published or could not be found.")
        if st.button("Back to the path"):
            update_page("map")
            st.rerun()
        return
    idx, item = active_image(lesson)
    if item is None:
        st.info("This lesson has no pictures yet.")
        if st.button("Back to the path"):
            update_page("map")
            st.rerun()
        return
    if st.session_state.get("meter_lesson_id") != lesson["id"] or st.session_state.get("meter_image_id") != item["id"]:
        st.session_state.meter_lesson_id = lesson["id"]
        st.session_state.meter_image_id = item["id"]
        previous = image_score(lesson, item["id"], viewer_id)
        st.session_state.path_energy = previous if previous is not None else 50
    st.markdown(f'<div class="wb-eyebrow">Story time · {idx+1} of {len(lesson["items"])}</div><h1 style="margin-bottom:.25rem">{html.escape(lesson["title"])}</h1>', unsafe_allow_html=True)
    main, hud = st.columns([12, 1], gap="medium")
    with main:
        media = store.media_for_streamlit(item.get("image_url", ""))
        if media:
            st.image(media, use_container_width=True)
        else:
            st.info("This picture's file is unavailable.")
        if item.get("caption"):
            st.markdown(f"<p class='wb-subtitle'>{html.escape(item['caption'])}</p>", unsafe_allow_html=True)
        audio_cols = st.columns(2)
        with audio_cols[0]:
            if item.get("narration_url"):
                st.markdown("**Narration**")
                audio_ref = store.media_for_streamlit(item["narration_url"])
                if audio_ref:
                    try:
                        st.audio(audio_ref, autoplay=True)
                    except TypeError:
                        st.audio(audio_ref)
        with audio_cols[1]:
            if item.get("sound_url"):
                st.markdown("**Scene sound**")
                sound_ref = store.media_for_streamlit(item["sound_url"])
                if sound_ref:
                    st.audio(sound_ref)
        nav1, nav2, nav3, nav4 = st.columns([1, 1, 1, 2])
        with nav1:
            if st.button("← Previous", disabled=(idx <= 0), use_container_width=True):
                st.session_state.present_index = idx - 1
                st.rerun()
        with nav2:
            if st.button("Next →", disabled=(idx >= len(lesson["items"]) - 1), use_container_width=True):
                st.session_state.present_index = idx + 1
                st.rerun()
        with nav3:
            if st.button("Quiz ✨", use_container_width=True):
                st.session_state.quiz_run = {"lesson_id": lesson["id"], "image_id": item["id"], "index": 0, "correct": 0,
                                             "answers": [], "answered": None, "energy": float(st.session_state.get("path_energy", 50)),
                                             "finished": False}
                st.session_state.quiz_open = True
                st.rerun()
        with nav4:
            st.caption(f"Picture {idx+1} / {len(lesson['items'])} · {len(item.get('quiz', []))} quiz questions")
    with hud:
        run = st.session_state.get("quiz_run") or {}
        if st.session_state.get("quiz_open") and run.get("lesson_id") == lesson["id"]:
            p = int(run.get("energy", st.session_state.get("path_energy", 50)))
            st.session_state.path_energy = p
        else:
            p = int(st.session_state.get("path_energy", 50))
        render_meter(p)
    back1, back2 = st.columns([1, 5])
    with back1:
        if st.button("↶ Your path"):
            update_page("map")
            st.rerun()
    with back2:
        score = lesson_score(lesson, viewer_id)
        if score:
            st.caption(f"Your latest path score: {score['percentage']}% ({score['correct']} / {score['total']} correct across {score['images_completed']} picture quiz/zes)")
    if st.session_state.get("quiz_open"):
        current_lesson = store.get_lesson(st.session_state.quiz_run.get("lesson_id"), include_unpublished=False)
        if current_lesson:
            current_item = next((x for x in current_lesson.get("items", []) if x["id"] == st.session_state.quiz_run.get("image_id")), None)
            if current_item:
                quiz_dialog(current_lesson, current_item, viewer_id)


def data_url_to_bytes(value: Any) -> tuple[bytes, str] | None:
    if not isinstance(value, str) or not value.startswith("data:") or "," not in value:
        return None
    header, encoded = value.split(",", 1)
    mime = header[5:].split(";", 1)[0] or "application/octet-stream"
    try:
        return base64.b64decode(encoded), mime
    except Exception:
        return None


def convert_legacy_quiz(raw_quiz: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_quiz, dict):
        return []
    raw_questions = raw_quiz.get("questions") or []
    if not raw_questions and raw_quiz.get("question"):
        raw_questions = [{"type": raw_quiz.get("type"), "question": raw_quiz.get("question"),
                          "choices": raw_quiz.get("choices", []), "correctIndex": raw_quiz.get("correctIndex", 0),
                          "correctAnswer": raw_quiz.get("correctAnswer", "")}]
    converted = []
    for q in raw_questions:
        qtype = q.get("type", "multiple")
        prompt = str(q.get("question", "")).strip()
        if not prompt:
            continue
        qid = uuid.uuid4().hex
        if qtype in ("truefalse", "tf", "true_false"):
            choices = q.get("choices", ["True", "False"])
            try:
                idx = int(q.get("correctIndex", 0))
            except (TypeError, ValueError):
                idx = 0
            converted.append({"id": qid, "type": "tf", "prompt": prompt, "answer": idx == 0})
        elif qtype in ("shortanswer", "short", "short_answer"):
            answers = q.get("correctAnswer", "")
            if isinstance(answers, list):
                accepted = [str(x).strip() for x in answers if str(x).strip()]
            else:
                accepted = [x.strip() for x in re.split(r"[|\n]", str(answers)) if x.strip()]
            converted.append({"id": qid, "type": "short", "prompt": prompt, "answers": accepted or [str(answers).strip()]})
        else:
            choices = [str(x) for x in q.get("choices", [])]
            if not choices:
                choices = ["A", "B", "C", "D"]
            try:
                answer = max(0, min(len(choices) - 1, int(q.get("correctIndex", 0))))
            except (TypeError, ValueError):
                answer = 0
            converted.append({"id": qid, "type": "mcq", "prompt": prompt, "choices": choices, "answer": answer})
    return converted


def import_legacy_bundle(uploaded) -> tuple[int, int]:
    bundle = json.loads(uploaded.getvalue().decode("utf-8-sig"))
    if bundle.get("format") != "wonderbook-streamlit-export-v1" or not isinstance(bundle.get("lessons"), list):
        raise ValueError("This is not a Wonderbook export pack. In the standalone app, click Export for sharing first.")
    imported_lessons = 0
    imported_images = 0
    for old_lesson in bundle["lessons"]:
        lesson_id = uuid.uuid4().hex
        items = []
        for old_image in old_lesson.get("images", []):
            name = str(old_image.get("name") or "picture.webp")
            image_payload = data_url_to_bytes(old_image.get("blob"))
            if image_payload is None:
                continue
            image_bytes, image_mime = image_payload
            image_url = store.save_media_bytes(lesson_id, name, image_bytes, "images", image_mime)
            narration_url = ""
            audio_payload = data_url_to_bytes(old_image.get("audioBlob"))
            if audio_payload:
                audio_bytes, audio_mime = audio_payload
                audio_url = store.save_media_bytes(lesson_id, old_image.get("audioName") or "narration.mp3", audio_bytes, "narration", audio_mime)
                narration_url = audio_url
            sound_url = ""
            sound_payload = data_url_to_bytes(old_image.get("soundEffectBlob"))
            if sound_payload:
                sound_bytes, sound_mime = sound_payload
                sound_url = store.save_media_bytes(lesson_id, old_image.get("soundEffectName") or "scene-sound.mp3", sound_bytes, "sounds", sound_mime)
            elif str(old_image.get("soundEffectSourceUrl", "")).startswith(("http://", "https://")):
                sound_url = str(old_image.get("soundEffectSourceUrl"))
            items.append({
                "id": uuid.uuid4().hex, "name": name, "image_url": image_url,
                "caption": str(old_image.get("notes", "")), "narration_url": narration_url,
                "sound_url": sound_url, "quiz": convert_legacy_quiz(old_image.get("quiz")),
                "sound_source_url": str(old_image.get("soundEffectSourcePageUrl", "")),
                "sound_license": str(old_image.get("soundEffectLicense", "")),
                "sound_library": str(old_image.get("soundEffectLibrary", "")),
            })
            imported_images += 1
        if not items:
            continue
        store.save_lesson({"id": lesson_id, "title": str(old_lesson.get("name") or "Imported lesson"),
                           "description": "Imported from your standalone Wonderbook library.", "published": True, "items": items})
        imported_lessons += 1
    return imported_lessons, imported_images


def manage_lessons():
    st.markdown('<div class="wb-eyebrow">For the storyteller</div><h1>Manage lessons</h1><p class="wb-subtitle">Add picture stories, narration, scene sounds, and a set of quiz questions for each image. Published lessons appear to everyone with the share link.</p>', unsafe_allow_html=True)
    if not REMOTE_ENABLED:
        st.warning("This is local storage mode. Lessons will be saved in this folder, but a public Streamlit deployment needs Supabase configured so everyone sees the same lesson library and media.")
    if not get_editor_unlocked():
        return
    with st.expander("⇧ Import lessons from your existing standalone Wonderbook", expanded=False):
        st.markdown("If you already added lessons to the HTML version, open the **export-enabled** HTML file, click **Export for sharing**, then upload its JSON pack here. Images, narration, available sound files, and quizzes are imported into the shared library.")
        legacy_pack = st.file_uploader("Wonderbook lesson pack (.json)", type=["json"], key="legacy_wonderbook_bundle")
        if st.button("Import lesson pack", key="import_legacy_bundle", type="primary", use_container_width=True):
            if not legacy_pack:
                st.warning("Choose the JSON file exported from the standalone Wonderbook app first.")
            else:
                try:
                    imported_lessons, imported_images = import_legacy_bundle(legacy_pack)
                    st.success(f"Imported {imported_lessons} lesson(s) and {imported_images} picture(s). They are published to the shared path.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Import failed: {exc}")

    with st.expander("＋ Create a new lesson", expanded=not bool(store.list_lessons(True))):
        with st.form("create_lesson_form", clear_on_submit=True):
            title = st.text_input("Lesson title", placeholder="e.g. Good character and kindness")
            description = st.text_area("Short introduction", placeholder="What will learners discover in this story?")
            uploads = st.file_uploader("Choose the lesson images", type=["png", "jpg", "jpeg", "webp", "gif"], accept_multiple_files=True)
            published = st.checkbox("Publish this lesson to everyone with the link", value=True)
            create = st.form_submit_button("Create lesson", type="primary", use_container_width=True)
        if create:
            if not title.strip():
                st.error("Add a lesson title first.")
            elif not uploads:
                st.error("Choose at least one image.")
            else:
                lid = uuid.uuid4().hex
                items = []
                for uploaded in uploads:
                    try:
                        image_url = store.save_media(lid, uploaded, "images")
                        items.append({"id": uuid.uuid4().hex, "name": uploaded.name, "image_url": image_url,
                                      "caption": Path(uploaded.name).stem.replace("_", " "), "narration_url": "", "sound_url": "", "quiz": []})
                    except Exception as exc:
                        st.error(f"Could not save {uploaded.name}: {exc}")
                if items:
                    store.save_lesson({"id": lid, "title": title.strip(), "description": description.strip(), "published": published, "items": items})
                    st.success("Lesson created. You can now attach narration, sound effects, and quizzes to individual pictures below.")
                    st.rerun()

    lessons = store.list_lessons(include_unpublished=True)
    if not lessons:
        st.info("No lessons yet. Create your first one above.")
        return
    st.markdown("### Edit a lesson")
    selected_id = st.selectbox("Choose a lesson", options=[l["id"] for l in lessons], format_func=lambda lid: next((l["title"] + (" · Published" if l["published"] else " · Draft") for l in lessons if l["id"] == lid), lid), key="edit_lesson_id")
    lesson = store.get_lesson(selected_id, include_unpublished=True)
    if not lesson:
        st.warning("Lesson not found.")
        return
    with st.form(f"lesson_details_{lesson['id']}"):
        new_title = st.text_input("Title", value=lesson["title"])
        new_desc = st.text_area("Introduction", value=lesson.get("description", ""))
        new_published = st.checkbox("Published / visible to students", value=lesson.get("published", True))
        save_details = st.form_submit_button("Save lesson details", type="primary")
    if save_details:
        lesson["title"] = new_title.strip() or lesson["title"]
        lesson["description"] = new_desc.strip()
        lesson["published"] = new_published
        save_and_refresh(lesson, "Lesson details saved.")

    st.markdown("### Pictures, narration, and quizzes")
    for item_index, item in enumerate(lesson.get("items", [])):
        with st.expander(f"Picture {item_index+1}: {item.get('name', 'Image')} · {len(item.get('quiz', []))} questions", expanded=False):
            left, right = st.columns([1, 2])
            with left:
                image_ref = store.media_for_streamlit(item.get("image_url", ""))
                if image_ref:
                    st.image(image_ref, use_container_width=True)
            with right:
                with st.form(f"caption_{lesson['id']}_{item['id']}"):
                    cap = st.text_input("Picture caption", value=item.get("caption", ""))
                    cap_save = st.form_submit_button("Save caption")
                if cap_save:
                    item["caption"] = cap
                    save_and_refresh(lesson, "Caption saved.")
                audio_left, audio_right = st.columns(2)
                with audio_left:
                    st.markdown("**Narration recording**")
                    if item.get("narration_url"):
                        ref = store.media_for_streamlit(item["narration_url"])
                        if ref:
                            st.audio(ref)
                    audio_up = st.file_uploader("Upload narration", type=["mp3", "wav", "ogg", "m4a", "aac", "mp4"], key=f"narration_upload_{item['id']}")
                    if st.button("Save narration", key=f"narration_save_{item['id']}", use_container_width=True):
                        if audio_up:
                            try:
                                item["narration_url"] = store.save_media(lesson["id"], audio_up, "narration")
                                save_and_refresh(lesson, "Narration attached to this picture.")
                            except Exception as exc:
                                st.error(f"Could not upload narration: {exc}")
                        else:
                            st.warning("Choose an audio file first.")
                with audio_right:
                    st.markdown("**Scene sound effect**")
                    if item.get("sound_url"):
                        ref = store.media_for_streamlit(item["sound_url"])
                        if ref:
                            st.audio(ref)
                    sound_up = st.file_uploader("Upload scene sound", type=["mp3", "wav", "ogg", "m4a", "aac", "mp4"], key=f"sound_upload_{item['id']}")
                    if st.button("Save scene sound", key=f"sound_save_{item['id']}", use_container_width=True):
                        if sound_up:
                            try:
                                item["sound_url"] = store.save_media(lesson["id"], sound_up, "sounds")
                                save_and_refresh(lesson, "Scene sound attached to this picture.")
                            except Exception as exc:
                                st.error(f"Could not upload sound: {exc}")
                        else:
                            st.warning("Choose a sound file first.")
            st.markdown("**Quiz questions for this picture**")
            if item.get("quiz"):
                for qi, q in enumerate(item["quiz"]):
                    with st.container(border=True):
                        qt = {"mcq": "Multiple choice", "tf": "True / false", "short": "Short answer"}.get(q.get("type"), "Question")
                        st.markdown(f"**{qi+1}. {html.escape(q.get('prompt', 'Question'))}** · {qt}")
                        if q.get("type") == "mcq":
                            choices = q.get("choices", [])
                            answer = q.get("answer", 0)
                            answer_text = choices[answer] if isinstance(answer, int) and 0 <= answer < len(choices) else str(answer)
                            st.caption("Choices: " + " · ".join(choices) + f" | Correct: {answer_text}")
                        elif q.get("type") == "tf":
                            st.caption("Correct: " + ("True" if q.get("answer", True) else "False"))
                        else:
                            answers = q.get("answers", [])
                            st.caption("Accepted answer(s): " + (", ".join(answers) if isinstance(answers, list) else str(answers)))
                        if st.button("Remove question", key=f"delete_q_{item['id']}_{q.get('id', qi)}"):
                            item["quiz"] = [old for old in item["quiz"] if old.get("id") != q.get("id")]
                            save_and_refresh(lesson, "Question removed.")
            with st.form(f"add_question_{item['id']}"):
                qtype_label = st.selectbox("Question type", ["Multiple choice", "True / false", "Short answer"], key=f"qtype_{item['id']}")
                prompt = st.text_input("Question", placeholder="What detail can you remember from this picture?", key=f"prompt_{item['id']}")
                if qtype_label == "Multiple choice":
                    c1, c2 = st.columns(2)
                    with c1:
                        ch1 = st.text_input("Choice A", key=f"choice_a_{item['id']}")
                        ch2 = st.text_input("Choice B", key=f"choice_b_{item['id']}")
                    with c2:
                        ch3 = st.text_input("Choice C", key=f"choice_c_{item['id']}")
                        ch4 = st.text_input("Choice D", key=f"choice_d_{item['id']}")
                    answer_label = st.selectbox("Correct choice", ["A", "B", "C", "D"], key=f"answer_{item['id']}")
                elif qtype_label == "True / false":
                    tf_answer = st.radio("Correct answer", ["True", "False"], horizontal=True, key=f"tf_answer_{item['id']}")
                else:
                    short_answers = st.text_input("Accepted answers (use | between alternatives)", placeholder="kindness | being kind", key=f"short_answers_{item['id']}")
                add_q = st.form_submit_button("＋ Add question to this picture", use_container_width=True)
            if add_q:
                if not prompt.strip():
                    st.error("Write the question first.")
                else:
                    new_q = {"id": uuid.uuid4().hex, "prompt": prompt.strip()}
                    if qtype_label == "Multiple choice":
                        choices = [ch1.strip(), ch2.strip(), ch3.strip(), ch4.strip()]
                        if any(not choice for choice in choices):
                            st.error("Fill in all four answer choices.")
                            continue_save = False
                        else:
                            new_q.update({"type": "mcq", "choices": choices, "answer": ["A", "B", "C", "D"].index(answer_label)})
                            continue_save = True
                    elif qtype_label == "True / false":
                        new_q.update({"type": "tf", "answer": tf_answer == "True"})
                        continue_save = True
                    else:
                        answers = [a.strip() for a in short_answers.split("|") if a.strip()]
                        if not answers:
                            st.error("Add at least one accepted answer.")
                            continue_save = False
                        else:
                            new_q.update({"type": "short", "answers": answers})
                            continue_save = True
                    if continue_save:
                        item.setdefault("quiz", []).append(new_q)
                        save_and_refresh(lesson, "Question added to this picture.")
            if st.button("Remove this picture from lesson", key=f"remove_image_{item['id']}"):
                lesson["items"] = [old for old in lesson["items"] if old["id"] != item["id"]]
                save_and_refresh(lesson, "Picture removed from the lesson.")
    with st.expander("Danger zone", expanded=False):
        st.warning("Deleting a lesson removes it from the shared path. Media files already uploaded to Supabase Storage are not automatically deleted.")
        if st.button("Delete this entire lesson", type="secondary", key=f"delete_lesson_{lesson['id']}"):
            store.delete_lesson(lesson["id"])
            st.session_state.pop("edit_lesson_id", None)
            st.success("Lesson deleted.")
            st.rerun()


def render_about():
    st.markdown("# Share Wonderbook with your learners")
    st.markdown("""
This starter moves the essential lesson library into a hosted, multi-user Streamlit app. You can upload a lesson, attach narration and scene-sound files to each picture, create mixed-type image quizzes, and publish the lesson so viewers can access it through the same link.

**For shared, persistent lessons**, deploy with Supabase configured. Local SQLite mode is intended for trying the app on your own computer.

The Streamlit edition preserves the storybook visual direction and the central image/quiz workflow. Some browser-only features of the original standalone HTML—especially automated external sound-library matching and the full set of presentation transitions—are not yet ported in this starter.
""")
    st.markdown("### Deployment guide")
    st.markdown("1. Put this folder in a GitHub repository.\n2. Create a Supabase project and run `setup_supabase.sql` in its SQL Editor.\n3. Create a Streamlit Community Cloud app pointed at `app.py`.\n4. Add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `EDITOR_PASSWORD` in Streamlit **Secrets**.\n5. Open **Manage lessons**, unlock the editor, add lessons, and leave **Publish** enabled for lessons other people should see.")
    st.markdown("[Streamlit deployment instructions](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app) · [Streamlit secrets](https://docs.streamlit.io/develop/concepts/connections/secrets-management) · [Supabase setup guide](https://docs.streamlit.io/develop/tutorials/databases/supabase)")


# Session initialization and URL-based opening from the clickable HTML map.
if "page" not in st.session_state:
    st.session_state.page = "home"
if "viewer_id" not in st.session_state:
    st.session_state.viewer_id = uuid.uuid4().hex
if "present_index" not in st.session_state:
    st.session_state.present_index = 0
if "quiz_open" not in st.session_state:
    st.session_state.quiz_open = False

open_lesson_param = st.query_params.get("open_lesson")
if open_lesson_param:
    candidate = store.get_lesson(str(open_lesson_param), include_unpublished=False)
    if candidate:
        if st.session_state.get("active_lesson_id") != candidate["id"]:
            st.session_state.present_index = 0
        st.session_state.active_lesson_id = candidate["id"]
        st.session_state.page = "present"

# Header / navigation.
nav = st.columns([2.6, 1, 1.15, 1.35, 1])
with nav[0]:
    st.markdown("<div style='display:flex;gap:10px;align-items:center;padding-top:6px'><span style='font-size:2rem'>✦</span><div><div style='font:800 1.25rem Playfair Display,Georgia,serif;color:#684822'>Start the Hijra</div><div style='font-size:.74rem;color:#8b744d'>Every lesson brings you closer to Allah</div></div></div>", unsafe_allow_html=True)
with nav[1]:
    if st.button("Home", use_container_width=True):
        update_page("home")
        st.rerun()
with nav[2]:
    if st.button("Your path", use_container_width=True):
        update_page("map")
        st.rerun()
with nav[3]:
    if st.button("Manage lessons", use_container_width=True):
        update_page("manage")
        st.rerun()
with nav[4]:
    if st.button("Share setup", use_container_width=True):
        update_page("about")
        st.rerun()

st.markdown("<hr style='border:none;border-top:1px solid #e2cf9f;margin:.8rem 0 1.3rem'>", unsafe_allow_html=True)

if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "map":
    render_map(st.session_state.viewer_id)
elif st.session_state.page == "present":
    render_present(st.session_state.viewer_id)
elif st.session_state.page == "manage":
    manage_lessons()
else:
    render_about()

st.markdown("<div class='wb-footer'>Wonderbook · A little wonder in every lesson</div>", unsafe_allow_html=True)
