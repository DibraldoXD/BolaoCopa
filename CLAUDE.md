# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Copa** is a World Cup 2026 bolão (prediction pool) web app. Users register (name/email/phone), pick the **top 3 teams per group** (12 groups), and the app auto-generates the R32 knockout bracket. Users also predict individual match scores. A leaderboard scores both prediction types in real time.

Design reference: `pics/image.png` — light theme, gold/green World Cup palette, card-based group layout.

## Running the App

```bash
uv run streamlit run streamlit_app.py
```

App runs at `http://localhost:8501`. Credentials live in `.streamlit/secrets.toml` (gitignored):
```toml
[supabase]
url = "..."
anon_key = "..."
```

## Architecture

```
streamlit_app.py          # Entry point: st.navigation, session init, sidebar
app_pages/
  register.py             # Cadastro (name/email/phone) + email lookup
  groups.py               # Top-3 picks per group, @st.fragment cards, lock on 2026-06-11
  matches.py              # Score predictions per match, locked when match starts
  bracket.py              # R32 bracket from user's group picks + official results
  leaderboard.py          # Auto-refresh every 60s via @st.fragment(run_every="60s")
  admin.py                # Enter official group results + match scores (is_admin guard)
lib/
  db.py                   # All Supabase queries; @st.cache_data decorators here
  utils.py                # flag_img() + team_html() — flagcdn.com <img> tags
  seed_data.py            # 48 official WC2026 teams (reference only, not called at runtime)
  bracket.py              # generate_bracket() — R32 pairing logic
  scoring.py              # get_user_rank() wrapper around leaderboard view
```

## Database (Supabase PostgreSQL)

**Tables:** `teams`, `users`, `matches`, `group_predictions`, `group_results`, `match_predictions`  
**View:** `leaderboard` — calculates points in SQL (group: 10pts exact position, 5pts wrong position; match: 3pts exact score, 1pt correct outcome)

**RLS rules:** anon key has SELECT on `teams`/`matches`/`group_results`; INSERT/UPDATE on `users`/`group_predictions`/`match_predictions`. **The anon key cannot INSERT into `teams` or `matches`** — use Supabase migrations for any data changes to those tables.

**Seeding:** Teams and group-stage matches are seeded via SQL migration `004_seed_wc2026_teams_and_matches`. To re-seed after clearing, apply a new migration — do NOT try to seed from the app.

**Admin setup:** `UPDATE users SET is_admin=true WHERE email='...'` in Supabase.

## Key Patterns

**Cache invalidation:** `get_teams_by_group()` has `ttl=3600`. After any DB change to teams or matches, restart the app to clear in-memory cache.

**Flag rendering:** Windows doesn't render Unicode Regional Indicator flag emojis. All team display uses `lib/utils.py:team_html(emoji, name)` which generates `<img>` tags from `flagcdn.com`. Selectboxes use plain team names (no HTML). flagcdn.com only supports widths `[20, 40, 80, 160, 320, 640, 1280, 2560]` — `_snap_width()` handles rounding.

**Fragment pattern:** Each group card in `groups.py` is a `@st.fragment`. Picks are read INSIDE the fragment (not passed as arguments) so `st.rerun(scope="fragment")` fetches fresh data after save. The cache is cleared via `get_user_group_predictions.clear()` after every upsert.

**Leaderboard:** Reads from the `leaderboard` SQL view directly; no Python-side scoring logic.

## Theme

Defined in `.streamlit/config.toml`. Primary gold `#C8960C`, link/accent green `#1B6C2B`, dark green sidebar `#1A3B22`. Font: Barlow (loaded from Google Fonts). Do not add Inter/Roboto/Arial or generic purple/blue palettes.

## Skills

- `/frontend-design` — UI component design guidance
- `/developing-with-streamlit` — Streamlit patterns, layouts, theming reference
