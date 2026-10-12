WONDERBOOK STREAMLIT QUICKSTART

A) Try locally:
  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  Create .streamlit/secrets.toml with:
    EDITOR_PASSWORD = "your-local-password"
  streamlit run app.py

B) Share with other people after uploading lessons:
  1. Create a Supabase project.
  2. Run setup_supabase.sql in its SQL Editor.
  3. Upload this folder to a GitHub repository.
  4. Deploy app.py on https://share.streamlit.io/.
  5. In Streamlit app Secrets add:
       SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
       SUPABASE_SERVICE_KEY = "YOUR_SERVICE_ROLE_KEY"
       EDITOR_PASSWORD = "your-long-private-password"
  6. Open Manage lessons, unlock the editor, upload and publish the lessons.
  7. Share the deployed Streamlit URL.

Important: local SQLite storage is for a local test. For a reliable shared public library, configure Supabase before deploying. Never upload the service-role key to GitHub.
See README.md for the full guide and limitations of this first Streamlit migration.
