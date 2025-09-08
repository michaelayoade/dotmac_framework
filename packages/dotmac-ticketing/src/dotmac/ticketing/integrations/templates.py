"""
Minimal notification template strategy using string.Template.
Provides template rendering with no external dependencies, with optional Jinja2 support.
"""

import logging
from string import Template
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Template renderer with fallback from Jinja2 to string.Template."""
    
    def __init__(self, use_jinja2: bool = True):
        """Initialize template renderer.
        
        Args:
            use_jinja2: Whether to try using Jinja2 templates first
        """
        self.use_jinja2 = use_jinja2
        self._jinja2_env = None
        
        if use_jinja2:
            self._init_jinja2()
    
    def _init_jinja2(self):
        """Initialize Jinja2 environment if available."""
        try:
            from jinja2 import Environment, BaseLoader
            
            class StringLoader(BaseLoader):
                """Load templates from strings."""
                
                def __init__(self, templates: Dict[str, str]):
                    self.templates = templates
                
                def get_source(self, environment, template):
                    if template in self.templates:
                        source = self.templates[template]
                        return source, None, lambda: True
                    raise FileNotFoundError(f"Template '{template}' not found")
            
            self._jinja2_env = Environment(loader=StringLoader({}))
            logger.debug("Jinja2 template rendering enabled")
            
        except ImportError:
            logger.debug("Jinja2 not available, using string.Template fallback")
            self._jinja2_env = None
    
    def render_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """Render template with given context.
        
        Args:
            template_content: Template content string
            context: Variables to substitute in template
            
        Returns:
            Rendered template string
        """
        # Try Jinja2 first if available
        if self._jinja2_env:
            try:
                template = self._jinja2_env.from_string(template_content)
                return template.render(**context)
            except Exception as e:
                logger.warning(f"Jinja2 template rendering failed: {e}, falling back to string.Template")
        
        # Fallback to string.Template
        return self._render_string_template(template_content, context)
    
    def _render_string_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """Render template using string.Template."""
        try:
            template = Template(template_content)
            # string.Template uses $variable syntax, so we need safe_substitute
            # to handle missing variables gracefully
            return template.safe_substitute(**context)
        except Exception as e:
            logger.error(f"String template rendering failed: {e}")
            # Return template as-is if rendering fails
            return template_content


class NotificationTemplateManager:
    """Manager for notification templates with multiple rendering strategies."""
    
    # Default templates using string.Template syntax for compatibility
    DEFAULT_TEMPLATES = {
        "ticket_created": {
            "subject": "Support Ticket Created - #$ticket_number",
            "body": """Hello $customer_name,

Your support ticket has been created and assigned number $ticket_number.

Title: $title
Priority: $priority
Status: $status

We will review your request and respond within our standard SLA timeframe.

You can track the progress of your ticket using the ticket number above.

Best regards,
Support Team""",
            "html_body": """<html><body>
<h2>Support Ticket Created</h2>
<p>Hello <strong>$customer_name</strong>,</p>

<p>Your support ticket has been created and assigned number <strong>$ticket_number</strong>.</p>

<table border="1" cellpadding="5">
  <tr><td><strong>Title:</strong></td><td>$title</td></tr>
  <tr><td><strong>Priority:</strong></td><td>$priority</td></tr>
  <tr><td><strong>Status:</strong></td><td>$status</td></tr>
</table>

<p>We will review your request and respond within our standard SLA timeframe.</p>
<p>You can track the progress of your ticket using the ticket number above.</p>

<p>Best regards,<br/>Support Team</p>
</body></html>"""
        },
        
        "ticket_assigned": {
            "subject": "Your ticket has been assigned - #$ticket_number", 
            "body": """Hello $customer_name,

Your support ticket #$ticket_number has been assigned to our $assigned_team team.

Assigned to: $assigned_to
Team: $assigned_team

Your ticket will be reviewed and we will provide updates as we work on your request.

Best regards,
Support Team""",
            "html_body": """<html><body>
<h2>Ticket Assigned</h2>
<p>Hello <strong>$customer_name</strong>,</p>

<p>Your support ticket <strong>#$ticket_number</strong> has been assigned to our $assigned_team team.</p>

<ul>
  <li><strong>Assigned to:</strong> $assigned_to</li>
  <li><strong>Team:</strong> $assigned_team</li>
</ul>

<p>Your ticket will be reviewed and we will provide updates as we work on your request.</p>

<p>Best regards,<br/>Support Team</p>
</body></html>"""
        },
        
        "ticket_resolved": {
            "subject": "Your support ticket has been resolved - #$ticket_number",
            "body": """Hello $customer_name,

Great news! Your support ticket #$ticket_number has been resolved.

Title: $title
Resolution: $resolution_comment
Resolved by: $resolved_by

If you have any questions about this resolution or need further assistance, please reply to this email or create a new ticket.

Thank you for using our support services.

Best regards,
Support Team""",
            "html_body": """<html><body>
<h2>Ticket Resolved</h2>
<p>Hello <strong>$customer_name</strong>,</p>

<p><strong>Great news!</strong> Your support ticket <strong>#$ticket_number</strong> has been resolved.</p>

<table border="1" cellpadding="5">
  <tr><td><strong>Title:</strong></td><td>$title</td></tr>
  <tr><td><strong>Resolution:</strong></td><td>$resolution_comment</td></tr>
  <tr><td><strong>Resolved by:</strong></td><td>$resolved_by</td></tr>
</table>

<p>If you have any questions about this resolution or need further assistance, please reply to this email or create a new ticket.</p>

<p>Thank you for using our support services.</p>

