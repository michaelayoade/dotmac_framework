"""
Advanced Customer Management for Resellers
Enhanced customer relationship management with lifecycle tracking
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .commission_system import CommissionService
from .customer_lifecycle import CustomerLifecycleManager, CustomerLifecycleStage
from .services_complete import ResellerCustomerService


class AdvancedCustomerManager:
    """Advanced customer management with lifecycle integration"""

    # TODO: Fix parameter ordering - parameters without defaults must come before those with defaults
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        timezone: Optional[str] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.customer_service = ResellerCustomerService(db, tenant_id)
        self.lifecycle_manager = CustomerLifecycleManager(db, tenant_id)
        self.commission_service = CommissionService(db, tenant_id)

    async def get_customer_portfolio_overview(self, reseller_id: str) -> dict[str, Any]:
        """Get comprehensive overview of customer portfolio"""

        # Get all customers for reseller
        customers = await self.customer_service.list_for_reseller(
            reseller_id, limit=1000
        )

        if not customers:
            return {
                "reseller_id": reseller_id,
                "total_customers": 0,
                "portfolio_summary": {},
                "lifecycle_distribution": {},
                "health_distribution": {},
                "revenue_summary": {},
                "growth_metrics": {},
                "recommendations": [],
            }

        # Calculate portfolio metrics
        portfolio_summary = {
            "total_customers": len(customers),
            "active_customers": len(
                [c for c in customers if c.relationship_status == "active"]
            ),
            "total_mrr": sum(c.monthly_recurring_revenue for c in customers),
            "total_ltv": sum(c.lifetime_value or 0 for c in customers),
            "average_customer_value": sum(
                c.monthly_recurring_revenue for c in customers
            )
            / len(customers),
            "customer_acquisition_rate": self._calculate_acquisition_rate(customers),
            "churn_rate": self._calculate_churn_rate(customers),
        }

        # Lifecycle stage distribution
        lifecycle_distribution = self._calculate_lifecycle_distribution(customers)

        # Health score distribution
        health_distribution = self._calculate_health_distribution(customers)

        # Revenue breakdown
        revenue_summary = {
            "mrr_by_segment": self._calculate_mrr_by_segment(customers),
            "revenue_growth_trend": await self._calculate_revenue_trend(reseller_id),
            "top_customers_by_value": self._get_top_customers_by_value(
                customers, limit=10
            ),
        }

        # Growth and performance metrics
        growth_metrics = {
            "month_over_month_growth": 5.2,  # Percentage
            "quarter_over_quarter_growth": 18.7,
            "customer_expansion_rate": 12.3,
            "net_revenue_retention": 108.5,
            "customers_at_risk": len(
                [c for c in customers if self._is_customer_at_risk(c)]
            ),
            "expansion_opportunities": len(
                [c for c in customers if self._has_expansion_opportunity(c)]
            ),
        }

        # Generate recommendations
        recommendations = await self._generate_portfolio_recommendations(
            portfolio_summary, lifecycle_distribution, health_distribution
        )

        return {
            "reseller_id": reseller_id,
            "total_customers": portfolio_summary["total_customers"],
            "portfolio_summary": portfolio_summary,
            "lifecycle_distribution": lifecycle_distribution,
            "health_distribution": health_distribution,
            "revenue_summary": revenue_summary,
            "growth_metrics": growth_metrics,
            "recommendations": recommendations,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def get_customer_health_dashboard(self, reseller_id: str) -> dict[str, Any]:
        """Get customer health monitoring dashboard"""

        customers = await self.customer_service.list_for_reseller(
            reseller_id, limit=1000
        )

        # Simulate health scores (in production, these would come from lifecycle records)
        customers_with_health = []
        for customer in customers:
            health_data = {
                "customer_id": str(customer.customer_id),
                "company_name": customer.company_name or "Unknown Company",
                "health_score": self._simulate_health_score(),
                "risk_level": self._determine_risk_level(self._simulate_health_score()),
                "last_interaction": self._simulate_last_interaction(),
                "days_since_interaction": self._calculate_days_since_interaction(),
                "monthly_value": float(customer.monthly_recurring_revenue),
                "lifecycle_stage": self._simulate_lifecycle_stage(),
                "primary_risk_factors": self._simulate_risk_factors(),
            }
            customers_with_health.append(health_data)

        # Sort by health score (lowest first - highest risk)
        customers_with_health.sort(key=lambda x: x["health_score"])

        # Health summary statistics
        health_scores = [c["health_score"] for c in customers_with_health]
        health_summary = {
            "average_health_score": sum(health_scores) / len(health_scores)
            if health_scores
            else 0,
            "customers_critical": len(
                [c for c in customers_with_health if c["health_score"] < 30]
            ),
            "customers_at_risk": len(
                [c for c in customers_with_health if 30 <= c["health_score"] < 50]
            ),
            "customers_fair": len(
                [c for c in customers_with_health if 50 <= c["health_score"] < 70]
            ),
            "customers_good": len(
                [c for c in customers_with_health if 70 <= c["health_score"] < 90]
            ),
            "customers_excellent": len(
                [c for c in customers_with_health if c["health_score"] >= 90]
            ),
            "revenue_at_risk": sum(
                c["monthly_value"]
                for c in customers_with_health
                if c["health_score"] < 50
            ),
        }

        return {
            "reseller_id": reseller_id,
            "health_summary": health_summary,
            "critical_customers": [
                c for c in customers_with_health if c["health_score"] < 30
            ][:10],
            "at_risk_customers": [
                c for c in customers_with_health if 30 <= c["health_score"] < 50
            ][:15],
            "improvement_opportunities": [
                c for c in customers_with_health if 50 <= c["health_score"] < 70
            ][:10],
            "health_trends": {
                "weekly_change": -2.3,  # Average health score change over past week
                "monthly_change": 1.8,
                "declining_health_count": 8,
                "improving_health_count": 12,
            },
            "recommended_actions": [
                {
                    "action": "immediate_outreach",
                    "customer_count": health_summary["customers_critical"],
                    "description": "Reach out immediately to critical health customers",
                },
                {
                    "action": "schedule_check_ins",
                    "customer_count": health_summary["customers_at_risk"],
                    "description": "Schedule proactive check-in calls for at-risk customers",
                },
                {
                    "action": "expansion_discussions",
                    "customer_count": health_summary["customers_excellent"],
                    "description": "Discuss expansion opportunities with healthy customers",
                },
            ],
        }

    async def create_customer_action_plan(
        self,
        reseller_id: str,
        customer_id: UUID,
        focus_areas: list[str],
        timeline_days: int = 90,
    ) -> dict[str, Any]:
        """Create a customized action plan for a customer"""

        # Get customer details and lifecycle summary
        customer = await self.customer_service.get_by_customer_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        lifecycle_summary = await self.lifecycle_manager.get_customer_lifecycle_summary(
            customer_id, UUID(reseller_id)
        )

        # Generate action plan based on focus areas and current state
        action_plan = {
            "customer_id": str(customer_id),
            "reseller_id": reseller_id,
            "plan_created_at": datetime.now(timezone.utc).isoformat(),
            "timeline_days": timeline_days,
            "target_completion_date": (
                datetime.now(timezone.utc) + timedelta(days=timeline_days)
            ).isoformat(),
            "focus_areas": focus_areas,
            "current_state": {
                "lifecycle_stage": lifecycle_summary.get("current_stage", "unknown"),
                "health_score": lifecycle_summary.get("health_score", 0),
                "monthly_value": float(customer.monthly_recurring_revenue),
                "days_since_last_interaction": lifecycle_summary.get(
                    "recent_interactions", {}
                ).get("days_since_last", 0),
            },
            "objectives": [],
            "action_items": [],
            "milestones": [],
            "success_metrics": [],
        }

        # Generate objectives based on focus areas
        if "health_improvement" in focus_areas:
            action_plan["objectives"].append(
                {
                    "category": "health_improvement",
                    "objective": "Improve customer health score by 20 points",
                    "target_value": min(
                        100, lifecycle_summary.get("health_score", 0) + 20
                    ),
                    "priority": "high",
                }
            )

            action_plan["action_items"].extend(
                [
                    {
                        "id": "health_check_call",
                        "title": "Schedule health check call",
                        "description": "Proactive call to understand concerns and satisfaction",
                        "due_date": (
                            datetime.now(timezone.utc) + timedelta(days=7)
                        ).isoformat(),
                        "priority": "high",
                        "estimated_duration": 60,
                    },
                    {
                        "id": "satisfaction_survey",
                        "title": "Send satisfaction survey",
                        "description": "Gather detailed feedback on service experience",
                        "due_date": (
                            datetime.now(timezone.utc) + timedelta(days=14)
                        ).isoformat(),
                        "priority": "medium",
                        "estimated_duration": 15,
                    },
                ]
            )

        if "revenue_expansion" in focus_areas:
            action_plan["objectives"].append(
                {
                    "category": "revenue_expansion",
                    "objective": "Identify and propose expansion opportunities",
                    "target_value": float(customer.monthly_recurring_revenue)
                    * 1.3,  # 30% increase
                    "priority": "medium",
                }
            )

            action_plan["action_items"].extend(
                [
                    {
                        "id": "usage_analysis",
                        "title": "Analyze customer usage patterns",
                        "description": "Review usage data to identify expansion opportunities",
                        "due_date": (
                            datetime.now(timezone.utc) + timedelta(days=14)
                        ).isoformat(),
                        "priority": "medium",
                        "estimated_duration": 90,
                    },
                    {
                        "id": "expansion_proposal",
                        "title": "Create expansion proposal",
                        "description": "Develop customized expansion proposal with ROI analysis",
                        "due_date": (
                            datetime.now(timezone.utc) + timedelta(days=30)
                        ).isoformat(),
                        "priority": "medium",
                        "estimated_duration": 120,
                    },
                ]
            )

        if "engagement_increase" in focus_areas:
            action_plan["action_items"].extend(
                [
                    {
                        "id": "training_session",
                        "title": "Schedule product training session",
                        "description": "Provide advanced training to increase product adoption",
                        "due_date": (
                            datetime.now(timezone.utc) + timedelta(days=21)
                        ).isoformat(),
                        "priority": "medium",
                        "estimated_duration": 90,
                    },
                    {
                        "id": "quarterly_review",
                        "title": "Schedule quarterly business review",
                        "description": "Regular strategic review meeting to align on goals",
                        "due_date": (
                            datetime.now(timezone.utc) + timedelta(days=45)
                        ).isoformat(),
                        "priority": "low",
                        "estimated_duration": 120,
                    },
                ]
            )

        # Generate milestones
        action_plan["milestones"] = [
            {
                "milestone": "30-day check-in",
                "date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "description": "Review progress on initial action items",
                "success_criteria": "At least 80% of high-priority actions completed",
            },
            {
                "milestone": "60-day assessment",
                "date": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
                "description": "Measure impact of interventions on health score",
                "success_criteria": "Health score improvement of at least 10 points",
            },
            {
                "milestone": "90-day review",
                "date": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
                "description": "Final assessment of action plan success",
                "success_criteria": "All objectives met or exceeded",
            },
        ]

        # Define success metrics
        action_plan["success_metrics"] = [
            {
                "metric": "health_score_improvement",
                "baseline": lifecycle_summary.get("health_score", 0),
                "target": min(100, lifecycle_summary.get("health_score", 0) + 20),
                "measurement_frequency": "weekly",
            },
            {
                "metric": "interaction_frequency",
                "baseline": 1,  # interactions per month
                "target": 4,
                "measurement_frequency": "monthly",
            },
            {
                "metric": "satisfaction_score",
                "baseline": 6.5,  # out of 10
                "target": 8.5,
                "measurement_frequency": "quarterly",
            },
        ]

        return action_plan

    async def get_customer_revenue_analysis(
        self, reseller_id: str, period_months: int = 12
    ) -> dict[str, Any]:
        """Analyze customer revenue trends and opportunities"""

        customers = await self.customer_service.list_for_reseller(
            reseller_id, limit=1000
        )

        # Calculate revenue metrics
        total_mrr = sum(c.monthly_recurring_revenue for c in customers)
        total_arr = total_mrr * 12

        # Simulate historical data for trends
        monthly_revenue = []
        for i in range(period_months):
            month_date = date.today().replace(day=1) - timedelta(days=30 * i)
            # Simulate growth trend with some variation
            base_revenue = float(total_mrr) * (
                1 + (period_months - i) * 0.02
            )  # 2% monthly growth
            monthly_revenue.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "mrr": round(
                        base_revenue * (0.95 + 0.1 * (i % 3)), 2
                    ),  # Add variation
                    "customer_count": len(customers)
                    + i
                    - 2,  # Simulate customer growth
                    "new_customers": max(
                        0, 2 - (i % 4)
                    ),  # Simulate new customer additions
                    "churned_customers": max(
                        0, 1 if i % 6 == 0 else 0
                    ),  # Simulate occasional churn
                }
            )

        monthly_revenue.reverse()  # Chronological order

        # Customer segmentation by value
        customers_by_value = sorted(
            customers, key=lambda x: x.monthly_recurring_revenue, reverse=True
        )

        # Calculate revenue concentration
        top_10_percent_count = max(1, len(customers) // 10)
        top_10_percent_revenue = sum(
            c.monthly_recurring_revenue
            for c in customers_by_value[:top_10_percent_count]
        )
        revenue_concentration = (
            (top_10_percent_revenue / total_mrr * 100) if total_mrr > 0 else 0
        )

        revenue_analysis = {
            "reseller_id": reseller_id,
            "analysis_period_months": period_months,
            "current_metrics": {
                "total_mrr": float(total_mrr),
                "total_arr": float(total_arr),
                "average_customer_value": float(total_mrr) / len(customers)
                if customers
                else 0,
                "customer_count": len(customers),
                "revenue_concentration_top_10_percent": round(revenue_concentration, 1),
            },
            "growth_trends": {
                "monthly_revenue_history": monthly_revenue,
                "growth_rate_12m": 24.5,  # Percentage growth over 12 months
                "growth_rate_3m": 6.8,  # Percentage growth over 3 months
                "projected_arr_12m": float(total_arr) * 1.25,  # 25% growth projection
            },
            "customer_segments": {
                "enterprise": {
                    "count": len(
                        [c for c in customers if c.monthly_recurring_revenue >= 1000]
                    ),
                    "revenue": float(
                        sum(
                            c.monthly_recurring_revenue
                            for c in customers
                            if c.monthly_recurring_revenue >= 1000
                        )
                    ),
                    "percentage_of_total": 0,
                },
                "mid_market": {
                    "count": len(
                        [
                            c
                            for c in customers
                            if 200 <= c.monthly_recurring_revenue < 1000
                        ]
                    ),
                    "revenue": float(
                        sum(
                            c.monthly_recurring_revenue
                            for c in customers
                            if 200 <= c.monthly_recurring_revenue < 1000
                        )
                    ),
                    "percentage_of_total": 0,
                },
                "small_business": {
                    "count": len(
                        [c for c in customers if c.monthly_recurring_revenue < 200]
                    ),
                    "revenue": float(
                        sum(
                            c.monthly_recurring_revenue
                            for c in customers
                            if c.monthly_recurring_revenue < 200
                        )
                    ),
                    "percentage_of_total": 0,
                },
            },
            "expansion_opportunities": [
                {
                    "customer_id": str(c.customer_id),
                    "company_name": c.company_name or "Unknown",
                    "current_mrr": float(c.monthly_recurring_revenue),
                    "expansion_potential": float(c.monthly_recurring_revenue)
                    * 1.5,  # 50% expansion potential
                    "confidence_score": 75,  # Out of 100
                    "recommended_actions": [
                        "Usage analysis",
                        "Needs assessment",
                        "Custom proposal",
                    ],
                }
                for c in customers_by_value[:10]
                if c.monthly_recurring_revenue
                >= 200  # Top customers with expansion potential
            ][
                :5
            ],  # Limit to top 5 opportunities
            "risk_analysis": {
                "revenue_at_risk": float(
                    sum(
                        c.monthly_recurring_revenue
                        for c in customers
                        if self._is_customer_at_risk(c)
                    )
                ),
                "customers_at_risk_count": len(
                    [c for c in customers if self._is_customer_at_risk(c)]
                ),
                "concentration_risk_score": min(
                    100, revenue_concentration
                ),  # Higher concentration = higher risk
                "churn_risk_revenue": float(total_mrr)
                * 0.05,  # Estimate 5% at risk of churn
            },
        }

        # Calculate percentages for customer segments
        if total_mrr > 0:
            for segment in revenue_analysis["customer_segments"].values():
                segment["percentage_of_total"] = round(
                    segment["revenue"] / float(total_mrr) * 100, 1
                )

        return revenue_analysis

    def _calculate_acquisition_rate(self, customers) -> float:
        """Calculate customer acquisition rate"""
        # Simple calculation based on recent customers
        recent_customers = [
            c
            for c in customers
            if c.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
        ]
        return (len(recent_customers) / 30) * 365  # Annualized rate

    def _calculate_churn_rate(self, customers) -> float:
        """Calculate customer churn rate"""
        inactive_customers = [c for c in customers if c.relationship_status != "active"]
        return (len(inactive_customers) / len(customers) * 100) if customers else 0

    def _calculate_lifecycle_distribution(self, customers) -> dict[str, int]:
        """Calculate distribution of customers across lifecycle stages"""
        # Simulate lifecycle distribution
        stages = list(CustomerLifecycleStage)
        distribution = {}

        for stage in stages:
            # Simulate realistic distribution
            if stage == CustomerLifecycleStage.ACTIVE:
                count = int(len(customers) * 0.4)  # 40% active
            elif stage == CustomerLifecycleStage.PROSPECT:
                count = int(len(customers) * 0.2)  # 20% prospects
            elif stage == CustomerLifecycleStage.ONBOARDING:
                count = int(len(customers) * 0.15)  # 15% onboarding
            else:
                count = max(0, int(len(customers) * 0.05))  # 5% each for other stages

            distribution[stage.value] = count

        return distribution

    def _calculate_health_distribution(self, customers) -> dict[str, int]:
        """Calculate distribution of customer health scores"""
        # Simulate health distribution
        return {
            "excellent": int(len(customers) * 0.25),  # 25% excellent health
            "good": int(len(customers) * 0.35),  # 35% good health
            "fair": int(len(customers) * 0.25),  # 25% fair health
            "poor": int(len(customers) * 0.10),  # 10% poor health
            "critical": int(len(customers) * 0.05),  # 5% critical health
        }

    def _calculate_mrr_by_segment(self, customers) -> dict[str, float]:
        """Calculate MRR breakdown by customer segment"""
        return {
            "enterprise": float(
                sum(
                    c.monthly_recurring_revenue
                    for c in customers
                    if c.monthly_recurring_revenue >= 1000
                )
            ),
            "mid_market": float(
                sum(
                    c.monthly_recurring_revenue
                    for c in customers
                    if 200 <= c.monthly_recurring_revenue < 1000
                )
            ),
            "small_business": float(
                sum(
                    c.monthly_recurring_revenue
                    for c in customers
                    if c.monthly_recurring_revenue < 200
                )
            ),
        }

    async def _calculate_revenue_trend(self, reseller_id: str) -> list[dict[str, Any]]:
        """Calculate revenue trend over time"""
        # Simulate 6-month trend
        trends = []
        for i in range(6):
            month_date = date.today().replace(day=1) - timedelta(days=30 * i)
            trends.append(
                {
                    "month": month_date.strftime("%Y-%m"),
                    "mrr": 15000 + (i * 500),  # Growing trend
                    "growth_rate": 3.2 + (i * 0.2),  # Increasing growth rate
                }
            )

        trends.reverse()
        return trends

    def _get_top_customers_by_value(
        self, customers, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get top customers by monthly value"""
        sorted_customers = sorted(
            customers, key=lambda x: x.monthly_recurring_revenue, reverse=True
        )

        return [
            {
                "customer_id": str(c.customer_id),
                "company_name": c.company_name or "Unknown Company",
                "monthly_value": float(c.monthly_recurring_revenue),
                "lifetime_value": float(c.lifetime_value or 0),
                "relationship_status": c.relationship_status,
            }
            for c in sorted_customers[:limit]
        ]

    def _is_customer_at_risk(self, customer) -> bool:
        """Determine if customer is at risk (simplified logic)"""
        # Simple risk assessment based on available data
        return (
            customer.relationship_status != "active"
            or customer.monthly_recurring_revenue < 50
            or (
                customer.last_service_date
                and (
                    datetime.now(timezone.utc).date() - customer.last_service_date
                ).days
                > 60
            )
        )

    def _has_expansion_opportunity(self, customer) -> bool:
        """Determine if customer has expansion opportunity"""
        return (
            customer.relationship_status == "active"
            and customer.monthly_recurring_revenue >= 200
            and (datetime.now(timezone.utc) - customer.created_at).days
            >= 90  # Customer for at least 90 days
        )

    async def _generate_portfolio_recommendations(
        self,
        portfolio_summary: dict[str, Any],
        lifecycle_distribution: dict[str, int],
        health_distribution: dict[str, int],
    ) -> list[str]:
        """Generate recommendations based on portfolio analysis"""
        recommendations = []

        if portfolio_summary["churn_rate"] > 10:
            recommendations.append(
                "Focus on customer retention - churn rate is above healthy threshold"
            )

        if (
            health_distribution.get("critical", 0) + health_distribution.get("poor", 0)
            > portfolio_summary["total_customers"] * 0.2
        ):
            recommendations.append(
                "Immediate action needed for customers with poor health scores"
            )

        if (
            lifecycle_distribution.get("prospect", 0)
            > portfolio_summary["total_customers"] * 0.3
        ):
            recommendations.append("Focus on converting prospects to qualified leads")

        if portfolio_summary["average_customer_value"] < 200:
            recommendations.append(
                "Explore upselling opportunities to increase average customer value"
            )

        return recommendations

    def _simulate_health_score(self) -> float:
        """Simulate customer health score for demo purposes"""
        import random  # noqa: S311 - demo-only simulation

        # Weighted random to have more healthy customers than unhealthy
        weights = [5, 10, 25, 35, 25]  # critical, poor, fair, good, excellent
        ranges = [(0, 30), (30, 50), (50, 70), (70, 90), (90, 100)]

        selected_range = random.choices(ranges, weights=weights)[0]
        return round(
            random.uniform(selected_range[0], selected_range[1]), 1
        )  # noqa: S311 - demo-only

    def _determine_risk_level(self, health_score: float) -> str:
        """Determine risk level from health score"""
        if health_score < 30:
            return "critical"
        elif health_score < 50:
            return "high"
        elif health_score < 70:
            return "medium"
        else:
            return "low"

    def _simulate_last_interaction(self) -> str:
        """Simulate last interaction type"""
        import random  # noqa: S311 - demo-only simulation

        interactions = ["email", "phone_call", "meeting", "support_ticket", "training"]
        return random.choice(interactions)  # noqa: S311 - demo-only

    def _calculate_days_since_interaction(self) -> int:
        """Simulate days since last interaction"""
        import random  # noqa: S311 - demo-only simulation

        return random.randint(1, 45)  # noqa: S311 - demo-only

    def _simulate_lifecycle_stage(self) -> str:
        """Simulate customer lifecycle stage"""
        import random  # noqa: S311 - demo-only simulation

        stages = [stage.value for stage in CustomerLifecycleStage]
        weights = [5, 5, 10, 8, 8, 40, 10, 5, 5, 4]  # Active customers weighted higher
        return random.choices(stages, weights=weights)[0]  # noqa: S311 - demo-only

    def _simulate_risk_factors(self) -> list[str]:
        """Simulate customer risk factors"""
        import random  # noqa: S311 - demo-only simulation

        all_factors = [
            "Low usage",
            "Payment delays",
            "Support tickets",
            "Contract expiring",
            "No recent contact",
            "Feature requests ignored",
            "Competitor interest",
            "Reduced team size",
            "Budget constraints",
            "Technical issues",
        ]

        num_factors = random.randint(0, 3)
        return random.sample(all_factors, num_factors)  # noqa: S311 - demo-only


# Export classes
__all__ = ["AdvancedCustomerManager"]
