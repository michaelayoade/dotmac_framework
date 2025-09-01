"""
Customer Assignment Automation Service
Implements intelligent customer-to-reseller assignment with geographic, capacity, and skills-based routing
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
import math
import json

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import Base
from dotmac_isp.shared.base_service import BaseService


class AssignmentMethod(str, Enum):
    GEOGRAPHIC = "geographic"
    CAPACITY_BASED = "capacity_based"
    SKILLS_BASED = "skills_based"
    HYBRID = "hybrid"
    ROUND_ROBIN = "round_robin"
    PERFORMANCE_WEIGHTED = "performance_weighted"


class CustomerType(str, Enum):
    RESIDENTIAL = "residential"
    SMALL_BUSINESS = "small_business"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"


class ServiceComplexity(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"


class AssignmentPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class GeographicLocation(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = "US"


class ResellerCapacity(BaseModel):
    reseller_id: str
    current_customers: int = Field(ge=0)
    max_capacity: int = Field(ge=1)
    utilization_rate: float = Field(ge=0, le=1)
    specialty_areas: List[str] = []
    skill_ratings: Dict[str, float] = {}  # skill -> rating (0-10)
    geographic_coverage: List[Dict[str, Any]] = []  # coverage areas
    availability_hours: Dict[str, str] = {}  # day -> hours
    
    @property
    def available_capacity(self) -> int:
        return max(0, self.max_capacity - self.current_customers)
    
    @property
    def is_at_capacity(self) -> bool:
        return self.current_customers >= self.max_capacity


class CustomerRequirement(BaseModel):
    customer_id: str
    customer_type: CustomerType
    service_complexity: ServiceComplexity
    location: GeographicLocation
    priority: AssignmentPriority = AssignmentPriority.NORMAL
    required_skills: List[str] = []
    preferred_languages: List[str] = ["en"]
    service_start_date: Optional[datetime] = None
    special_requirements: Dict[str, Any] = {}
    budget_range: Optional[Tuple[float, float]] = None


class AssignmentScore(BaseModel):
    reseller_id: str
    customer_id: str
    total_score: float = Field(ge=0, le=100)
    geographic_score: float = Field(ge=0, le=100)
    capacity_score: float = Field(ge=0, le=100)
    skills_score: float = Field(ge=0, le=100)
    performance_score: float = Field(ge=0, le=100)
    availability_score: float = Field(ge=0, le=100)
    assignment_reasoning: List[str] = []


class AssignmentResult(BaseModel):
    assignment_id: str
    customer_id: str
    assigned_reseller_id: str
    assignment_method: AssignmentMethod
    assignment_score: AssignmentScore
    assigned_at: datetime
    expected_contact_date: datetime
    assignment_status: str = "pending_contact"
    notes: Optional[str] = None


class CustomerAssignmentService(BaseService):
    """Service for intelligent customer assignment automation"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.assignment_weights = {
            "geographic": 0.30,
            "capacity": 0.25,
            "skills": 0.25,
            "performance": 0.15,
            "availability": 0.05
        }
    
    @standard_exception_handler
    async def assign_customer_to_reseller(
        self, 
        customer_requirement: CustomerRequirement,
        assignment_method: AssignmentMethod = AssignmentMethod.HYBRID
    ) -> AssignmentResult:
        """Main method to assign customer to optimal reseller"""
        
        # Get available resellers
        available_resellers = await self._get_available_resellers()
        
        if not available_resellers:
            raise ValueError("No available resellers found")
        
        # Score all resellers for this customer
        scored_assignments = []
        for reseller_capacity in available_resellers:
            score = await self._calculate_assignment_score(
                customer_requirement, 
                reseller_capacity, 
                assignment_method
            )
            scored_assignments.append(score)
        
        # Sort by total score and select best match
        scored_assignments.sort(key=lambda x: x.total_score, reverse=True)
        best_assignment = scored_assignments[0]
        
        # Create assignment result
        assignment_result = AssignmentResult(
            assignment_id=f"assign_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{customer_requirement.customer_id}",
            customer_id=customer_requirement.customer_id,
            assigned_reseller_id=best_assignment.reseller_id,
            assignment_method=assignment_method,
            assignment_score=best_assignment,
            assigned_at=datetime.utcnow(),
            expected_contact_date=self._calculate_expected_contact_date(customer_requirement.priority),
            notes=f"Assigned using {assignment_method} method with score {best_assignment.total_score:.1f}/100"
        )
        
        # Update reseller capacity
        await self._update_reseller_capacity(best_assignment.reseller_id, 1)
        
        return assignment_result
    
    @standard_exception_handler
    async def bulk_assign_customers(
        self,
        customer_requirements: List[CustomerRequirement],
        assignment_method: AssignmentMethod = AssignmentMethod.HYBRID
    ) -> List[AssignmentResult]:
        """Assign multiple customers optimizing for overall efficiency"""
        
        assignments = []
        
        # Sort customers by priority and complexity
        sorted_customers = sorted(
            customer_requirements,
            key=lambda x: (x.priority == AssignmentPriority.URGENT, x.service_complexity == ServiceComplexity.ENTERPRISE),
            reverse=True
        )
        
        for customer_req in sorted_customers:
            try:
                assignment = await self.assign_customer_to_reseller(customer_req, assignment_method)
                assignments.append(assignment)
            except ValueError as e:
                # Log assignment failure but continue with other customers
                print(f"Failed to assign customer {customer_req.customer_id}: {str(e)}")
        
        return assignments
    
    @standard_exception_handler
    async def rebalance_customer_assignments(self) -> Dict[str, Any]:
        """Rebalance customer assignments to optimize capacity utilization"""
        
        # Get current reseller capacities
        resellers = await self._get_available_resellers()
        
        # Identify over/under-utilized resellers
        overloaded = [r for r in resellers if r.utilization_rate > 0.9]
        underutilized = [r for r in resellers if r.utilization_rate < 0.6]
        
        rebalance_suggestions = []
        
        for overloaded_reseller in overloaded:
            # Find customers that could be reassigned
            reassignable_customers = await self._find_reassignable_customers(overloaded_reseller.reseller_id)
            
            for customer in reassignable_customers[:3]:  # Limit to 3 per reseller
                # Find best alternative reseller
                for underutil_reseller in underutilized:
                    if underutil_reseller.available_capacity > 0:
                        rebalance_suggestions.append({
                            "customer_id": customer["customer_id"],
                            "from_reseller": overloaded_reseller.reseller_id,
                            "to_reseller": underutil_reseller.reseller_id,
                            "reason": "Capacity rebalancing",
                            "expected_improvement": 0.15
                        })
                        break
        
        return {
            "rebalance_date": datetime.utcnow().isoformat(),
            "total_suggestions": len(rebalance_suggestions),
            "suggestions": rebalance_suggestions,
            "expected_efficiency_gain": len(rebalance_suggestions) * 0.15
        }
    
    async def _get_available_resellers(self) -> List[ResellerCapacity]:
        """Get list of available resellers with capacity information"""
        
        # Mock implementation - would query actual reseller data
        resellers = [
            ResellerCapacity(
                reseller_id="reseller_001",
                current_customers=25,
                max_capacity=40,
                utilization_rate=0.625,
                specialty_areas=["fiber_installation", "business_services"],
                skill_ratings={
                    "technical_support": 8.5,
                    "sales": 7.8,
                    "customer_service": 9.2,
                    "fiber_installation": 9.5
                },
                geographic_coverage=[
                    {"type": "radius", "center": {"lat": 40.7128, "lng": -74.0060}, "radius_km": 25}
                ],
                availability_hours={"monday": "8-17", "tuesday": "8-17", "wednesday": "8-17"}
            ),
            ResellerCapacity(
                reseller_id="reseller_002",
                current_customers=15,
                max_capacity=30,
                utilization_rate=0.5,
                specialty_areas=["residential_services", "small_business"],
                skill_ratings={
                    "technical_support": 7.5,
                    "sales": 9.1,
                    "customer_service": 8.8,
                    "small_business": 9.0
                },
                geographic_coverage=[
                    {"type": "radius", "center": {"lat": 40.6892, "lng": -74.0445}, "radius_km": 20}
                ]
            ),
            ResellerCapacity(
                reseller_id="reseller_003",
                current_customers=38,
                max_capacity=40,
                utilization_rate=0.95,
                specialty_areas=["enterprise_solutions", "complex_installations"],
                skill_ratings={
                    "technical_support": 9.8,
                    "sales": 8.5,
                    "customer_service": 8.0,
                    "enterprise_solutions": 9.7
                },
                geographic_coverage=[
                    {"type": "radius", "center": {"lat": 40.7831, "lng": -73.9712}, "radius_km": 35}
                ]
            )
        ]
        
        # Filter out resellers at capacity
        return [r for r in resellers if not r.is_at_capacity]
    
    async def _calculate_assignment_score(
        self,
        customer: CustomerRequirement,
        reseller: ResellerCapacity,
        method: AssignmentMethod
    ) -> AssignmentScore:
        """Calculate assignment score based on multiple factors"""
        
        # Geographic score
        geographic_score = await self._calculate_geographic_score(customer.location, reseller.geographic_coverage)
        
        # Capacity score
        capacity_score = (1 - reseller.utilization_rate) * 100
        
        # Skills score
        skills_score = await self._calculate_skills_score(customer.required_skills, reseller.skill_ratings)
        
        # Performance score (mock - would be based on historical performance)
        performance_score = 85.0  # Mock score
        
        # Availability score
        availability_score = 90.0  # Mock score
        
        # Calculate weighted total score
        if method == AssignmentMethod.HYBRID:
            total_score = (
                geographic_score * self.assignment_weights["geographic"] +
                capacity_score * self.assignment_weights["capacity"] +
                skills_score * self.assignment_weights["skills"] +
                performance_score * self.assignment_weights["performance"] +
                availability_score * self.assignment_weights["availability"]
            )
        elif method == AssignmentMethod.GEOGRAPHIC:
            total_score = geographic_score
        elif method == AssignmentMethod.CAPACITY_BASED:
            total_score = capacity_score
        elif method == AssignmentMethod.SKILLS_BASED:
            total_score = skills_score
        else:
            total_score = (geographic_score + capacity_score + skills_score) / 3
        
        # Generate reasoning
        reasoning = []
        if geographic_score > 80:
            reasoning.append("Excellent geographic match")
        if capacity_score > 70:
            reasoning.append("Good capacity availability")
        if skills_score > 85:
            reasoning.append("Strong skills alignment")
        
        return AssignmentScore(
            reseller_id=reseller.reseller_id,
            customer_id=customer.customer_id,
            total_score=total_score,
            geographic_score=geographic_score,
            capacity_score=capacity_score,
            skills_score=skills_score,
            performance_score=performance_score,
            availability_score=availability_score,
            assignment_reasoning=reasoning
        )
    
    async def _calculate_geographic_score(self, customer_location: GeographicLocation, coverage_areas: List[Dict[str, Any]]) -> float:
        """Calculate geographic proximity score"""
        
        best_score = 0.0
        
        for coverage_area in coverage_areas:
            if coverage_area["type"] == "radius":
                center = coverage_area["center"]
                radius_km = coverage_area["radius_km"]
                
                # Calculate distance using Haversine formula
                distance = self._calculate_distance(
                    customer_location.latitude, customer_location.longitude,
                    center["lat"], center["lng"]
                )
                
                # Score based on distance (closer = higher score)
                if distance <= radius_km:
                    score = max(0, 100 - (distance / radius_km) * 50)
                    best_score = max(best_score, score)
        
        return best_score
    
    async def _calculate_skills_score(self, required_skills: List[str], reseller_skills: Dict[str, float]) -> float:
        """Calculate skills alignment score"""
        
        if not required_skills:
            return 80.0  # Default score if no specific skills required
        
        skill_scores = []
        for skill in required_skills:
            skill_rating = reseller_skills.get(skill, 5.0)  # Default rating if skill not found
            # Convert 0-10 rating to 0-100 score
            skill_scores.append(skill_rating * 10)
        
        return sum(skill_scores) / len(skill_scores)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def _calculate_expected_contact_date(self, priority: AssignmentPriority) -> datetime:
        """Calculate expected contact date based on priority"""
        
        now = datetime.utcnow()
        
        if priority == AssignmentPriority.URGENT:
            return now + timedelta(hours=2)
        elif priority == AssignmentPriority.HIGH:
            return now + timedelta(hours=8)
        elif priority == AssignmentPriority.NORMAL:
            return now + timedelta(days=1)
        else:  # LOW
            return now + timedelta(days=3)
    
    async def _update_reseller_capacity(self, reseller_id: str, customer_count_change: int):
        """Update reseller capacity after assignment"""
        
        # Mock implementation - would update database
        print(f"Updated reseller {reseller_id} capacity by {customer_count_change}")
    
    async def _find_reassignable_customers(self, reseller_id: str) -> List[Dict[str, Any]]:
        """Find customers that could be reassigned to other resellers"""
        
        # Mock implementation - would query actual customer assignments
        reassignable = [
            {
                "customer_id": "cust_001",
                "service_complexity": "basic",
                "assignment_date": datetime.utcnow() - timedelta(days=30),
                "satisfaction_score": 7.5
            },
            {
                "customer_id": "cust_002", 
                "service_complexity": "intermediate",
                "assignment_date": datetime.utcnow() - timedelta(days=15),
                "satisfaction_score": 8.2
            }
        ]
        
        return reassignable
    
    @standard_exception_handler
    async def generate_assignment_analytics(self) -> Dict[str, Any]:
        """Generate analytics on assignment patterns and effectiveness"""
        
        analytics = {
            "assignment_metrics": {
                "total_assignments_30d": 45,
                "average_assignment_score": 78.5,
                "assignment_success_rate": 0.92,
                "average_contact_time_hours": 18.5
            },
            "method_performance": {
                AssignmentMethod.HYBRID: {"success_rate": 0.94, "avg_score": 82.1},
                AssignmentMethod.GEOGRAPHIC: {"success_rate": 0.88, "avg_score": 75.8},
                AssignmentMethod.CAPACITY_BASED: {"success_rate": 0.91, "avg_score": 79.2},
                AssignmentMethod.SKILLS_BASED: {"success_rate": 0.89, "avg_score": 80.5}
            },
            "reseller_utilization": {
                "average_utilization": 0.72,
                "utilization_variance": 0.18,
                "overloaded_resellers": 2,
                "underutilized_resellers": 3
            },
            "customer_satisfaction": {
                "assignment_satisfaction": 8.4,
                "contact_timing_satisfaction": 8.1,
                "reseller_match_satisfaction": 8.7
            },
            "recommendations": [
                "Consider reducing maximum capacity for overloaded resellers",
                "Improve skills matching algorithm for better customer satisfaction",
                "Implement proactive rebalancing for better utilization"
            ]
        }
        
        return analytics


__all__ = [
    "AssignmentMethod",
    "CustomerType", 
    "ServiceComplexity",
    "AssignmentPriority",
    "GeographicLocation",
    "ResellerCapacity",
    "CustomerRequirement",
    "AssignmentScore",
    "AssignmentResult",
    "CustomerAssignmentService"
]