from __future__ import annotations

import hashlib
import json
import os
import re
import runpy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from supabase import create_client
except Exception:
    create_client = None

APP_DIR = Path(__file__).parent.resolve()
HTML_PATH = APP_DIR / "legacy" / "wonderbook_visual_automatch_fixed.html"

st.set_page_config(
    page_title="Start the Hijra — Every lesson brings you closer to Allah",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Keep the previous Streamlit library editor available without adding new controls
# to the original Wonderbook home screen.
if st.query_params.get("manage_shared") == "1":
    runpy.run_path(str(APP_DIR / "streamlit_library_admin.py"), run_name="__main__")
    st.stop()


def get_setting(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def get_published_lessons() -> list[dict[str, Any]]:
    url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_SERVICE_KEY")
    if not (url and key and create_client):
        return []
    try:
        client = create_client(url, key)
        rows = (
            client.table("wonderbook_lessons")
            .select("id,title,description,published,items,updated_at")
            .eq("published", True)
            .order("updated_at", desc=True)
            .execute()
            .data or []
        )
        safe_rows: list[dict[str, Any]] = []
        for row in rows:
            items = row.get("items", [])
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            safe_items = []
            for item in items if isinstance(items, list) else []:
                safe_items.append({
                    "id": str(item.get("id") or ""),
                    "name": str(item.get("name") or "picture"),
                    "image_url": str(item.get("image_url") or ""),
                    "caption": str(item.get("caption") or ""),
                    "narration_url": str(item.get("narration_url") or ""),
                    "narration_name": str(item.get("narration_name") or ""),
                    "sound_url": str(item.get("sound_url") or ""),
                    "sound_name": str(item.get("sound_name") or ""),
                    "sound_source_url": str(item.get("sound_source_url") or ""),
                    "sound_source_page_url": str(item.get("sound_source_page_url") or ""),
                    "sound_license": str(item.get("sound_license") or ""),
                    "sound_license_url": str(item.get("sound_license_url") or ""),
                    "sound_library": str(item.get("sound_library") or ""),
                    "quiz": item.get("quiz", []) if isinstance(item.get("quiz", []), list) else [],
                })
            safe_rows.append({
                "id": str(row.get("id") or ""),
                "title": str(row.get("title") or "Untitled lesson"),
                "description": str(row.get("description") or ""),
                "updated_at": str(row.get("updated_at") or ""),
                "items": safe_items,
            })
        return safe_rows
    except Exception:
        # Keep the familiar frontend available even if the shared backend is offline.
        return []



def get_shared_pdfs() -> list[dict[str, Any]]:
    """Discover PDF files in Supabase Storage and create short-lived browser URLs."""
    url = get_setting("SUPABASE_URL")
    key = get_setting("SUPABASE_SERVICE_KEY")
    bucket_name = get_setting("SUPABASE_PDF_BUCKET", "pdf").strip() or "pdf"
    if not (url and key and create_client):
        return []
    try:
        client = create_client(url, key)
        storage = client.storage.from_(bucket_name)
    except Exception:
        return []

    found: list[dict[str, Any]] = []
    visited: set[str] = set()

    def absolute_url(candidate: Any) -> str:
        if isinstance(candidate, dict):
            candidate = candidate.get("signedURL") or candidate.get("signedUrl") or candidate.get("publicUrl") or candidate.get("publicURL") or ""
        elif not isinstance(candidate, str):
            candidate = getattr(candidate, "signed_url", "") or getattr(candidate, "signedURL", "") or ""
        candidate = str(candidate or "")
        if candidate.startswith(("https://", "http://")):
            return candidate
        if candidate.startswith("/storage/v1/"):
            return url.rstrip("/") + candidate
        if candidate.startswith("/object/"):
            return url.rstrip("/") + "/storage/v1" + candidate
        return ""

    def make_url(path: str) -> str:
        try:
            link = absolute_url(storage.create_signed_url(path, 7 * 24 * 60 * 60))
            if link:
                return link
        except Exception:
            pass
        try:
            return absolute_url(storage.get_public_url(path))
        except Exception:
            return ""

    def walk(folder: str = "", depth: int = 0) -> None:
        if depth > 5 or folder in visited:
            return
        visited.add(folder)
        try:
            entries = storage.list(folder, {"limit": 1000, "offset": 0, "sortBy": {"column": "name", "order": "asc"}}) or []
        except Exception:
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "").strip()
            if not name or name in {".", "..", ".emptyFolderPlaceholder"}:
                continue
            path = f"{folder}/{name}" if folder else name
            if name.lower().endswith(".pdf"):
                link = make_url(path)
                if not link:
                    continue
                timestamp = str(entry.get("updated_at") or entry.get("created_at") or datetime.now(timezone.utc).isoformat())
                stable_id = "shared-pdf-" + hashlib.sha256(f"{bucket_name}:{path}".encode("utf-8")).hexdigest()[:28]
                found.append({"id": stable_id, "path": path, "name": name, "title": Path(name).stem or name,
                              "url": link, "updated_at": timestamp, "bucket": bucket_name})
            elif depth < 5 and entry.get("id") is None and not entry.get("metadata"):
                walk(path, depth + 1)

    walk()
    return sorted(found, key=lambda item: (item["title"].casefold(), item["path"].casefold()))


def json_for_script(value: Any) -> str:
    # Prevent database text from closing the injected script element.
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def load_original_html() -> str:
    if not HTML_PATH.is_file():
        raise FileNotFoundError(f"Could not find the original Wonderbook HTML at {HTML_PATH}")
    page = HTML_PATH.read_text(encoding="utf-8")

    # The repository copy has an optional Streamlit lesson-pack export action.
    # Keep that small addition to support publishing, without changing any of the
    # original controls or PDF conversion functions.
    shared_lessons = get_published_lessons()
    shared_pdfs = get_shared_pdfs()
    injected = (
        "window.__WB_SHARED_LESSONS__ = " + json_for_script(shared_lessons) + "; "
        + "window.__WB_SHARED_PDFS__ = " + json_for_script(shared_pdfs) + ";"
    )
    db_anchor = "  const DB_NAME = 'LessonFlowDB';"
    if db_anchor not in page:
        raise RuntimeError("The original Wonderbook database initialization was not found.")
    page = page.replace(db_anchor, "  " + injected + "\n" + db_anchor, 1)

    put_anchor = "        id: lesson.id,\n        name: lesson.name,\n        images: lesson.images.map(img => ({"
    put_replacement = "        id: lesson.id,\n        name: lesson.name,\n        sharedUpdatedAt: Math.max(0, Number(lesson.sharedUpdatedAt) || 0),\n        sharedSourcePdf: Boolean(lesson.sharedSourcePdf),\n        sharedPdfPath: String(lesson.sharedPdfPath || ''),\n        images: lesson.images.map(img => ({"
    if put_anchor not in page:
        raise RuntimeError("The original Wonderbook lesson-save function was not found.")
    page = page.replace(put_anchor, put_replacement, 1)

    init_anchor = """  async function init(){
    const ok = await openDatabase();
    lessons = (await getAllLessons()).map(reviveLesson);"""
    init_replacement = r"""  async function fetchSharedBlob(url){
    if (!url || !/^https?:\/\//i.test(url)) return null;
    try {
      const response = await fetch(url, {mode:'cors', credentials:'omit'});
      if (!response.ok) return null;
      return await response.blob();
    } catch (err) {
      console.warn('Could not load shared lesson media', err);
      return null;
    }
  }

  function sharedQuizToLocal(raw, updatedAt){
    if (!Array.isArray(raw) || !raw.length) return null;
    return {
      questions: raw.map((q, index) => ({
        id: String(q.id || ('shared-q-' + index)),
        type: q.type === 'tf' ? 'truefalse' : (q.type === 'short' ? 'shortanswer' : 'multiple'),
        question: String(q.prompt || q.question || ''),
        choices: Array.isArray(q.choices) ? q.choices.map(String) : [],
        correctIndex: Number(q.answer ?? q.correctIndex) || 0,
        correctAnswer: Array.isArray(q.answers) ? q.answers.join(' | ') : String(q.correctAnswer || '')
      })),
      updatedAt: updatedAt || Date.now(),
      attempts: 0,
      bestPercent: null,
      lastScore: null
    };
  }

  async function seedSharedLessonsFromServer(){
    const sources = Array.isArray(window.__WB_SHARED_LESSONS__) ? window.__WB_SHARED_LESSONS__ : [];
    if (!db || !sources.length) return;
    const localLessons = await getAllLessons();
    const localById = new Map(localLessons.map(item => [item.id, item]));
    for (const source of sources){
      if (!source || !source.id) continue;
      const updatedAt = Date.parse(source.updated_at || '') || 0;
      const existing = localById.get(source.id);
      if (existing && Number(existing.sharedUpdatedAt || 0) >= updatedAt) continue;
      const images = [];
      for (const image of (Array.isArray(source.items) ? source.items : [])){
        const blob = await fetchSharedBlob(image.image_url);
        if (!blob) continue;
        const audioBlob = await fetchSharedBlob(image.narration_url);
        const soundEffectBlob = await fetchSharedBlob(image.sound_url);
        images.push({
          id: String(image.id || newId()),
          name: String(image.name || 'picture'),
          blob,
          notes: String(image.caption || ''),
          audioBlob,
          audioName: String(image.narration_name || ''),
          audioType: audioBlob ? audioBlob.type : '',
          soundEffectBlob,
          soundEffectName: String(image.sound_name || ''),
          soundEffectType: soundEffectBlob ? soundEffectBlob.type : '',
          soundEffectScene: '',
          soundEffectSourceUrl: String(image.sound_source_url || image.sound_url || ''),
          soundEffectSourcePageUrl: String(image.sound_source_page_url || ''),
          soundEffectLicense: String(image.sound_license || ''),
          soundEffectLicenseUrl: String(image.sound_license_url || ''),
          soundEffectLibrary: String(image.sound_library || ''),
          quiz: sharedQuizToLocal(image.quiz, updatedAt)
        });
      }
      if (images.length){
        await putLesson({id:String(source.id), name:String(source.title || 'Untitled lesson'), sharedUpdatedAt:updatedAt, images});
      }
    }
  }

  async function seedSharedPdfsFromBucket(){
    const sources = Array.isArray(window.__WB_SHARED_PDFS__) ? window.__WB_SHARED_PDFS__ : [];
    if (!db || !sources.length) return;
    const currentLessons = await getAllLessons();
    const localById = new Map(currentLessons.map(lesson => [lesson.id, lesson]));
    for (const source of sources){
      if (!source || !source.id || !source.url) continue;
      const updatedAt = Date.parse(source.updated_at || '') || Date.now();
      const existing = localById.get(source.id);
      if (existing && Number(existing.sharedUpdatedAt || 0) >= updatedAt) continue;
      try {
        const pdfBlob = await fetchSharedBlob(source.url);
        if (!pdfBlob) {
          console.warn('Could not load shared PDF:', source.path || source.name);
          continue;
        }
        const pdfFile = new File([pdfBlob], source.name || 'Shared lesson.pdf', {type:'application/pdf'});
        const renderedPages = await pdfToImages(pdfFile);
        if (!renderedPages.length) continue;
        const previousPages = existing && Array.isArray(existing.images) ? existing.images : [];
        const images = renderedPages.map((page, pageIndex) => {
          const old = previousPages[pageIndex] || {};
          return {
            ...page,
            id: old.id || (source.id + '-page-' + String(pageIndex + 1).padStart(4, '0')),
            notes: old.notes || '',
            audioBlob: old.audioBlob || null,
            audioName: old.audioName || '',
            audioType: old.audioType || '',
            soundEffectBlob: old.soundEffectBlob || null,
            soundEffectName: old.soundEffectName || '',
            soundEffectType: old.soundEffectType || '',
            soundEffectScene: old.soundEffectScene || '',
            soundEffectSourceUrl: old.soundEffectSourceUrl || '',
            soundEffectSourcePageUrl: old.soundEffectSourcePageUrl || '',
            soundEffectLicense: old.soundEffectLicense || '',
            soundEffectLicenseUrl: old.soundEffectLicenseUrl || '',
            soundEffectLibrary: old.soundEffectLibrary || '',
            quiz: old.quiz || null
          };
        });
        const sharedLesson = {
          id: source.id,
          name: source.title || String(source.name || 'Shared PDF').replace(/\.pdf$/i, ''),
          sharedUpdatedAt: updatedAt,
          sharedSourcePdf: true,
          sharedPdfPath: source.path || source.name || '',
          images
        };
        await putLesson(sharedLesson);
        localById.set(source.id, sharedLesson);
        renderedPages.forEach(page => { if (page.url) URL.revokeObjectURL(page.url); });
      } catch (err) {
        console.warn('Could not convert shared PDF into a lesson:', source.path || source.name, err);
      }
    }
  }

  async function init(){
    const ok = await openDatabase();
    if (ok) {
      await seedSharedLessonsFromServer();
      await seedSharedPdfsFromBucket();
    }
    lessons = (await getAllLessons()).map(reviveLesson);"""
    if init_anchor not in page:
        raise RuntimeError("The original Wonderbook startup routine was not found.")
    page = page.replace(init_anchor, init_replacement, 1)

    # Keep the iframe sized to the visible app viewport so presentation/full-screen
    # behavior remains as close as possible to the standalone HTML.
    fit_script = r"""
<script>
(function(){
  function fitWonderbookFrame(){
    try {
      const frame = window.frameElement;
      const parentHeight = window.parent && window.parent.innerHeight;
      if (frame && parentHeight) {
        frame.style.height = Math.max(600, parentHeight) + 'px';
        frame.style.width = '100%';
      }
    } catch (_) {}
  }
  fitWonderbookFrame();
  window.addEventListener('resize', fitWonderbookFrame);
  try { window.parent.addEventListener('resize', fitWonderbookFrame); } catch (_) {}
})();
</script>
"""
    if "</body>" in page:
        page = page.replace("</body>", fit_script + "\n</body>", 1)
    return page


# Keep Streamlit itself visually invisible so the HTML app remains the interface.
st.markdown(
    """
    <style>
      [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
      [data-testid="stStatusWidget"], #MainMenu, footer { display:none !important; visibility:hidden !important; }
      [data-testid="stMain"], section[data-testid="stMain"] { padding:0 !important; margin:0 !important; }
      .stMainBlockContainer, .block-container { max-width:none !important; padding:0 !important; margin:0 !important; }
      [data-testid="stElementContainer"]:has(iframe) { margin:0 !important; padding:0 !important; }
      iframe { border:0 !important; }
      .stApp, [data-testid="stAppViewContainer"] { margin:0 !important; padding:0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    wonderbook_html = load_original_html()
except Exception as exc:
    st.error(f"Wonderbook could not start: {exc}")
    st.stop()

# The original JavaScript—including PDF.js parsing and page rendering—runs as-is.
st.components.v1.html(wonderbook_html, height=1000, scrolling=True)
