"""
Background Operations Inspection API (Management Platform)

Provides read-only endpoints to inspect idempotency keys and saga workflows.
Attempts Redis first; falls back to in-memory manager if available on app.state.
"""

from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Query

try:
    from dotmac_shared.database.caching import get_redis_client
except Exception:  # pragma: no cover
    get_redis_client = None  # type: ignore

router = APIRouter(prefix="/api/v1/bgops", tags=["background-operations"])


async def _redis_available() -> bool:
    return get_redis_client is not None


async def _get_from_redis(key: str) -> Optional[Dict[str, Any]]:
    if not await _redis_available():
        return None
    try:
        redis = await get_redis_client()
        data = await redis.hgetall(key)
        if data:
            return data
        blob = await redis.get(key)
        return json.loads(blob) if blob else None
    except Exception:
        return None


@router.get("/idempotency", summary="List recent idempotency keys")
async def list_idempotency_keys(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    if await _redis_available():
        try:
            redis = await get_redis_client()
            # Get latest keys from index zset
            keys = await redis.zrevrange("bgops:idempo:index", 0, limit - 1)
            items: List[Dict[str, Any]] = []
            for k in keys:
                data = await redis.hgetall(f"bgops:idempo:{k}")
                if data:
                    data["key"] = k
                    items.append(data)
            return {"source": "redis", "count": len(items), "items": items}
        except Exception as e:
            return {"source": "redis", "error": str(e), "items": []}
    # Fallback: no redis
    return {"source": "memory", "items": []}


@router.get("/idempotency/{key}", summary="Get idempotency key details")
async def get_idempotency_key(key: str, request: Request) -> Dict[str, Any]:
    # Try Redis first
    data = await _get_from_redis(f"bgops:idempo:{key}")
    if data:
        data["key"] = key
        return {"source": "redis", "item": data}

    # Fallback to in-memory manager if available
    manager = getattr(request.app.state, "background_operations_manager", None)
    if manager:
        item = await manager.check_idempotency(key)
        if item:
            return {
                "source": "memory",
                "item": {
                    "key": item.key,
                    "tenant_id": item.tenant_id,
                    "user_id": item.user_id,
                    "operation_type": item.operation_type,
                    "created_at": item.created_at.isoformat(),
                    "expires_at": item.expires_at.isoformat(),
                    "status": item.status.value,
                },
            }
    raise HTTPException(status_code=404, detail="Idempotency key not found")


@router.get("/sagas/{saga_id}", summary="Get saga workflow state")
async def get_saga(saga_id: str, request: Request) -> Dict[str, Any]:
    # Try Redis first
    if await _redis_available():
        try:
            redis = await get_redis_client()
            data = await redis.get(f"bgops:saga:{saga_id}")
            if data:
                return {"source": "redis", "saga": json.loads(data)}
        except Exception:
            pass

    # Fallback to in-memory
    manager = getattr(request.app.state, "background_operations_manager", None)
    if manager:
        saga = manager.saga_workflows.get(saga_id)
        if saga:
            return {
                "source": "memory",
                "saga": {
                    "saga_id": saga.saga_id,
                    "tenant_id": saga.tenant_id,
                    "workflow_type": saga.workflow_type,
                    "status": saga.status.value,
                    "current_step": saga.current_step,
                    "steps": [
                        {
                            "step_id": s.step_id,
                            "name": s.name,
                            "status": s.status.value,
                            "error": s.error,
                        }
                        for s in saga.steps
                    ],
                },
            }
    raise HTTPException(status_code=404, detail="Saga not found")


@router.get("/sagas/{saga_id}/history", summary="Get saga step history")
async def get_saga_history(saga_id: str) -> Dict[str, Any]:
    if await _redis_available():
        try:
            redis = await get_redis_client()
            entries = await redis.lrange(f"bgops:saga:history:{saga_id}", 0, -1)
            items = [json.loads(e) for e in entries]
            return {"source": "redis", "items": items}
        except Exception as e:
            return {"source": "redis", "error": str(e), "items": []}
    return {"source": "memory", "items": []}

