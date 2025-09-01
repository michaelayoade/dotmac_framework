"""
Email templates and enhanced notification service for resellers
Professional email templates for all reseller communications
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json

from .db_models import ResellerApplication, Reseller


class EmailTemplates:
    """Professional email templates for reseller communications"""
    
    @staticmethod
    def application_confirmation(application: ResellerApplication) -> Dict[str, str]:
        """Application confirmation email template"""
        return {
            'subject': f"Application Received - {application.company_name}",
            'html_body': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Application Received</h1>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Dear {application.contact_name},</p>
                    
                    <p>Thank you for submitting your reseller partner application. We have successfully received your application and wanted to confirm the details:</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #333; margin-top: 0;">Application Details</h3>
                        <p><strong>Application ID:</strong> {application.application_id}</p>
                        <p><strong>Company:</strong> {application.company_name}</p>
                        <p><strong>Contact:</strong> {application.contact_name}</p>
                        <p><strong>Email:</strong> {application.contact_email}</p>
                        <p><strong>Submitted:</strong> {application.submitted_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                    </div>
                    
                    <h3 style="color: #333;">Next Steps</h3>
                    <ul style="line-height: 1.6;">
                        <li>Our partner team will review your application within 24-48 business hours</li>
                        <li>You will receive an email update when your application moves to "Under Review" status</li>
                        <li>If approved, you'll receive welcome materials and portal access information</li>
                        <li>Our account manager will schedule an onboarding call within 48 hours of approval</li>
                    </ul>
                    
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Questions?</strong> Contact our partner team at <a href="mailto:partners@company.com">partners@company.com</a> or reference your Application ID: <strong>{application.application_id}</strong></p>
                    </div>
                    
                    <p>We appreciate your interest in becoming a partner and look forward to potentially working together!</p>
                    
                    <p>Best regards,<br>
                    The Partner Team</p>
                </div>
                
                <div style="background: #333; color: white; padding: 20px; text-align: center; font-size: 12px;">
                    <p style="margin: 0;">This email was sent regarding your reseller application. Please do not reply to this automated message.</p>
                </div>
            </div>
            """,
            'text_body': f"""
Dear {application.contact_name},

Thank you for submitting your reseller partner application.

Application Details:
- Application ID: {application.application_id}
- Company: {application.company_name}
- Contact: {application.contact_name}
- Email: {application.contact_email}
- Submitted: {application.submitted_at.strftime('%B %d, %Y at %I:%M %p')}

Next Steps:
1. Our partner team will review your application within 24-48 business hours
2. You will receive an email update when your application moves to "Under Review" status
3. If approved, you'll receive welcome materials and portal access information
4. Our account manager will schedule an onboarding call within 48 hours of approval

Questions? Contact our partner team at partners@company.com or reference your Application ID: {application.application_id}

Best regards,
The Partner Team
            """
        }
    
    @staticmethod
    def application_under_review(application: ResellerApplication) -> Dict[str, str]:
        """Application under review email template"""
        return {
            'subject': f"Application Under Review - {application.application_id}",
            'html_body': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Application Under Review</h1>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Dear {application.contact_name},</p>
                    
                    <p>Great news! Your reseller partner application is now under active review by our team.</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #333; margin-top: 0;">Application Status Update</h3>
                        <p><strong>Application ID:</strong> {application.application_id}</p>
                        <p><strong>Company:</strong> {application.company_name}</p>
                        <p><strong>Current Status:</strong> Under Review</p>
                        <p><strong>Review Started:</strong> {application.reviewed_at.strftime('%B %d, %Y at %I:%M %p') if application.reviewed_at else 'Just now'}</p>
                    </div>
                    
                    <h3 style="color: #333;">What Happens Next</h3>
                    <ul style="line-height: 1.6;">
                        <li>Our team is evaluating your application details and qualifications</li>
                        <li>We may reach out for additional information if needed</li>
                        <li>You'll receive a final decision within 3-5 business days</li>
                        <li>Approved applications will receive immediate onboarding materials</li>
                    </ul>
                    
                    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                        <p style="margin: 0;"><strong>Please ensure your email and phone are monitored</strong> as we may need to contact you for clarification or additional information.</p>
                    </div>
                    
                    <p>Thank you for your patience during the review process.</p>
                    
                    <p>Best regards,<br>
                    The Partner Review Team</p>
                </div>
            </div>
            """,
            'text_body': f"""
Dear {application.contact_name},

Your reseller partner application is now under active review by our team.

Application Status Update:
- Application ID: {application.application_id}
- Company: {application.company_name}
- Current Status: Under Review
- Review Started: {application.reviewed_at.strftime('%B %d, %Y at %I:%M %p') if application.reviewed_at else 'Just now'}

What Happens Next:
1. Our team is evaluating your application details and qualifications
2. We may reach out for additional information if needed
3. You'll receive a final decision within 3-5 business days
4. Approved applications will receive immediate onboarding materials

Please ensure your email and phone are monitored as we may need to contact you.

Best regards,
The Partner Review Team
            """
        }
    
    @staticmethod
    def application_approved(application: ResellerApplication, reseller: Reseller) -> Dict[str, str]:
        """Application approval email template"""
        return {
            'subject': f"🎉 Welcome to Our Partner Program - {reseller.reseller_id}",
            'html_body': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 40px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🎉 Application Approved!</h1>
                    <p style="color: white; font-size: 18px; margin: 10px 0 0 0;">Welcome to Our Partner Program</p>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Dear {application.contact_name},</p>
                    
                    <p style="font-size: 18px; color: #28a745;"><strong>Congratulations! Your reseller application has been approved.</strong></p>
                    
                    <p>We're excited to welcome {application.company_name} to our partner program. You're now an official partner with full access to our systems and support.</p>
                    
                    <div style="background: white; padding: 25px; border-radius: 8px; margin: 25px 0; border: 2px solid #28a745;">
                        <h3 style="color: #333; margin-top: 0;">Your Partner Account Details</h3>
                        <p><strong>Reseller ID:</strong> <span style="background: #e8f5e8; padding: 5px 10px; border-radius: 4px; font-family: monospace;">{reseller.reseller_id}</span></p>
                        <p><strong>Company:</strong> {reseller.company_name}</p>
                        <p><strong>Status:</strong> Active Partner</p>
                        <p><strong>Commission Rate:</strong> {reseller.commission_rate_display}</p>
                        <p><strong>Agreement Start:</strong> {reseller.agreement_start_date.strftime('%B %d, %Y') if reseller.agreement_start_date else 'Today'}</p>
                    </div>
                    
                    <h3 style="color: #333;">Immediate Next Steps</h3>
                    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <ol style="line-height: 1.8; padding-left: 20px;">
                            <li><strong>Portal Access:</strong> You'll receive portal credentials within 24 hours</li>
                            <li><strong>Welcome Call:</strong> Our account manager will contact you within 48 hours</li>
                            <li><strong>Training Materials:</strong> Access links will be sent separately</li>
                            <li><strong>Marketing Kit:</strong> Download branded materials from your portal</li>
                            <li><strong>First Sale Support:</strong> Dedicated support for your first customer</li>
                        </ol>
                    </div>
                    
                    <h3 style="color: #333;">Partner Benefits You Now Have Access To</h3>
                    <ul style="line-height: 1.6;">
                        <li>✅ Commission on all sales ({reseller.commission_rate_display})</li>
                        <li>✅ Dedicated account manager support</li>
                        <li>✅ Marketing and sales materials</li>
                        <li>✅ Technical support and training</li>
                        <li>✅ Partner portal with real-time reporting</li>
                        <li>✅ Lead sharing opportunities</li>
                    </ul>
                    
                    <div style="background: #d1ecf1; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #bee5eb;">
                        <h4 style="margin-top: 0; color: #0c5460;">Important Contact Information</h4>
                        <p style="margin: 5px 0;"><strong>Account Manager:</strong> Will be assigned within 48 hours</p>
                        <p style="margin: 5px 0;"><strong>Partner Support:</strong> <a href="mailto:partners@company.com">partners@company.com</a></p>
                        <p style="margin: 5px 0;"><strong>Technical Support:</strong> <a href="mailto:tech-support@company.com">tech-support@company.com</a></p>
                        <p style="margin: 5px 0;"><strong>Your Reseller ID:</strong> {reseller.reseller_id} (always reference this)</p>
                    </div>
                    
                    <p>We're thrilled to have you as a partner and look forward to a successful relationship!</p>
                    
                    <p>Welcome to the team!</p>
                    
                    <p>Best regards,<br>
                    <strong>The Partner Team</strong></p>
                </div>
            </div>
            """,
            'text_body': f"""
Dear {application.contact_name},

CONGRATULATIONS! Your reseller application has been approved.

We're excited to welcome {application.company_name} to our partner program.

Your Partner Account Details:
- Reseller ID: {reseller.reseller_id}
- Company: {reseller.company_name}
- Status: Active Partner
- Commission Rate: {reseller.commission_rate_display}
- Agreement Start: {reseller.agreement_start_date.strftime('%B %d, %Y') if reseller.agreement_start_date else 'Today'}

Immediate Next Steps:
1. Portal Access: You'll receive portal credentials within 24 hours
2. Welcome Call: Our account manager will contact you within 48 hours
3. Training Materials: Access links will be sent separately
4. Marketing Kit: Download branded materials from your portal
5. First Sale Support: Dedicated support for your first customer

Important Contact Information:
- Partner Support: partners@company.com
- Technical Support: tech-support@company.com
- Your Reseller ID: {reseller.reseller_id} (always reference this)

Welcome to the team!

Best regards,
The Partner Team
            """
        }
    
    @staticmethod
    def application_rejected(application: ResellerApplication, reason: str) -> Dict[str, str]:
        """Application rejection email template"""
        return {
            'subject': f"Application Update - {application.application_id}",
            'html_body': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #6c757d; padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Application Update</h1>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Dear {application.contact_name},</p>
                    
                    <p>Thank you for your interest in becoming a partner with us. After careful review of your application, we have decided not to move forward at this time.</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #333; margin-top: 0;">Application Details</h3>
                        <p><strong>Application ID:</strong> {application.application_id}</p>
                        <p><strong>Company:</strong> {application.company_name}</p>
                        <p><strong>Decision Date:</strong> {application.decision_date.strftime('%B %d, %Y') if application.decision_date else datetime.now().strftime('%B %d, %Y')}</p>
                    </div>
                    
                    <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
                        <h4 style="margin-top: 0; color: #721c24;">Reason for Decision</h4>
                        <p style="margin: 0;">{reason}</p>
                    </div>
                    
                    <h3 style="color: #333;">Future Opportunities</h3>
                    <p>This decision is based on our current partnership needs and criteria. We encourage you to:</p>
                    <ul style="line-height: 1.6;">
                        <li>Continue building your business and experience</li>
                        <li>Consider reapplying in the future as our needs evolve</li>
                        <li>Stay connected with us through our newsletter and updates</li>
                    </ul>
                    
                    <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Questions about this decision?</strong> Contact our partner team at <a href="mailto:partners@company.com">partners@company.com</a> and reference Application ID: {application.application_id}</p>
                    </div>
                    
                    <p>Thank you again for your interest in partnering with us.</p>
                    
                    <p>Best regards,<br>
                    The Partner Review Team</p>
                </div>
            </div>
            """,
            'text_body': f"""
Dear {application.contact_name},

Thank you for your interest in becoming a partner with us. After careful review of your application, we have decided not to move forward at this time.

Application Details:
- Application ID: {application.application_id}
- Company: {application.company_name}
- Decision Date: {application.decision_date.strftime('%B %d, %Y') if application.decision_date else datetime.now().strftime('%B %d, %Y')}

Reason for Decision: {reason}

Future Opportunities:
This decision is based on our current partnership needs and criteria. We encourage you to:
- Continue building your business and experience
- Consider reapplying in the future as our needs evolve
- Stay connected with us through our newsletter and updates

Questions? Contact our partner team at partners@company.com and reference Application ID: {application.application_id}

Thank you again for your interest.

Best regards,
The Partner Review Team
            """
        }
    
    @staticmethod
    def welcome_package(reseller: Reseller) -> Dict[str, str]:
        """Welcome package email template"""
        return {
            'subject': f"🚀 Welcome Package & Getting Started - {reseller.reseller_id}",
            'html_body': f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🚀 Welcome Package</h1>
                    <p style="color: white; font-size: 18px; margin: 10px 0 0 0;">Everything You Need to Get Started</p>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Hello {reseller.primary_contact_name},</p>
                    
                    <p>Welcome to our partner program! This email contains everything you need to start selling and supporting customers.</p>
                    
                    <div style="background: white; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 5px solid #667eea;">
                        <h3 style="color: #333; margin-top: 0;">📋 30-Day Onboarding Checklist</h3>
                        <ul style="line-height: 1.8;">
                            <li>☐ Complete portal setup and training (Week 1)</li>
                            <li>☐ Review partner handbook and policies (Week 1)</li>
                            <li>☐ Download and customize marketing materials (Week 2)</li>
                            <li>☐ Complete product training modules (Week 2-3)</li>
                            <li>☐ Schedule launch strategy call with account manager (Week 3)</li>
                            <li>☐ Process first customer (Week 4)</li>
                        </ul>
                    </div>
                    
                    <h3 style="color: #333;">🔐 Portal Access</h3>
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <p><strong>Portal URL:</strong> https://partners.company.com</p>
                        <p><strong>Login credentials will be sent separately within 24 hours</strong></p>
                        <p>Your portal includes: customer management, sales reporting, commission tracking, marketing materials, and support tickets.</p>
                    </div>
                    
                    <h3 style="color: #333;">📚 Training & Resources</h3>
                    <ul style="line-height: 1.6;">
                        <li><strong>Partner Handbook:</strong> Complete policies and procedures</li>
                        <li><strong>Product Training:</strong> Technical specifications and features</li>
                        <li><strong>Sales Training:</strong> Best practices and competitive positioning</li>
                        <li><strong>Marketing Kit:</strong> Logos, brochures, case studies, and templates</li>
                        <li><strong>Installation Guides:</strong> Step-by-step technical documentation</li>
                    </ul>
                    
                    <h3 style="color: #333;">💰 Commission Structure</h3>
                    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <p><strong>Your Commission Rate:</strong> {reseller.commission_rate_display}</p>
                        <p><strong>Payment Terms:</strong> {reseller.payment_terms or 'Net 30'}</p>
                        <p><strong>Payment Method:</strong> {reseller.payment_method or 'Bank Transfer'}</p>
                        <p><strong>Commission Period:</strong> Monthly</p>
                        <p>Commissions are calculated on net revenue and paid monthly following the end of each period.</p>
                    </div>
                    
                    <h3 style="color: #333;">🎯 Your First 30 Days Goals</h3>
                    <ul style="line-height: 1.6;">
                        <li>Complete all training modules (80% completion rate target)</li>
                        <li>Set up your branded marketing materials</li>
                        <li>Identify and contact your first 10 prospects</li>
                        <li>Process your first customer installation</li>
                        <li>Establish regular communication rhythm with your account manager</li>
                    </ul>
                    
                    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <h4 style="margin-top: 0;">📞 Your Support Team</h4>
                        <p style="margin: 5px 0;"><strong>Account Manager:</strong> Will be assigned within 48 hours</p>
                        <p style="margin: 5px 0;"><strong>Technical Support:</strong> tech-support@company.com</p>
                        <p style="margin: 5px 0;"><strong>Sales Support:</strong> sales-support@company.com</p>
                        <p style="margin: 5px 0;"><strong>Partner Help:</strong> partners@company.com</p>
                        <p style="margin: 5px 0;"><strong>Emergency Support:</strong> 1-800-XXX-XXXX</p>
                    </div>
                    
                    <p>We're here to support your success every step of the way. Don't hesitate to reach out with questions!</p>
                    
                    <p>Ready to get started?</p>
                    
                    <p>Best regards,<br>
                    <strong>The Partner Success Team</strong></p>
                </div>
            </div>
            """,
            'text_body': f"""
Hello {reseller.primary_contact_name},

Welcome to our partner program! This email contains everything you need to start selling and supporting customers.

30-Day Onboarding Checklist:
☐ Complete portal setup and training (Week 1)
☐ Review partner handbook and policies (Week 1)
☐ Download and customize marketing materials (Week 2)
☐ Complete product training modules (Week 2-3)
☐ Schedule launch strategy call with account manager (Week 3)
☐ Process first customer (Week 4)

Portal Access:
- Portal URL: https://partners.company.com
- Login credentials will be sent separately within 24 hours

Commission Structure:
- Your Commission Rate: {reseller.commission_rate_display}
- Payment Terms: {reseller.payment_terms or 'Net 30'}
- Payment Method: {reseller.payment_method or 'Bank Transfer'}

Your Support Team:
- Technical Support: tech-support@company.com
- Sales Support: sales-support@company.com
- Partner Help: partners@company.com
- Emergency Support: 1-800-XXX-XXXX

Ready to get started!

Best regards,
The Partner Success Team
            """
        }


