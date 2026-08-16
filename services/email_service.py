import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
import os
from config.email_config import email_config
from database import record_email_log

logger = logging.getLogger("email_service")

class EmailService:
    """Send transactional and notification emails via Gmail SMTP."""

    @staticmethod
    async def send_welcome_email(
        recipient_email: str,
        user_name: str = "",
        user_id: int = None
    ) -> dict:
        """
        Send branded welcome email to new Google Sign-In student.
        """
        recipient_clean = (recipient_email or "").strip().lower()
        if not recipient_clean:
            return {"status": "failed", "message": "Recipient email is missing"}

        display_name = user_name.strip() if user_name else recipient_clean.split("@")[0].title()
        subject = "Welcome to BU Prepz AI! 🎓 Your Academic Edge is Ready"
        login_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to BU Prepz AI</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0b0f19; padding: 30px 15px;">
                <tr>
                    <td align="center">
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 580px; background: #151c2e; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.1); overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6);">
                            <!-- Header Banner -->
                            <tr>
                                <td style="padding: 34px 32px 24px; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); text-align: center;">
                                    <div style="font-size: 40px; margin-bottom: 8px;">🎓</div>
                                    <h1 style="margin: 0; color: #ffffff; font-size: 25px; font-weight: 800; letter-spacing: -0.5px;">BU Prepz AI</h1>
                                    <p style="margin: 6px 0 0; color: #e0e7ff; font-size: 13.5px;">Bennett University Exam Preparation & Academic Intelligence Platform</p>
                                </td>
                            </tr>

                            <!-- Body Content -->
                            <tr>
                                <td style="padding: 32px;">
                                    <h2 style="margin: 0 0 14px; color: #ffffff; font-size: 20px; font-weight: 700;">Welcome, {display_name}! 👋</h2>
                                    <p style="margin: 0 0 20px; color: #cbd5e1; font-size: 14.5px; line-height: 1.6;">
                                        Your <strong>BU Prepz AI</strong> workspace account is now active via Google Sign-In (<strong>{recipient_clean}</strong>) as of <em>{login_time}</em>.
                                    </p>

                                    <!-- Quick Feature Highlights -->
                                    <div style="background: rgba(11, 15, 25, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                                        <div style="color: #818cf8; font-weight: 700; font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px;">What You Can Do Now:</div>
                                        
                                        <div style="margin-bottom: 12px; display: flex; align-items: flex-start;">
                                            <span style="margin-right: 12px; font-size: 16px;">⚡</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.45;"><strong>AI Doubt Solver:</strong> Ask complex engineering questions and get instant step-by-step verified solutions.</span>
                                        </div>
                                        <div style="margin-bottom: 12px; display: flex; align-items: flex-start;">
                                            <span style="margin-right: 12px; font-size: 16px;">🎯</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.45;"><strong>Concept Weakness Profiler:</strong> Diagnose prerequisite blocker gaps and take adaptive practice tests.</span>
                                        </div>
                                        <div style="margin-bottom: 12px; display: flex; align-items: flex-start;">
                                            <span style="margin-right: 12px; font-size: 16px;">📚</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.45;"><strong>Course Repository:</strong> Access notes, PYQs, tutorials, lab manuals, and faculty playlists.</span>
                                        </div>
                                        <div style="display: flex; align-items: flex-start;">
                                            <span style="margin-right: 12px; font-size: 16px;">📈</span>
                                            <span style="color: #e2e8f0; font-size: 13.5px; line-height: 1.45;"><strong>Exam Paper Predictor:</strong> Analyze recurring mid-term & end-term question recurrence patterns.</span>
                                        </div>
                                    </div>

                                    <!-- Launch Button -->
                                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 24px;">
                                        <tr>
                                            <td align="center">
                                                <a href="https://om123bansal-prepz-app.hf.space" style="display: inline-block; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; font-weight: 700; font-size: 14.5px; text-decoration: none; padding: 13px 30px; border-radius: 10px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45);">
                                                    Open BU Prepz Workspace &rarr;
                                                </a>
                                            </td>
                                        </tr>
                                    </table>

                                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 16px; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                                        <p style="margin: 0;">🔒 <strong>Security Note:</strong> This notification confirms your Google sign-in. If you did not initiate this, please review your Google account security immediately.</p>
                                    </div>
                                </td>
                            </tr>

                            <!-- Footer -->
                            <tr>
                                <td style="padding: 20px 32px; background: #0b0f19; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); color: #64748b; font-size: 11.5px;">
                                    &copy; {datetime.now().year} BU Prepz AI &bull; Bennett University Engineering Intelligence Platform &bull; All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        # Dispatch via Gmail SMTP
        if email_config.GMAIL_USERNAME and email_config.GMAIL_APP_PASSWORD:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = email_config.MAIL_FROM
                msg["To"] = recipient_clean
                msg.attach(MIMEText(html_content, "html"))

                server = smtplib.SMTP(email_config.MAIL_SERVER, email_config.MAIL_PORT, timeout=email_config.MAIL_TIMEOUT)
                if email_config.MAIL_STARTTLS:
                    server.starttls()
                server.login(email_config.GMAIL_USERNAME, email_config.GMAIL_APP_PASSWORD)
                server.send_message(msg)
                server.quit()

                # Audit Log
                record_email_log(
                    user_id=user_id,
                    recipient_email=recipient_clean,
                    email_type="welcome",
                    subject=subject,
                    status="success"
                )
                logger.info(f"Welcome email successfully delivered to {recipient_clean}")
                return {"status": "success", "message": "Welcome email sent", "recipient": recipient_clean}

            except Exception as e:
                logger.error(f"Gmail SMTP dispatch failed for {recipient_clean}: {e}")
                record_email_log(
                    user_id=user_id,
                    recipient_email=recipient_clean,
                    email_type="welcome",
                    subject=subject,
                    status="failed",
                    error_message=str(e)
                )
                return {"status": "failed", "message": "Email sending failed", "error": str(e)}
        else:
            logger.info(f"SMTP credentials not configured. Mock logged welcome email to: {recipient_clean}")
            record_email_log(
                user_id=user_id,
                recipient_email=recipient_clean,
                email_type="welcome",
                subject=subject,
                status="logged_mock",
                error_message="SMTP credentials not provided in .env"
            )
            return {"status": "success", "message": "Welcome email logged (dev mode)", "recipient": recipient_clean}

email_service = EmailService()
