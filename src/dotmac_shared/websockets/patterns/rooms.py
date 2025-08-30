"""
Advanced Room Management System

Sophisticated room-based messaging with hierarchical rooms, permissions,
moderation capabilities, and advanced routing patterns.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..core.events import EventPriority, WebSocketEvent

logger = logging.getLogger(__name__)


class RoomType(str, Enum):
    """Room types with different behavior."""

    PUBLIC = "public"  # Anyone can join
    PRIVATE = "private"  # Invitation only
    PROTECTED = "protected"  # Password required
    TEMPORARY = "temporary"  # Auto-delete when empty
    PERSISTENT = "persistent"  # Never auto-delete


class MemberRole(str, Enum):
    """Member roles within rooms."""

    OWNER = "owner"  # Full control
    ADMIN = "admin"  # Can moderate and manage
    MODERATOR = "moderator"  # Can moderate messages
    MEMBER = "member"  # Regular participant
    GUEST = "guest"  # Limited access
    MUTED = "muted"  # Cannot send messages


@dataclass
class RoomMember:
    """Room member information."""

    connection_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    role: MemberRole = MemberRole.MEMBER
    joined_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Room:
    """Room configuration and state."""

    room_id: str
    name: str
    room_type: RoomType = RoomType.PUBLIC
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None

    # Room settings
    max_members: int = 1000
    password: Optional[str] = None
    description: Optional[str] = None
    tags: Set[str] = field(default_factory=set)

    # Room state
    members: Dict[str, RoomMember] = field(default_factory=dict)
    message_count: int = 0
    last_activity: datetime = field(default_factory=datetime.utcnow)

    # Room configuration
    settings: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[MemberRole, Set[str]] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default permissions."""
        if not self.permissions:
            self.permissions = {
                MemberRole.OWNER: {
                    "send_messages",
                    "delete_messages",
                    "kick_members",
                    "ban_members",
                    "change_settings",
                    "delete_room",
                },
                MemberRole.ADMIN: {
                    "send_messages",
                    "delete_messages",
                    "kick_members",
                    "ban_members",
                    "change_settings",
                },
                MemberRole.MODERATOR: {
                    "send_messages",
                    "delete_messages",
                    "kick_members",
                },
                MemberRole.MEMBER: {"send_messages"},
                MemberRole.GUEST: {"send_messages"},
                MemberRole.MUTED: set(),
            }


