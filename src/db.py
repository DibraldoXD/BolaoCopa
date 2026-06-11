"""Camada de acesso ao Supabase. Sem imports de streamlit exceto cache decorators."""

from __future__ import annotations

import hashlib
import hmac
import os

import streamlit as st
from supabase import create_client, Client


# ── Hashing de senha (PBKDF2-HMAC-SHA256) ────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
        return hmac.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


# ── Users ─────────────────────────────────────────────────────────────────────

def upsert_user(name: str, email: str, phone: str, password: str) -> dict:
    client = get_supabase()
    row = {
        "name": name,
        "email": email,
        "phone": phone,
        "password_hash": hash_password(password),
    }
    result = (
        client.table("users")
        .upsert(row, on_conflict="email")
        .execute()
    )
    user = result.data[0]
    user.pop("password_hash", None)  # nunca expõe o hash na sessão
    return user


def get_user_by_email(email: str) -> dict | None:
    """Retorna o usuário sem expor password_hash. Usar check_user_login() para autenticar."""
    client = get_supabase()
    result = (
        client.table("users")
        .select("*")
        .eq("email", email.strip().lower())
        .maybe_single()
        .execute()
    )
    if not result.data:
        return None
    user = dict(result.data)
    user.pop("password_hash", None)
    return user


def check_user_login(email: str, password: str) -> dict | None:
    """Autentica e-mail + senha. Retorna usuário (sem hash) ou None se falhar."""
    client = get_supabase()
    result = (
        client.table("users")
        .select("*")
        .eq("email", email.strip().lower())
        .maybe_single()
        .execute()
    )
    if not result.data:
        return None
    user = dict(result.data)
    stored = user.pop("password_hash", None)
    if not stored:
        return "no_password"  # conta antiga sem senha
    if not verify_password(password, stored):
        return None
    return user


# ── Teams ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_teams_by_group() -> dict[str, list[dict]]:
    client = get_supabase()
    result = client.table("teams").select("*").order("group_code").order("name").execute()
    groups: dict[str, list] = {}
    for t in result.data:
        groups.setdefault(t["group_code"], []).append(t)
    return groups


@st.cache_data(ttl=3600)
def get_teams_by_id() -> dict[int, dict]:
    client = get_supabase()
    result = client.table("teams").select("*").execute()
    return {t["id"]: t for t in result.data}


# ── Group predictions ─────────────────────────────────────────────────────────

def upsert_group_predictions(user_id: str, group_code: str, picks: dict[int, int]) -> None:
    """picks = {1: team_id, 2: team_id, 3: team_id}"""
    client = get_supabase()
    rows = [
        {"user_id": user_id, "group_code": group_code, "position": pos, "team_id": tid}
        for pos, tid in picks.items()
    ]
    client.table("group_predictions").upsert(
        rows, on_conflict="user_id,group_code,position"
    ).execute()
    get_user_group_predictions.clear()


@st.cache_data(ttl=300, max_entries=500)
def get_user_group_predictions(user_id: str) -> dict[str, dict[int, int]]:
    """Retorna {group_code: {position: team_id}}"""
    client = get_supabase()
    result = (
        client.table("group_predictions")
        .select("group_code, position, team_id")
        .eq("user_id", user_id)
        .execute()
    )
    preds: dict[str, dict] = {}
    for row in result.data:
        preds.setdefault(row["group_code"], {})[row["position"]] = row["team_id"]
    return preds


def count_completed_groups(predictions: dict[str, dict[int, int]]) -> int:
    return sum(1 for g in predictions.values() if len(g) == 3)


# ── Group results (admin) ─────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_group_results() -> dict[str, dict[int, int]]:
    """Retorna {group_code: {position: team_id}}"""
    client = get_supabase()
    result = client.table("group_results").select("*").execute()
    res: dict[str, dict] = {}
    for row in result.data:
        res.setdefault(row["group_code"], {})[row["position"]] = row["team_id"]
    return res


def upsert_group_result(group_code: str, position: int, team_id: int) -> None:
    client = get_supabase()
    client.table("group_results").upsert(
        {"group_code": group_code, "position": position, "team_id": team_id},
        on_conflict="group_code,position",
    ).execute()
    get_group_results.clear()


# ── Matches ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_matches(stage: str | None = None) -> list[dict]:
    client = get_supabase()
    q = (
        client.table("matches")
        .select(
            "*, "
            "home_team:teams!matches_home_team_id_fkey(id, name, flag_emoji), "
            "away_team:teams!matches_away_team_id_fkey(id, name, flag_emoji)"
        )
        .order("match_number")
    )
    if stage:
        q = q.eq("stage", stage)
    return q.execute().data


def save_match_result(match_id: int, home_score: int, away_score: int) -> None:
    client = get_supabase()
    client.table("matches").update(
        {"home_score": home_score, "away_score": away_score, "is_finished": True}
    ).eq("id", match_id).execute()
    get_matches.clear()


# ── Match predictions ─────────────────────────────────────────────────────────

def upsert_match_prediction(user_id: str, match_id: int, home: int, away: int) -> None:
    client = get_supabase()
    client.table("match_predictions").upsert(
        {"user_id": user_id, "match_id": match_id, "predicted_home": home, "predicted_away": away},
        on_conflict="user_id,match_id",
    ).execute()
    get_user_match_predictions.clear()


@st.cache_data(ttl=300, max_entries=500)
def get_user_match_predictions(user_id: str) -> dict[int, tuple[int, int]]:
    """Retorna {match_id: (predicted_home, predicted_away)}"""
    client = get_supabase()
    result = (
        client.table("match_predictions")
        .select("match_id, predicted_home, predicted_away")
        .eq("user_id", user_id)
        .execute()
    )
    return {r["match_id"]: (r["predicted_home"], r["predicted_away"]) for r in result.data}


# ── Leaderboard ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def get_leaderboard() -> list[dict]:
    client = get_supabase()
    result = client.from_("leaderboard").select("*").execute()
    return result.data


# ── Seed ──────────────────────────────────────────────────────────────────────

def ensure_seeded() -> None:
    """Times e jogos são gerenciados via SQL migrations — nada a fazer aqui."""
    st.session_state["_seeded"] = True
