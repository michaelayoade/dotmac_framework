"""
Support Automation Workflows
Automated support ticket management, escalation, and resolution
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from celery import shared_task
from dotmac_shared.exceptions import ExceptionContext


@shared_task(bind=True, max_retries=3)
def categorize_ticket(self, ticket_data: dict[str, Any]) -> dict[str, Any]:
    """Automatically categorize support tickets"""

    try:
        ticket_content = f"{ticket_data.get('subject', '')} {ticket_data.get('description', '')}"

        # Keyword-based categorization
        categories = {
            "billing": [
                "bill",
                "payment",
                "charge",
                "invoice",
                "refund",
                "subscription",
            ],
            "technical": [
                "connection",
                "slow",
                "outage",
                "error",
                "not working",
                "bug",
            ],
            "account": ["login", "password", "access", "account", "profile"],
            "sales": ["upgrade", "plan", "pricing", "quote", "purchase"],
            "cancellation": ["cancel", "terminate", "close", "end service"],
        }

        # Priority keywords
        priority_keywords = {
            "critical": [
                "down",
                "outage",
                "emergency",
                "urgent",
                "critical",
                "not working",
            ],
            "high": ["slow", "issue", "problem", "error", "help"],
            "normal": ["question", "request", "information", "how to"],
            "low": ["feature", "suggestion", "feedback"],
        }

        # Determine category
        detected_category = "general"
        category_score = 0

        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword.lower() in ticket_content.lower())
            if score > category_score:
                category_score = score
                detected_category = category

        # Determine priority
        detected_priority = "normal"
        priority_score = 0

        for priority, keywords in priority_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in ticket_content.lower())
            if score > priority_score:
                priority_score = score
                detected_priority = priority

        # Auto-assign based on category
        assignment_rules = {
            "billing": "billing_team",
            "technical": "technical_support",
            "account": "customer_success",
            "sales": "sales_team",
            "cancellation": "retention_team",
            "general": "general_support",
        }

        assigned_team = assignment_rules.get(detected_category, "general_support")

        # Calculate estimated resolution time
        resolution_times = {
            "critical": 4,  # hours
            "high": 24,
            "normal": 72,
            "low": 168,
        }

        estimated_hours = resolution_times.get(detected_priority, 72)
        estimated_resolution = (datetime.now(timezone.utc) + timedelta(hours=estimated_hours)).isoformat()

        categorization_result = {
            "ticket_id": ticket_data.get("ticket_id"),
            "category": detected_category,
            "priority": detected_priority,
            "assigned_team": assigned_team,
            "confidence_score": max(category_score, priority_score),
            "estimated_resolution": estimated_resolution,
            "auto_responses": get_auto_responses(detected_category, detected_priority),
            "categorized_at": datetime.now(timezone.utc).isoformat(),
        }

        return categorization_result

    except ExceptionContext.PARSING_EXCEPTIONS as e:
        raise self.retry(countdown=60, exc=e) from e


def get_auto_responses(category: str, priority: str) -> list[str]:
    """Get appropriate auto-responses based on category and priority"""

    responses = []

    if category == "billing":
        responses.extend(
            [
                "We've received your billing inquiry and our billing team will review it within 24 hours.",
                "For immediate billing questions, you can also check your account portal.",
            ]
        )
    elif category == "technical":
        if priority in ["critical", "high"]:
            responses.extend(
                [
                    "We've identified this as a technical issue requiring urgent attention.",
                    "Our technical team has been notified and will investigate immediately.",
                ]
            )
        else:
            responses.extend(
                [
                    "Thank you for reporting this technical issue.",
                    "Our team will investigate and provide updates within 24-48 hours.",
                ]
            )
    elif category == "account":
        responses.extend(
            [
                "We'll help you with your account access issue.",
                "For security purposes, we may need to verify your identity.",
            ]
        )

    return responses


@shared_task(bind=True)
def auto_respond_to_ticket(self, categorization_result: dict[str, Any]) -> dict[str, Any]:
    """Send automatic response to customer"""

    ticket_id = categorization_result["ticket_id"]
    category = categorization_result["category"]
    priority = categorization_result["priority"]
    auto_responses = categorization_result.get("auto_responses", [])

    # Build response message
    response_parts = [
        f"Thank you for contacting support. Your ticket #{ticket_id} has been received.",
        f"Category: {category.title()}",
        f"Priority: {priority.title()}",
        f"Estimated resolution time: {categorization_result['estimated_resolution']}",
    ]

    if auto_responses:
        response_parts.extend(auto_responses)

    response_parts.extend(
        [
            "",
            "You will receive updates as we work on your request.",
            "Best regards,",
            "DotMac Support Team",
        ]
    )

    response_message = "\n".join(response_parts)

    # In real implementation, this would send actual email/SMS
    # notification_service.send_email(
    #     to=ticket_data['customer_email'],
    #     subject=f"Re: Support Ticket #{ticket_id}",
    #     body=response_message
    # )

    return {
        "ticket_id": ticket_id,
        "auto_response_sent": True,
        "response_message": response_message,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@shared_task(bind=True)
def assign_to_team(self, categorization_result: dict[str, Any]) -> dict[str, Any]:
    """Assign ticket to appropriate team"""

    ticket_id = categorization_result["ticket_id"]
    assigned_team = categorization_result["assigned_team"]
    priority = categorization_result["priority"]

    # Get available team members
    team_members = get_available_team_members(assigned_team, priority)

    if not team_members:
        # Escalate if no team members available
        return escalate_ticket.delay(categorization_result)

    # Assign to least loaded team member
    assigned_agent = min(team_members, key=lambda x: x["current_load"])

    assignment_result = {
        "ticket_id": ticket_id,
        "assigned_team": assigned_team,
        "assigned_agent": assigned_agent["agent_id"],
        "agent_name": assigned_agent["name"],
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "sla_deadline": calculate_sla_deadline(priority),
    }

    # Update ticket in database (placeholder)
    # update_ticket_assignment(ticket_id, assignment_result)

    # Notify assigned agent
    # notify_agent_assignment(assigned_agent['agent_id'], assignment_result)

    return assignment_result


def get_available_team_members(team: str, priority: str) -> list[dict[str, Any]]:
    """Get available team members (placeholder)"""

    # This would query actual staffing system
    team_data = {
        "billing_team": [
            {
                "agent_id": "AGT_BILL_001",
                "name": "Sarah Johnson",
                "current_load": 3,
                "skills": ["billing", "payments"],
            },
            {
                "agent_id": "AGT_BILL_002",
                "name": "Mike Chen",
                "current_load": 5,
                "skills": ["billing", "refunds"],
            },
        ],
        "technical_support": [
            {
                "agent_id": "AGT_TECH_001",
                "name": "Alex Rodriguez",
                "current_load": 7,
                "skills": ["networking", "troubleshooting"],
            },
            {
                "agent_id": "AGT_TECH_002",
                "name": "Lisa Wang",
                "current_load": 4,
                "skills": ["internet", "email"],
            },
        ],
        "customer_success": [
            {
                "agent_id": "AGT_CS_001",
                "name": "David Kim",
                "current_load": 2,
                "skills": ["onboarding", "training"],
            },
            {
                "agent_id": "AGT_CS_002",
                "name": "Emma Davis",
                "current_load": 6,
                "skills": ["retention", "upselling"],
            },
        ],
    }

    return team_data.get(team, [])


def calculate_sla_deadline(priority: str) -> str:
    """Calculate SLA deadline based on priority"""

    sla_hours = {"critical": 4, "high": 24, "normal": 72, "low": 168}

    hours = sla_hours.get(priority, 72)
    deadline = datetime.now(timezone.utc) + timedelta(hours=hours)
    return deadline.isoformat()


@shared_task
def check_escalation() -> dict[str, Any]:
    """Check for tickets that need escalation"""

    # Get tickets approaching SLA deadline
    tickets_near_deadline = get_tickets_near_sla_deadline()
    overdue_tickets = get_overdue_tickets()

    escalated_tickets = []

    # Escalate tickets near deadline
    for ticket in tickets_near_deadline:
        escalation_result = escalate_ticket.delay(ticket)
        escalated_tickets.append(
            {
                "ticket_id": ticket["ticket_id"],
                "reason": "approaching_sla_deadline",
                "escalation_id": escalation_result.id,
            }
        )

    # Escalate overdue tickets
    for ticket in overdue_tickets:
        escalation_result = escalate_ticket.delay(ticket)
        escalated_tickets.append(
            {
                "ticket_id": ticket["ticket_id"],
                "reason": "sla_breach",
                "escalation_id": escalation_result.id,
            }
        )

    return {
        "check_time": datetime.now(timezone.utc).isoformat(),
        "tickets_checked": len(tickets_near_deadline) + len(overdue_tickets),
        "escalated_count": len(escalated_tickets),
        "escalated_tickets": escalated_tickets,
    }


def get_tickets_near_sla_deadline() -> list[dict[str, Any]]:
    """Get tickets approaching SLA deadline (placeholder)"""
    # Would query database for tickets with SLA deadline within next 2 hours
    return [
        {
            "ticket_id": "TKT_001",
            "priority": "high",
            "sla_deadline": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "assigned_agent": "AGT_TECH_001",
        }
    ]


def get_overdue_tickets() -> list[dict[str, Any]]:
    """Get overdue tickets (placeholder)"""
    # Would query database for tickets past SLA deadline
    return [
        {
            "ticket_id": "TKT_002",
            "priority": "critical",
            "sla_deadline": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "assigned_agent": "AGT_TECH_002",
        }
    ]


@shared_task(bind=True)
def escalate_ticket(self, ticket_data: dict[str, Any]) -> dict[str, Any]:
    """Escalate ticket to higher level support"""

    ticket_id = ticket_data["ticket_id"]
    current_priority = ticket_data.get("priority", "normal")

    # Determine escalation level
    escalation_levels = {
        "low": "normal",
        "normal": "high",
        "high": "critical",
        "critical": "executive",
    }

    new_priority = escalation_levels.get(current_priority, "high")

    # Escalation assignments
    escalation_teams = {
        "critical": "senior_technical_team",
        "executive": "executive_support",
        "high": "specialist_team",
    }

    escalated_team = escalation_teams.get(new_priority, "specialist_team")

    escalation_result = {
        "ticket_id": ticket_id,
        "escalated_from": current_priority,
        "escalated_to": new_priority,
        "escalated_team": escalated_team,
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "escalation_reason": ticket_data.get("reason", "sla_approach"),
    }

    # Notify stakeholders about escalation
    notify_escalation.delay(escalation_result)

    return escalation_result


@shared_task
def notify_escalation(escalation_data: dict[str, Any]):
    """Notify stakeholders about ticket escalation"""

    ticket_id = escalation_data["ticket_id"]
    new_priority = escalation_data["escalated_to"]

    # Determine notification recipients
    notification_recipients = {
        "critical": ["support_manager@example.com", "technical_director@example.com"],
        "executive": ["ceo@example.com", "support_manager@example.com"],
        "high": ["support_manager@example.com"],
    }

    recipients = notification_recipients.get(new_priority, [])

    # Send notifications (placeholder)
    for _recipient in recipients:
        # email_service.send_escalation_notification(recipient, escalation_data)
        pass

    return {
        "ticket_id": ticket_id,
        "notifications_sent": len(recipients),
        "recipients": recipients,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@shared_task
def analyze_support_metrics() -> dict[str, Any]:
    """Analyze support team performance metrics"""

    # Calculate metrics for the last 24 hours
    metrics_period_start = datetime.now(timezone.utc) - timedelta(days=1)

    metrics = {
        "period_start": metrics_period_start.isoformat(),
        "period_end": datetime.now(timezone.utc).isoformat(),
        "total_tickets": get_ticket_count(metrics_period_start),
        "resolved_tickets": get_resolved_ticket_count(metrics_period_start),
        "average_resolution_time": calculate_avg_resolution_time(metrics_period_start),
        "sla_compliance": calculate_sla_compliance(metrics_period_start),
        "customer_satisfaction": get_customer_satisfaction_score(metrics_period_start),
        "team_performance": get_team_performance_metrics(metrics_period_start),
    }

    # Generate alerts for performance issues
    alerts = []

    if metrics["sla_compliance"] < 0.85:  # Below 85%
        alerts.append(
            {
                "type": "sla_compliance_low",
                "message": f"SLA compliance is {metrics['sla_compliance']:.1%}, below target of 85%",
                "severity": "high",
            }
        )

    if metrics["customer_satisfaction"] < 4.0:  # Below 4.0/5.0
        alerts.append(
            {
                "type": "low_satisfaction",
                "message": f"Customer satisfaction is {metrics['customer_satisfaction']:.1f}/5.0, below target of 4.0",
                "severity": "medium",
            }
        )

    metrics["alerts"] = alerts

    # Send metrics report to management
    if alerts or datetime.now(timezone.utc).hour == 9:  # Daily report at 9 AM or when alerts
        send_support_metrics_report.delay(metrics)

    return metrics


def get_ticket_count(since: datetime) -> int:
    """Get total ticket count (placeholder)"""
    return 145


def get_resolved_ticket_count(since: datetime) -> int:
    """Get resolved ticket count (placeholder)"""
    return 132


def calculate_avg_resolution_time(since: datetime) -> float:
    """Calculate average resolution time in hours (placeholder)"""
    return 18.5


def calculate_sla_compliance(since: datetime) -> float:
    """Calculate SLA compliance percentage (placeholder)"""
    return 0.91  # 91%


def get_customer_satisfaction_score(since: datetime) -> float:
    """Get customer satisfaction score (placeholder)"""
    return 4.3  # 4.3/5.0


def get_team_performance_metrics(since: datetime) -> dict[str, Any]:
    """Get team performance metrics (placeholder)"""
    return {
        "billing_team": {
            "tickets_handled": 45,
            "avg_resolution_time": 12.5,
            "satisfaction": 4.5,
        },
        "technical_support": {
            "tickets_handled": 67,
            "avg_resolution_time": 24.2,
            "satisfaction": 4.1,
        },
        "customer_success": {
            "tickets_handled": 33,
            "avg_resolution_time": 15.8,
            "satisfaction": 4.6,
        },
    }


@shared_task
def send_support_metrics_report(metrics: dict[str, Any]):
    """Send support metrics report to management"""

    # Format report (placeholder)
    # report_html = generate_metrics_report_html(metrics)
    # email_service.send_html_email(
    #     to=['support_manager@example.com', 'operations@example.com'],
    #     subject=f"Support Metrics Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
    #     html_body=report_html
    # )

    return {
        "report_sent": True,
        "metrics_included": list(metrics.keys()),
        "alerts_count": len(metrics.get("alerts", [])),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@shared_task
def knowledge_base_update_suggestion(ticket_data: dict[str, Any]) -> dict[str, Any]:
    """Suggest knowledge base updates based on common issues"""

    # Analyze ticket patterns to suggest KB articles
    common_issues = analyze_common_ticket_patterns()

    suggestions = []

    for issue in common_issues:
        if issue["frequency"] >= 5 and not issue["has_kb_article"]:
            suggestions.append(
                {
                    "issue_type": issue["type"],
                    "frequency": issue["frequency"],
                    "suggested_title": issue["suggested_article_title"],
                    "priority": "high" if issue["frequency"] >= 10 else "medium",
                }
            )

    if suggestions:
        # Notify content team about KB gaps
        notify_kb_team.delay(suggestions)

    return {
        "suggestions_count": len(suggestions),
        "suggestions": suggestions,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def analyze_common_ticket_patterns() -> list[dict[str, Any]]:
    """Analyze common ticket patterns (placeholder)"""
    return [
        {
            "type": "email_setup",
            "frequency": 12,
            "has_kb_article": False,
            "suggested_article_title": "How to Set Up Email on Mobile Devices",
        },
        {
            "type": "password_reset",
            "frequency": 8,
            "has_kb_article": True,
            "suggested_article_title": None,
        },
    ]


@shared_task
def notify_kb_team(suggestions: list[dict[str, Any]]):
    """Notify knowledge base team about content suggestions"""

    # Send suggestions to content team (placeholder)
    # email_service.send_kb_suggestions(suggestions)

    return {
        "notifications_sent": True,
        "suggestions_count": len(suggestions),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
