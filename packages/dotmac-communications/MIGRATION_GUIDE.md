# DotMac Communications Migration Guide

This guide helps you migrate from the separate `dotmac-notifications`, `dotmac-websockets`, and `dotmac-events` packages to the unified `dotmac-communications` package.

## Overview

The DotMac Communications package consolidates three previously separate packages into a single, cohesive communication system:

- `dotmac-notifications` → `dotmac.communications.notifications`
- `dotmac-websockets` → `dotmac.communications.websockets`
- `dotmac-events` → `dotmac.communications.events`

## Quick Migration

### 1. Update Dependencies

**Before:**
```toml
[tool.poetry.dependencies]
dotmac-notifications = "^1.0.0"
dotmac-websockets = "^1.0.0" 
dotmac-events = "^1.0.0"
```

**After:**
```toml
[tool.poetry.dependencies]
dotmac-communications = "^1.0.0"
```

### 2. Update Imports

**Before:**
```python
from dotmac.notifications import UnifiedNotificationService
from dotmac.websockets import WebSocketGateway
from dotmac.events import EventBus, create_memory_bus
```

**After:**
```python
from dotmac.communications.notifications import UnifiedNotificationService
from dotmac.communications.websockets import WebSocketGateway  
from dotmac.communications.events import EventBus
from dotmac.communications.events.adapters import create_memory_bus
```

**Or use the unified interface:**
```python
from dotmac.communications import create_communications_service

# Get all services in one place
comm = create_communications_service()
notifications = comm.notifications
websockets = comm.websockets
events = comm.events
```

## Detailed Migration

### Notifications Migration

**Before:**
```python
from dotmac.notifications import (
    UnifiedNotificationService,
    NotificationRequest,
    NotificationTemplate
)

# Initialize service
service = UnifiedNotificationService()

# Send notification
request = NotificationRequest(
    recipient="user@example.com",
    message="Welcome!",
    notification_type="email"
)
await service.send(request)
```

**After:**
```python
from dotmac.communications.notifications import (
    UnifiedNotificationService,
    NotificationRequest, 
    NotificationTemplate
)

# Same API - no changes needed to your code!
service = UnifiedNotificationService()
request = NotificationRequest(
    recipient="user@example.com", 
    message="Welcome!",
    notification_type="email"
)
await service.send(request)
```

**Or use the unified service:**
```python
from dotmac.communications import create_communications_service

comm = create_communications_service()
# Access through unified interface
await comm.notifications.send(request)
```

### WebSockets Migration

**Before:**
```python
from dotmac.websockets import (
    WebSocketGateway,
    ChannelManager,
    BroadcastManager
)

gateway = WebSocketGateway()
channel_manager = ChannelManager()
```

**After:**
```python
from dotmac.communications.websockets import (
    WebSocketGateway,
    ChannelManager, 
    BroadcastManager
)

# Same API - no changes needed!
gateway = WebSocketGateway()
channel_manager = ChannelManager()
```

### Events Migration

**Before:**
```python
from dotmac.events import (
    create_memory_bus,
    EventBus,
    Event
)

bus = create_memory_bus()
event = Event(topic="user.created", payload={"user_id": 123})
await bus.publish(event)
```

**After:**
```python
from dotmac.communications.events.adapters import create_memory_bus
from dotmac.communications.events import Event

bus = create_memory_bus()
event = Event(topic="user.created", payload={"user_id": 123})
await bus.publish(event)
```

## Configuration Migration

### Before: Separate Configs

```python
# notifications_config.py
NOTIFICATION_CONFIG = {
    "retry_attempts": 3,
    "delivery_timeout": 300
}

# websockets_config.py  
WEBSOCKET_CONFIG = {
    "connection_timeout": 60,
    "heartbeat_interval": 30
}

# events_config.py
EVENTS_CONFIG = {
    "default_adapter": "redis",
    "max_retries": 5
}
```

### After: Unified Config

```python
# communications_config.py
COMMUNICATIONS_CONFIG = {
    "notifications": {
        "retry_attempts": 3,
        "delivery_timeout": 300
    },
    "websockets": {
        "connection_timeout": 60, 
        "heartbeat_interval": 30
    },
    "events": {
        "default_adapter": "redis",
        "max_retries": 5
    }
}

# Use with service
from dotmac.communications import create_communications_service
comm = create_communications_service(COMMUNICATIONS_CONFIG)
```

## Advanced Migration Patterns

### Pattern 1: Gradual Migration

You can migrate gradually by keeping old imports and slowly moving to new ones:

```python
# Phase 1: Keep existing imports, add unified service
from dotmac.notifications import UnifiedNotificationService  # Old
from dotmac.communications import create_communications_service  # New

# Phase 2: Start using unified service for new features  
comm = create_communications_service()
new_feature_notifications = comm.notifications

# Phase 3: Migrate existing code to new imports
from dotmac.communications.notifications import UnifiedNotificationService
```

### Pattern 2: Service Factory Pattern

**Before:**
```python
class MyService:
    def __init__(self):
        self.notifications = UnifiedNotificationService()
        self.websockets = WebSocketGateway()
        self.events = create_memory_bus()
```

**After:**
```python
class MyService:
    def __init__(self):
        self.comm = create_communications_service()
    
    @property
    def notifications(self):
        return self.comm.notifications
        
    @property  
    def websockets(self):
        return self.comm.websockets
        
    @property
    def events(self):
        return self.comm.events
```

### Pattern 3: Dependency Injection

**Before:**
```python
def create_app(notification_service, websocket_manager, event_bus):
    # App setup
    pass

app = create_app(
    UnifiedNotificationService(),
    WebSocketGateway(), 
    create_memory_bus()
)
```

**After:**
```python
def create_app(communications_service):
    # App setup - access all services through communications_service
    pass

from dotmac.communications import create_communications_service
app = create_app(create_communications_service())
```

## Breaking Changes

### None!

The unified package maintains full backward compatibility with all existing APIs. The only changes are:

1. **Import paths** - updated to use new module structure
2. **Package dependencies** - consolidate to single package
3. **Configuration structure** - unified but backward compatible

## Testing Your Migration

### 1. Run Import Tests

```python
# test_migration.py
def test_notifications_import():
    from dotmac.communications.notifications import UnifiedNotificationService
    assert UnifiedNotificationService is not None

def test_websockets_import():
    from dotmac.communications.websockets import WebSocketGateway
    assert WebSocketGateway is not None
    
def test_events_import():
    from dotmac.communications.events.adapters import create_memory_bus
    assert create_memory_bus is not None

def test_unified_service():
    from dotmac.communications import create_communications_service
    comm = create_communications_service()
    assert comm.notifications is not None
    assert comm.websockets is not None  
    assert comm.events is not None
```

### 2. Run Integration Tests

```bash
# Install the new package
poetry add dotmac-communications

# Remove old packages
poetry remove dotmac-notifications dotmac-websockets dotmac-events

# Run your existing tests
poetry run pytest

# Run migration validation
poetry run python -c "
from dotmac.communications import create_communications_service
comm = create_communications_service()
print('✅ Migration successful!')
"
```

## Troubleshooting

### Common Issues

**Issue 1: Import errors after migration**
```python
# Error: ModuleNotFoundError: No module named 'dotmac.notifications'
# Solution: Update imports to new paths
from dotmac.communications.notifications import UnifiedNotificationService
```

**Issue 2: Configuration not working**
```python
# Old config structure might not work
# Solution: Update to nested config structure
config = {
    "notifications": {"retry_attempts": 3},
    "websockets": {"connection_timeout": 60}, 
    "events": {"max_retries": 5}
}
```

**Issue 3: Service initialization errors**
```python
# Some services might need different initialization
# Solution: Use factory functions
from dotmac.communications import create_notification_service
service = create_notification_service()
```

### Getting Help

1. **Documentation**: Check the updated API documentation
2. **Tests**: Look at the test files for usage examples
3. **Issues**: Report migration issues on GitHub
4. **Examples**: Check the examples directory for patterns

## Rollback Plan

If you need to rollback the migration:

1. **Restore old dependencies**:
   ```toml
   dotmac-notifications = "^1.0.0"
   dotmac-websockets = "^1.0.0"
   dotmac-events = "^1.0.0"
   ```

2. **Revert import changes**:
   ```python
   # Change back to old imports
   from dotmac.notifications import UnifiedNotificationService
   from dotmac.websockets import WebSocketGateway
   from dotmac.events import create_memory_bus
   ```

3. **Update configuration** back to separate config files

The old packages remain available and functional for backward compatibility.

## Benefits After Migration

✅ **Simplified Dependencies**: One package instead of three
✅ **Unified Configuration**: Single config for all communication  
✅ **Better Integration**: Components work together seamlessly
✅ **Improved Performance**: Shared resources and connection pooling
✅ **Enhanced Developer Experience**: Consistent APIs and documentation
✅ **Future-Proof**: Better positioned for new features and updates