"""
Plugin Version Comparison and Management System.

Handles semantic versioning, version comparisons, compatibility checks,
and update recommendations for plugins.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from repositories.plugin_additional import ()
    PluginRepository,
    PluginInstallationRepository,
    PluginVersionRepository
, timezone)

logger = logging.getLogger(__name__)


class VersionType(Enum):
    """Types of version updates."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    UNKNOWN = "unknown"


class CompatibilityLevel(Enum):
    """Compatibility levels between versions."""
    COMPATIBLE = "compatible"
    BREAKING_CHANGES = "breaking_changes"
    DEPRECATED = "deprecated"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


@dataclass
class SemanticVersion:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None
    
    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version
    
    def __lt__(self, other: 'SemanticVersion') -> bool:
        """Less than comparison."""
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        
        # Handle prerelease comparison
        if self.prerelease is None and other.prerelease is None:
            return False
        if self.prerelease is None:
            return False  # Release versions are greater than prerelease
        if other.prerelease is None:
            return True
        
        return self.prerelease < other.prerelease
    
    def __eq__(self, other: 'SemanticVersion') -> bool:
        """Equality comparison."""
        return (self.major == other.major and )
                self.minor == other.minor and 
                self.patch == other.patch and 
                self.prerelease == other.prerelease)
    
    def __le__(self, other: 'SemanticVersion') -> bool:
        return self < other or self == other
    
    def __gt__(self, other: 'SemanticVersion') -> bool:
        return not self <= other
    
    def __ge__(self, other: 'SemanticVersion') -> bool:
        return not self < other


@dataclass
class VersionComparison:
    """Result of version comparison."""
    current_version: str
    target_version: str
    is_upgrade: bool
    version_type: VersionType
    compatibility_level: CompatibilityLevel
    breaking_changes: List[str]
    new_features: List[str]
    bug_fixes: List[str]
    security_fixes: List[str]
    migration_required: bool
    risk_level: str  # low, medium, high


