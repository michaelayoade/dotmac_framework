"""Omnichannel-specific caching using existing Redis infrastructure."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
import json

from dotmac_isp.shared.cache import CacheManager
from dotmac_isp.shared.exceptions import EntityNotFoundError

logger = logging.getLogger(__name__, timezone)


class OmnichannelCache:
    """Omnichannel-specific caching layer."""

    def __init__(self):
        """  Init   operation."""
        self.cache = CacheManager()
        self.namespace = "omnichannel"

    # ===== AGENT STATUS CACHING =====

    def cache_agent_status(
        self, tenant_id: str, agent_id: str, status_data: Dict[str, Any], ttl: int = 300
    ):
        """Cache agent status and availability."""
        key = f"agent_status:{tenant_id}:{agent_id}"

        # Add timestamp to status data
        status_data["cached_at"] = datetime.now(timezone.utc).isoformat()
        status_data["ttl"] = ttl

        success = self.cache.set(key, status_data, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug(f"Cached agent status for {agent_id}")

        return success

    def get_agent_status(
        self, tenant_id: str, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached agent status."""
        key = f"agent_status:{tenant_id}:{agent_id}"
        return self.cache.get(key, namespace=self.namespace)

    def invalidate_agent_status(self, tenant_id: str, agent_id: str):
        """Invalidate agent status cache."""
        key = f"agent_status:{tenant_id}:{agent_id}"
        return self.cache.delete(key, namespace=self.namespace)

    def get_available_agents(
        self, tenant_id: str, team_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get list of available agents (cached)."""
        cache_key = f"available_agents:{tenant_id}"
        if team_id:
            cache_key += f":{team_id}"

        cached_agents = self.cache.get(cache_key, namespace=self.namespace)
        if cached_agents:
            logger.debug(f"Retrieved {len(cached_agents)} available agents from cache")
            return cached_agents

        # Cache miss - need to query database
        return None

    def cache_available_agents(
        self,
        tenant_id: str,
        agents: List[Dict[str, Any]],
        team_id: str = None,
        ttl: int = 60,
    ):
        """Cache list of available agents."""
        cache_key = f"available_agents:{tenant_id}"
        if team_id:
            cache_key += f":{team_id}"

        # Add metadata
        cache_data = {
            "agents": agents,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "team_id": team_id,
            "count": len(agents),
        }

        success = self.cache.set(
            cache_key, cache_data, ttl=ttl, namespace=self.namespace
        )
        if success:
            logger.debug(f"Cached {len(agents)} available agents")

        return success

    def invalidate_team_cache(self, tenant_id: str, team_id: str = None):
        """Invalidate team-related caches."""
        if team_id:
            pattern = f"{self.namespace}:available_agents:{tenant_id}:{team_id}"
        else:
            pattern = f"{self.namespace}:available_agents:{tenant_id}*"

        # Use cache manager's pattern deletion if available
        try:
            deleted = self.cache.delete_pattern(pattern)
            logger.debug(f"Invalidated {deleted} team cache entries")
            return deleted
        except AttributeError:
            # Fallback - just delete the main key
            main_key = f"available_agents:{tenant_id}"
            return self.cache.delete(main_key, namespace=self.namespace)

    # ===== ROUTING RULES CACHING =====

    def cache_routing_rules(
        self, tenant_id: str, rules: List[Dict[str, Any]], ttl: int = 600
    ):
        """Cache routing rules for faster processing."""
        key = f"routing_rules:{tenant_id}"

        cache_data = {
            "rules": rules,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "count": len(rules),
        }

        success = self.cache.set(key, cache_data, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug(f"Cached {len(rules)} routing rules")

        return success

    def get_routing_rules(self, tenant_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached routing rules."""
        key = f"routing_rules:{tenant_id}"
        cached_data = self.cache.get(key, namespace=self.namespace)

        if cached_data and isinstance(cached_data, dict):
            return cached_data.get("rules", [])

        return None

    def invalidate_routing_rules(self, tenant_id: str):
        """Invalidate routing rules cache."""
        key = f"routing_rules:{tenant_id}"
        return self.cache.delete(key, namespace=self.namespace)

    # ===== CHANNEL PLUGIN HEALTH CACHING =====

    def cache_plugin_health(
        self,
        tenant_id: str,
        channel_id: str,
        health_data: Dict[str, Any],
        ttl: int = 300,
    ):
        """Cache plugin health status."""
        key = f"plugin_health:{tenant_id}:{channel_id}"

        health_data["cached_at"] = datetime.now(timezone.utc).isoformat()

        success = self.cache.set(key, health_data, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug(f"Cached plugin health for {channel_id}")

        return success

    def get_plugin_health(
        self, tenant_id: str, channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached plugin health status."""
        key = f"plugin_health:{tenant_id}:{channel_id}"
        return self.cache.get(key, namespace=self.namespace)

    def get_all_plugin_health(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """Get health status for all plugins (from cache)."""
        pattern = f"plugin_health:{tenant_id}:*"

        try:
            # Get all keys matching pattern
            keys = self.cache.redis_client.keys(f"{self.namespace}:{pattern}")
            health_statuses = {}

            for key in keys:
                # Extract channel_id from key
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                parts = key_str.split(":")
                if len(parts) >= 4:
                    channel_id = parts[3]
                    health_data = self.cache.get(
                        f"plugin_health:{tenant_id}:{channel_id}",
                        namespace=self.namespace,
                    )
                    if health_data:
                        health_statuses[channel_id] = health_data

            return health_statuses

        except Exception as e:
            logger.error(f"Failed to get all plugin health: {e}")
            return {}

    def invalidate_plugin_health(self, tenant_id: str, channel_id: str = None):
        """Invalidate plugin health cache."""
        if channel_id:
            key = f"plugin_health:{tenant_id}:{channel_id}"
            return self.cache.delete(key, namespace=self.namespace)
        else:
            # Invalidate all plugin health for tenant
            pattern = f"{self.namespace}:plugin_health:{tenant_id}:*"
            try:
                return self.cache.delete_pattern(pattern)
            except AttributeError:
                logger.warning(
                    "Pattern deletion not available, cannot invalidate all plugin health"
                )
                return False

    # ===== INTERACTION CACHING =====

    def cache_interaction_context(
        self,
        tenant_id: str,
        interaction_id: str,
        context_data: Dict[str, Any],
        ttl: int = 3600,
    ):
        """Cache interaction context for quick access."""
        key = f"interaction_context:{tenant_id}:{interaction_id}"

        context_data["cached_at"] = datetime.now(timezone.utc).isoformat()

        success = self.cache.set(key, context_data, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug(f"Cached interaction context for {interaction_id}")

        return success

    def get_interaction_context(
        self, tenant_id: str, interaction_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached interaction context."""
        key = f"interaction_context:{tenant_id}:{interaction_id}"
        return self.cache.get(key, namespace=self.namespace)

    def invalidate_interaction_context(self, tenant_id: str, interaction_id: str):
        """Invalidate interaction context cache."""
        key = f"interaction_context:{tenant_id}:{interaction_id}"
        return self.cache.delete(key, namespace=self.namespace)

    # ===== CONVERSATION THREADING CACHE =====

    def cache_conversation_thread(
        self,
        tenant_id: str,
        thread_id: str,
        thread_data: Dict[str, Any],
        ttl: int = 1800,
    ):
        """Cache conversation thread data."""
        key = f"conversation_thread:{tenant_id}:{thread_id}"

        thread_data["cached_at"] = datetime.now(timezone.utc).isoformat()

        success = self.cache.set(key, thread_data, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug(f"Cached conversation thread {thread_id}")

        return success

    def get_conversation_thread(
        self, tenant_id: str, thread_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached conversation thread."""
        key = f"conversation_thread:{tenant_id}:{thread_id}"
        return self.cache.get(key, namespace=self.namespace)

    def cache_customer_active_threads(
        self,
        tenant_id: str,
        customer_id: str,
        threads: List[Dict[str, Any]],
        ttl: int = 600,
    ):
        """Cache customer's active conversation threads."""
        key = f"customer_threads:{tenant_id}:{customer_id}"

        cache_data = {
            "threads": threads,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "count": len(threads),
        }

        success = self.cache.set(key, cache_data, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug(
                f"Cached {len(threads)} active threads for customer {customer_id}"
            )

        return success

    def get_customer_active_threads(
        self, tenant_id: str, customer_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached customer active threads."""
        key = f"customer_threads:{tenant_id}:{customer_id}"
        cached_data = self.cache.get(key, namespace=self.namespace)

        if cached_data and isinstance(cached_data, dict):
            return cached_data.get("threads", [])

        return None

    def invalidate_customer_threads(self, tenant_id: str, customer_id: str):
        """Invalidate customer threads cache."""
        key = f"customer_threads:{tenant_id}:{customer_id}"
        return self.cache.delete(key, namespace=self.namespace)

    # ===== ANALYTICS CACHING =====

    def cache_dashboard_stats(
        self, tenant_id: str, stats: Dict[str, Any], ttl: int = 300
    ):
        """Cache dashboard statistics."""
        key = f"dashboard_stats:{tenant_id}"

        stats["cached_at"] = datetime.now(timezone.utc).isoformat()

        success = self.cache.set(key, stats, ttl=ttl, namespace=self.namespace)
        if success:
            logger.debug("Cached dashboard statistics")

        return success

    def get_dashboard_stats(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get cached dashboard statistics."""
        key = f"dashboard_stats:{tenant_id}"
        return self.cache.get(key, namespace=self.namespace)

    def invalidate_dashboard_stats(self, tenant_id: str):
        """Invalidate dashboard statistics cache."""
        key = f"dashboard_stats:{tenant_id}"
        return self.cache.delete(key, namespace=self.namespace)

    # ===== BULK OPERATIONS =====

    def warm_cache_for_tenant(self, tenant_id: str):
        """Warm up frequently accessed cache entries for a tenant."""
        logger.info(f"Warming cache for tenant {tenant_id}")

        # This would be called from a background task to pre-populate cache
        # Implementation would load commonly accessed data like:
        # - Active agents
        # - Routing rules
        # - Plugin health status
        # - Dashboard stats

        # For now, return True to indicate warming is supported
        return True

    def get_cache_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            # Count cache entries for tenant
            patterns_to_check = [
                f"agent_status:{tenant_id}:*",
                f"available_agents:{tenant_id}*",
                f"routing_rules:{tenant_id}",
                f"plugin_health:{tenant_id}:*",
                f"interaction_context:{tenant_id}:*",
                f"conversation_thread:{tenant_id}:*",
                f"customer_threads:{tenant_id}:*",
                f"dashboard_stats:{tenant_id}",
            ]

            stats = {
                "tenant_id": tenant_id,
                "cache_entries": {},
                "total_entries": 0,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

            for pattern in patterns_to_check:
                try:
                    keys = self.cache.redis_client.keys(f"{self.namespace}:{pattern}")
                    entry_count = len(keys) if keys else 0
                    category = pattern.split(":")[0]
                    stats["cache_entries"][category] = entry_count
                    stats["total_entries"] += entry_count
                except Exception as e:
                    logger.error(
                        f"Failed to count cache entries for pattern {pattern}: {e}"
                    )
                    stats["cache_entries"][pattern.split(":")[0]] = -1

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                "tenant_id": tenant_id,
                "error": str(e),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    def clear_tenant_cache(self, tenant_id: str) -> int:
        """Clear all cache entries for a tenant."""
        try:
            pattern = f"{self.namespace}:*:{tenant_id}:*"
            deleted_count = self.cache.delete_pattern(pattern)
            logger.info(f"Cleared {deleted_count} cache entries for tenant {tenant_id}")
            return deleted_count
        except AttributeError:
            logger.warning("Pattern deletion not available")
            return 0
        except Exception as e:
            logger.error(f"Failed to clear tenant cache: {e}")
            return 0


# Global cache instance
omnichannel_cache = OmnichannelCache()
