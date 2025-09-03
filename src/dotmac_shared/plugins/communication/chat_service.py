"""
Chat Service - Business Logic for Live Chat System
Leverages existing DotMac service patterns and integrations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, asc, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .live_chat_plugin import (
    AgentStatus, ChatMessage, ChatSession, ChatStatus, MessageType,
    ChatSessionCreate, ChatSessionResponse, ChatMessageCreate, ChatMessageResponse,
    AgentStatusUpdate
)
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.ticketing.core.models import Ticket, TicketCreate, TicketCategory, TicketPriority, TicketSource
from dotmac_shared.ticketing.services.ticket_service import TicketService

logger = logging.getLogger(__name__)


class ChatService:
    """Business logic service for live chat system."""
    
    def __init__(self, db_session_factory=None, config: Dict[str, Any] = None):
        """Initialize chat service."""
        self.db_session_factory = db_session_factory
        self.config = config or {}
        
        # Service configuration
        self.max_wait_time_minutes = self.config.get('max_wait_time', 15)
        self.max_session_duration_hours = self.config.get('max_session_duration', 4)
        self.auto_close_after_minutes = self.config.get('auto_close_minutes', 30)
        
        # Integrate with existing ticket system
        self.ticket_service = None  # Will be injected
    
    async def create_session(
        self,
        db: AsyncSession,
        tenant_id: str,
        session_data: ChatSessionCreate,
        customer_id: str = None,
        visitor_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> ChatSessionResponse:
        """Create a new chat session."""
        try:
            # Generate unique session ID
            session_id = f"chat_{int(datetime.now(timezone.utc).timestamp())}_{hash(customer_id or visitor_id or ip_address) % 10000}"
            
            session = ChatSession(
                tenant_id=tenant_id,
                session_id=session_id,
                status=ChatStatus.WAITING,
                customer_id=customer_id,
                customer_name=session_data.customer_name,
                customer_email=session_data.customer_email,
                visitor_id=visitor_id,
                initial_message=session_data.initial_message,
                page_url=session_data.page_url,
                user_agent=user_agent,
                ip_address=ip_address,
                metadata=session_data.metadata
            )
            
            db.add(session)
            await db.commit()
            await db.refresh(session)
            
            logger.info(f"Created chat session {session_id} for tenant {tenant_id}")
            
            # If there's an initial message, save it
            if session_data.initial_message:
                await self.add_message(
                    db=db,
                    session_id=session.id,
                    content=session_data.initial_message,
                    sender_type="customer",
                    sender_id=customer_id,
                    sender_name=session_data.customer_name or "Customer"
                )
            
            # Trigger events for agent assignment
            await self._trigger_session_created_events(session)
            
            return ChatSessionResponse.model_validate(session)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating chat session: {str(e)}")
            raise

    async def get_session(
        self,
        db: AsyncSession,
        tenant_id: str,
        session_id: str
    ) -> Optional[ChatSessionResponse]:
        """Get chat session by ID."""
        query = (
            select(ChatSession)
            .where(and_(
                ChatSession.session_id == session_id,
                ChatSession.tenant_id == tenant_id
            ))
            .options(selectinload(ChatSession.messages))
        )
        
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        response = ChatSessionResponse.model_validate(session)
        response.message_count = len(session.messages)
        
        return response

    async def get_session_messages(
        self,
        db: AsyncSession,
        tenant_id: str,
        session_id: str,
        page: int = 1,
        page_size: int = 50,
        include_internal: bool = False
    ) -> List[ChatMessageResponse]:
        """Get messages for a chat session."""
        try:
            # Get session first to verify access
            session_query = (
                select(ChatSession)
                .where(and_(
                    ChatSession.session_id == session_id,
                    ChatSession.tenant_id == tenant_id
                ))
            )
            
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                return []
            
            # Build messages query
            query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
            )
            
            # Filter internal messages if needed
            if not include_internal:
                query = query.where(ChatMessage.is_internal.is_(False))
            
            # Apply sorting and pagination
            query = query.order_by(asc(ChatMessage.sent_at))
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            return [ChatMessageResponse.model_validate(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"Error getting session messages: {str(e)}")
            return []

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        content: str,
        sender_type: str,
        sender_id: str = None,
        sender_name: str = None,
        message_type: MessageType = MessageType.TEXT,
        is_internal: bool = False,
        file_attachments: List[str] = None
    ) -> Optional[ChatMessageResponse]:
        """Add a message to a chat session."""
        try:
            # Get session to verify it exists and get tenant_id
            session_query = select(ChatSession).where(ChatSession.id == session_id)
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                return None
            
            message = ChatMessage(
                session_id=session_id,
                tenant_id=session.tenant_id,
                content=content,
                message_type=message_type,
                sender_type=sender_type,
                sender_id=sender_id,
                sender_name=sender_name or "Unknown",
                is_internal=is_internal,
                file_attachments=file_attachments or []
            )
            
            db.add(message)
            
            # Update session activity and message count
            session.last_activity = datetime.now(timezone.utc)
            session.message_count = session.message_count + 1
            
            await db.commit()
            await db.refresh(message)
            
            logger.info(f"Added message to session {session_id}")
            
            return ChatMessageResponse.model_validate(message)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            raise

    async def assign_agent(
        self,
        db: AsyncSession,
        session_id: str,
        agent_id: str,
        agent_name: str = None
    ) -> Optional[ChatSessionResponse]:
        """Assign an agent to a chat session."""
        try:
            # Get session
            session_query = select(ChatSession).where(ChatSession.session_id == session_id)
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session or session.status != ChatStatus.WAITING:
                return None
            
            # Update session
            session.assigned_agent_id = agent_id
            session.assigned_agent_name = agent_name or "Agent"
            session.status = ChatStatus.ACTIVE
            session.started_at = datetime.now(timezone.utc)
            
            # Calculate wait time
            if session.created_at:
                wait_time = datetime.now(timezone.utc) - session.created_at
                session.wait_time_seconds = int(wait_time.total_seconds())
            
            # Add system message
            await self.add_message(
                db=db,
                session_id=session.id,
                content=f"{agent_name or 'An agent'} has joined the chat.",
                sender_type="system",
                message_type=MessageType.AGENT_JOIN
            )
            
            await db.commit()
            await db.refresh(session)
            
            logger.info(f"Assigned agent {agent_id} to session {session_id}")
            
            # Update agent status
            await self._update_agent_chat_count(db, agent_id, session.tenant_id, 1)
            
            return ChatSessionResponse.model_validate(session)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error assigning agent to session {session_id}: {str(e)}")
            raise

    async def transfer_session(
        self,
        db: AsyncSession,
        session_id: str,
        from_agent_id: str,
        to_agent_id: str,
        reason: str = None
    ) -> Optional[ChatSessionResponse]:
        """Transfer a chat session between agents."""
        try:
            session_query = select(ChatSession).where(ChatSession.session_id == session_id)
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session or session.assigned_agent_id != from_agent_id:
                return None
            
            # Update session assignment
            old_agent_name = session.assigned_agent_name
            session.assigned_agent_id = to_agent_id
            session.assigned_agent_name = f"Agent {to_agent_id}"  # In production, get from user table
            
            # Add transfer message
            transfer_message = f"Chat transferred from {old_agent_name} to {session.assigned_agent_name}"
            if reason:
                transfer_message += f". Reason: {reason}"
            
            await self.add_message(
                db=db,
                session_id=session.id,
                content=transfer_message,
                sender_type="system",
                message_type=MessageType.SYSTEM
            )
            
            await db.commit()
            await db.refresh(session)
            
            # Update agent chat counts
            await self._update_agent_chat_count(db, from_agent_id, session.tenant_id, -1)
            await self._update_agent_chat_count(db, to_agent_id, session.tenant_id, 1)
            
            logger.info(f"Transferred session {session_id} from {from_agent_id} to {to_agent_id}")
            
            return ChatSessionResponse.model_validate(session)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error transferring session {session_id}: {str(e)}")
            raise

    async def end_session(
        self,
        db: AsyncSession,
        session_id: str,
        agent_id: str = None,
        summary: str = None,
        create_ticket: bool = False
    ) -> Optional[ChatSessionResponse]:
        """End a chat session."""
        try:
            session_query = select(ChatSession).where(ChatSession.session_id == session_id)
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                return None
            
            # Update session
            session.status = ChatStatus.ENDED
            session.ended_at = datetime.now(timezone.utc)
            
            # Calculate session duration
            if session.started_at:
                duration = datetime.now(timezone.utc) - session.started_at
                session.session_duration_seconds = int(duration.total_seconds())
            
            # Add end message
            if agent_id:
                await self.add_message(
                    db=db,
                    session_id=session.id,
                    content="The agent has ended the chat session.",
                    sender_type="system",
                    message_type=MessageType.AGENT_LEAVE
                )
            
            # Create support ticket if requested
            if create_ticket and self.ticket_service:
                await self._create_ticket_from_chat(db, session, summary)
            
            await db.commit()
            await db.refresh(session)
            
            # Update agent status
            if agent_id:
                await self._update_agent_chat_count(db, agent_id, session.tenant_id, -1)
            
            logger.info(f"Ended session {session_id}")
            
            return ChatSessionResponse.model_validate(session)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error ending session {session_id}: {str(e)}")
            raise

    async def rate_session(
        self,
        db: AsyncSession,
        tenant_id: str,
        session_id: str,
        rating: int,
        feedback: str = None
    ) -> bool:
        """Rate a chat session."""
        try:
            session_query = (
                select(ChatSession)
                .where(and_(
                    ChatSession.session_id == session_id,
                    ChatSession.tenant_id == tenant_id
                ))
            )
            
            session_result = await db.execute(session_query)
            session = session_result.scalar_one_or_none()
            
            if not session:
                return False
            
            session.customer_rating = rating
            session.customer_feedback = feedback
            
            await db.commit()
            
            logger.info(f"Rated session {session_id}: {rating}/5")
            
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error rating session {session_id}: {str(e)}")
            return False

    async def get_agent_status(
        self,
        db: AsyncSession,
        agent_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get agent status information."""
        try:
            query = (
                select(AgentStatus)
                .where(and_(
                    AgentStatus.agent_id == agent_id,
                    AgentStatus.tenant_id == tenant_id
                ))
            )
            
            result = await db.execute(query)
            agent_status = result.scalar_one_or_none()
            
            if not agent_status:
                # Create default status
                agent_status = AgentStatus(
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                    status=AgentStatus.OFFLINE
                )
                db.add(agent_status)
                await db.commit()
                await db.refresh(agent_status)
            
            return {
                "agent_id": agent_status.agent_id,
                "status": agent_status.status,
                "status_message": agent_status.status_message,
                "current_chat_count": agent_status.current_chat_count,
                "max_concurrent_chats": agent_status.max_concurrent_chats,
                "last_seen": agent_status.last_seen.isoformat(),
                "is_available": (
                    agent_status.status == AgentStatus.ONLINE and 
                    agent_status.current_chat_count < agent_status.max_concurrent_chats
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting agent status: {str(e)}")
            return {}

    async def update_agent_status(
        self,
        db: AsyncSession,
        agent_id: str,
        tenant_id: str,
        status_data: AgentStatusUpdate
    ) -> Dict[str, Any]:
        """Update agent status."""
        try:
            query = (
                select(AgentStatus)
                .where(and_(
                    AgentStatus.agent_id == agent_id,
                    AgentStatus.tenant_id == tenant_id
                ))
            )
            
            result = await db.execute(query)
            agent_status = result.scalar_one_or_none()
            
            if not agent_status:
                agent_status = AgentStatus(
                    agent_id=agent_id,
                    tenant_id=tenant_id
                )
                db.add(agent_status)
            
            # Update fields
            update_dict = status_data.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(agent_status, field, value)
            
            agent_status.last_seen = datetime.now(timezone.utc)
            agent_status.status_changed_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(agent_status)
            
            logger.info(f"Updated agent {agent_id} status to {agent_status.status}")
            
            return await self.get_agent_status(db, agent_id, tenant_id)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating agent status: {str(e)}")
            raise

    async def get_agent_sessions(
        self,
        db: AsyncSession,
        agent_id: str,
        tenant_id: str,
        status_filter: List[str] = None
    ) -> List[ChatSessionResponse]:
        """Get chat sessions assigned to an agent."""
        try:
            query = (
                select(ChatSession)
                .where(and_(
                    ChatSession.assigned_agent_id == agent_id,
                    ChatSession.tenant_id == tenant_id
                ))
            )
            
            if status_filter:
                query = query.where(ChatSession.status.in_(status_filter))
            
            query = query.order_by(desc(ChatSession.last_activity))
            
            result = await db.execute(query)
            sessions = result.scalars().all()
            
            return [ChatSessionResponse.model_validate(session) for session in sessions]
            
        except Exception as e:
            logger.error(f"Error getting agent sessions: {str(e)}")
            return []

    async def list_sessions(
        self,
        db: AsyncSession,
        tenant_id: str,
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ChatSessionResponse], int]:
        """List chat sessions with filtering and pagination."""
        try:
            query = select(ChatSession).where(ChatSession.tenant_id == tenant_id)
            
            # Apply filters
            if filters:
                if "status" in filters and filters["status"]:
                    query = query.where(ChatSession.status.in_(filters["status"]))
                
                if "agent_id" in filters and filters["agent_id"]:
                    query = query.where(ChatSession.assigned_agent_id == filters["agent_id"])
                
                if "date_from" in filters and filters["date_from"]:
                    date_from = datetime.fromisoformat(filters["date_from"])
                    query = query.where(ChatSession.created_at >= date_from)
                
                if "date_to" in filters and filters["date_to"]:
                    date_to = datetime.fromisoformat(filters["date_to"])
                    query = query.where(ChatSession.created_at <= date_to)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply pagination and sorting
            query = query.order_by(desc(ChatSession.created_at))
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            result = await db.execute(query)
            sessions = result.scalars().all()
            
            session_responses = [ChatSessionResponse.model_validate(session) for session in sessions]
            
            return session_responses, total_count
            
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            return [], 0

    async def get_analytics_overview(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get chat analytics overview."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Total sessions
            total_sessions_query = (
                select(func.count(ChatSession.id))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.created_at >= cutoff_date
                ))
            )
            total_sessions_result = await db.execute(total_sessions_query)
            total_sessions = total_sessions_result.scalar()
            
            # Sessions by status
            status_query = (
                select(ChatSession.status, func.count(ChatSession.id))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.created_at >= cutoff_date
                ))
                .group_by(ChatSession.status)
            )
            status_result = await db.execute(status_query)
            status_breakdown = {row[0]: row[1] for row in status_result}
            
            # Average wait time
            avg_wait_query = (
                select(func.avg(ChatSession.wait_time_seconds))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.created_at >= cutoff_date,
                    ChatSession.wait_time_seconds.isnot(None)
                ))
            )
            avg_wait_result = await db.execute(avg_wait_query)
            avg_wait_seconds = avg_wait_result.scalar() or 0
            
            # Average session duration
            avg_duration_query = (
                select(func.avg(ChatSession.session_duration_seconds))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.created_at >= cutoff_date,
                    ChatSession.session_duration_seconds.isnot(None)
                ))
            )
            avg_duration_result = await db.execute(avg_duration_query)
            avg_duration_seconds = avg_duration_result.scalar() or 0
            
            # Customer satisfaction
            avg_rating_query = (
                select(func.avg(ChatSession.customer_rating))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.created_at >= cutoff_date,
                    ChatSession.customer_rating.isnot(None)
                ))
            )
            avg_rating_result = await db.execute(avg_rating_query)
            avg_rating = avg_rating_result.scalar() or 0
            
            return {
                "period_days": days,
                "total_sessions": total_sessions,
                "status_breakdown": status_breakdown,
                "avg_wait_time_seconds": round(avg_wait_seconds, 1),
                "avg_session_duration_seconds": round(avg_duration_seconds, 1),
                "customer_satisfaction": round(avg_rating, 2),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics overview: {str(e)}")
            return {}

    async def get_agent_performance_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get agent performance analytics."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = (
                select(
                    ChatSession.assigned_agent_id,
                    ChatSession.assigned_agent_name,
                    func.count(ChatSession.id).label("total_sessions"),
                    func.avg(ChatSession.session_duration_seconds).label("avg_duration"),
                    func.avg(ChatSession.customer_rating).label("avg_rating")
                )
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.created_at >= cutoff_date,
                    ChatSession.assigned_agent_id.isnot(None)
                ))
                .group_by(ChatSession.assigned_agent_id, ChatSession.assigned_agent_name)
                .order_by(desc("total_sessions"))
            )
            
            result = await db.execute(query)
            performance_data = []
            
            for row in result:
                performance_data.append({
                    "agent_id": row.assigned_agent_id,
                    "agent_name": row.assigned_agent_name,
                    "total_sessions": row.total_sessions,
                    "avg_duration_seconds": round(row.avg_duration or 0, 1),
                    "avg_customer_rating": round(row.avg_rating or 0, 2)
                })
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Error getting agent performance analytics: {str(e)}")
            return []

    async def get_queue_status(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Get current queue status."""
        try:
            # Waiting sessions
            waiting_query = (
                select(func.count(ChatSession.id))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.status == ChatStatus.WAITING
                ))
            )
            waiting_result = await db.execute(waiting_query)
            waiting_count = waiting_result.scalar()
            
            # Active sessions
            active_query = (
                select(func.count(ChatSession.id))
                .where(and_(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.status == ChatStatus.ACTIVE
                ))
            )
            active_result = await db.execute(active_query)
            active_count = active_result.scalar()
            
            # Available agents
            available_agents_query = (
                select(func.count(AgentStatus.agent_id))
                .where(and_(
                    AgentStatus.tenant_id == tenant_id,
                    AgentStatus.status == AgentStatus.ONLINE,
                    AgentStatus.current_chat_count < AgentStatus.max_concurrent_chats
                ))
            )
            available_result = await db.execute(available_agents_query)
            available_agents = available_result.scalar()
            
            # Estimated wait time (simple calculation)
            estimated_wait_minutes = 0
            if waiting_count > 0 and available_agents > 0:
                estimated_wait_minutes = min((waiting_count / available_agents) * 2, 15)  # Max 15 min estimate
            elif waiting_count > 0:
                estimated_wait_minutes = 10  # Default when no agents available
            
            return {
                "waiting_sessions": waiting_count,
                "active_sessions": active_count,
                "available_agents": available_agents,
                "estimated_wait_minutes": round(estimated_wait_minutes, 1),
                "queue_status": "normal" if waiting_count <= 5 else "busy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            return {}

    # Private helper methods
    
    async def _update_agent_chat_count(self, db: AsyncSession, agent_id: str, tenant_id: str, delta: int):
        """Update agent's current chat count."""
        try:
            stmt = (
                update(AgentStatus)
                .where(and_(
                    AgentStatus.agent_id == agent_id,
                    AgentStatus.tenant_id == tenant_id
                ))
                .values(current_chat_count=AgentStatus.current_chat_count + delta)
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to update agent chat count: {e}")

    async def _create_ticket_from_chat(self, db: AsyncSession, session: ChatSession, summary: str = None):
        """Create a support ticket from chat session."""
        try:
            if not self.ticket_service:
                return
            
            # Build ticket description from chat messages
            messages_query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(asc(ChatMessage.sent_at))
                .limit(50)  # Limit to first 50 messages
            )
            
            messages_result = await db.execute(messages_query)
            messages = messages_result.scalars().all()
            
            # Format chat transcript
            transcript_lines = [
                f"Chat Session: {session.session_id}",
                f"Started: {session.created_at}",
                f"Duration: {session.session_duration_seconds} seconds",
                "",
                "Chat Transcript:",
                "=" * 50
            ]
            
            for message in messages:
                if not message.is_internal:
                    timestamp = message.sent_at.strftime("%H:%M:%S")
                    sender = message.sender_name or message.sender_type
                    transcript_lines.append(f"[{timestamp}] {sender}: {message.content}")
            
            transcript = "\n".join(transcript_lines)
            
            # Create ticket
            ticket_data = TicketCreate(
                title=f"Chat Session Follow-up: {session.session_id}",
                description=summary or f"Follow-up ticket created from chat session {session.session_id}",
                category=TicketCategory.TECHNICAL_SUPPORT,
                priority=TicketPriority.NORMAL,
                source=TicketSource.CHAT,
                customer_email=session.customer_email,
                customer_name=session.customer_name,
                metadata={
                    "chat_session_id": session.session_id,
                    "chat_transcript": transcript,
                    "chat_rating": session.customer_rating,
                    "chat_feedback": session.customer_feedback
                }
            )
            
            ticket = await self.ticket_service.create_customer_ticket(
                db=db,
                tenant_id=session.tenant_id,
                customer_id=session.customer_id,
                title=ticket_data.title,
                description=ticket_data.description,
                category=ticket_data.category,
                priority=ticket_data.priority,
                customer_email=session.customer_email,
                metadata=ticket_data.metadata
            )
            
            if ticket:
                # Link ticket to chat session
                session.ticket_id = ticket.id
                await db.commit()
                
                logger.info(f"Created ticket {ticket.id} from chat session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Error creating ticket from chat session: {e}")

    async def _trigger_session_created_events(self, session: ChatSession):
        """Trigger events when session is created."""
        logger.info(f"Chat session created events triggered for {session.session_id}")
        # In production, this would integrate with event system for agent notifications