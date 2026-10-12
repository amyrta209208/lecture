# Wonderbook — Start the Hijra

This Streamlit deployment serves the original Wonderbook HTML interface inside Streamlit rather than rebuilding the screens from Streamlit widgets. This preserves the existing layout, drag/reorder controls, image selection and deletion, narration/audio tools, quiz editor, image transitions, PDF import/rendering, and PDF/PowerPoint export behavior from the HTML source.

## Auto-load PDFs from Supabase Storage

The main Wonderbook URL scans the configured Supabase Storage bucket (default name: `pdf`) when a visitor opens the app. Every PDF it finds is fetched through a short-lived signed URL and converted into page images in the browser with the **same PDF.js settings used by the standalone interface**. The resulting page images appear as a lesson named after the PDF. New or updated PDFs are refreshed using the Storage object's update timestamp.

To enable this, configure these values in Streamlit Community Cloud → **Manage app → Settings → Secrets**:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_PDF_BUCKET = "pdf"
EDITOR_PASSWORD = "choose-a-long-private-password"
```

Use a server-side secret/service-role key only in Streamlit Secrets; never place it in frontend code or commit it to GitHub. The app needs list/read permission through the server-side key. PDFs do not need to be manually imported as JSON packs after this configuration is active. Visitors still need internet access for PDF.js and for the PDF object to be fetched.

## How the app runs

- Main app: `app.py`. It embeds `legacy/wonderbook_visual_automatch_fixed.html` and keeps its browser-side JavaScript behavior, including the PDF.js page-to-image conversion.
- Shared-library editor/importer: open the same app URL with `?manage_shared=1`, for example `https://YOUR-APP.streamlit.app/?manage_shared=1`.
- Published lessons are read from Supabase and seeded into the original browser UI. Lesson updates are published by exporting a JSON lesson pack from the main interface, then importing that pack through the shared-library route.
- The local lesson database in the browser remains device/browser-specific. Only lessons exported and imported into the shared library become visible to other visitors.

## Try it locally

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Without Supabase secrets, the original interface still runs and stores its lesson library locally in the browser. The shared-library route will show that hosted sharing is not configured.

## Configure shared lessons

1. Create a project at [supabase.com](https://supabase.com/).
2. In Supabase SQL Editor, run `setup_supabase.sql`.
3. In the Supabase API settings, copy the project URL and server-side service-role key.
4. In Streamlit Community Cloud, open App settings → Secrets and add:

```toml
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
EDITOR_PASSWORD = "choose-a-long-private-password"
```

Never commit the real service-role key or editor password to GitHub. The media bucket in the SQL script is public because published lesson images/audio need to be loaded by viewers; do not publish private or sensitive content.

## Publish the lessons you created

1. Open the main app URL and work in the original Wonderbook interface.
2. Click **Export for sharing** and save the generated JSON lesson pack.
3. Open the app URL with `?manage_shared=1`.
4. Unlock **Manage lessons**, open **Import lessons from your existing standalone Wonderbook**, and upload the JSON pack.
5. Keep **Publish this lesson to everyone with the link** enabled. Return to the main URL; published lessons will load into the same original UI.
6. To update an already-shared lesson, export and import it again. Lesson and picture IDs are retained so re-import updates the existing lesson rather than making a duplicate.

The import/publication workflow requires Supabase to be configured for durable sharing across different browsers. Without Supabase, the app runs locally but the shared store is not durable across visitors/restarts.

## PDF behavior

PDF-to-image conversion stays in the original HTML/JavaScript implementation (PDF.js); this wrapper does not parse or rasterize PDFs in Python. The PDF rendering settings and output page naming therefore remain in the existing source file. PDF.js and its worker load from a CDN, so the browser needs an internet connection when opening the app.

## Files

- `app.py` — Streamlit wrapper that embeds the original UI.
- `legacy/wonderbook_visual_automatch_fixed.html` — original HTML/JavaScript application and PDF processing.
- `streamlit_library_admin.py` — shared-library management and lesson-pack importer.
- `setup_supabase.sql` — shared database and public media bucket.
- `requirements.txt` — Python dependencies.
