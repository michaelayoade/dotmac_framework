import logging

logger = logging.getLogger(__name__)

"""
Environment Validation Tests

Validates that the dockerized test environment is properly set up
and all required services are accessible and functional.
"""

import pytest
import requests
import redis
import psycopg2
import time
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.environment_validation
def test_redis_connectivity():
    """
    Environment Test: Redis is accessible and functional.
    """
    # Given: Redis should be running on test port
    redis_client = redis.Redis(host='localhost', port=6380, decode_responses=True)
    
    # When: We ping Redis
    response = redis_client.ping()
    
    # Then: Should respond with PONG
    assert response is True
    
    # And: We should be able to set/get values
    test_key = "test:environment:validation"
    test_value = "redis_working"
    
    redis_client.set(test_key, test_value)
    retrieved_value = redis_client.get(test_key)
    
    assert retrieved_value == test_value
    
    # Cleanup
    redis_client.delete(test_key)


@pytest.mark.integration
@pytest.mark.environment_validation
def test_postgres_connectivity():
    """
    Environment Test: PostgreSQL is accessible and functional.
    """
    # Given: PostgreSQL should be running on test port
    connection_params = {
        'host': 'localhost',
        'port': 5433,
        'database': 'dotmac_test',
        'user': 'test_user',
        'password': 'test_password'
    }
    
    # When: We connect to PostgreSQL
    conn = psycopg2.connect(**connection_params)
    cursor = conn.cursor()
    
    # Then: Should be able to execute queries
    cursor.execute("SELECT version()")
    version = cursor.fetchone()
    assert version is not None
    assert 'PostgreSQL' in version[0]
    
    # And: Should be able to create/query tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_validation (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    cursor.execute("""
        INSERT INTO test_validation (name) VALUES (%s) RETURNING id
    """, ('environment_test',)
    
    result = cursor.fetchone()
    assert result is not None
    test_id = result[0]
    
    # Verify data was inserted
    cursor.execute("SELECT name FROM test_validation WHERE id = %s", (test_id,)
    retrieved_name = cursor.fetchone()[0]
    assert retrieved_name == 'environment_test'
    
    # Cleanup
    cursor.execute("DROP TABLE IF EXISTS test_validation")
    conn.commit()
    cursor.close()
    conn.close()


@pytest.mark.integration
@pytest.mark.environment_validation
def test_http_mock_service():
    """
    Environment Test: HTTP mock service is accessible and functional.
    """
    # Given: HTTP mock service should be running
    base_url = "http://localhost:8080"
    
    # When: We make HTTP requests
    get_response = requests.get(f"{base_url}/get")
    
    # Then: Should respond correctly
    assert get_response.status_code == 200
    get_data = get_response.json()
    
    assert "headers" in get_data
    assert "url" in get_data
    assert get_data["url"] == f"{base_url}/get"
    
    # And: Should handle POST requests
    post_data = {"test": "data", "environment": "validation"}
    post_response = requests.post(f"{base_url}/post", json=post_data)
    
    assert post_response.status_code == 200
    post_result = post_response.json()
    
    assert "json" in post_result
    assert post_result["json"] == post_data


@pytest.mark.integration
@pytest.mark.environment_validation
def test_cross_service_integration():
    """
    Integration Test: Multiple services can work together.
    
    This test validates that we can use all services in a coordinated way,
    simulating a real application workflow.
    """
    # Given: All services are running
    redis_client = redis.Redis(host='localhost', port=6380, decode_responses=True)
    pg_conn = psycopg2.connect(
        host='localhost', port=5433, database='dotmac_test',
        user='test_user', password='test_password'
    )
    cursor = pg_conn.cursor()
    
    # When: We simulate a complete workflow
    # 1. Store session data in Redis
    session_id = f"session_{int(time.time() * 1000)}"  # Use unique session ID
    session_data = {"user_id": f"test_user_{int(time.time() * 1000)}", "authenticated": "true"}  # Redis values as strings
    redis_client.hset(f"session:{session_id}", mapping=session_data)
    
    # 2. Create user record in PostgreSQL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) UNIQUE,
            session_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    cursor.execute("""
        INSERT INTO test_users (user_id, session_id) VALUES (%s, %s) RETURNING id
    """, (session_data["user_id"], session_id)
    
    user_record_id = cursor.fetchone()[0]
    pg_conn.commit()
    
    # 3. Make HTTP request with session context
    response = requests.get("http://localhost:8080/headers", 
                          headers={"X-Session-ID": session_id})
    assert response.status_code == 200
    
    # Then: All data should be consistent
    # Verify Redis session
    retrieved_session = redis_client.hgetall(f"session:{session_id}")
    assert retrieved_session["user_id"] == session_data["user_id"]
    assert retrieved_session["authenticated"] == session_data["authenticated"]
    
    # Verify PostgreSQL record
    cursor.execute("SELECT user_id, session_id FROM test_users WHERE id = %s", 
                  (user_record_id,)
    db_user, db_session = cursor.fetchone()
    assert db_user == session_data["user_id"]
    assert db_session == session_id
    
    # Verify HTTP response included our session header
    http_response_data = response.json()
    assert "X-Session-Id" in http_response_data["headers"]  # httpbin normalizes header names
    assert http_response_data["headers"]["X-Session-Id"] == session_id
    
    # Cleanup
    redis_client.delete(f"session:{session_id}")
    cursor.execute("DROP TABLE IF EXISTS test_users")
    pg_conn.commit()
    cursor.close()
    pg_conn.close()


@pytest.mark.integration
@pytest.mark.performance_baseline
def test_environment_performance_baseline():
    """
    Performance Baseline Test: Establish performance metrics for test environment.
    
    This test establishes baseline performance metrics that can be used
    to detect regressions in the test infrastructure itself.
    """
    import time
    
    # Test database connection speed
    start_time = time.time()
    conn = psycopg2.connect(
        host='localhost', port=5433, database='dotmac_test',
        user='test_user', password='test_password'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    cursor.fetchone()
    db_connection_time = time.time() - start_time
    cursor.close()
    conn.close()
    
    # Test Redis connection speed
    start_time = time.time()
    redis_client = redis.Redis(host='localhost', port=6380)
    redis_client.ping()
    redis_connection_time = time.time() - start_time
    
    # Test HTTP service response time
    start_time = time.time()
    response = requests.get("http://localhost:8080/get")
    http_response_time = time.time() - start_time
    
    # Baseline expectations (these are generous for Docker containers)
    assert db_connection_time < 1.0, f"DB connection too slow: {db_connection_time:.3f}s"
    assert redis_connection_time < 0.5, f"Redis connection too slow: {redis_connection_time:.3f}s"
    assert http_response_time < 2.0, f"HTTP response too slow: {http_response_time:.3f}s"
    assert response.status_code == 200
    
    # Log performance metrics for monitoring
logger.info(f"\n📊 Environment Performance Baseline:")
logger.info(f"  Database connection: {db_connection_time:.3f}s")
logger.info(f"  Redis connection: {redis_connection_time:.3f}s")
logger.info(f"  HTTP response: {http_response_time:.3f}s")