from __future__ import annotations

from supabase import Client, create_client

from src.config import Settings


def create_supabase_client(settings: Settings, *, privileged: bool = False) -> Client:
    key = settings.service_role_key if privileged else settings.anon_key
    if not settings.supabase_url or not key:
        role = "service-role" if privileged else "anonymous"
        raise ValueError(f"Supabase URL or {role} key is missing.")
    return create_client(settings.supabase_url, key)
