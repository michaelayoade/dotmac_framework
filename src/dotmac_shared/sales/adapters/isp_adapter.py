"""ISP Framework adapter for sales package integration."""

import logging
from typing import Any, Dict, List, Optional

try:
    from ..core.models import Lead, Opportunity, SalesActivity
    from ..core.schemas import LeadCreate, OpportunityCreate, SalesActivityCreate
    from ..services.lead_service import LeadService

    SALES_DEPENDENCIES_AVAILABLE = True
except ImportError:
    SALES_DEPENDENCIES_AVAILABLE = False
    Lead = Opportunity = SalesActivity = None
    LeadCreate = OpportunityCreate = SalesActivityCreate = None
    LeadService = None

logger = logging.getLogger(__name__)


class ISPSalesAdapter:
    """
    Adapter for integrating sales package with ISP Framework.

    This adapter provides ISP-specific sales functionality including:
    - Customer prospect management
    - Service opportunity tracking
    - Sales activity integration with customer portal
    - Territory-based sales management
    """

    def __init__(self, database_session=None, config: Dict[str, Any] = None):
        """Initialize ISP sales adapter."""
        if not SALES_DEPENDENCIES_AVAILABLE:
            raise ImportError("Sales package dependencies not available")

        self.db_session = database_session
        self.config = config or {}

        # Initialize sales services
        if database_session:
            self.lead_service = LeadService(database_session, config)
        else:
            self.lead_service = None

    async def create_customer_prospect(
        self, customer_data: Dict[str, Any], tenant_id: str
    ) -> Dict[str, Any]:
        """Create a sales prospect from ISP customer inquiry."""
        if not self.lead_service:
            raise RuntimeError("Lead service not available")

        # Map ISP customer data to lead format
        lead_data = LeadCreate(
            first_name=customer_data.get("first_name", ""),
            last_name=customer_data.get("last_name", ""),
            email=customer_data.get("email"),
            phone=customer_data.get("phone"),
            company=customer_data.get("company_name"),
            job_title=customer_data.get("job_title"),
            lead_source=self._map_isp_lead_source(customer_data.get("inquiry_source")),
            customer_type=self._map_isp_customer_type(
                customer_data.get("customer_type")
            ),
            budget=customer_data.get("monthly_budget"),
            need=customer_data.get("service_requirements"),
            timeline=customer_data.get("service_timeline"),
            street_address=customer_data.get("service_address", {}).get("street"),
            city=customer_data.get("service_address", {}).get("city"),
            state_province=customer_data.get("service_address", {}).get("state"),
            postal_code=customer_data.get("service_address", {}).get("zip_code"),
            country_code=customer_data.get("service_address", {}).get("country", "US"),
            notes=f"ISP Customer Inquiry - Services: {', '.join(customer_data.get('interested_services', []))}",
        )

        # Create lead through sales service
        lead_response = await self.lead_service.create_lead(lead_data, tenant_id)

        # Log ISP-specific activity
        logger.info(f"Created ISP customer prospect {lead_response.id} from inquiry")

        return {
            "prospect_id": lead_response.id,
            "lead_id": getattr(lead_response, "lead_id", None),
            "lead_score": lead_response.lead_score,
            "status": lead_response.lead_status,
            "created_at": lead_response.created_at,
        }

    async def create_service_opportunity(
        self, prospect_id: str, service_data: Dict[str, Any], tenant_id: str
    ) -> Dict[str, Any]:
        """Create service opportunity for ISP customer."""
        # This would integrate with opportunity service
        # For now, return mock data structure
        return {
            "opportunity_id": f"ISP-OPP-{prospect_id}",
            "prospect_id": prospect_id,
            "services": service_data.get("services", []),
            "estimated_value": service_data.get("monthly_value", 0) * 12,  # Annualized
            "installation_timeline": service_data.get("timeline"),
            "created_at": "2024-01-01T00:00:00Z",
        }

    async def track_customer_interaction(
        self, prospect_id: str, interaction_data: Dict[str, Any], tenant_id: str
    ) -> Dict[str, Any]:
        """Track customer service interactions as sales activities."""
        # This would integrate with activity service
        # For now, return mock data
        return {
            "activity_id": f"ACT-{prospect_id}-{interaction_data.get('type')}",
            "prospect_id": prospect_id,
            "interaction_type": interaction_data.get("type"),
            "channel": interaction_data.get("channel"),
            "outcome": interaction_data.get("outcome"),
            "follow_up_required": interaction_data.get("follow_up_required", False),
        }

    async def get_territory_prospects(
        self, territory_code: str, tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Get prospects for a specific ISP territory."""
        if not self.lead_service:
            raise RuntimeError("Lead service not available")

        # Use ISP territory mapping to filter leads
        territory_filters = {
            "custom_fields": {"isp_territory": territory_code},
            "lead_status": ["new", "contacted", "qualified"],
        }

        leads_result = await self.lead_service.list_leads(
            tenant_id=tenant_id, filters=territory_filters
        )

        # Format for ISP consumption
        prospects = []
        for lead in leads_result.get("leads", []):
            prospects.append(
                {
                    "prospect_id": lead.id,
                    "customer_name": f"{lead.first_name} {lead.last_name}",
                    "company": lead.company,
                    "service_address": {
                        "street": lead.street_address,
                        "city": lead.city,
                        "state": lead.state_province,
                        "zip": lead.postal_code,
                    },
                    "interested_services": self._extract_interested_services(
                        lead.notes
                    ),
                    "lead_score": lead.lead_score,
                    "status": lead.lead_status,
                    "assigned_technician": lead.assigned_to,
                }
            )

        return prospects

    async def get_sales_dashboard_data(self, tenant_id: str) -> Dict[str, Any]:
        """Get ISP-specific sales dashboard data."""
        if not self.lead_service:
            raise RuntimeError("Lead service not available")

        # Get basic lead metrics
        leads_result = await self.lead_service.list_leads(tenant_id=tenant_id)

        # Calculate ISP-specific metrics
        total_prospects = leads_result.get("total_count", 0)
        high_value_prospects = len(
            [
                lead
                for lead in leads_result.get("leads", [])
                if lead.budget and lead.budget > 100  # $100+ monthly
            ]
        )

        return {
            "total_prospects": total_prospects,
            "high_value_prospects": high_value_prospects,
            "conversion_opportunities": len(
                [
                    lead
                    for lead in leads_result.get("leads", [])
                    if lead.lead_score >= 70
                ]
            ),
            "service_territories": self._get_territory_breakdown(
                leads_result.get("leads", [])
            ),
            "pipeline_value": self._calculate_pipeline_value(
                leads_result.get("leads", [])
            ),
        }

    def _map_isp_lead_source(self, inquiry_source: str) -> str:
        """Map ISP inquiry source to sales lead source."""
        source_mapping = {
            "website": "website",
            "phone": "cold_call",
            "referral": "referral",
            "existing_customer": "existing_customer",
            "partner": "partner",
            "event": "event",
            "advertisement": "advertisement",
        }

        return source_mapping.get(inquiry_source, "other")

    def _map_isp_customer_type(self, customer_type: str) -> str:
        """Map ISP customer type to sales customer type."""
        type_mapping = {
            "residential": "residential",
            "small_business": "small_business",
            "medium_business": "medium_business",
            "enterprise": "enterprise",
            "government": "government",
            "education": "education",
            "healthcare": "healthcare",
        }

        return type_mapping.get(customer_type, "residential")

    def _extract_interested_services(self, notes: str) -> List[str]:
        """Extract interested services from lead notes."""
        if not notes:
            return []

        # Simple keyword extraction for ISP services
        services = []
        service_keywords = {
            "fiber": "Fiber Internet",
            "broadband": "Broadband Internet",
            "business": "Business Internet",
            "phone": "VoIP Phone",
            "tv": "IPTV",
            "security": "Security Services",
        }

        notes_lower = notes.lower()
        for keyword, service in service_keywords.items():
            if keyword in notes_lower:
                services.append(service)

        return services or ["Internet Service"]

    def _get_territory_breakdown(self, leads: List[Any]) -> Dict[str, int]:
        """Get breakdown of prospects by territory."""
        territory_counts = {}

        for lead in leads:
            # Use city as territory for basic implementation
            territory = lead.city or "Unknown"
            territory_counts[territory] = territory_counts.get(territory, 0) + 1

        return territory_counts

    def _calculate_pipeline_value(self, leads: List[Any]) -> Dict[str, float]:
        """Calculate pipeline value for ISP services."""
        total_monthly = 0
        qualified_monthly = 0

        for lead in leads:
            if lead.budget:
                monthly_value = float(lead.budget)
                total_monthly += monthly_value

                if lead.lead_status == "qualified":
                    qualified_monthly += monthly_value

        return {
            "total_monthly_pipeline": total_monthly,
            "total_annual_pipeline": total_monthly * 12,
            "qualified_monthly_pipeline": qualified_monthly,
            "qualified_annual_pipeline": qualified_monthly * 12,
        }
