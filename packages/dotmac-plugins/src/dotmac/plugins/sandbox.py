"""
Plugin sandboxing and security policy enforcement.

Provides safety flags, resource limitations, and security policies
for plugin execution. Note that this module provides policy declarations
rather than actual sandboxing enforcement, which would require OS-level isolation.
"""

import logging
import resource
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Callable

from .interfaces import IPlugin
from .types import PluginSecurityError


class SecurityLevel(Enum):
    """Security levels for plugin execution."""
    
    UNRESTRICTED = auto()  # No security restrictions
    LOW = auto()           # Basic safety checks
    MEDIUM = auto()        # Moderate restrictions
    HIGH = auto()          # Strict security policy
    STRICT = auto()        # Maximum security


class ResourceType(Enum):
    """Types of system resources that can be limited."""
    
    MEMORY = "memory"
    CPU_TIME = "cpu_time"
    FILE_DESCRIPTORS = "file_descriptors"
    NETWORK_CONNECTIONS = "network_connections"
    DISK_SPACE = "disk_space"
    THREADS = "threads"


@dataclass
class ResourceLimits:
    """Resource usage limits for plugins."""
    
    # Memory limits (bytes)
    max_memory: Optional[int] = None
    
    # CPU time limits (seconds)
    max_cpu_time: Optional[float] = None
    
    # File system limits
    max_file_descriptors: Optional[int] = None
    max_disk_usage: Optional[int] = None
    
    # Network limits
    max_network_connections: Optional[int] = None
    
    # Threading limits
    max_threads: Optional[int] = None
    
    # Execution timeout (seconds)
    execution_timeout: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "max_memory": self.max_memory,
            "max_cpu_time": self.max_cpu_time,
            "max_file_descriptors": self.max_file_descriptors,
            "max_disk_usage": self.max_disk_usage,
            "max_network_connections": self.max_network_connections,
            "max_threads": self.max_threads,
            "execution_timeout": self.execution_timeout,
        }


@dataclass
class SecurityPolicy:
    """Security policy for plugin execution."""
    
    # Security level
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    
    # Resource limits
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Capability flags
    allow_network_access: bool = True
    allow_file_system_access: bool = True
    allow_subprocess_execution: bool = False
    allow_native_code: bool = False
    allow_dynamic_imports: bool = True
    allow_eval_exec: bool = False
    
    # Allowed file system paths
    allowed_filesystem_paths: Set[str] = field(default_factory=set)
    
    # Allowed network hosts/ports
    allowed_network_hosts: Set[str] = field(default_factory=set)
    allowed_network_ports: Set[int] = field(default_factory=set)
    
    # Environment variable access
    allowed_env_vars: Set[str] = field(default_factory=set)
    
    # Additional restrictions
    read_only_mode: bool = False
    audit_all_operations: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "security_level": self.security_level.name,
            "resource_limits": self.resource_limits.to_dict(),
            "allow_network_access": self.allow_network_access,
            "allow_file_system_access": self.allow_file_system_access,
            "allow_subprocess_execution": self.allow_subprocess_execution,
            "allow_native_code": self.allow_native_code,
            "allow_dynamic_imports": self.allow_dynamic_imports,
            "allow_eval_exec": self.allow_eval_exec,
            "allowed_filesystem_paths": list(self.allowed_filesystem_paths),
            "allowed_network_hosts": list(self.allowed_network_hosts),
            "allowed_network_ports": list(self.allowed_network_ports),
            "allowed_env_vars": list(self.allowed_env_vars),
            "read_only_mode": self.read_only_mode,
            "audit_all_operations": self.audit_all_operations,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityPolicy":
        """Create security policy from dictionary."""
        # Parse security level
        security_level = SecurityLevel.MEDIUM
        if "security_level" in data:
            try:
                security_level = SecurityLevel[data["security_level"]]
            except KeyError:
                pass
        
        # Parse resource limits
        resource_limits = ResourceLimits()
        if "resource_limits" in data:
            limits_data = data["resource_limits"]
            resource_limits = ResourceLimits(
                max_memory=limits_data.get("max_memory"),
                max_cpu_time=limits_data.get("max_cpu_time"),
                max_file_descriptors=limits_data.get("max_file_descriptors"),
                max_disk_usage=limits_data.get("max_disk_usage"),
                max_network_connections=limits_data.get("max_network_connections"),
                max_threads=limits_data.get("max_threads"),
                execution_timeout=limits_data.get("execution_timeout"),
            )
        
        return cls(
            security_level=security_level,
            resource_limits=resource_limits,
            allow_network_access=data.get("allow_network_access", True),
            allow_file_system_access=data.get("allow_file_system_access", True),
            allow_subprocess_execution=data.get("allow_subprocess_execution", False),
            allow_native_code=data.get("allow_native_code", False),
            allow_dynamic_imports=data.get("allow_dynamic_imports", True),
            allow_eval_exec=data.get("allow_eval_exec", False),
            allowed_filesystem_paths=set(data.get("allowed_filesystem_paths", [])),
            allowed_network_hosts=set(data.get("allowed_network_hosts", [])),
            allowed_network_ports=set(data.get("allowed_network_ports", [])),
            allowed_env_vars=set(data.get("allowed_env_vars", [])),
            read_only_mode=data.get("read_only_mode", False),
            audit_all_operations=data.get("audit_all_operations", False),
        )


