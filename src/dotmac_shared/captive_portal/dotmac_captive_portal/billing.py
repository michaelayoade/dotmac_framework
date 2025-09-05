"""
Billing integration and usage tracking for captive portal systems.

Provides comprehensive billing functionality including usage tracking,
payment processing, subscription management, and integration with
external payment providers.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BillingPlan, Session, UsageLog

logger = structlog.get_logger(__name__)


class BillingType(Enum):
    """Billing types for captive portal access."""

    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    PREPAID = "prepaid"
    USAGE_BASED = "usage_based"
    TIME_BASED = "time_based"
    DATA_BASED = "data_based"


class PaymentStatus(Enum):
    """Payment transaction status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class UsageMetrics:
    """Usage tracking metrics."""

    session_duration_minutes: int
    bytes_downloaded: int
    bytes_uploaded: int
    total_bytes: int
    peak_download_mbps: float
    peak_upload_mbps: float
    average_signal_strength: int | None = None
    connection_drops: int = 0


@dataclass
class BillingTransaction:
    """Billing transaction record."""

    transaction_id: str
    user_id: str
    portal_id: str
    amount: Decimal
    currency: str
    description: str
    payment_method: str
    payment_provider: str
    provider_transaction_id: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class UsageTracker:
    """Tracks user usage for billing purposes."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self._active_tracking: dict[str, dict[str, Any]] = {}
        self.usage_cache: dict[str, UsageMetrics] = {}

    async def start_usage_tracking(
        self,
        session_id: str,
        user_id: str,
        portal_id: str,
        billing_plan_id: str | None = None,
    ):
        """Start tracking usage for a session."""
        tracking_data = {
            "session_id": session_id,
            "user_id": user_id,
            "portal_id": portal_id,
            "billing_plan_id": billing_plan_id,
            "start_time": datetime.now(UTC),
            "last_update": datetime.now(UTC),
            "bytes_downloaded": 0,
            "bytes_uploaded": 0,
            "peak_download_mbps": 0.0,
            "peak_upload_mbps": 0.0,
            "signal_strength_samples": [],
            "connection_drops": 0,
        }

        self._active_tracking[session_id] = tracking_data

        logger.info(
            "Usage tracking started",
            session_id=session_id,
            user_id=user_id,
            portal_id=portal_id,
        )

    async def update_usage_metrics(
        self,
        session_id: str,
        bytes_downloaded: int = 0,
        bytes_uploaded: int = 0,
        download_mbps: float = 0.0,
        upload_mbps: float = 0.0,
        signal_strength: int | None = None,
        connection_event: str | None = None,
    ):
        """Update usage metrics for active session."""
        if session_id not in self._active_tracking:
            logger.warning("Session not being tracked", session_id=session_id)
            return

        tracking = self._active_tracking[session_id]

        # Update bandwidth usage
        tracking["bytes_downloaded"] += bytes_downloaded
        tracking["bytes_uploaded"] += bytes_uploaded
        tracking["last_update"] = datetime.now(UTC)

        # Track peak bandwidth
        tracking["peak_download_mbps"] = max(
            tracking["peak_download_mbps"], download_mbps
        )
        tracking["peak_upload_mbps"] = max(tracking["peak_upload_mbps"], upload_mbps)

        # Track signal strength
        if signal_strength is not None:
            tracking["signal_strength_samples"].append(signal_strength)

        # Track connection events
        if connection_event == "disconnect":
            tracking["connection_drops"] += 1

        # Log usage to database periodically
        await self._log_usage_sample(session_id, tracking)

    async def stop_usage_tracking(self, session_id: str) -> UsageMetrics | None:
        """Stop tracking and return final usage metrics."""
        if session_id not in self._active_tracking:
            return None

        tracking = self._active_tracking[session_id]
        end_time = datetime.now(UTC)

        # Calculate session duration
        duration = end_time - tracking["start_time"]
        duration_minutes = int(duration.total_seconds() / 60)

        # Calculate average signal strength
        avg_signal_strength = None
        if tracking["signal_strength_samples"]:
            avg_signal_strength = sum(tracking["signal_strength_samples"]) // len(
                tracking["signal_strength_samples"],
            )

        # Create final usage metrics
        usage_metrics = UsageMetrics(
            session_duration_minutes=duration_minutes,
            bytes_downloaded=tracking["bytes_downloaded"],
            bytes_uploaded=tracking["bytes_uploaded"],
            total_bytes=tracking["bytes_downloaded"] + tracking["bytes_uploaded"],
            peak_download_mbps=tracking["peak_download_mbps"],
            peak_upload_mbps=tracking["peak_upload_mbps"],
            average_signal_strength=avg_signal_strength,
            connection_drops=tracking["connection_drops"],
        )

        # Cache metrics
        self.usage_cache[session_id] = usage_metrics

        # Final usage log
        await self._log_final_usage(session_id, usage_metrics)

        # Clean up tracking
        del self._active_tracking[session_id]

        logger.info(
            "Usage tracking stopped",
            session_id=session_id,
            duration_minutes=duration_minutes,
            total_mb=usage_metrics.total_bytes / (1024 * 1024),
        )

        return usage_metrics

    async def get_user_usage_summary(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get usage summary for a user."""
        if not start_date:
            start_date = datetime.now(UTC) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(UTC)

        # Query usage logs from database
        query = (
            self.db.query(UsageLog)
            .filter(
                UsageLog.session_id.in_(
                    self.db.query(Session.id).filter(
                        Session.guest_user_id == uuid.UUID(user_id),
                    ),
                ),
            )
            .filter(UsageLog.timestamp.between(start_date, end_date))
        )

        usage_logs = await query.all()

        # Aggregate usage data
        total_bytes_down = sum(log.bytes_downloaded for log in usage_logs)
        total_bytes_up = sum(log.bytes_uploaded for log in usage_logs)
        total_sessions = len({str(log.session_id) for log in usage_logs})

        # Get session durations
        session_query = self.db.query(Session).filter(
            Session.guest_user_id == uuid.UUID(user_id),
            Session.start_time.between(start_date, end_date),
        )
        sessions = await session_query.all()

        total_duration = sum(
            (session.end_time or datetime.now(UTC) - session.start_time).total_seconds()
            for session in sessions
        )

        return {
            "user_id": user_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "usage": {
                "total_sessions": total_sessions,
                "total_duration_hours": total_duration / 3600,
                "total_bytes_downloaded": total_bytes_down,
                "total_bytes_uploaded": total_bytes_up,
                "total_bytes": total_bytes_down + total_bytes_up,
                "total_gb": (total_bytes_down + total_bytes_up) / (1024**3),
            },
        }

    async def _log_usage_sample(self, session_id: str, tracking: dict[str, Any]):
        """Log usage sample to database."""
        usage_log = UsageLog(
            session_id=uuid.UUID(session_id),
            portal_id=uuid.UUID(tracking["portal_id"]),
            tenant_id=None,  # Would be set from session
            bytes_downloaded=tracking["bytes_downloaded"],
            bytes_uploaded=tracking["bytes_uploaded"],
            event_type="usage_update",
            event_data={
                "peak_download_mbps": tracking["peak_download_mbps"],
                "peak_upload_mbps": tracking["peak_upload_mbps"],
                "connection_drops": tracking["connection_drops"],
            },
        )

        self.db.add(usage_log)
        await self.db.commit()

    async def _log_final_usage(self, session_id: str, metrics: UsageMetrics):
        """Log final usage metrics to database."""
        # In a real implementation, update the session record with final metrics
        logger.info(
            "Final usage logged", session_id=session_id, metrics=metrics.__dict__
        )


