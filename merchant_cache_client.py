"""
merchant_cache_client.py
────────────────────────────────────────────────────────────────────────────
Option A:  Redis is the fast-path cache (Tier 0A).
           Spring Boot DB is the persistent backup (Tier 0B).

Lookup order:
  1. Redis GET  →  hit: return instantly  (< 1 ms)
  2. Spring Boot HTTP GET  →  hit: warm Redis, return
  3. Both miss  →  caller falls through to Tier 1/2/3

Save order  (after Groq classifies a new merchant):
  1. Redis SET   (immediate effect for next request)
  2. Spring Boot HTTP POST  (persistent DB backup)

Key schema:  merchant:<user_id>:<MERCHANT_NAME_UPPER>  →  "Category Name"
────────────────────────────────────────────────────────────────────────────
"""

# pyrefly: ignore [missing-import]
import os
import httpx
import redis
from dotenv import load_dotenv
from config import REDIS_URL, REDIS_CACHE_TTL

load_dotenv()

# ── Spring Boot endpoints (persistent DB backup, unchanged) ───────────────
SPRING_BOOT_BASE_URL = os.getenv("SPRING_BOOT_BASE_URL", "http://localhost:8080")
CACHE_LOOKUP_URL     = f"{SPRING_BOOT_BASE_URL}/api/merchant-cache/lookup"
CACHE_SAVE_URL       = f"{SPRING_BOOT_BASE_URL}/api/merchant-cache"
_http_client         = httpx.Client(timeout=5.0)

# ── Redis connection (lazy singleton with built-in connection pool) ────────
_redis_client: redis.Redis | None = None


def _get_redis() -> "redis.Redis | None":
    """
    Returns a shared Redis client, creating it on first call.
    Returns None if Redis is unreachable so callers degrade gracefully.
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=True,    # always return str, not bytes
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _redis_client.ping()          # fail fast at startup if Redis is down
            print(f"[Redis] Connected → {REDIS_URL}")
        except redis.RedisError as e:
            print(f"[Redis] Connection failed ({e}) — degrading to Spring Boot only")
            _redis_client = None
    return _redis_client


def _make_key(user_id: int, merchant_name: str) -> str:
    """Builds a consistent, namespaced Redis key."""
    return f"merchant:{user_id}:{merchant_name.upper()}"


def _redis_set(r: "redis.Redis | None", key: str, value: str) -> None:
    """Writes to Redis, respecting the configured TTL. Swallows errors silently."""
    if r is None:
        return
    try:
        if REDIS_CACHE_TTL > 0:
            r.setex(key, REDIS_CACHE_TTL, value)
        else:
            r.set(key, value)
    except redis.RedisError as e:
        print(f"[Redis] Write error for key '{key}': {e}")


# ── Public API (identical signatures to the old httpx-only version) ────────

def lookup_merchant_cache(user_id: int, merchant_name: str) -> str | None:
    """
    Tier 0A — Redis fast path:
        GET merchant:<user_id>:<MERCHANT>
        HIT  → return category string immediately
        MISS → fall through to Tier 0B

    Tier 0B — Spring Boot persistent DB backup:
        HTTP GET /api/merchant-cache/lookup
        HIT  → warm Redis with this result, return category string
        MISS → return None  (caller proceeds to Tier 1/2)
    """
    # No userId = no personal cache to check; skip both tiers cleanly
    if not user_id:
        return None

    key = _make_key(user_id, merchant_name)
    r   = _get_redis()

    # Tier 0A: Redis ──────────────────────────────────────────────────────
    if r is not None:
        try:
            cached = r.get(key)
            if cached:
                print(f"[Redis HIT]  '{merchant_name}' → '{cached}'")
                return cached
        except redis.RedisError as e:
            print(f"[Redis] Lookup error for '{merchant_name}': {e}")

    # Tier 0B: Spring Boot DB (fallback + Redis warm-up) ─────────────────
    try:
        response = _http_client.get(
            CACHE_LOOKUP_URL,
            params={"userId": user_id, "merchantName": merchant_name.upper()}
        )
        if response.status_code == 200:
            category = response.json().get("categoryName")
            if category:
                print(f"[Spring HIT] '{merchant_name}' → '{category}' (warming Redis)")
                _redis_set(r, key, category)   # warm Redis for next request
                return category

    except httpx.RequestError as e:
        print(f"[Spring] Lookup failed for '{merchant_name}': {e}")

    return None   # complete miss — proceed to Tier 1 / 2 / 3


def save_merchant_cache(user_id: int, merchant_name: str, category_name: str) -> None:
    """
    Writes a newly classified merchant → category to:
      1. Redis     — instant effect for next request in this or any session
      2. Spring Boot DB — persistent backup that survives a Redis flush/restart

    Both writes are non-fatal — a failure in either won't crash the pipeline.
    """
    key = _make_key(user_id, merchant_name)
    r   = _get_redis()

    # Write 1: Redis (fast path)
    _redis_set(r, key, category_name)
    print(f"[Redis SAVE] '{merchant_name}' → '{category_name}'")

    # Write 2: Spring Boot persistent DB
    try:
        response = _http_client.post(
            CACHE_SAVE_URL,
            json={
                "userId":       user_id,
                "merchantName": merchant_name.upper(),
                "categoryName": category_name,
            }
        )
        if response.status_code in (200, 201):
            print(f"[Spring DB] MySQL save confirmed for '{merchant_name}' → '{category_name}'")
        else:
            print(f"[Spring DB] Warning: MySQL save failed for '{merchant_name}' with status {response.status_code}")
    except httpx.RequestError as e:
        print(f"[Spring DB] MySQL save failed due to network error for '{merchant_name}': {e}")