class PluginVersionManager:
    """Service for plugin version management and comparison."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.plugin_repo = PluginRepository(db)
        self.installation_repo = PluginInstallationRepository(db)
        self.version_repo = PluginVersionRepository(db)
    
    def parse_version(self, version_string: str) -> SemanticVersion:
        """Parse a version string into a SemanticVersion object."""
        # Remove 'v' prefix if present
        version_string = version_string.lstrip('v')
        
        # Semantic versioning regex
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$')
        
        match = re.match(semver_pattern, version_string)
        if not match:
            # Try simpler patterns
            simple_patterns = [
                r'^(\d+)\.(\d+)\.(\d+)$',  # 1.2.3
                r'^(\d+)\.(\d+)$',         # 1.2 -> 1.2.0
                r'^(\d+)$'                 # 1 -> 1.0.0 ]
            
            for pattern in simple_patterns:
                match = re.match(pattern, version_string)
                if match:
                    groups = match.groups(
)                    major = int(groups[0])
                    minor = int(groups[1]) if len(groups) > 1 and groups[1] else 0
                    patch = int(groups[2]) if len(groups) > 2 and groups[2] else 0
                    return SemanticVersion(major, minor, patch)
            
            # Fallback for non-standard versions
            logger.warning(f"Could not parse version: {version_string}, using fallback")
            return SemanticVersion(0, 0, 0, prerelease=version_string)
        
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        prerelease = match.group(4)
        build = match.group(5)
        
        return SemanticVersion(major, minor, patch, prerelease, build)
    
    def compare_versions(self, current: str, target: str) -> VersionComparison:
        """Compare two version strings and return detailed comparison."""
        try:
            current_semver = self.parse_version(current)
            target_semver = self.parse_version(target)
            
            is_upgrade = target_semver > current_semver
            
            # Determine version type
            version_type = self._determine_version_type(current_semver, target_semver)
            
            # Determine compatibility level
            compatibility_level = self._determine_compatibility(current_semver, target_semver, version_type)
            
            # Determine risk level
            risk_level = self._determine_risk_level(version_type, compatibility_level)
            
            return VersionComparison(current_version=current,
                target_version=target,
                is_upgrade=is_upgrade,
                version_type=version_type,
                compatibility_level=compatibility_level,
                breaking_changes=[],  # Would be populated from release notes
                new_features=[],      # Would be populated from release notes
                bug_fixes=[],         # Would be populated from release notes
                security_fixes=[],    # Would be populated from release notes
                migration_required=compatibility_level == CompatibilityLevel.BREAKING_CHANGES,
                risk_level=risk_level
            
        except Exception as e:
            logger.error(f"Failed to compare versions {current) and {target}: {e}")
            return VersionComparison(current_version=current,
                target_version=target,
                is_upgrade=False,
                version_type=VersionType.UNKNOWN,
                compatibility_level=CompatibilityLevel.UNKNOWN,
                breaking_changes=[],
                new_features=[],
                bug_fixes=[],
                security_fixes=[],
                migration_required=False,
                risk_level="unknown"
    
    async def get_available_updates(:)
        self,
    installation_id: UUID)
    ) -> Dict[str, Any]:
        """Get available updates for a plugin installation."""
        try:
            installation = await self.installation_repo.get_with_plugin(installation_id)
            if not installation or not installation.plugin:
                return {"error": "Installation or plugin not found")
            
            current_version = installation.installed_version
            plugin = installation.plugin
            
            # Get all available versions for this plugin
            available_versions = await self.version_repo.get_by_plugin_id(plugin.id)
            
            # Filter versions newer than current
            current_semver = self.parse_version(current_version)
            
            updates = []
            for version in available_versions:
                version_semver = self.parse_version(version.version)
                
                if version_semver > current_semver:
                    comparison = self.compare_versions(current_version, version.version)
                    
                    updates.append({)
                        "version": version.version,
                        "release_date": version.release_date.isoformat( if version.release_date else None,
                        "version_type": comparison.version_type.value,
                        "compatibility_level": comparison.compatibility_level.value,
                        "risk_level": comparison.risk_level,
                        "release_notes": version.release_notes,
                        "security_update": version.is_security_update,
)                        "recommended": self._is_recommended_update(comparison, version)
                    })
            
            # Sort by version (newest first)
            updates.sort(key=lambda x: self.parse_version(x["version"]), reverse=True)
            
            # Get recommended update
            recommended_update = None
            for update in updates:
                if update["recommended"]:
                    recommended_update = update
                    break
            
            return {
                "installation_id": installation_id,
                "plugin_name": plugin.name,
                "current_version": current_version,
                "available_updates": updates,
                "recommended_update": recommended_update,
                "update_available": len(updates) > 0,
                "security_updates_available": any(u["security_update"] for u in updates),
                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get available updates: {e}")
            return {"error": str(e)}
    
    async def get_tenant_update_summary(:)
        self,
    tenant_id: UUID)
    ) -> Dict[str, Any]:
        """Get update summary for all plugins in a tenant."""
        try:
            installations = await self.installation_repo.get_by_tenant(tenant_id)
            
            if not installations:
                return {
                    "tenant_id": tenant_id,
                    "total_plugins": 0,
                    "update_summary": {}
                }
            
            summary = {
                "total_plugins": len(installations),
                "plugins_with_updates": 0,
                "security_updates_available": 0,
                "major_updates_available": 0,
                "minor_updates_available": 0,
                "patch_updates_available": 0,
                "plugins_needing_attention": [],
                "recommended_updates": []
            }
            
            for installation in installations:
                if not installation.plugin:
                    continue
                
                updates_info = await self.get_available_updates(installation.id)
                
                if updates_info.get("update_available"):
                    summary["plugins_with_updates"] += 1
                    
                    available_updates = updates_info.get("available_updates", [])
                    
                    # Count by update type
                    for update in available_updates:
                        if update["security_update"]:
                            summary["security_updates_available"] += 1
                        
                        version_type = update["version_type"]
                        if version_type == "major":
                            summary["major_updates_available"] += 1
                        elif version_type == "minor":
                            summary["minor_updates_available"] += 1
                        elif version_type == "patch":
                            summary["patch_updates_available"] += 1
                    
                    # Add to recommended updates if there's a recommended version
                    recommended = updates_info.get("recommended_update")
                    if recommended:
                        summary["recommended_updates"].append({)
                            "plugin_name": installation.plugin.name,
                            "installation_id": installation.id,
                            "current_version": updates_info["current_version"],
                            "recommended_version": recommended["version"],
                            "update_type": recommended["version_type"],
                            "risk_level": recommended["risk_level"],
                            "security_update": recommended["security_update"]
                        })
                    
                    # Check if plugin needs immediate attention
                    if any(u["security_update"] for u in available_updates):
                        summary["plugins_needing_attention"].append({)
                            "plugin_name": installation.plugin.name,
                            "installation_id": installation.id,
                            "reason": "Security update available",
                            "urgency": "high"
                        })
                    elif any(u["risk_level"] == "high" for u in available_updates):
                        summary["plugins_needing_attention"].append({)
                            "plugin_name": installation.plugin.name,
                            "installation_id": installation.id,
                            "reason": "High-risk update available",
                            "urgency": "medium"
                        })
            
            return {
                "tenant_id": tenant_id,
                "update_summary": summary,
                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get tenant update summary: {e}")
            return {"error": str(e)}
    
    async def check_version_compatibility(:)
        self,
        plugin_id: UUID,
        target_version: str,
    dependency_versions: Dict[str, str])
    ) -> Dict[str, Any]:
        """Check if a target version is compatible with dependency versions."""
        try:
            plugin = await self.plugin_repo.get_by_id(plugin_id)
            if not plugin:
                return {"error": "Plugin not found"}
            
            # Get version details
            version_details = await self.version_repo.get_by_plugin_and_version(plugin_id, target_version)
            if not version_details:
                return {"error": f"Version {target_version} not found"}
            
            compatibility_results = {
                "plugin_name": plugin.name,
                "target_version": target_version,
                "compatible": True,
                "compatibility_issues": [],
                "dependency_checks": {}
            }
            
            # Check dependency compatibility
            if version_details.dependencies:
                for dep_name, required_version in version_details.dependencies.items(:
    )                    current_dep_version = dependency_versions.get(dep_name)
                    
                    if not current_dep_version:
                        compatibility_results["compatible"] = False
                        compatibility_results["compatibility_issues"].append()
                            f"Missing dependency: {dep_name} (required: {required_version})"
                        compatibility_results["dependency_checks"][dep_name] = {
                            "required": required_version,
                            "current": None,
                            "compatible": False,
                            "issue": "Missing dependency"
                        }
                        continue
                    
                    # Check version compatibility
                    is_compatible = self._check_dependency_compatibility(}
                        current_dep_version, required_version
                    }
                    
                    compatibility_results["dependency_checks"][dep_name] = {
                        "required": required_version,
                        "current": current_dep_version,
                        "compatible": is_compatible,
                        "issue": None if is_compatible else "Version mismatch"
                    }
                    
                    if not is_compatible:
                        compatibility_results["compatible"] = False
                        compatibility_results["compatibility_issues"].append(}
                            f"Dependency version mismatch: {dep_name} "
                            f"(required: {required_version}, current: {current_dep_version})"
                        }
            
            # Check platform compatibility
            if version_details.platform_requirements:
                platform_compatible = self._check_platform_compatibility(}
                    version_details.platform_requirements
                }
                
                if not platform_compatible["compatible"]:
                    compatibility_results["compatible"] = False
                    compatibility_results["compatibility_issues"].extend(}
                        platform_compatible["issues"]
                    }
            
            return compatibility_results
            
        except Exception as e:
            logger.error(f"Failed to check version compatibility: {e}"}
            return {"error": str(e)}
    
    def _determine_version_type(}
        self,
        current: SemanticVersion,
    target: SemanticVersion}
    ) -> VersionType:
        """Determine the type of version change."""
        if target.major > current.major:
            return VersionType.MAJOR
        elif target.minor > current.minor:
            return VersionType.MINOR
        elif target.patch > current.patch:
            return VersionType.PATCH
        elif target.prerelease and not current.prerelease:
            return VersionType.PRERELEASE
        elif target.prerelease and current.prerelease:
            return VersionType.PRERELEASE
        else:
            return VersionType.UNKNOWN
    
    def _determine_compatibility(}
        self,
        current: SemanticVersion,
        target: SemanticVersion,
    version_type: VersionType}
    ) -> CompatibilityLevel:
        """Determine compatibility level between versions."""
        if version_type == VersionType.MAJOR:
            return CompatibilityLevel.BREAKING_CHANGES
        elif version_type == VersionType.MINOR:
            return CompatibilityLevel.COMPATIBLE
        elif version_type == VersionType.PATCH:
            return CompatibilityLevel.COMPATIBLE
        elif version_type == VersionType.PRERELEASE:
            return CompatibilityLevel.COMPATIBLE
        else:
            return CompatibilityLevel.UNKNOWN
    
    def _determine_risk_level(}
        self,
        version_type: VersionType,
    compatibility_level: CompatibilityLevel}
    ) -> str:
        """Determine risk level of the update."""
        if compatibility_level == CompatibilityLevel.BREAKING_CHANGES:
            return "high"
        elif version_type == VersionType.MAJOR:
            return "medium"
        elif version_type == VersionType.MINOR:
            return "low"
        elif version_type == VersionType.PATCH:
            return "low"
        else:
            return "unknown"
    
    def _is_recommended_update(}
        self,
        comparison: VersionComparison,
    version: Any}
    ) -> bool:
        """Determine if an update is recommended."""
        # Security updates are always recommended
        if hasattr(version, 'is_security_update') and version.is_security_update:
            return True
        
        # Low risk updates are recommended
        if comparison.risk_level == "low":
            return True
        
        # Medium risk minor updates are recommended
        if (comparison.risk_level == "medium" and }
            comparison.version_type == VersionType.MINOR):
            return True
        
        return False
    
    def _check_dependency_compatibility(}
        self,
        current_version: str,
    required_version: str}
    ) -> bool:
        """Check if current version satisfies required version constraint."""
        try:
            # Handle version constraints like ">=1.2.0", "~1.2.0", "^1.2.0"
            if required_version.startswith('>='):
                required = self.parse_version(required_version[2:])
                current = self.parse_version(current_version}
                return current >= required
            elif required_version.startswith('~'):
                # Compatible within patch versions
                required = self.parse_version(required_version[1:])
                current = self.parse_version(current_version}
                return (current.major == required.major and }
                        current.minor == required.minor and 
                        current >= required}
            elif required_version.startswith('^'):
                # Compatible within minor versions
                required = self.parse_version(required_version[1:])
                current = self.parse_version(current_version}
                return (current.major == required.major and }
                        current >= required}
            else:
                # Exact version match
                return current_version == required_version
                
        except Exception as e:
            logger.error(f"Failed to check dependency compatibility: {e}"}
            return False
    
    def _check_platform_compatibility(}
        self,
    platform_requirements: Dict[str, Any])
    ) -> Dict[str, Any]:
        """Check platform compatibility requirements."""
        # This would check against actual platform capabilities
        # For now, return compatible
        return {
            "compatible": True,
            "issues": []
        }
