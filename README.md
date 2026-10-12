# Wonderbook — Start the Hijra (Streamlit edition)

A shareable, server-backed starter for **Start the Hijra — Every lesson brings you closer to Allah**. It keeps the warm storybook visual direction and adds a shared published lesson library, image-based lesson paths, per-image narration and sound uploads, mixed-type quizzes, and session-specific scores.

## Current polish pass

- The homepage uses the supplied panoramic illustration as one clickable banner, so its artwork headline and “Start the Hijra” button are not duplicated by an extra overlay.
- Clicking the banner opens **Your Hijra Path**.
- Quiz answer feedback uses a short gold-star burst for correct answers; the vertical **Path Energy** meter stays in the presentation HUD, not inside the quiz dialog.

## What this version includes

- Storybook-style home screen and illustrated golden path.
- First-image thumbnails on the path for each lesson.
- Lesson manager to create, publish/unpublish, edit, and delete lessons.
- Multiple images per lesson, captions, narration audio, and scene sound uploads per image.
- Multiple-choice, true/false, and short-answer questions per image.
- Quiz modal, per-attempt percentage scores, and score badges on the path.
- Local SQLite mode for trying the app on one computer.
- Optional Supabase Postgres + Storage backend for a persistent shared lesson library after deployment.
- Migration from the standalone HTML app: use the included export-enabled `legacy/wonderbook_visual_automatch_fixed.html` to download a JSON lesson pack, then import it in **Manage lessons**. The pack contains image files, available per-image narration/sound blobs, captions, and quiz questions.

**Migration scope:** this is the first Streamlit edition of the core shared lesson/presentation flow, not a pixel-for-pixel conversion of every capability in the standalone HTML. In particular, browser-based automatic sound-library matching and the full set of theatrical image transitions are not yet ported. When migrating, browser-origin rules may mean the export-enabled HTML needs to replace your current local HTML file at the same path before it can see the existing IndexedDB records.

## Try it locally

Requires Python 3.10 or newer.

### Windows

1. Install Python from [python.org](https://www.python.org/downloads/) if needed.
2. Open this folder in a terminal.
3. Run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   streamlit run app.py
   ```

4. Create `.streamlit/secrets.toml` with an editor password:

   ```toml
   EDITOR_PASSWORD = "choose-a-long-local-password"
   ```

5. Open the local URL printed in the terminal. In local mode, lessons are saved in `data/wonderbook.sqlite3` and uploaded files in `data/media/`.

Local mode is suitable for trying out the app. It does not automatically copy lesson data to a public website. Keep `.streamlit/secrets.toml` private; it is excluded by `.gitignore`.

## Make a public app with shared lessons

For a link that other people can open and that retains lessons after app restarts, deploy the app with a Supabase backend. Streamlit Community Cloud provides a shareable `*.streamlit.app` URL after deployment, while Supabase stores the shared lesson metadata and uploaded media.

### 1. Create the Supabase database and media bucket

1. Create a project at [supabase.com](https://supabase.com/).
2. Open **SQL Editor** in the project.
3. Paste and run the contents of `setup_supabase.sql`.
4. In **Project Settings → API**, copy the project URL and the server-side `service_role` key. Treat that key like a password: never put it in GitHub or browser code.

The setup script creates `wonderbook_lessons`, `wonderbook_attempts`, and a public media bucket called `wonderbook-media`. The media bucket is public because published lesson images and audio are meant to be playable by viewers with the app link. Do not upload confidential material.

### 2. Put this folder in GitHub

Create a GitHub repository and upload the contents of this folder. Keep `.streamlit/secrets.toml` out of Git; `.gitignore` already excludes it. Do not upload real keys or passwords.

### 3. Deploy with Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/).
2. Choose **Create app** and select your repository.
3. Set the entrypoint file to `app.py`.
4. In the app's **Secrets** settings, add the following TOML with your own values:

   ```toml
   SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
   SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
   EDITOR_PASSWORD = "choose-a-long-private-password"
   ```

5. Deploy. Streamlit will give the app a URL you can share. See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).

### 4. Add and publish lessons

1. Open your deployed URL.
2. Click **Manage lessons**.
3. Enter the `EDITOR_PASSWORD` you set in Streamlit Secrets.
4. Create a lesson, upload its images, then add narration/sound and questions to individual pictures.
5. Leave **Published / visible to students** enabled for lessons you want others to see.
6. Share the Streamlit URL with your learners. They can explore published lessons and complete quizzes without the editor password.

Published scores are tracked per anonymous Streamlit session, not as identified student records. This avoids collecting student names by default. If you later want class rosters, teacher reports, or durable student accounts, that should be added deliberately with proper access controls.

## Backups

For local mode, back up the whole `data/` folder. For hosted mode, use Supabase's database backup/export tools and keep copies of lesson source media where appropriate.

## Security notes

- Never commit `SUPABASE_SERVICE_KEY` or `EDITOR_PASSWORD` to GitHub.
- Public lessons and the uploaded media bucket are intended to be available to app viewers; do not publish private/student-sensitive content.
- Before sharing broadly, set a strong `EDITOR_PASSWORD` and configure Supabase so edits are persisted centrally.
