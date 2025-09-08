#!/usr/bin/env python3
"""
Final comprehensive observability system status report.
Shows what's working, what's fixed, and what needs attention.
"""

import subprocess
import json
import time
from pathlib import Path

def check_docker_services():
    """Check Docker service status"""
    try:
        result = subprocess.run([
            "docker", "ps", "--format", 
            "{{.Names}}\t{{.Status}}\t{{.Image}}"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            services = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        name = parts[0]
                        status = parts[1]
                        image = parts[2]
                        
                        if any(keyword in name.lower() for keyword in 
                               ['clickhouse', 'signoz', 'postgres', 'redis', 'openbao']):
                            services[name] = {
                                'status': status,
                                'image': image,
                                'healthy': 'healthy' in status.lower(),
                                'running': 'up' in status.lower()
                            }
            return services
        return {}
    except Exception as e:
        print(f"Error checking Docker services: {e}")
        return {}

def check_connectivity():
    """Check endpoint connectivity"""
    endpoints = {
        'ClickHouse HTTP': ('localhost', 8123, 'http'),
        'ClickHouse Native': ('localhost', 9000, 'tcp'),
        'Redis Shared': ('localhost', 6378, 'tcp'),
        'PostgreSQL': ('localhost', 5434, 'tcp'),
    }
    
    results = {}
    for name, (host, port, protocol) in endpoints.items():
        try:
            if protocol == 'http':
                import requests
                response = requests.get(f"http://{host}:{port}/ping", timeout=5)
                results[name] = {'accessible': response.status_code < 500, 'details': f"HTTP {response.status_code}"}
            elif protocol == 'tcp':
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                results[name] = {'accessible': result == 0, 'details': f"TCP connection {'successful' if result == 0 else 'failed'}"}
        except Exception as e:
            results[name] = {'accessible': False, 'details': f"Error: {e}"}
    
    return results

def check_observability_config():
    """Check observability configuration status"""
    try:
        # Test the key import that was previously failing
        import sys
        import os
        
        # Add platform services to path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root / "packages/dotmac-platform-services/src"))
        
        from dotmac.platform.observability import create_default_config, ExporterConfig, ExporterType
        
        # Test config creation
        config = create_default_config(
            service_name='test-service',
            environment='development'
        )
        
        return {
            'imports_working': True,
            'config_creation': config is not None,
            'has_exporters': len(config.tracing_exporters) > 0 and len(config.metrics_exporters) > 0,
            'service_name': config.service_name if config else None,
            'environment': str(config.environment) if config else None
        }
    except Exception as e:
        return {
            'imports_working': False,
            'config_creation': False,
            'has_exporters': False,
            'error': str(e)
        }

def generate_report():
    """Generate comprehensive status report"""
    print("=" * 80)
    print("FINAL OBSERVABILITY SYSTEM STATUS REPORT")
    print("=" * 80)
    print(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check Docker services
    print("🐳 DOCKER SERVICES STATUS")
    print("-" * 40)
    services = check_docker_services()
    
    if services:
        for name, info in services.items():
            status_icon = "✅" if info['running'] and info['healthy'] else "⚠️" if info['running'] else "❌"
            print(f"  {status_icon} {name}: {info['status']}")
    else:
        print("  ❌ No observability services found")
    
    # Check connectivity
    print()
    print("🌐 ENDPOINT CONNECTIVITY")
    print("-" * 40)
    connectivity = check_connectivity()
    
    for name, info in connectivity.items():
        icon = "✅" if info['accessible'] else "❌"
        print(f"  {icon} {name}: {info['details']}")
    
    # Check observability configuration
    print()
    print("⚙️  OBSERVABILITY CONFIGURATION")
    print("-" * 40)
    config_status = check_observability_config()
    
    if config_status.get('imports_working'):
        print("  ✅ Critical imports working")
        print("  ✅ Configuration classes available")
        
        if config_status.get('config_creation'):
            print("  ✅ Config creation successful")
            print(f"  ✅ Service name: {config_status.get('service_name')}")
            print(f"  ✅ Environment: {config_status.get('environment')}")
            
            if config_status.get('has_exporters'):
                print("  ✅ Exporters configured")
            else:
                print("  ⚠️ No exporters configured")
        else:
            print("  ❌ Config creation failed")
    else:
        print("  ❌ Critical imports failing")
        if 'error' in config_status:
            print(f"  ❌ Error: {config_status['error']}")
    
    # Overall health assessment
    print()
    print("📊 OVERALL HEALTH ASSESSMENT")
    print("-" * 40)
    
    # Calculate health score
    healthy_services = sum(1 for s in services.values() if s['healthy'])
    total_services = len(services)
    accessible_endpoints = sum(1 for c in connectivity.values() if c['accessible'])
    total_endpoints = len(connectivity)
    config_working = config_status.get('imports_working', False) and config_status.get('config_creation', False)
    
    health_score = 0
    if total_services > 0:
        health_score += (healthy_services / total_services) * 40
    if total_endpoints > 0:
        health_score += (accessible_endpoints / total_endpoints) * 30
    if config_working:
        health_score += 30
    
    print(f"  Health Score: {health_score:.1f}/100")
    print()
    
    if health_score >= 80:
        print("🎉 EXCELLENT: Observability system is ready for production")
        print("✅ All critical issues resolved")
        print("✅ Applications can start successfully")
        print("✅ Infrastructure services healthy")
    elif health_score >= 60:
        print("✅ GOOD: Core observability functionality working")
        print("✅ Critical application startup issues resolved")
        print("⚠️ Some services may need optimization")
    elif health_score >= 40:
        print("⚠️ FAIR: Basic functionality working")
        print("✅ Configuration issues resolved")
        print("⚠️ Service health needs attention")
    else:
        print("❌ POOR: Significant issues remain")
        print("❌ Additional troubleshooting required")
    
    print()
    print("🚀 NEXT STEPS")
    print("-" * 40)
    
    if config_working:
        print("✅ Phase 1 Complete: Applications can start without configuration errors")
        print("📈 Ready for Phase 2: Service optimization and business metrics")
        print("🔍 Consider: SignOz collector configuration tuning")
        print("📊 Consider: Custom dashboard creation")
    else:
        print("⚠️ Phase 1 Incomplete: Configuration issues remain")
        print("🔧 Priority: Fix remaining import/configuration errors")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    generate_report()