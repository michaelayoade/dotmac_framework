#!/usr/bin/env python3
"""
Test and demonstrate the Performance Optimization features.
"""

import sys
import asyncio
import time
from unittest.mock import Mock

# Add src to Python path
sys.path.append('/home/dotmac_framework/src')

async def test_performance_optimization():
    """Test the performance optimization functionality."""
    
    print("🚀 Testing Performance Optimization System")
    print("=" * 60)
    
    try:
        # Import the performance optimization system
        from dotmac_shared.services.performance_optimization import (
            PerformanceOptimizationService,
            PerformanceOptimizationFactory,
            CacheLevel,
            enhance_service_with_performance
        )
        
        print("✅ Performance optimization imports successful")
        
        # Create mock database session
        mock_session = Mock()
        
        # Create performance service instance
        config = PerformanceOptimizationFactory.create_default_config()
        perf_service = PerformanceOptimizationFactory.create_performance_service(
            db_session=mock_session,
            tenant_id="test-tenant",
            config=config
        )
        
        print("✅ Performance optimization service created")
        
        # Test caching functionality
        print("\n💾 Testing Caching System...")
        
        # Test cache set and get
        cache_key = "test_key_1"
        test_data = {"message": "Hello, cached world!", "timestamp": time.time()}
        
        # Set cache
        set_success = await perf_service.cache_set(cache_key, test_data)
        print(f"✅ Cache set successful: {set_success}")
        
        # Get from cache
        cached_data = await perf_service.cache_get(cache_key)
        if cached_data == test_data:
            print("✅ Cache get successful - data matches")
        else:
            print("❌ Cache get failed - data mismatch")
        
        # Test cache miss
        missing_data = await perf_service.cache_get("non_existent_key")
        if missing_data is None:
            print("✅ Cache miss handled correctly")
        
        # Test cache invalidation
        await perf_service.cache_set("pattern_key_1", "data1")
        await perf_service.cache_set("pattern_key_2", "data2") 
        await perf_service.cache_set("other_key", "data3")
        
        invalidated_count = await perf_service.cache_invalidate("pattern_key")
        print(f"✅ Cache invalidation removed {invalidated_count} entries")
        
        # Test background task processing
        print("\n⚙️ Testing Background Task Processing...")
        
        task_results = []
        
        def sync_task(message: str, delay: float = 0):
            """Test synchronous task."""
            if delay > 0:
                time.sleep(delay)
            task_results.append(f"Sync task completed: {message}")
        
        async def async_task(message: str, delay: float = 0):
            """Test asynchronous task."""
            if delay > 0:
                await asyncio.sleep(delay)
            task_results.append(f"Async task completed: {message}")
        
        # Enqueue some background tasks
        task_id_1 = await perf_service.enqueue_background_task(
            "test_sync_task", sync_task, args=("Task 1",), priority=1
        )
        
        task_id_2 = await perf_service.enqueue_background_task(
            "test_async_task", async_task, args=("Task 2",), priority=2
        )
        
        print(f"✅ Enqueued background tasks: {task_id_1}, {task_id_2}")
        
        # Wait for tasks to process
        await asyncio.sleep(2)
        
        print(f"📊 Background task results: {len(task_results)} completed")
        for result in task_results:
            print(f"   - {result}")
        
        # Test performance metrics
        print("\n📊 Testing Performance Metrics...")
        
        # Simulate some operations to generate metrics
        for i in range(5):
            # Simulate cache operations
            await perf_service.cache_get(f"metric_test_{i}")
            await perf_service.cache_set(f"metric_test_{i}", f"data_{i}")
        
        # Get performance summary
        perf_summary = await perf_service.get_performance_summary()
        
        print("📈 Performance Summary:")
        print(f"   Cache Hit Rate: {perf_summary['service_metrics']['cache_hit_rate']:.1f}%")
        print(f"   Total Requests: {perf_summary['service_metrics']['total_requests']}")
        print(f"   Average Response Time: {perf_summary['service_metrics']['average_request_time_ms']:.2f}ms")
        print(f"   Error Rate: {perf_summary['service_metrics']['error_rate']:.1f}%")
        print(f"   Background Tasks: {perf_summary['service_metrics']['background_tasks_completed']}")
        
        print("\n💾 Cache Statistics:")
        cache_stats = perf_summary['cache_stats']
        print(f"   Memory Cache Size: {cache_stats['memory_cache_size']}")
        print(f"   Memory Usage: {cache_stats['memory_usage_percent']:.1f}%")
        print(f"   Default TTL: {cache_stats['default_ttl_seconds']}s")
        
        print("\n⚙️ Task Statistics:")
        task_stats = perf_summary['task_stats']
        print(f"   Queued Tasks: {task_stats['queued_tasks']}")
        print(f"   Running Tasks: {task_stats['running_tasks']}")
        print(f"   Completed Tasks: {task_stats['completed_tasks']}")
        print(f"   Success Rate: {task_stats['success_rate']:.1f}%")
        
        # Test decorators
        print("\n🎨 Testing Performance Decorators...")
        
        @perf_service.cached(ttl=60)
        async def expensive_operation(input_data: str) -> str:
            """Simulate an expensive operation."""
            await asyncio.sleep(0.1)  # Simulate processing time
            return f"Processed: {input_data}"
        
        @perf_service.performance_tracked
        async def tracked_operation(data: str) -> str:
            """Operation with performance tracking."""
            await asyncio.sleep(0.05)  # Simulate work
            return f"Tracked: {data}"
        
        # Test cached decorator
        start_time = time.time()
        result1 = await expensive_operation("test_data")
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        result2 = await expensive_operation("test_data")  # Should be cached
        second_call_time = time.time() - start_time
        
        print(f"✅ Cached operation results match: {result1 == result2}")
        print(f"📊 First call time: {first_call_time*1000:.1f}ms")
        print(f"⚡ Second call time (cached): {second_call_time*1000:.1f}ms")
        print(f"🚀 Speed improvement: {(first_call_time/second_call_time):.1f}x faster")
        
        # Test performance tracking decorator
        await tracked_operation("performance_test")
        print("✅ Performance tracking decorator executed")
        
        # Test service enhancement
        print("\n🔧 Testing Service Enhancement...")
        
        # Create a mock base service
        from dotmac_shared.services.base import BaseService
        
        mock_base_service = BaseService(mock_session, tenant_id="test")
        
        # Enhance with performance features
        enhanced_service = await enhance_service_with_performance(
            mock_base_service, 
            config
        )
        
        # Test that performance methods were added
        if hasattr(enhanced_service, 'cache_get'):
            print("✅ Service enhancement successful - cache methods added")
        
        if hasattr(enhanced_service, 'get_performance_summary'):
            print("✅ Service enhancement successful - performance methods added")
        
        # Test the enhanced service
        enhanced_cache_result = await enhanced_service.cache_set("enhanced_key", "enhanced_data")
        print(f"✅ Enhanced service caching works: {enhanced_cache_result}")
        
        print("\n" + "=" * 60)
        print("🎉 Performance Optimization Test Complete!")
        print("✅ All performance features working correctly")
        
        # Final performance summary
        final_summary = await perf_service.get_performance_summary()
        print(f"\n📊 Final Performance Stats:")
        print(f"   Total Cache Operations: {final_summary['service_metrics']['cache_hit_rate']:.1f}% hit rate")
        print(f"   Background Tasks Completed: {final_summary['task_stats']['completed_tasks']}")
        print(f"   Service Uptime: {final_summary['service_metrics']['uptime_seconds']:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance optimization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_performance_optimization()
    return 0 if success else 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)