class EnhancedEmailService:
    """Enhanced email service with professional templates"""
    
    def __init__(self, smtp_config: Optional[Dict[str, str]] = None):
        self.smtp_config = smtp_config or {}
        self.templates = EmailTemplates()
    
    async def send_application_confirmation(self, application: ResellerApplication) -> bool:
        """Send professional application confirmation email"""
        template = self.templates.application_confirmation(application)
        return await self._send_email(
            to_email=application.contact_email,
            to_name=application.contact_name,
            subject=template['subject'],
            html_body=template['html_body'],
            text_body=template['text_body']
        )
    
    async def send_application_under_review(self, application: ResellerApplication) -> bool:
        """Send application under review notification"""
        template = self.templates.application_under_review(application)
        return await self._send_email(
            to_email=application.contact_email,
            to_name=application.contact_name,
            subject=template['subject'],
            html_body=template['html_body'],
            text_body=template['text_body']
        )
    
    async def send_application_approved(self, application: ResellerApplication, reseller: Reseller) -> bool:
        """Send application approval notification"""
        template = self.templates.application_approved(application, reseller)
        return await self._send_email(
            to_email=application.contact_email,
            to_name=application.contact_name,
            subject=template['subject'],
            html_body=template['html_body'],
            text_body=template['text_body']
        )
    
    async def send_application_rejected(self, application: ResellerApplication, reason: str) -> bool:
        """Send application rejection notification"""
        template = self.templates.application_rejected(application, reason)
        return await self._send_email(
            to_email=application.contact_email,
            to_name=application.contact_name,
            subject=template['subject'],
            html_body=template['html_body'],
            text_body=template['text_body']
        )
    
    async def send_welcome_package(self, reseller: Reseller) -> bool:
        """Send comprehensive welcome package"""
        template = self.templates.welcome_package(reseller)
        return await self._send_email(
            to_email=reseller.primary_contact_email,
            to_name=reseller.primary_contact_name,
            subject=template['subject'],
            html_body=template['html_body'],
            text_body=template['text_body']
        )
    
    async def _send_email(
        self, 
        to_email: str, 
        to_name: str,
        subject: str, 
        html_body: str, 
        text_body: str
    ) -> bool:
        """Send email using configured SMTP or email service"""
        
        # For development/testing, log the email
        print(f"\n📧 EMAIL SENT TO: {to_name} <{to_email}>")
        print(f"📧 SUBJECT: {subject}")
        print(f"📧 TIMESTAMP: {datetime.now().isoformat()}")
        print("📧 CONTENT: [Professional HTML email sent]")
        
        # In production, integrate with actual email service:
        # - AWS SES
        # - SendGrid
        # - Mailgun
        # - SMTP server
        
        # Example integration structure:
        # if self.smtp_config.get('provider') == 'ses':
        #     return await self._send_via_ses(to_email, subject, html_body, text_body)
        # elif self.smtp_config.get('provider') == 'sendgrid':
        #     return await self._send_via_sendgrid(to_email, subject, html_body, text_body)
        
        return True
    
    async def _send_via_ses(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send via AWS SES (example implementation)"""
        # Implementation would go here
        pass
    
    async def _send_via_sendgrid(self, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
        """Send via SendGrid (example implementation)"""
        # Implementation would go here
        pass


# Export classes
__all__ = [
    "EmailTemplates",
    "EnhancedEmailService"
]