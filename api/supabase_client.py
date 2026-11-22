from functools import lru_cache

from django.conf import settings
from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Cliente Supabase do ambiente ativo (APP_ENV), criado uma única vez."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