class RoomManager:
    """
    Advanced room management system for WebSocket connections.

    Features:
    - Hierarchical room structure
    - Role-based permissions
    - Room moderation and security
    - Temporary and persistent rooms
    - Room statistics and analytics
    - Custom room events and hooks
    """

    def __init__(self, websocket_manager, event_manager, config=None):
        self.websocket_manager = websocket_manager
        self.event_manager = event_manager
        self.config = config or {}

        # Room storage
        self.rooms: Dict[str, Room] = {}
        self.room_hierarchies: Dict[str, Set[str]] = {}  # parent -> children

        # User mappings
        self.user_rooms: Dict[str, Set[str]] = {}  # user_id -> room_ids
        self.tenant_rooms: Dict[str, Set[str]] = {}  # tenant_id -> room_ids

        # Security and moderation
        self.banned_users: Dict[str, Set[str]] = {}  # room_id -> banned_user_ids
        self.room_passwords: Dict[str, str] = {}  # room_id -> password

        # Metrics
        self.metrics = {
            "rooms_created": 0,
            "rooms_deleted": 0,
            "members_joined": 0,
            "members_left": 0,
            "messages_sent": 0,
            "moderation_actions": 0,
        }

        # Event hooks
        self.room_hooks: Dict[str, List[Callable]] = {
            "room_created": [],
            "room_deleted": [],
            "member_joined": [],
            "member_left": [],
            "member_promoted": [],
            "member_demoted": [],
            "message_sent": [],
        }

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        """Start the room manager."""
        if self._is_running:
            return

        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_rooms())
        logger.info("Room manager started")

    async def stop(self):
        """Stop the room manager."""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Room manager stopped")

    async def create_room(
        self,
        room_id: str,
        name: str,
        room_type: RoomType = RoomType.PUBLIC,
        creator_connection_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        max_members: int = 1000,
        password: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        parent_room_id: Optional[str] = None,
    ) -> Room:
        """
        Create a new room.

        Args:
            room_id: Unique room identifier
            name: Human-readable room name
            room_type: Type of room (public, private, etc.)
            creator_connection_id: Connection ID of room creator
            tenant_id: Tenant identifier for isolation
            max_members: Maximum number of members
            password: Room password (for protected rooms)
            description: Room description
            settings: Additional room settings
            parent_room_id: Parent room for hierarchical structure

        Returns:
            Created Room object

        Raises:
            ValueError: If room already exists or invalid parameters
        """
        if room_id in self.rooms:
            raise ValueError(f"Room {room_id} already exists")

        # Get creator info
        creator_user_id = None
        if creator_connection_id:
            conn_info = self.websocket_manager.get_connection_info(
                creator_connection_id
            )
            if conn_info:
                creator_user_id = conn_info.user_id
                if not tenant_id and conn_info.tenant_id:
                    tenant_id = conn_info.tenant_id

        # Create room
        room = Room(
            room_id=room_id,
            name=name,
            room_type=room_type,
            tenant_id=tenant_id,
            created_by=creator_user_id,
            max_members=max_members,
            password=password,
            description=description,
            settings=settings or {},
        )

        # Store room
        self.rooms[room_id] = room

        # Update tenant mapping
        if tenant_id:
            if tenant_id not in self.tenant_rooms:
                self.tenant_rooms[tenant_id] = set()
            self.tenant_rooms[tenant_id].add(room_id)

        # Handle hierarchy
        if parent_room_id and parent_room_id in self.rooms:
            if parent_room_id not in self.room_hierarchies:
                self.room_hierarchies[parent_room_id] = set()
            self.room_hierarchies[parent_room_id].add(room_id)

        # Add creator as owner
        if creator_connection_id:
            await self.join_room(creator_connection_id, room_id, role=MemberRole.OWNER)

        # Update metrics
        self.metrics["rooms_created"] += 1

        # Call hooks
        await self._call_room_hooks("room_created", room, creator_connection_id)

        # Publish event
        if self.event_manager:
            event = WebSocketEvent(
                event_type="room_created",
                data={
                    "room_id": room_id,
                    "name": name,
                    "type": room_type.value,
                    "created_by": creator_user_id,
                },
                tenant_id=tenant_id,
                priority=EventPriority.NORMAL,
            )
            await self.event_manager.publish_event(event)

        logger.info(f"Room created: {room_id} ({name}) by {creator_user_id}")
        return room

    async def delete_room(
        self, room_id: str, deleter_connection_id: Optional[str] = None
    ) -> bool:
        """
        Delete a room and remove all members.

        Args:
            room_id: Room identifier
            deleter_connection_id: Connection requesting deletion

        Returns:
            True if room was deleted
        """
        room = self.rooms.get(room_id)
        if not room:
            return False

        # Check permissions
        if deleter_connection_id:
            member = room.members.get(deleter_connection_id)
            if not member or not self._has_permission(member.role, "delete_room"):
                logger.warning(f"Insufficient permissions to delete room {room_id}")
                return False

        # Notify all members
        if self.event_manager:
            event = WebSocketEvent(
                event_type="room_deleted",
                data={"room_id": room_id, "name": room.name},
                room=room_id,
                tenant_id=room.tenant_id,
                priority=EventPriority.HIGH,
            )
            await self.event_manager.publish_event(event)

        # Remove all members from WebSocket rooms
        for connection_id in list(room.members.keys()):
            await self.websocket_manager.leave_room(connection_id, room_id)

        # Clean up mappings
        for user_id in [m.user_id for m in room.members.values() if m.user_id]:
            if user_id in self.user_rooms:
                self.user_rooms[user_id].discard(room_id)
                if not self.user_rooms[user_id]:
                    del self.user_rooms[user_id]

        if room.tenant_id and room.tenant_id in self.tenant_rooms:
            self.tenant_rooms[room.tenant_id].discard(room_id)
            if not self.tenant_rooms[room.tenant_id]:
                del self.tenant_rooms[room.tenant_id]

        # Clean up hierarchy
        for parent_id, children in list(self.room_hierarchies.items()):
            children.discard(room_id)
            if not children:
                del self.room_hierarchies[parent_id]

        if room_id in self.room_hierarchies:
            del self.room_hierarchies[room_id]

        # Clean up security data
        self.banned_users.pop(room_id, None)
        self.room_passwords.pop(room_id, None)

        # Remove room
        del self.rooms[room_id]

        # Update metrics
        self.metrics["rooms_deleted"] += 1

        # Call hooks
        await self._call_room_hooks("room_deleted", room, deleter_connection_id)

        logger.info(f"Room deleted: {room_id}")
        return True

    async def join_room(
        self,
        connection_id: str,
        room_id: str,
        password: Optional[str] = None,
        role: MemberRole = MemberRole.MEMBER,
    ) -> bool:
        """
        Add connection to a room.

        Args:
            connection_id: WebSocket connection ID
            room_id: Room identifier
            password: Room password (for protected rooms)
            role: Member role (for initial assignment)

        Returns:
            True if joined successfully
        """
        # Get connection info
        conn_info = self.websocket_manager.get_connection_info(connection_id)
        if not conn_info:
            logger.warning(f"Connection not found: {connection_id}")
            return False

        # Get room
        room = self.rooms.get(room_id)
        if not room:
            logger.warning(f"Room not found: {room_id}")
            return False

        # Check if already in room
        if connection_id in room.members:
            logger.debug(f"Connection {connection_id} already in room {room_id}")
            return True

        # Check capacity
        if len(room.members) >= room.max_members:
            logger.warning(f"Room {room_id} at capacity ({room.max_members})")
            return False

        # Check bans
        if (
            room_id in self.banned_users
            and conn_info.user_id in self.banned_users[room_id]
        ):
            logger.warning(f"User {conn_info.user_id} banned from room {room_id}")
            return False

        # Tenant isolation check
        if room.tenant_id and conn_info.tenant_id != room.tenant_id:
            logger.warning(f"Tenant isolation violation: {connection_id} -> {room_id}")
            return False

        # Room type checks
        if room.room_type == RoomType.PRIVATE:
            # Private rooms require invitation (handled by role assignment)
            if role == MemberRole.MEMBER:
                logger.warning(f"Private room {room_id} requires invitation")
                return False

        elif room.room_type == RoomType.PROTECTED:
            # Protected rooms require password
            if room.password and password != room.password:
                logger.warning(f"Invalid password for room {room_id}")
                return False

        # Create member
        member = RoomMember(
            connection_id=connection_id,
            user_id=conn_info.user_id,
            tenant_id=conn_info.tenant_id,
            role=role,
            metadata=conn_info.metadata.copy(),
        )

        # Add to room
        room.members[connection_id] = member
        room.last_activity = datetime.utcnow()

        # Add to WebSocket room
        await self.websocket_manager.join_room(connection_id, room_id)

        # Update user mapping
        if conn_info.user_id:
            if conn_info.user_id not in self.user_rooms:
                self.user_rooms[conn_info.user_id] = set()
            self.user_rooms[conn_info.user_id].add(room_id)

        # Update metrics
        self.metrics["members_joined"] += 1

        # Notify room members
        if self.event_manager:
            event = WebSocketEvent(
                event_type="member_joined",
                data={
                    "room_id": room_id,
                    "user_id": conn_info.user_id,
                    "role": role.value,
                    "member_count": len(room.members),
                },
                room=room_id,
                tenant_id=room.tenant_id,
                priority=EventPriority.NORMAL,
            )
            await self.event_manager.publish_event(event)

        # Call hooks
        await self._call_room_hooks("member_joined", room, connection_id, member)

        logger.info(f"Member joined room: {connection_id} -> {room_id} ({role.value})")
        return True

    async def leave_room(self, connection_id: str, room_id: str) -> bool:
        """
        Remove connection from a room.

        Args:
            connection_id: WebSocket connection ID
            room_id: Room identifier

        Returns:
            True if left successfully
        """
        room = self.rooms.get(room_id)
        if not room or connection_id not in room.members:
            return False

        member = room.members[connection_id]

        # Remove from room
        del room.members[connection_id]
        room.last_activity = datetime.utcnow()

        # Remove from WebSocket room
        await self.websocket_manager.leave_room(connection_id, room_id)

        # Update user mapping
        if member.user_id and member.user_id in self.user_rooms:
            self.user_rooms[member.user_id].discard(room_id)
            if not self.user_rooms[member.user_id]:
                del self.user_rooms[member.user_id]

        # Update metrics
        self.metrics["members_left"] += 1

        # Check if room should be deleted (temporary rooms)
        if (
            room.room_type == RoomType.TEMPORARY
            and not room.members
            and self.config.get("auto_delete_empty_rooms", True)
        ):
            await self.delete_room(room_id)
            return True

        # Notify room members
        if self.event_manager:
            event = WebSocketEvent(
                event_type="member_left",
                data={
                    "room_id": room_id,
                    "user_id": member.user_id,
                    "member_count": len(room.members),
                },
                room=room_id,
                tenant_id=room.tenant_id,
                priority=EventPriority.NORMAL,
            )
            await self.event_manager.publish_event(event)

        # Call hooks
        await self._call_room_hooks("member_left", room, connection_id, member)

        logger.info(f"Member left room: {connection_id} <- {room_id}")
        return True

    async def send_room_message(
        self, connection_id: str, room_id: str, message: Dict[str, Any]
    ) -> bool:
        """
        Send message to room with permission checking.

        Args:
            connection_id: Sender connection ID
            room_id: Target room ID
            message: Message data

        Returns:
            True if message sent successfully
        """
        room = self.rooms.get(room_id)
        if not room:
            return False

        member = room.members.get(connection_id)
        if not member:
            logger.warning(f"Connection {connection_id} not in room {room_id}")
            return False

        # Check permissions
        if not self._has_permission(member.role, "send_messages"):
            logger.warning(f"Member {connection_id} cannot send messages in {room_id}")
            return False

        # Update activity
        member.last_activity = datetime.utcnow()
        room.last_activity = datetime.utcnow()
        room.message_count += 1

        # Create message event
        message_event = WebSocketEvent(
            event_type="room_message",
            data={
                "room_id": room_id,
                "sender_id": member.user_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=room_id,
            tenant_id=room.tenant_id,
            user_id=member.user_id,
            priority=EventPriority.NORMAL,
        )

        # Send to room members
        result = await self.event_manager.publish_event(message_event)

        # Update metrics
        if result["delivered"] > 0:
            self.metrics["messages_sent"] += 1

        # Call hooks
        await self._call_room_hooks("message_sent", room, connection_id, message)

        return result["delivered"] > 0

    async def change_member_role(
        self,
        changer_connection_id: str,
        target_connection_id: str,
        room_id: str,
        new_role: MemberRole,
    ) -> bool:
        """
        Change a member's role in a room.

        Args:
            changer_connection_id: Connection requesting the change
            target_connection_id: Target member connection
            room_id: Room identifier
            new_role: New role to assign

        Returns:
            True if role changed successfully
        """
        room = self.rooms.get(room_id)
        if not room:
            return False

        changer = room.members.get(changer_connection_id)
        target = room.members.get(target_connection_id)

        if not changer or not target:
            return False

        # Permission check (owners and admins can change roles)
        if changer.role not in [MemberRole.OWNER, MemberRole.ADMIN]:
            logger.warning(f"Insufficient permissions for role change in {room_id}")
            return False

        # Cannot change owner role or promote to owner
        if target.role == MemberRole.OWNER or new_role == MemberRole.OWNER:
            if changer.role != MemberRole.OWNER:
                logger.warning(f"Cannot change owner role in {room_id}")
                return False

        old_role = target.role
        target.role = new_role

        # Update metrics
        self.metrics["moderation_actions"] += 1

        # Notify room
        if self.event_manager:
            event = WebSocketEvent(
                event_type="member_role_changed",
                data={
                    "room_id": room_id,
                    "user_id": target.user_id,
                    "old_role": old_role.value,
                    "new_role": new_role.value,
                    "changed_by": changer.user_id,
                },
                room=room_id,
                tenant_id=room.tenant_id,
                priority=EventPriority.HIGH,
            )
            await self.event_manager.publish_event(event)

        # Call hooks
        hook_name = (
            "member_promoted" if new_role.value > old_role.value else "member_demoted"
        )
        await self._call_room_hooks(hook_name, room, target_connection_id, target)

        logger.info(
            f"Role changed in {room_id}: {target.user_id} {old_role.value} -> {new_role.value}"
        )
        return True

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID."""
        return self.rooms.get(room_id)

    def get_user_rooms(self, user_id: str) -> Set[str]:
        """Get all rooms a user is in."""
        return self.user_rooms.get(user_id, set()).copy()

    def get_tenant_rooms(self, tenant_id: str) -> Set[str]:
        """Get all rooms for a tenant."""
        return self.tenant_rooms.get(tenant_id, set()).copy()

    def get_room_stats(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get room statistics."""
        room = self.rooms.get(room_id)
        if not room:
            return None

        return {
            "room_id": room_id,
            "name": room.name,
            "type": room.room_type.value,
            "member_count": len(room.members),
            "max_members": room.max_members,
            "message_count": room.message_count,
            "created_at": room.created_at.isoformat(),
            "last_activity": room.last_activity.isoformat(),
            "is_active": (datetime.utcnow() - room.last_activity).seconds < 3600,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get room manager metrics."""
        return {
            **self.metrics,
            "active_rooms": len(self.rooms),
            "total_members": sum(len(room.members) for room in self.rooms.values()),
        }

    # Hook management
    def add_room_hook(self, event_type: str, hook: Callable):
        """Add room event hook."""
        if event_type in self.room_hooks:
            self.room_hooks[event_type].append(hook)

    def remove_room_hook(self, event_type: str, hook: Callable):
        """Remove room event hook."""
        if event_type in self.room_hooks:
            try:
                self.room_hooks[event_type].remove(hook)
            except ValueError:
                pass

    # Private methods
    def _has_permission(self, role: MemberRole, permission: str) -> bool:
        """Check if role has permission."""
        # Default permissions are set in Room.__post_init__
        return permission in {
            MemberRole.OWNER: {
                "send_messages",
                "delete_messages",
                "kick_members",
                "ban_members",
                "change_settings",
                "delete_room",
            },
            MemberRole.ADMIN: {
                "send_messages",
                "delete_messages",
                "kick_members",
                "ban_members",
                "change_settings",
            },
            MemberRole.MODERATOR: {"send_messages", "delete_messages", "kick_members"},
            MemberRole.MEMBER: {"send_messages"},
            MemberRole.GUEST: {"send_messages"},
            MemberRole.MUTED: set(),
        }.get(role, set())

    async def _call_room_hooks(
        self, event_type: str, room: Room, connection_id: str = None, *args
    ):
        """Call room event hooks."""
        hooks = self.room_hooks.get(event_type, [])
        if not hooks:
            return

        # Call hooks concurrently
        hook_tasks = []
        for hook in hooks:
            try:
                task = hook(event_type, room, connection_id, *args)
                if asyncio.iscoroutine(task):
                    hook_tasks.append(task)
            except Exception as e:
                logger.error(f"Error calling room hook: {e}")

        if hook_tasks:
            await asyncio.gather(*hook_tasks, return_exceptions=True)

    async def _cleanup_inactive_rooms(self):
        """Background task to cleanup inactive temporary rooms."""
        while self._is_running:
            try:
                inactive_threshold = datetime.utcnow() - timedelta(
                    hours=self.config.get("inactive_room_hours", 24)
                )

                rooms_to_delete = []
                for room_id, room in self.rooms.items():
                    if (
                        room.room_type == RoomType.TEMPORARY
                        and not room.members
                        and room.last_activity < inactive_threshold
                    ):
                        rooms_to_delete.append(room_id)

                # Delete inactive rooms
                for room_id in rooms_to_delete:
                    await self.delete_room(room_id)

                if rooms_to_delete:
                    logger.info(f"Cleaned up {len(rooms_to_delete)} inactive rooms")

                await asyncio.sleep(3600)  # Check every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Room cleanup error: {e}")
                await asyncio.sleep(600)  # Error backoff
