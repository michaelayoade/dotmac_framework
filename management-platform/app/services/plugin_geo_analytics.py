"""
Plugin Geographic Distribution Analytics Service.

Provides geographic analysis and distribution metrics for plugin installations
across different regions, countries, and cities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import json
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.plugin_additional import (
    PluginInstallationRepository,
    PluginRepository
)

logger = logging.getLogger(__name__)


class PluginGeoAnalytics:
    """Service for plugin geographic distribution analytics."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.installation_repo = PluginInstallationRepository(db)
        self.plugin_repo = PluginRepository(db)
    
    async def get_plugin_geographic_distribution(
        self,
        plugin_id: UUID,
        granularity: str = "country"
    ) -> Dict[str, Any]:
        """Get geographic distribution for a specific plugin."""
        try:
            plugin = await self.plugin_repo.get_by_id(plugin_id)
            if not plugin:
                raise ValueError(f"Plugin not found: {plugin_id}")
            
            installations = await self.installation_repo.get_by_plugin(plugin_id)
            
            if not installations:
                return {
                    "plugin_id": plugin_id,
                    "plugin_name": plugin.name,
                    "total_installations": 0,
                    "geographic_distribution": {},
                    "top_regions": []
                }
            
            # Group installations by geographic location
            geo_data = defaultdict(lambda: {
                "installation_count": 0,
                "active_installations": 0,
                "tenant_count": 0,
                "tenants": set(),
                "first_installation": None,
                "latest_installation": None
            })
            
            for installation in installations:
                # Extract geographic info from tenant or installation metadata
                location = self._extract_location(installation, granularity)
                
                geo_data[location]["installation_count"] += 1
                geo_data[location]["tenants"].add(str(installation.tenant_id))
                
                if installation.status == "installed" and installation.enabled:
                    geo_data[location]["active_installations"] += 1
                
                # Track first and latest installations
                install_date = installation.installed_at or installation.created_at
                if (geo_data[location]["first_installation"] is None or 
                    install_date < geo_data[location]["first_installation"]):
                    geo_data[location]["first_installation"] = install_date
                
                if (geo_data[location]["latest_installation"] is None or 
                    install_date > geo_data[location]["latest_installation"]):
                    geo_data[location]["latest_installation"] = install_date
            
            # Convert sets to counts and format data
            distribution = {}
            for location, data in geo_data.items():
                data["tenant_count"] = len(data["tenants"])
                data["tenants"] = list(data["tenants"])  # Convert set to list for JSON
                data["first_installation"] = data["first_installation"].isoformat() if data["first_installation"] else None
                data["latest_installation"] = data["latest_installation"].isoformat() if data["latest_installation"] else None
                distribution[location] = data
            
            # Get top regions by installation count
            top_regions = sorted(
                [(location, data["installation_count"]) for location, data in distribution.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "plugin_id": plugin_id,
                "plugin_name": plugin.name,
                "total_installations": len(installations),
                "unique_locations": len(distribution),
                "granularity": granularity,
                "geographic_distribution": distribution,
                "top_regions": [
                    {"location": loc, "installations": count} 
                    for loc, count in top_regions
                ],
                "geographic_insights": self._generate_geographic_insights(distribution),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get geographic distribution: {e}")
            return {"error": str(e)}
    
    async def get_marketplace_geographic_overview(
        self,
        granularity: str = "country"
    ) -> Dict[str, Any]:
        """Get geographic overview of all plugin installations in the marketplace."""
        try:
            # Get all active installations
            installations = await self.installation_repo.get_all_active()
            
            if not installations:
                return {
                    "total_installations": 0,
                    "geographic_overview": {},
                    "market_penetration": {}
                }
            
            # Group by location
            location_stats = defaultdict(lambda: {
                "total_installations": 0,
                "unique_plugins": set(),
                "unique_tenants": set(),
                "plugin_categories": defaultdict(int),
                "installation_timeline": []
            })
            
            for installation in installations:
                location = self._extract_location(installation, granularity)
                
                location_stats[location]["total_installations"] += 1
                location_stats[location]["unique_tenants"].add(str(installation.tenant_id))
                
                if installation.plugin:
                    location_stats[location]["unique_plugins"].add(str(installation.plugin.id))
                    if installation.plugin.category:
                        location_stats[location]["plugin_categories"][installation.plugin.category] += 1
                
                # Add to timeline
                install_date = installation.installed_at or installation.created_at
                location_stats[location]["installation_timeline"].append({
                    "date": install_date.isoformat(),
                    "plugin_name": installation.plugin.name if installation.plugin else "Unknown"
                })
            
            # Convert and format data
            geographic_overview = {}
            for location, stats in location_stats.items():
                # Sort timeline by date
                stats["installation_timeline"] = sorted(
                    stats["installation_timeline"],
                    key=lambda x: x["date"]
                )
                
                geographic_overview[location] = {
                    "total_installations": stats["total_installations"],
                    "unique_plugins": len(stats["unique_plugins"]),
                    "unique_tenants": len(stats["unique_tenants"]),
                    "plugin_categories": dict(stats["plugin_categories"]),
                    "recent_installations": stats["installation_timeline"][-5:],  # Last 5
                    "market_diversity_score": self._calculate_diversity_score(stats)
                }
            
            # Market penetration analysis
            market_penetration = self._analyze_market_penetration(geographic_overview)
            
            # Global insights
            global_insights = self._generate_global_insights(geographic_overview)
            
            return {
                "total_locations": len(geographic_overview),
                "total_installations": sum(stats["total_installations"] for stats in geographic_overview.values()),
                "granularity": granularity,
                "geographic_overview": geographic_overview,
                "market_penetration": market_penetration,
                "global_insights": global_insights,
                "top_markets": self._get_top_markets(geographic_overview),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get marketplace geographic overview: {e}")
            return {"error": str(e)}
    
    async def get_regional_plugin_preferences(
        self,
        region: str,
        granularity: str = "country"
    ) -> Dict[str, Any]:
        """Get plugin preferences and trends for a specific region."""
        try:
            # Get installations for the region
            installations = await self.installation_repo.get_by_region(region, granularity)
            
            if not installations:
                return {
                    "region": region,
                    "total_installations": 0,
                    "plugin_preferences": {}
                }
            
            # Analyze plugin preferences
            plugin_stats = defaultdict(lambda: {
                "installation_count": 0,
                "tenant_count": 0,
                "tenants": set(),
                "average_rating": 0.0,
                "category": None,
                "recent_growth": 0
            })
            
            for installation in installations:
                if not installation.plugin:
                    continue
                
                plugin_id = str(installation.plugin.id)
                plugin_stats[plugin_id]["installation_count"] += 1
                plugin_stats[plugin_id]["tenants"].add(str(installation.tenant_id))
                plugin_stats[plugin_id]["category"] = installation.plugin.category
                plugin_stats[plugin_id]["plugin_name"] = installation.plugin.name
                plugin_stats[plugin_id]["average_rating"] = installation.plugin.rating or 0.0
            
            # Convert sets to counts
            for plugin_id, stats in plugin_stats.items():
                stats["tenant_count"] = len(stats["tenants"])
                del stats["tenants"]  # Remove set for JSON serialization
            
            # Sort by popularity
            popular_plugins = sorted(
                plugin_stats.items(),
                key=lambda x: x[1]["installation_count"],
                reverse=True
            )[:20]
            
            # Category analysis
            category_stats = defaultdict(int)
            for _, stats in plugin_stats.items():
                if stats["category"]:
                    category_stats[stats["category"]] += stats["installation_count"]
            
            return {
                "region": region,
                "granularity": granularity,
                "total_installations": len(installations),
                "unique_plugins": len(plugin_stats),
                "plugin_preferences": {
                    plugin_id: stats for plugin_id, stats in popular_plugins
                },
                "category_preferences": dict(category_stats),
                "regional_insights": self._generate_regional_insights(plugin_stats, category_stats),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get regional plugin preferences: {e}")
            return {"error": str(e)}
    
    async def get_plugin_adoption_heatmap(self) -> Dict[str, Any]:
        """Generate data for a plugin adoption heatmap visualization."""
        try:
            installations = await self.installation_repo.get_all_with_location()
            
            # Create heatmap data structure
            heatmap_data = []
            location_stats = defaultdict(int)
            
            for installation in installations:
                # Extract coordinates if available from tenant metadata
                coordinates = self._extract_coordinates(installation)
                if coordinates:
                    lat, lng = coordinates
                    location_key = f"{lat},{lng}"
                    location_stats[location_key] += 1
            
            # Convert to heatmap format
            for location, count in location_stats.items():
                lat, lng = location.split(',')
                heatmap_data.append({
                    "lat": float(lat),
                    "lng": float(lng),
                    "weight": count,
                    "installations": count
                })
            
            return {
                "heatmap_data": heatmap_data,
                "total_points": len(heatmap_data),
                "max_weight": max([point["weight"] for point in heatmap_data]) if heatmap_data else 0,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate adoption heatmap: {e}")
            return {"error": str(e)}
    
    def _extract_location(self, installation: Any, granularity: str) -> str:
        """Extract location information from installation or tenant data."""
        # Try to get location from tenant metadata
        if hasattr(installation, 'tenant') and installation.tenant:
            tenant_metadata = getattr(installation.tenant, 'metadata', {}) or {}
            
            if granularity == "country":
                return tenant_metadata.get('country', 'Unknown')
            elif granularity == "region":
                return tenant_metadata.get('region', 'Unknown')
            elif granularity == "city":
                country = tenant_metadata.get('country', 'Unknown')
                city = tenant_metadata.get('city', 'Unknown')
                return f"{city}, {country}"
        
        # Fallback to installation metadata
        if hasattr(installation, 'metadata'):
            metadata = installation.metadata or {}
            if granularity == "country":
                return metadata.get('country', 'Unknown')
            elif granularity == "region":
                return metadata.get('region', 'Unknown')
            elif granularity == "city":
                country = metadata.get('country', 'Unknown')
                city = metadata.get('city', 'Unknown')
                return f"{city}, {country}"
        
        return 'Unknown'
    
    def _extract_coordinates(self, installation: Any) -> Optional[Tuple[float, float]]:
        """Extract GPS coordinates from installation or tenant data."""
        # Try tenant metadata first
        if hasattr(installation, 'tenant') and installation.tenant:
            tenant_metadata = getattr(installation.tenant, 'metadata', {}) or {}
            lat = tenant_metadata.get('latitude')
            lng = tenant_metadata.get('longitude')
            
            if lat is not None and lng is not None:
                try:
                    return (float(lat), float(lng))
                except (ValueError, TypeError):
                    pass
        
        # Try installation metadata
        if hasattr(installation, 'metadata'):
            metadata = installation.metadata or {}
            lat = metadata.get('latitude')
            lng = metadata.get('longitude')
            
            if lat is not None and lng is not None:
                try:
                    return (float(lat), float(lng))
                except (ValueError, TypeError):
                    pass
        
        return None
    
    def _calculate_diversity_score(self, stats: Dict[str, Any]) -> float:
        """Calculate market diversity score based on plugin categories."""
        categories = stats["plugin_categories"]
        if not categories:
            return 0.0
        
        total = sum(categories.values())
        if total == 0:
            return 0.0
        
        # Calculate Shannon diversity index
        diversity = 0.0
        for count in categories.values():
            if count > 0:
                proportion = count / total
                diversity -= proportion * (proportion ** 0.5)  # Simplified diversity measure
        
        return round(diversity, 3)
    
    def _analyze_market_penetration(self, geographic_overview: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market penetration across regions."""
        total_installations = sum(stats["total_installations"] for stats in geographic_overview.values())
        
        penetration_analysis = {
            "high_penetration": [],
            "medium_penetration": [],
            "low_penetration": [],
            "emerging_markets": []
        }
        
        for location, stats in geographic_overview.items():
            penetration_rate = stats["total_installations"] / total_installations * 100
            
            if penetration_rate >= 10:
                penetration_analysis["high_penetration"].append({
                    "location": location,
                    "penetration_rate": round(penetration_rate, 2),
                    "installations": stats["total_installations"]
                })
            elif penetration_rate >= 2:
                penetration_analysis["medium_penetration"].append({
                    "location": location,
                    "penetration_rate": round(penetration_rate, 2),
                    "installations": stats["total_installations"]
                })
            elif penetration_rate >= 0.5:
                penetration_analysis["low_penetration"].append({
                    "location": location,
                    "penetration_rate": round(penetration_rate, 2),
                    "installations": stats["total_installations"]
                })
            else:
                penetration_analysis["emerging_markets"].append({
                    "location": location,
                    "penetration_rate": round(penetration_rate, 2),
                    "installations": stats["total_installations"]
                })
        
        return penetration_analysis
    
    def _generate_geographic_insights(self, distribution: Dict[str, Any]) -> List[str]:
        """Generate insights from geographic distribution data."""
        insights = []
        
        if not distribution:
            return ["No installation data available for analysis."]
        
        # Top market insight
        top_market = max(distribution.items(), key=lambda x: x[1]["installation_count"])
        insights.append(f"Top market: {top_market[0]} with {top_market[1]['installation_count']} installations")
        
        # Market concentration
        total_installations = sum(data["installation_count"] for data in distribution.values())
        top_3_markets = sorted(distribution.items(), key=lambda x: x[1]["installation_count"], reverse=True)[:3]
        top_3_concentration = sum(data[1]["installation_count"] for data in top_3_markets) / total_installations * 100
        
        if top_3_concentration > 70:
            insights.append(f"High market concentration: Top 3 markets account for {top_3_concentration:.1f}% of installations")
        elif top_3_concentration < 30:
            insights.append(f"Well-distributed adoption: Top 3 markets account for only {top_3_concentration:.1f}% of installations")
        
        # Growth opportunity
        single_installation_markets = sum(1 for data in distribution.values() if data["installation_count"] == 1)
        if single_installation_markets > len(distribution) * 0.3:
            insights.append(f"Growth opportunity: {single_installation_markets} markets have only 1 installation")
        
        return insights
    
    def _generate_global_insights(self, overview: Dict[str, Any]) -> List[str]:
        """Generate global marketplace insights."""
        insights = []
        
        if not overview:
            return ["No marketplace data available."]
        
        total_locations = len(overview)
        insights.append(f"Plugin marketplace active in {total_locations} locations")
        
        # Market maturity analysis
        mature_markets = sum(1 for stats in overview.values() if stats["total_installations"] >= 10)
        maturity_rate = mature_markets / total_locations * 100
        
        if maturity_rate > 50:
            insights.append(f"Mature marketplace: {mature_markets} ({maturity_rate:.1f}%) locations have 10+ installations")
        else:
            insights.append(f"Developing marketplace: Only {mature_markets} ({maturity_rate:.1f}%) locations have 10+ installations")
        
        # Diversity analysis
        avg_diversity = sum(stats["market_diversity_score"] for stats in overview.values()) / total_locations
        if avg_diversity > 0.5:
            insights.append(f"High plugin diversity across markets (avg score: {avg_diversity:.2f})")
        else:
            insights.append(f"Limited plugin diversity across markets (avg score: {avg_diversity:.2f})")
        
        return insights
    
    def _generate_regional_insights(
        self,
        plugin_stats: Dict[str, Any],
        category_stats: Dict[str, int]
    ) -> List[str]:
        """Generate insights for regional plugin preferences."""
        insights = []
        
        if not plugin_stats:
            return ["No plugin installation data available for this region."]
        
        # Most popular plugin
        most_popular = max(plugin_stats.items(), key=lambda x: x[1]["installation_count"])
        insights.append(f"Most popular plugin: {most_popular[1]['plugin_name']} with {most_popular[1]['installation_count']} installations")
        
        # Category preferences
        if category_stats:
            top_category = max(category_stats.items(), key=lambda x: x[1])
            insights.append(f"Preferred category: {top_category[0]} ({top_category[1]} installations)")
        
        # Market concentration
        total_installations = sum(stats["installation_count"] for stats in plugin_stats.values())
        top_plugin_share = most_popular[1]["installation_count"] / total_installations * 100
        
        if top_plugin_share > 30:
            insights.append(f"Market dominated by single plugin ({top_plugin_share:.1f}% market share)")
        else:
            insights.append(f"Diverse plugin adoption (top plugin has {top_plugin_share:.1f}% share)")
        
        return insights
    
    def _get_top_markets(self, overview: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get top markets by various metrics."""
        by_installations = sorted(
            overview.items(),
            key=lambda x: x[1]["total_installations"],
            reverse=True
        )[:5]
        
        by_diversity = sorted(
            overview.items(),
            key=lambda x: x[1]["market_diversity_score"],
            reverse=True
        )[:5]
        
        return {
            "by_installations": [
                {
                    "location": loc,
                    "installations": data["total_installations"],
                    "unique_plugins": data["unique_plugins"]
                }
                for loc, data in by_installations
            ],
            "by_diversity": [
                {
                    "location": loc,
                    "diversity_score": data["market_diversity_score"],
                    "unique_plugins": data["unique_plugins"]
                }
                for loc, data in by_diversity
            ]
        }