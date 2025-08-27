"""
Performance Monitoring API Endpoints
Provides performance metrics and optimization controls
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.performance import (
    performance_metrics,
    get_performance_report,
    DatabaseOptimizer,
    query_cache
)
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/performance", tags=["performance"])

@router.get("/metrics")
async def get_performance_metrics(
    endpoint: Optional[str] = Query(None, description="Specific endpoint to get metrics for"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get performance metrics"""
    
    # Only allow admin users to view performance metrics
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if endpoint:
        stats = performance_metrics.get_stats(endpoint)
        if not stats:
            raise HTTPException(status_code=404, detail="No metrics found for endpoint")
        return stats
    
    return performance_metrics.get_stats()

@router.get("/report")
async def get_comprehensive_performance_report(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get comprehensive performance report"""
    
    # Only allow admin users to view performance reports
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return get_performance_report()

@router.get("/database/analysis")
async def get_database_performance_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Analyze database performance"""
    
    # Only allow master admin to view database analysis
    if current_user.role != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin access required")
    
    try:
        analysis = await DatabaseOptimizer.analyze_query_performance(db)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database analysis failed: {str(e)}")

@router.post("/database/optimize/{table_name}")
async def optimize_database_table(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Optimize specific database table"""
    
    # Only allow master admin to optimize database
    if current_user.role != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin access required")
    
    # Validate table name (basic security check)
    if not table_name.isalnum() and '_' not in table_name:
        raise HTTPException(status_code=400, detail="Invalid table name")
    
    try:
        result = await DatabaseOptimizer.optimize_table(db, table_name)
        return {
            "message": f"Optimization completed for table: {table_name}",
            "results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table optimization failed: {str(e)}")

@router.get("/cache/stats")
async def get_cache_statistics(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get cache statistics"""
    
    # Only allow admin users to view cache stats
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return query_cache.stats()

@router.post("/cache/clear")
async def clear_cache(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Clear application cache"""
    
    # Only allow master admin to clear cache
    if current_user.role != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin access required")
    
    try:
        query_cache.clear()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")

@router.get("/health/detailed")
async def get_detailed_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get detailed system health check"""
    
    # Only allow admin users to view detailed health
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    health_status = {
        "timestamp": "2024-01-01T00:00:00Z",  # Will be updated by actual implementation
        "status": "healthy",
        "database": {"status": "connected", "response_time_ms": 0},
        "cache": {"status": "operational", "hit_rate": 0.0},
        "services": []
    }
    
    try:
        # Test database connection
        import time
        db_start = time.time()
        await db.execute("SELECT 1")
        db_time = (time.time() - db_start) * 1000
        
        health_status["database"] = {
            "status": "connected",
            "response_time_ms": round(db_time, 2)
        }
        
        # Get cache stats
        cache_stats = query_cache.stats()
        health_status["cache"] = {
            "status": "operational",
            "entries": cache_stats.get("entries", 0),
            "memory_usage": cache_stats.get("memory_usage", 0)
        }
        
        # Add performance metrics summary
        perf_report = get_performance_report()
        health_status["performance_summary"] = {
            "total_requests": perf_report["overview"]["total_requests"],
            "error_rate": perf_report["overview"]["overall_error_rate"],
            "cache_entries": cache_stats.get("entries", 0)
        }
        
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["error"] = str(e)
    
    return health_status

@router.get("/recommendations")
async def get_performance_recommendations(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get performance optimization recommendations"""
    
    # Only allow admin users to view recommendations
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    report = get_performance_report()
    
    return {
        "recommendations": report.get("recommendations", []),
        "slowest_endpoints": report.get("slowest_endpoints", [])[:5],  # Top 5
        "generated_at": report["overview"]["report_generated"]
    }

@router.post("/metrics/reset")
async def reset_performance_metrics(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Reset performance metrics (for testing/maintenance)"""
    
    # Only allow master admin to reset metrics
    if current_user.role != "master_admin":
        raise HTTPException(status_code=403, detail="Master admin access required")
    
    try:
        # Reset metrics
        performance_metrics.metrics.clear()
        performance_metrics.request_counts.clear()
        performance_metrics.error_counts.clear()
        
        return {"message": "Performance metrics reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics reset failed: {str(e)}")

@router.get("/endpoints/slowest")
async def get_slowest_endpoints(
    limit: int = Query(10, ge=1, le=50, description="Number of endpoints to return"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get slowest endpoints"""
    
    # Only allow admin users to view slow endpoints
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    report = get_performance_report()
    slowest = report.get("slowest_endpoints", [])
    
    return {
        "slowest_endpoints": slowest[:limit],
        "total_endpoints": len(report.get("endpoint_stats", {}))
    }

@router.get("/system/resources")
async def get_system_resource_usage(
    current_user: CurrentUser = Depends(get_current_user)
):
    """Get system resource usage information"""
    
    # Only allow admin users to view system resources
    if current_user.role not in ["master_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        import psutil
        import os
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "core_count": psutil.cpu_count(logical=True)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "usage_percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "usage_percent": (disk.used / disk.total) * 100
            },
            "process": {
                "pid": os.getpid(),
                "memory_usage": psutil.Process().memory_info().rss
            }
        }
    except ImportError:
        return {
            "error": "psutil not available - install with 'pip install psutil'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system resources: {str(e)}")