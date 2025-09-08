#!/usr/bin/env python3
"""
Database Testing Framework Example

Demonstrates how to use the comprehensive database testing framework
to validate transactions, constraints, data integrity, performance,
and tenant isolation.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotmac_shared.tenant.identity import TenantContext
from dotmac_shared.testing.database import DatabaseTestConfig, DatabaseTestSuite, run_full_database_test_suite
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Example models for testing
Base = declarative_base()


class User(Base):
    """Example User model with tenant isolation"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="user")


class Order(Base):
    """Example Order model with foreign key constraints"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    amount = Column(Integer, nullable=False)  # in cents
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")


async def main():
    """Run comprehensive database testing example"""

    # Database setup (using SQLite for example)
    DATABASE_URL = "sqlite:///:memory:"

    # Create tables
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.drop_all(engine)  # Clean slate
    Base.metadata.create_all(engine)

    print("🔍 Database Testing Framework Example")
    print("=" * 50)

    # Define models to test
    model_classes = [User, Order]

    # Prepare test data
    test_data = {
        User: [
            {"username": "user1", "email": "user1@example.com", "tenant_id": "tenant_1"},
            {"username": "user2", "email": "user2@example.com", "tenant_id": "tenant_1"},
            {"username": "user3", "email": "user3@example.com", "tenant_id": "tenant_2"},
        ],
        Order: [
            {"user_id": 1, "product_name": "Test Product 1", "amount": 1000, "tenant_id": "tenant_1"},
            {"user_id": 1, "product_name": "Test Product 2", "amount": 2000, "tenant_id": "tenant_1"},
            {"user_id": 3, "product_name": "Test Product 3", "amount": 1500, "tenant_id": "tenant_2"},
        ],
    }

    # Create tenant contexts for isolation testing
    tenant_contexts = [
        TenantContext(
            tenant_id="tenant_1",
            subdomain="company1",
            host="company1.example.com",
            is_management=False,
            is_verified=True,
            metadata={"plan": "premium"},
        ),
        TenantContext(
            tenant_id="tenant_2",
            subdomain="company2",
            host="company2.example.com",
            is_management=False,
            is_verified=True,
            metadata={"plan": "basic"},
        ),
    ]

    print(f"📊 Testing {len(model_classes)} models with {len(tenant_contexts)} tenants")
    print()

    # Example 1: Quick comprehensive test
    print("🚀 Running quick comprehensive test...")

    DatabaseTestConfig(
        database_url=DATABASE_URL,
        test_suites=[DatabaseTestSuite.COMPREHENSIVE],
        load_test_users=5,
        load_test_duration=10,
        concurrent_operations=3,
    )

    quick_results = await run_full_database_test_suite(
        DATABASE_URL,
        model_classes,
        test_data,
        tenant_contexts,
        test_suites=[DatabaseTestSuite.COMPREHENSIVE],
        load_test_users=5,
        load_test_duration=10,
    )

    print_test_summary(quick_results, "Quick Comprehensive Test")

    # Example 2: Focused transaction and integrity testing
    print("\n🔄 Running focused transaction and integrity tests...")

    focused_results = await run_full_database_test_suite(
        DATABASE_URL,
        model_classes,
        test_data,
        test_suites=[DatabaseTestSuite.TRANSACTIONS, DatabaseTestSuite.INTEGRITY],
        include_concurrent_tests=True,
        concurrent_operations=10,
    )

    print_test_summary(focused_results, "Transaction & Integrity Tests")

    # Example 3: Performance and tenant isolation focus
    print("\n⚡ Running performance and tenant isolation tests...")

    perf_results = await run_full_database_test_suite(
        DATABASE_URL,
        model_classes,
        test_data,
        tenant_contexts,
        test_suites=[DatabaseTestSuite.PERFORMANCE, DatabaseTestSuite.TENANT_ISOLATION],
        load_test_users=8,
        load_test_duration=20,
        include_performance_isolation=True,
    )

    print_test_summary(perf_results, "Performance & Isolation Tests")

    # Example 4: Custom configuration with all test types
    print("\n🎯 Running custom comprehensive testing...")

    custom_config = DatabaseTestConfig(
        database_url=DATABASE_URL,
        test_suites=[DatabaseTestSuite.COMPREHENSIVE],
        include_rollback_tests=True,
        include_isolation_tests=True,
        include_concurrent_tests=True,
        include_acid_tests=True,
        concurrent_operations=7,
        load_test_users=12,
        load_test_duration=15,
        include_performance_isolation=True,
    )

    tester = ComprehensiveDatabaseTester(custom_config)
    custom_results = await tester.run_comprehensive_tests(model_classes, test_data, tenant_contexts)

    print_test_summary(custom_results, "Custom Configuration Tests")

    # Show detailed recommendations
    print("\n💡 Detailed Recommendations")
    print("-" * 30)
    for recommendation in custom_results.get("recommendations", []):
        print(f"   • {recommendation}")

    # Show performance analysis
    if "performance_analysis" in custom_results:
        perf_analysis = custom_results["performance_analysis"]
        print("\n⚡ Performance Analysis")
        print("-" * 30)
        print(f"   Total execution time: {perf_analysis.get('total_time', 0):.2f}s")
        print(f"   Average suite time: {perf_analysis.get('average_suite_time', 0):.2f}s")

        if "slowest_suite" in perf_analysis:
            slowest = perf_analysis["slowest_suite"]
            print(f"   Slowest suite: {slowest['name']} ({slowest['time']:.2f}s)")

    print("\n✅ Database testing example completed!")

    # Clean up
    os.remove("test_database.db")


def print_test_summary(results: Dict, test_name: str):
    """Print a summary of test results"""

    print(f"\n📋 {test_name} Results:")
    print("-" * 40)

    if "summary" in results:
        summary = results["summary"]
        print(f"   Total tests: {summary.get('total_tests', 0)}")
        print(f"   Passed: {summary.get('passed_tests', 0)}")
        print(f"   Failed: {summary.get('failed_tests', 0)}")
        print(f"   Errors: {summary.get('error_tests', 0)}")
        print(f"   Pass rate: {summary.get('pass_rate', 0):.1f}%")
        print(f"   Execution time: {summary.get('total_execution_time', 0):.2f}s")
        print(f"   Suites run: {summary.get('suites_run', 0)}")

    if "recommendations" in results:
        recommendations = results["recommendations"]
        if recommendations:
            print(f"   Key recommendations: {len(recommendations)}")
            for rec in recommendations[:2]:  # Show first 2
                print(f"     • {rec}")


if __name__ == "__main__":
    # Import the comprehensive tester here to avoid circular import
    from dotmac_shared.testing.database.comprehensive_tester import ComprehensiveDatabaseTester

    asyncio.run(main())