<p>Best regards,<br/>Support Team</p>
</body></html>"""
        },
        
        "comment_added": {
            "subject": "New response to your support ticket - #$ticket_number",
            "body": """Hello $customer_name,

There has been a new response to your support ticket #$ticket_number.

From: $comment_author
Date: $comment_date

$comment_content

You can view the full ticket history by referencing your ticket number.

Best regards,
Support Team""",
            "html_body": """<html><body>
<h2>New Response</h2>
<p>Hello <strong>$customer_name</strong>,</p>

<p>There has been a new response to your support ticket <strong>#$ticket_number</strong>.</p>

<div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0; background-color: #f9f9f9;">
  <p><strong>From:</strong> $comment_author<br/>
     <strong>Date:</strong> $comment_date</p>
  <p>$comment_content</p>
</div>

<p>You can view the full ticket history by referencing your ticket number.</p>

<p>Best regards,<br/>Support Team</p>
</body></html>"""
        },
        
        "sla_warning": {
            "subject": "SLA Warning - #$ticket_number",
            "body": """Hello Team,

ALERT: Ticket #$ticket_number is approaching SLA breach.

Title: $title
Priority: $priority
SLA Breach Time: $sla_breach_time
Customer: $customer_name

Please review and take action immediately to avoid SLA breach.

Automated Alert System""",
            "html_body": """<html><body>
<h2 style="color: orange;">SLA Warning</h2>
<p><strong>ALERT:</strong> Ticket <strong>#$ticket_number</strong> is approaching SLA breach.</p>

<table border="1" cellpadding="5" style="border-color: orange;">
  <tr><td><strong>Title:</strong></td><td>$title</td></tr>
  <tr><td><strong>Priority:</strong></td><td>$priority</td></tr>
  <tr><td><strong>SLA Breach Time:</strong></td><td style="color: red;">$sla_breach_time</td></tr>
  <tr><td><strong>Customer:</strong></td><td>$customer_name</td></tr>
</table>

<p><strong>Please review and take action immediately to avoid SLA breach.</strong></p>

<p><em>Automated Alert System</em></p>
</body></html>"""
        }
    }
    
    def __init__(self, renderer: Optional[TemplateRenderer] = None, custom_templates: Optional[Dict[str, Dict[str, str]]] = None):
        """Initialize template manager.
        
        Args:
            renderer: Template renderer to use
            custom_templates: Custom template definitions to override defaults
        """
        self.renderer = renderer or TemplateRenderer()
        self.templates = self.DEFAULT_TEMPLATES.copy()
        
        if custom_templates:
            self.templates.update(custom_templates)
    
    def render_notification(
        self,
        template_name: str,
        context: Dict[str, Any],
        format_type: str = "body"
    ) -> Optional[str]:
        """Render notification template.
        
        Args:
            template_name: Name of template to render
            context: Variables to substitute
            format_type: Template format ('subject', 'body', 'html_body')
            
        Returns:
            Rendered template or None if template not found
        """
        if template_name not in self.templates:
            logger.error(f"Template '{template_name}' not found")
            return None
        
        template_def = self.templates[template_name]
        if format_type not in template_def:
            logger.error(f"Template format '{format_type}' not found in '{template_name}'")
            return None
        
        template_content = template_def[format_type]
        
        # Ensure all context values are strings and handle None values
        safe_context = self._prepare_context(context)
        
        try:
            return self.renderer.render_template(template_content, safe_context)
        except Exception as e:
            logger.error(f"Failed to render template '{template_name}' format '{format_type}': {e}")
            return template_content  # Return unrendered template as fallback
    
    def _prepare_context(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Prepare context for template rendering by converting all values to strings."""
        safe_context = {}
        
        for key, value in context.items():
            if value is None:
                safe_context[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                safe_context[key] = str(value)
            elif hasattr(value, '__str__'):
                safe_context[key] = str(value)
            else:
                safe_context[key] = repr(value)
        
        # Add common defaults
        safe_context.setdefault('customer_name', 'Customer')
        safe_context.setdefault('ticket_number', 'N/A')
        safe_context.setdefault('title', 'Support Request')
        safe_context.setdefault('priority', 'normal')
        safe_context.setdefault('status', 'open')
        
        return safe_context
    
    def get_available_templates(self) -> list[str]:
        """Get list of available template names."""
        return list(self.templates.keys())
    
    def add_custom_template(self, name: str, template_def: Dict[str, str]):
        """Add a custom template definition.
        
        Args:
            name: Template name
            template_def: Dictionary with 'subject', 'body', and optionally 'html_body'
        """
        required_fields = ['subject', 'body']
        for field in required_fields:
            if field not in template_def:
                raise ValueError(f"Template definition must include '{field}'")
        
        self.templates[name] = template_def
        logger.info(f"Added custom template '{name}'")


# Global template manager instance
default_template_manager = NotificationTemplateManager()


def render_notification_template(
    template_name: str,
    context: Dict[str, Any],
    format_type: str = "body",
    template_manager: Optional[NotificationTemplateManager] = None
) -> Optional[str]:
    """Convenience function to render notification templates.
    
    Args:
        template_name: Name of template to render
        context: Variables to substitute
        format_type: Template format ('subject', 'body', 'html_body')
        template_manager: Custom template manager, uses default if None
        
    Returns:
        Rendered template or None if template not found
    """
    manager = template_manager or default_template_manager
    return manager.render_notification(template_name, context, format_type)


def get_jinja2_availability() -> bool:
    """Check if Jinja2 is available for template rendering."""
    try:
        import jinja2
        return True
    except ImportError:
        return False