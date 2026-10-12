-- Run this script in your Supabase project's SQL Editor.
-- This is a server-side app: keep SUPABASE_SERVICE_KEY in Streamlit Secrets only.

create table if not exists public.wonderbook_lessons (
  id text primary key,
  title text not null,
  description text not null default '',
  published boolean not null default true,
  items jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.wonderbook_attempts (
  id text primary key,
  lesson_id text not null,
  image_id text not null,
  viewer_id text not null,
  correct integer not null default 0,
  total integer not null default 0,
  percentage numeric not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists wonderbook_attempts_viewer_lesson_idx
  on public.wonderbook_attempts (viewer_id, lesson_id, created_at);

-- Public media are appropriate here only because published lesson images/audio are intended
-- for anyone with the app link to view. Upload and deletion use the service key server-side.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'wonderbook-media',
  'wonderbook-media',
  true,
  52428800,
  array['image/jpeg','image/png','image/webp','image/gif','audio/mpeg','audio/wav','audio/ogg','audio/mp4','audio/aac','video/mp4']
)
on conflict (id) do update set public = excluded.public;

-- The Streamlit server accesses tables using the service-role key (stored as a secret).
-- Do not put that key in the repository or HTML/browser code. RLS is enabled as a safeguard.
alter table public.wonderbook_lessons enable row level security;
alter table public.wonderbook_attempts enable row level security;

-- Do not add anon write policies. This app performs all database actions on the server.
-- Public access to lesson content occurs through Streamlit's server-side reads.
