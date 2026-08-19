from fastapi import APIRouter
import redis.asyncio as aioredis
from app.core.config import settings
from app.db.session import check_db_health

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Verify application health and database/redis connectivity."""
    db_healthy = await check_db_health()
    
    redis_healthy = False
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        redis_healthy = await r.ping()
        await r.close()
    except Exception:
        redis_healthy = False

    status_str = "healthy" if (db_healthy and redis_healthy) else "unhealthy"

    return {
        "status": status_str,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "connected" if db_healthy else "disconnected",
            "redis": "connected" if redis_healthy else "disconnected"
        }
    }
