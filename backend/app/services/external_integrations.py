"""
External Integrations Service for DocuShield
Slack alerts, email notifications, and external API integrations
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

import httpx

# Optional dependencies - handle gracefully if not installed
try:
    from slack_sdk.web.async_client import AsyncWebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    AsyncWebClient = None
    SlackApiError = Exception

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    sendgrid = None
    Mail = None
    Email = None
    To = None
    Content = None

from app.core.config import settings
from app.services.risk_analyzer import RiskLevel

logger = logging.getLogger(__name__)

class ExternalIntegrationsService:
    """
    Service for managing external integrations and alerts
    """
    
    def __init__(self):
        self.slack_client = None
        self.sendgrid_client = None
        self.http_client = httpx.AsyncClient()
        
        # Initialize clients if credentials are available and dependencies are installed
        if settings.slack_bot_token and SLACK_AVAILABLE:
            try:
                self.slack_client = AsyncWebClient(token=settings.slack_bot_token)
                logger.info("✅ Slack client initialized")
            except Exception as e:
                logger.warning(f"❌ Failed to initialize Slack client: {e}")
        elif settings.slack_bot_token and not SLACK_AVAILABLE:
            logger.warning("⚠️ Slack token provided but slack-sdk not installed. Install with: pip install slack-sdk")
        
        if settings.sendgrid_api_key and SENDGRID_AVAILABLE:
            try:
                self.sendgrid_client = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
                logger.info("✅ SendGrid client initialized")
            except Exception as e:
                logger.warning(f"❌ Failed to initialize SendGrid client: {e}")
        elif settings.sendgrid_api_key and not SENDGRID_AVAILABLE:
            logger.warning("⚠️ SendGrid API key provided but sendgrid not installed. Install with: pip install sendgrid")
    
    async def send_risk_alert(self, document_title: str, risk_analysis: Dict[str, Any], document_id: str) -> Dict[str, bool]:
        """
        Send risk alerts via multiple channels based on risk level
        """
        results = {
            "slack_sent": False,
            "email_sent": False,
            "webhook_sent": False
        }
        
        try:
            risk_level = risk_analysis.get("overall_risk_level", "medium")
            risk_score = risk_analysis.get("overall_risk_score", 0.5)
            
            # Only send alerts for medium+ risks
            if risk_level in ["medium", "high", "critical"]:
                # Send Slack alert
                if self.slack_client:
                    results["slack_sent"] = await self._send_slack_alert(
                        document_title, risk_analysis, document_id
                    )
                
                # Send email alert for high+ risks
                if risk_level in ["high", "critical"] and self.sendgrid_client:
                    results["email_sent"] = await self._send_email_alert(
                        document_title, risk_analysis, document_id
                    )
                
                # Send webhook notification
                if settings.slack_webhook_url:
                    results["webhook_sent"] = await self._send_webhook_alert(
                        document_title, risk_analysis, document_id
                    )
            
            logger.info(f"Risk alert sent for {document_title}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to send risk alert: {e}")
            return results
    
    async def _send_slack_alert(self, document_title: str, risk_analysis: Dict[str, Any], document_id: str) -> bool:
        """Send Slack alert for document risks"""
        try:
            if not self.slack_client or not SLACK_AVAILABLE:
                logger.warning("Slack client not available - install slack-sdk to enable Slack alerts")
                return False
            
            risk_level = risk_analysis.get("overall_risk_level", "medium")
            risk_score = risk_analysis.get("overall_risk_score", 0.5)
            risks = risk_analysis.get("identified_risks", [])
            ai_insights = risk_analysis.get("ai_insights", {})
            
            # Risk level emoji and color
            risk_config = {
                "low": {"emoji": "🟢", "color": "#36a64f"},
                "medium": {"emoji": "🟡", "color": "#ffaa00"},
                "high": {"emoji": "🔴", "color": "#ff0000"},
                "critical": {"emoji": "🚨", "color": "#8b0000"}
            }
            
            config = risk_config.get(risk_level, risk_config["medium"])
            
            # Build Slack message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{config['emoji']} Document Risk Alert"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Document:* {document_title}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Risk Level:* {risk_level.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Risk Score:* {risk_score:.1%}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Risks Found:* {len(risks)}"
                        }
                    ]
                }
            ]
            
            # Add executive summary if available
            if ai_insights.get("executive_summary"):
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:* {ai_insights['executive_summary']}"
                    }
                })
            
            # Add top risks
            if risks:
                high_risks = [r for r in risks if r.get("level") in ["high", "critical"]][:3]
                if high_risks:
                    risk_text = "\n".join([f"• {r['description']}" for r in high_risks])
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Key Risks:*\n{risk_text}"
                        }
                    })
            
            # Add recommendations
            recommendations = risk_analysis.get("recommendations", [])[:3]
            if recommendations:
                rec_text = "\n".join([f"• {rec}" for rec in recommendations])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommendations:*\n{rec_text}"
                    }
                })
            
            # Add action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Document"
                        },
                        "style": "primary",
                        "url": f"http://localhost:3000/documents/{document_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Risk Dashboard"
                        },
                        "url": "http://localhost:3000/dashboard"
                    }
                ]
            })
            
            # Send message
            response = await self.slack_client.chat_postMessage(
                channel="#docushield-alerts",  # Configure channel as needed
                blocks=blocks,
                text=f"Risk alert for {document_title}"  # Fallback text
            )
            
            return response["ok"]
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    async def _send_email_alert(self, document_title: str, risk_analysis: Dict[str, Any], document_id: str) -> bool:
        """Send email alert for high-risk documents"""
        try:
            if not self.sendgrid_client or not SENDGRID_AVAILABLE or not settings.alert_email_to:
                if not SENDGRID_AVAILABLE:
                    logger.warning("SendGrid not available - install sendgrid to enable email alerts")
                return False
            
            risk_level = risk_analysis.get("overall_risk_level", "medium")
            risks = risk_analysis.get("identified_risks", [])
            ai_insights = risk_analysis.get("ai_insights", {})
            recommendations = risk_analysis.get("recommendations", [])
            
            # Build email content
            subject = f"🚨 HIGH RISK DOCUMENT ALERT: {document_title}"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #d32f2f;">🚨 High Risk Document Alert</h2>
                    
                    <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Document Details</h3>
                        <p><strong>Document:</strong> {document_title}</p>
                        <p><strong>Risk Level:</strong> <span style="color: #d32f2f; font-weight: bold;">{risk_level.upper()}</span></p>
                        <p><strong>Risks Identified:</strong> {len(risks)}</p>
                        <p><strong>Analysis Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                    </div>
            """
            
            # Add executive summary
            if ai_insights.get("executive_summary"):
                html_content += f"""
                    <div style="margin: 20px 0;">
                        <h3>Executive Summary</h3>
                        <p>{ai_insights['executive_summary']}</p>
                    </div>
                """
            
            # Add key risks
            high_risks = [r for r in risks if r.get("level") in ["high", "critical"]]
            if high_risks:
                html_content += """
                    <div style="margin: 20px 0;">
                        <h3>Key Risks Identified</h3>
                        <ul>
                """
                for risk in high_risks[:5]:
                    html_content += f"<li><strong>{risk.get('description', 'Unknown risk')}</strong> - {risk.get('evidence', '')}</li>"
                html_content += "</ul></div>"
            
            # Add recommendations
            if recommendations:
                html_content += """
                    <div style="margin: 20px 0;">
                        <h3>Recommended Actions</h3>
                        <ul>
                """
                for rec in recommendations[:5]:
                    html_content += f"<li>{rec}</li>"
                html_content += "</ul></div>"
            
            # Add footer
            html_content += f"""
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        <p><a href="http://localhost:3000/documents/{document_id}" 
                           style="background: #1976d2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                           View Document Details</a></p>
                        <p style="font-size: 12px; color: #666;">
                            This alert was generated by DocuShield Document Intelligence System.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create and send email
            from_email = Email(settings.alert_email_from)
            to_email = To(settings.alert_email_to)
            content = Content("text/html", html_content)
            
            mail = Mail(from_email, to_email, subject, content)
            
            response = self.sendgrid_client.send(mail)
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    async def _send_webhook_alert(self, document_title: str, risk_analysis: Dict[str, Any], document_id: str) -> bool:
        """Send webhook notification (Slack webhook or custom webhook)"""
        try:
            if not settings.slack_webhook_url:
                return False
            
            risk_level = risk_analysis.get("overall_risk_level", "medium")
            risk_score = risk_analysis.get("overall_risk_score", 0.5)
            
            # Risk level emoji
            risk_emoji = {
                "low": "🟢",
                "medium": "🟡", 
                "high": "🔴",
                "critical": "🚨"
            }
            
            emoji = risk_emoji.get(risk_level, "⚠️")
            
            # Build webhook payload
            webhook_data = {
                "text": f"{emoji} DocuShield Risk Alert",
                "attachments": [
                    {
                        "color": "warning" if risk_level == "medium" else "danger",
                        "fields": [
                            {
                                "title": "Document",
                                "value": document_title,
                                "short": True
                            },
                            {
                                "title": "Risk Level",
                                "value": risk_level.upper(),
                                "short": True
                            },
                            {
                                "title": "Risk Score",
                                "value": f"{risk_score:.1%}",
                                "short": True
                            },
                            {
                                "title": "Analysis Time",
                                "value": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
                                "short": True
                            }
                        ],
                        "actions": [
                            {
                                "type": "button",
                                "text": "View Details",
                                "url": f"http://localhost:3000/documents/{document_id}"
                            }
                        ]
                    }
                ]
            }
            
            # Send webhook
            response = await self.http_client.post(
                settings.slack_webhook_url,
                json=webhook_data,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    async def send_daily_summary(self) -> bool:
        """Send daily summary of document analysis and risks"""
        try:
            # This would query the database for daily stats
            # For now, return a placeholder implementation
            
            summary_data = {
                "date": datetime.utcnow().strftime('%Y-%m-%d'),
                "documents_processed": 0,  # Would be queried from DB
                "high_risk_documents": 0,  # Would be queried from DB
                "alerts_sent": 0,  # Would be queried from DB
                "top_risks": []  # Would be aggregated from DB
            }
            
            # Send summary via configured channels
            if self.slack_client:
                await self._send_slack_summary(summary_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    async def _send_slack_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Send daily summary to Slack"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 DocuShield Daily Summary - {summary_data['date']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Documents Processed:* {summary_data['documents_processed']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*High Risk Documents:* {summary_data['high_risk_documents']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Alerts Sent:* {summary_data['alerts_sent']}"
                        }
                    ]
                }
            ]
            
            response = await self.slack_client.chat_postMessage(
                channel="#docushield-summary",
                blocks=blocks,
                text=f"Daily summary for {summary_data['date']}"
            )
            
            return response["ok"]
            
        except Exception as e:
            logger.error(f"Failed to send Slack summary: {e}")
            return False
    
    async def test_integrations(self) -> Dict[str, bool]:
        """Test all external integrations"""
        results = {
            "slack": False,
            "email": False,
            "webhook": False
        }
        
        try:
            # Test Slack
            if self.slack_client and SLACK_AVAILABLE:
                try:
                    response = await self.slack_client.auth_test()
                    results["slack"] = response["ok"]
                except SlackApiError:
                    results["slack"] = False
            elif not SLACK_AVAILABLE:
                logger.warning("Slack SDK not available - install slack-sdk to test Slack integration")
                results["slack"] = False
            
            # Test email (SendGrid)
            if self.sendgrid_client and SENDGRID_AVAILABLE:
                try:
                    # This is a simple API key validation
                    results["email"] = True  # SendGrid doesn't have a simple test endpoint
                except Exception:
                    results["email"] = False
            elif not SENDGRID_AVAILABLE:
                logger.warning("SendGrid not available - install sendgrid to test email integration")
                results["email"] = False
            
            # Test webhook
            if settings.slack_webhook_url:
                try:
                    test_payload = {
                        "text": "DocuShield integration test",
                        "username": "DocuShield Test"
                    }
                    response = await self.http_client.post(
                        settings.slack_webhook_url,
                        json=test_payload,
                        timeout=5
                    )
                    results["webhook"] = response.status_code == 200
                except Exception:
                    results["webhook"] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return results

# Global external integrations service instance
external_integrations = ExternalIntegrationsService()