class PaymentProcessor:
    """Handles payment processing for captive portal billing."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.enabled_providers = config.get("providers", ["stripe"])
        self.default_currency = config.get("default_currency", "USD")
        self.stripe_config = config.get("stripe", {})
        self.paypal_config = config.get("paypal", {})
        self._transactions: dict[str, BillingTransaction] = {}

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        portal_id: str,
        billing_plan_id: str | None = None,
        payment_method: str = "card",
        provider: str = "stripe",
        **metadata,
    ) -> dict[str, Any]:
        """Create a payment intent for captive portal access."""
        transaction_id = str(uuid.uuid4())

        transaction = BillingTransaction(
            transaction_id=transaction_id,
            user_id=user_id,
            portal_id=portal_id,
            amount=amount,
            currency=currency,
            description=f"Captive Portal Access - {portal_id}",
            payment_method=payment_method,
            payment_provider=provider,
            status=PaymentStatus.PENDING,
            created_at=datetime.now(UTC),
            metadata={
                "billing_plan_id": billing_plan_id,
                "portal_id": portal_id,
                **metadata,
            },
        )

        self._transactions[transaction_id] = transaction

        # Create payment intent with provider
        if provider == "stripe":
            intent_data = await self._create_stripe_payment_intent(
                transaction,
                billing_plan_id,
            )
        elif provider == "paypal":
            intent_data = await self._create_paypal_payment(
                transaction, billing_plan_id
            )
        else:
            msg = f"Unsupported payment provider: {provider}"
            raise ValueError(msg)

        logger.info(
            "Payment intent created",
            transaction_id=transaction_id,
            amount=float(amount),
            currency=currency,
            provider=provider,
            user_id=user_id,
        )

        return {
            "transaction_id": transaction_id,
            "amount": float(amount),
            "currency": currency,
            "provider": provider,
            "client_secret": intent_data.get("client_secret"),
            "payment_url": intent_data.get("payment_url"),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }

    async def confirm_payment(
        self,
        transaction_id: str,
        provider_transaction_id: str,
        **confirmation_data,
    ) -> dict[str, Any]:
        """Confirm payment completion."""
        if transaction_id not in self._transactions:
            msg = f"Transaction not found: {transaction_id}"
            raise ValueError(msg)

        transaction = self._transactions[transaction_id]
        transaction.provider_transaction_id = provider_transaction_id
        transaction.status = PaymentStatus.COMPLETED
        transaction.completed_at = datetime.now(UTC)

        # Verify payment with provider
        if transaction.payment_provider == "stripe":
            verified = await self._verify_stripe_payment(
                provider_transaction_id,
                confirmation_data,
            )
        elif transaction.payment_provider == "paypal":
            verified = await self._verify_paypal_payment(
                provider_transaction_id,
                confirmation_data,
            )
        else:
            verified = False

        if not verified:
            transaction.status = PaymentStatus.FAILED
            logger.error(
                "Payment verification failed",
                transaction_id=transaction_id,
                provider_id=provider_transaction_id,
            )
            return {"success": False, "error": "Payment verification failed"}

        logger.info(
            "Payment confirmed",
            transaction_id=transaction_id,
            provider_id=provider_transaction_id,
            amount=float(transaction.amount),
        )

        return {
            "success": True,
            "transaction_id": transaction_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "status": "completed",
        }

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Decimal | None = None,
        reason: str = "requested_by_customer",
    ) -> dict[str, Any]:
        """Process payment refund."""
        if transaction_id not in self._transactions:
            msg = f"Transaction not found: {transaction_id}"
            raise ValueError(msg)

        transaction = self._transactions[transaction_id]

        if transaction.status != PaymentStatus.COMPLETED:
            msg = "Can only refund completed payments"
            raise ValueError(msg)

        refund_amount = amount or transaction.amount

        # Process refund with provider
        if transaction.payment_provider == "stripe":
            refund_result = await self._create_stripe_refund(
                transaction.provider_transaction_id,
                refund_amount,
                reason,
            )
        elif transaction.payment_provider == "paypal":
            refund_result = await self._create_paypal_refund(
                transaction.provider_transaction_id,
                refund_amount,
                reason,
            )
        else:
            msg = f"Refunds not supported for {transaction.payment_provider}"
            raise ValueError(msg)

        if refund_result.get("success"):
            transaction.status = PaymentStatus.REFUNDED
            logger.info(
                "Payment refunded",
                transaction_id=transaction_id,
                refund_amount=float(refund_amount),
            )

        return refund_result

    def get_transaction(self, transaction_id: str) -> BillingTransaction | None:
        """Get transaction by ID."""
        return self._transactions.get(transaction_id)

    async def _create_stripe_payment_intent(
        self,
        transaction: BillingTransaction,
        billing_plan_id: str | None,
    ) -> dict[str, Any]:
        """Create Stripe payment intent (implementation placeholder)."""
        # In real implementation, use Stripe API
        return {
            "client_secret": f"pi_{transaction.transaction_id}_secret",
            "payment_intent_id": f"pi_{transaction.transaction_id}",
        }

    async def _create_paypal_payment(
        self,
        transaction: BillingTransaction,
        billing_plan_id: str | None,
    ) -> dict[str, Any]:
        """Create PayPal payment (implementation placeholder)."""
        # In real implementation, use PayPal API
        return {
            "payment_url": f"https://paypal.com/checkout/{transaction.transaction_id}",
            "payment_id": f"pp_{transaction.transaction_id}",
        }

    async def _verify_stripe_payment(
        self,
        payment_intent_id: str,
        confirmation_data: dict[str, Any],
    ) -> bool:
        """Verify Stripe payment (implementation placeholder)."""
        # In real implementation, verify with Stripe API
        return True

    async def _verify_paypal_payment(
        self,
        payment_id: str,
        confirmation_data: dict[str, Any],
    ) -> bool:
        """Verify PayPal payment (implementation placeholder)."""
        # In real implementation, verify with PayPal API
        return True

    async def _create_stripe_refund(
        self,
        payment_intent_id: str,
        amount: Decimal,
        reason: str,
    ) -> dict[str, Any]:
        """Create Stripe refund (implementation placeholder)."""
        # In real implementation, use Stripe API
        return {"success": True, "refund_id": f"re_{uuid.uuid4().hex[:16]}"}

    async def _create_paypal_refund(
        self,
        payment_id: str,
        amount: Decimal,
        reason: str,
    ) -> dict[str, Any]:
        """Create PayPal refund (implementation placeholder)."""
        # In real implementation, use PayPal API
        return {"success": True, "refund_id": f"rf_{uuid.uuid4().hex[:16]}"}


class BillingIntegration:
    """Main billing integration class for captive portals."""

    def __init__(self, db_session: AsyncSession, payment_config: dict[str, Any]):
        self.db = db_session
        self.usage_tracker = UsageTracker(db_session)
        self.payment_processor = PaymentProcessor(payment_config)
        self._active_billing_sessions: dict[str, dict[str, Any]] = {}

    async def create_billing_plan(
        self,
        tenant_id: str,
        name: str,
        price: Decimal,
        billing_type: str = "one_time",
        **plan_data,
    ) -> BillingPlan:
        """Create a new billing plan."""
        plan = BillingPlan(
            tenant_id=uuid.UUID(tenant_id),
            name=name,
            plan_code=plan_data.get("plan_code", f"plan_{uuid.uuid4().hex[:8]}"),
            price=price,
            currency=plan_data.get("currency", "USD"),
            billing_type=billing_type,
            billing_cycle=plan_data.get("billing_cycle"),
            duration_minutes=plan_data.get("duration_minutes"),
            data_limit_mb=plan_data.get("data_limit_mb", 0),
            bandwidth_limit_down=plan_data.get("bandwidth_limit_down", 0),
            bandwidth_limit_up=plan_data.get("bandwidth_limit_up", 0),
            validity_days=plan_data.get("validity_days"),
            features=plan_data.get("features", {}),
            **plan_data,
        )

        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)

        logger.info(
            "Billing plan created",
            plan_id=str(plan.id),
            name=name,
            price=float(price),
            billing_type=billing_type,
        )

        return plan

    async def initiate_billing_session(
        self,
        user_id: str,
        session_id: str,
        portal_id: str,
        billing_plan_id: str,
    ) -> dict[str, Any]:
        """Initiate billing for a user session."""
        # Get billing plan
        billing_plan = await self.db.get(BillingPlan, uuid.UUID(billing_plan_id))
        if not billing_plan:
            msg = f"Billing plan not found: {billing_plan_id}"
            raise ValueError(msg)

        # Check if payment is required
        payment_required = billing_plan.price > 0

        if payment_required:
            # Create payment intent
            payment_intent = await self.payment_processor.create_payment_intent(
                amount=billing_plan.price,
                currency=billing_plan.currency,
                user_id=user_id,
                portal_id=portal_id,
                billing_plan_id=billing_plan_id,
                description=f"Access plan: {billing_plan.name}",
            )
        else:
            payment_intent = {"transaction_id": None}

        # Start usage tracking
        await self.usage_tracker.start_usage_tracking(
            session_id,
            user_id,
            portal_id,
            billing_plan_id,
        )

        # Store billing session
        billing_session = {
            "user_id": user_id,
            "session_id": session_id,
            "portal_id": portal_id,
            "billing_plan_id": billing_plan_id,
            "transaction_id": payment_intent.get("transaction_id"),
            "payment_required": payment_required,
            "payment_completed": not payment_required,
            "usage_limits": {
                "duration_minutes": billing_plan.duration_minutes,
                "data_limit_mb": billing_plan.data_limit_mb,
                "bandwidth_limit_down": billing_plan.bandwidth_limit_down,
                "bandwidth_limit_up": billing_plan.bandwidth_limit_up,
            },
            "created_at": datetime.now(UTC),
        }

        self._active_billing_sessions[session_id] = billing_session

        logger.info(
            "Billing session initiated",
            session_id=session_id,
            billing_plan=billing_plan.name,
            payment_required=payment_required,
        )

        result = {
            "billing_session_id": session_id,
            "billing_plan": {
                "id": str(billing_plan.id),
                "name": billing_plan.name,
                "price": float(billing_plan.price),
                "currency": billing_plan.currency,
            },
            "payment_required": payment_required,
        }

        if payment_required:
            result["payment_intent"] = payment_intent

        return result

    async def confirm_billing_payment(
        self,
        session_id: str,
        transaction_id: str,
        provider_transaction_id: str,
    ) -> dict[str, Any]:
        """Confirm payment for billing session."""
        if session_id not in self._active_billing_sessions:
            msg = f"Billing session not found: {session_id}"
            raise ValueError(msg)

        # Confirm payment
        payment_result = await self.payment_processor.confirm_payment(
            transaction_id,
            provider_transaction_id,
        )

        if payment_result["success"]:
            billing_session = self._active_billing_sessions[session_id]
            billing_session["payment_completed"] = True
            billing_session["payment_confirmed_at"] = datetime.now(UTC)

            logger.info(
                "Billing payment confirmed",
                session_id=session_id,
                transaction_id=transaction_id,
            )

        return payment_result

    async def check_usage_limits(
        self,
        session_id: str,
        current_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Check if session has exceeded usage limits."""
        if session_id not in self._active_billing_sessions:
            return {"within_limits": True}

        billing_session = self._active_billing_sessions[session_id]
        limits = billing_session["usage_limits"]

        # Get current usage metrics
        if not current_usage:
            if session_id in self.usage_tracker._active_tracking:
                tracking = self.usage_tracker._active_tracking[session_id]
                duration_minutes = int(
                    (datetime.now(UTC) - tracking["start_time"]).total_seconds() / 60,
                )
                current_usage = {
                    "duration_minutes": duration_minutes,
                    "data_mb": (
                        tracking["bytes_downloaded"] + tracking["bytes_uploaded"]
                    )
                    / (1024 * 1024),
                }
            else:
                current_usage = {"duration_minutes": 0, "data_mb": 0}

        # Check limits
        violations = []

        # Time limit
        if (
            limits["duration_minutes"]
            and current_usage["duration_minutes"] >= limits["duration_minutes"]
        ):
            violations.append("time_limit_exceeded")

        # Data limit
        if (
            limits["data_limit_mb"]
            and current_usage["data_mb"] >= limits["data_limit_mb"]
        ):
            violations.append("data_limit_exceeded")

        within_limits = len(violations) == 0

        return {
            "within_limits": within_limits,
            "violations": violations,
            "current_usage": current_usage,
            "limits": limits,
            "usage_percentage": {
                "time": (
                    (
                        current_usage["duration_minutes"]
                        / limits["duration_minutes"]
                        * 100
                    )
                    if limits["duration_minutes"]
                    else 0
                ),
                "data": (
                    (current_usage["data_mb"] / limits["data_limit_mb"] * 100)
                    if limits["data_limit_mb"]
                    else 0
                ),
            },
        }

    async def finalize_billing_session(self, session_id: str) -> dict[str, Any]:
        """Finalize billing session and calculate final charges."""
        if session_id not in self._active_billing_sessions:
            return {"error": "Billing session not found"}

        billing_session = self._active_billing_sessions[session_id]

        # Stop usage tracking and get final metrics
        usage_metrics = await self.usage_tracker.stop_usage_tracking(session_id)

        # Calculate any usage-based charges
        final_charges = await self._calculate_final_charges(
            billing_session,
            usage_metrics,
        )

        # Clean up billing session
        del self._active_billing_sessions[session_id]

        logger.info(
            "Billing session finalized",
            session_id=session_id,
            final_charges=final_charges,
            usage_metrics=usage_metrics.__dict__ if usage_metrics else None,
        )

        return {
            "session_id": session_id,
            "final_charges": final_charges,
            "usage_metrics": usage_metrics.__dict__ if usage_metrics else None,
            "finalized_at": datetime.now(UTC).isoformat(),
        }

    async def _calculate_final_charges(
        self,
        billing_session: dict[str, Any],
        usage_metrics: UsageMetrics | None,
    ) -> dict[str, Any]:
        """Calculate final charges based on usage."""
        # Get billing plan
        billing_plan = await self.db.get(
            BillingPlan,
            uuid.UUID(billing_session["billing_plan_id"]),
        )

        base_charge = billing_plan.price if billing_plan else Decimal(0)
        usage_charges = Decimal(0)

        # Calculate usage-based charges (placeholder logic)
        if (
            billing_plan
            and billing_plan.billing_type == "usage_based"
            and usage_metrics
        ):
            # Example: charge per GB over limit
            if billing_plan.data_limit_mb > 0:
                excess_mb = max(
                    0,
                    usage_metrics.total_bytes / (1024 * 1024)
                    - billing_plan.data_limit_mb,
                )
                usage_charges = Decimal(str(excess_mb / 1024)) * Decimal(
                    "1.00"
                )  # $1 per GB

        total_charges = base_charge + usage_charges

        return {
            "base_charge": float(base_charge),
            "usage_charges": float(usage_charges),
            "total_charges": float(total_charges),
            "currency": billing_plan.currency if billing_plan else "USD",
        }