class PluginSandbox:
    """
    Plugin sandbox manager for security policy enforcement.
    
    Note: This provides policy declaration and basic enforcement.
    Full sandboxing would require OS-level isolation (containers, VMs, etc.).
    """
    
    def __init__(
        self,
        default_policy: Optional[SecurityPolicy] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize plugin sandbox.
        
        Args:
            default_policy: Default security policy
            logger: Optional logger instance
        """
        self._logger = logger or logging.getLogger(__name__)
        self._default_policy = default_policy or self._create_default_policy()
        self._plugin_policies: Dict[str, SecurityPolicy] = {}
        self._resource_monitors: Dict[str, "ResourceMonitor"] = {}
        self._lock = threading.Lock()
    
    def _create_default_policy(self) -> SecurityPolicy:
        """Create default security policy."""
        return SecurityPolicy(
            security_level=SecurityLevel.MEDIUM,
            resource_limits=ResourceLimits(
                max_memory=100 * 1024 * 1024,  # 100MB
                max_cpu_time=30.0,             # 30 seconds
                max_file_descriptors=20,
                execution_timeout=60.0,        # 1 minute
            ),
            allow_network_access=True,
            allow_file_system_access=True,
            allow_subprocess_execution=False,
            allow_native_code=False,
            allow_eval_exec=False,
        )
    
    def set_plugin_policy(self, plugin_name: str, policy: SecurityPolicy) -> None:
        """
        Set security policy for specific plugin.
        
        Args:
            plugin_name: Plugin name
            policy: Security policy to apply
        """
        with self._lock:
            self._plugin_policies[plugin_name] = policy
            self._logger.info(f"Set security policy for plugin {plugin_name}")
    
    def get_plugin_policy(self, plugin_name: str) -> SecurityPolicy:
        """
        Get security policy for plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Security policy (default if no specific policy set)
        """
        with self._lock:
            return self._plugin_policies.get(plugin_name, self._default_policy)
    
    def validate_plugin_capabilities(self, plugin: IPlugin) -> List[str]:
        """
        Validate plugin capabilities against security policy.
        
        Args:
            plugin: Plugin to validate
            
        Returns:
            List of security violations (empty if valid)
        """
        violations = []
        policy = self.get_plugin_policy(plugin.name)
        
        # Check plugin metadata capabilities
        if hasattr(plugin.metadata, 'capabilities'):
            capabilities = plugin.metadata.capabilities
            
            # Check network access
            if capabilities.get('requires_network', False) and not policy.allow_network_access:
                violations.append("Plugin requires network access but policy disallows it")
            
            # Check file system access
            if capabilities.get('requires_filesystem', False) and not policy.allow_file_system_access:
                violations.append("Plugin requires file system access but policy disallows it")
            
            # Check subprocess execution
            if capabilities.get('requires_subprocess', False) and not policy.allow_subprocess_execution:
                violations.append("Plugin requires subprocess execution but policy disallows it")
            
            # Check native code
            if capabilities.get('uses_native_code', False) and not policy.allow_native_code:
                violations.append("Plugin uses native code but policy disallows it")
            
            # Check eval/exec usage
            if capabilities.get('uses_eval_exec', False) and not policy.allow_eval_exec:
                violations.append("Plugin uses eval/exec but policy disallows it")
        
        return violations
    
    def create_execution_context(self, plugin: IPlugin) -> "ExecutionContext":
        """
        Create execution context for plugin with resource monitoring.
        
        Args:
            plugin: Plugin to create context for
            
        Returns:
            Execution context with resource monitoring
        """
        policy = self.get_plugin_policy(plugin.name)
        return ExecutionContext(plugin.name, policy, self._logger)
    
    def enforce_resource_limits(self, plugin_name: str) -> None:
        """
        Enforce resource limits for plugin (basic enforcement).
        
        Args:
            plugin_name: Plugin name
        """
        policy = self.get_plugin_policy(plugin_name)
        limits = policy.resource_limits
        
        try:
            # Set memory limit (if supported)
            if limits.max_memory and hasattr(resource, 'RLIMIT_AS'):
                resource.setrlimit(resource.RLIMIT_AS, (limits.max_memory, limits.max_memory))
            
            # Set CPU time limit
            if limits.max_cpu_time and hasattr(resource, 'RLIMIT_CPU'):
                cpu_limit = int(limits.max_cpu_time)
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            
            # Set file descriptor limit
            if limits.max_file_descriptors and hasattr(resource, 'RLIMIT_NOFILE'):
                resource.setrlimit(
                    resource.RLIMIT_NOFILE, 
                    (limits.max_file_descriptors, limits.max_file_descriptors)
                )
                
        except (OSError, ValueError) as e:
            self._logger.warning(f"Failed to set resource limits for {plugin_name}: {e}")
    
    def get_security_report(self) -> Dict[str, Any]:
        """
        Get security report for all plugins.
        
        Returns:
            Security status report
        """
        with self._lock:
            policies_by_level = {}
            for level in SecurityLevel:
                policies_by_level[level.name] = 0
            
            for policy in self._plugin_policies.values():
                policies_by_level[policy.security_level.name] += 1
            
            return {
                "total_plugins": len(self._plugin_policies),
                "default_security_level": self._default_policy.security_level.name,
                "policies_by_level": policies_by_level,
                "plugins_with_custom_policies": list(self._plugin_policies.keys()),
                "active_monitors": len(self._resource_monitors),
            }


class ExecutionContext:
    """
    Execution context for plugin with resource monitoring and timeout enforcement.
    """
    
    def __init__(
        self, 
        plugin_name: str, 
        policy: SecurityPolicy, 
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize execution context.
        
        Args:
            plugin_name: Plugin name
            policy: Security policy
            logger: Optional logger
        """
        self.plugin_name = plugin_name
        self.policy = policy
        self._logger = logger or logging.getLogger(__name__)
        self._start_time: Optional[float] = None
        self._resource_monitor: Optional["ResourceMonitor"] = None
    
    def __enter__(self):
        """Enter execution context."""
        self._start_time = time.time()
        
        # Create resource monitor if limits are set
        if self._has_resource_limits():
            self._resource_monitor = ResourceMonitor(
                self.plugin_name, 
                self.policy.resource_limits,
                self._logger
            )
            self._resource_monitor.start()
        
        self._logger.debug(f"Entered execution context for plugin {self.plugin_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit execution context."""
        if self._resource_monitor:
            self._resource_monitor.stop()
            
            # Check for violations
            violations = self._resource_monitor.get_violations()
            if violations:
                self._logger.warning(
                    f"Resource violations for plugin {self.plugin_name}: {violations}"
                )
        
        if self._start_time:
            execution_time = time.time() - self._start_time
            timeout = self.policy.resource_limits.execution_timeout
            
            if timeout and execution_time > timeout:
                self._logger.warning(
                    f"Plugin {self.plugin_name} exceeded execution timeout: "
                    f"{execution_time:.2f}s > {timeout}s"
                )
        
        self._logger.debug(f"Exited execution context for plugin {self.plugin_name}")
    
    def _has_resource_limits(self) -> bool:
        """Check if any resource limits are set."""
        limits = self.policy.resource_limits
        return any([
            limits.max_memory,
            limits.max_cpu_time,
            limits.max_file_descriptors,
            limits.max_threads,
        ])
    
    def check_capability(self, capability: str) -> bool:
        """
        Check if capability is allowed by policy.
        
        Args:
            capability: Capability to check
            
        Returns:
            True if capability is allowed
        """
        capability_map = {
            'network': self.policy.allow_network_access,
            'filesystem': self.policy.allow_file_system_access,
            'subprocess': self.policy.allow_subprocess_execution,
            'native_code': self.policy.allow_native_code,
            'eval_exec': self.policy.allow_eval_exec,
            'dynamic_imports': self.policy.allow_dynamic_imports,
        }
        
        return capability_map.get(capability, False)
    
    def require_capability(self, capability: str) -> None:
        """
        Require capability, raising exception if not allowed.
        
        Args:
            capability: Required capability
            
        Raises:
            PluginSecurityError: If capability is not allowed
        """
        if not self.check_capability(capability):
            raise PluginSecurityError(
                f"Plugin {self.plugin_name} requires '{capability}' capability "
                f"which is not allowed by security policy"
            )


class ResourceMonitor:
    """
    Basic resource monitoring for plugin execution.
    
    Note: This provides basic monitoring. More sophisticated monitoring
    would require OS-specific tools or containerization.
    """
    
    def __init__(
        self, 
        plugin_name: str, 
        limits: ResourceLimits, 
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize resource monitor.
        
        Args:
            plugin_name: Plugin name
            limits: Resource limits to monitor
            logger: Optional logger
        """
        self.plugin_name = plugin_name
        self.limits = limits
        self._logger = logger or logging.getLogger(__name__)
        self._violations: List[str] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"ResourceMonitor-{self.plugin_name}",
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
    
    def get_violations(self) -> List[str]:
        """Get list of resource violations."""
        return self._violations.copy()
    
    def _monitor_loop(self) -> None:
        """Resource monitoring loop."""
        import psutil
        import os
        
        try:
            process = psutil.Process(os.getpid())
            
            while self._monitoring:
                try:
                    # Check memory usage
                    if self.limits.max_memory:
                        memory_info = process.memory_info()
                        if memory_info.rss > self.limits.max_memory:
                            violation = (
                                f"Memory limit exceeded: {memory_info.rss} > {self.limits.max_memory}"
                            )
                            if violation not in self._violations:
                                self._violations.append(violation)
                                self._logger.warning(f"Plugin {self.plugin_name}: {violation}")
                    
                    # Check CPU time
                    if self.limits.max_cpu_time:
                        cpu_times = process.cpu_times()
                        total_cpu_time = cpu_times.user + cpu_times.system
                        if total_cpu_time > self.limits.max_cpu_time:
                            violation = (
                                f"CPU time limit exceeded: {total_cpu_time} > {self.limits.max_cpu_time}"
                            )
                            if violation not in self._violations:
                                self._violations.append(violation)
                                self._logger.warning(f"Plugin {self.plugin_name}: {violation}")
                    
                    # Check thread count
                    if self.limits.max_threads:
                        thread_count = process.num_threads()
                        if thread_count > self.limits.max_threads:
                            violation = (
                                f"Thread limit exceeded: {thread_count} > {self.limits.max_threads}"
                            )
                            if violation not in self._violations:
                                self._violations.append(violation)
                                self._logger.warning(f"Plugin {self.plugin_name}: {violation}")
                    
                    time.sleep(1.0)  # Check every second
                    
                except psutil.NoSuchProcess:
                    # Process ended
                    break
                except Exception as e:
                    self._logger.error(f"Error in resource monitor for {self.plugin_name}: {e}")
                    time.sleep(1.0)
                    
        except ImportError:
            self._logger.warning(
                "psutil not available for resource monitoring. "
                "Install with: pip install psutil"
            )
        except Exception as e:
            self._logger.error(f"Failed to start resource monitoring: {e}")


# Predefined security policies

UNRESTRICTED_POLICY = SecurityPolicy(
    security_level=SecurityLevel.UNRESTRICTED,
    allow_network_access=True,
    allow_file_system_access=True,
    allow_subprocess_execution=True,
    allow_native_code=True,
    allow_eval_exec=True,
)

STRICT_POLICY = SecurityPolicy(
    security_level=SecurityLevel.STRICT,
    resource_limits=ResourceLimits(
        max_memory=50 * 1024 * 1024,  # 50MB
        max_cpu_time=10.0,            # 10 seconds
        max_file_descriptors=10,
        execution_timeout=30.0,       # 30 seconds
    ),
    allow_network_access=False,
    allow_file_system_access=False,
    allow_subprocess_execution=False,
    allow_native_code=False,
    allow_eval_exec=False,
    read_only_mode=True,
    audit_all_operations=True,
)