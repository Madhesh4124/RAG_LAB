"""Email service for password resets and API error alerts."""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails via SMTP for password resets and alerts."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SMTP_SENDER_EMAIL", "")
        self.sender_password = os.getenv("SMTP_SENDER_PASSWORD", "")
        self.admin_email = os.getenv("ADMIN_EMAIL", "")
        self.enabled = bool(self.sender_email and self.sender_password)

    def send_password_reset_email(self, recipient_email: str, reset_token: str, reset_url: Optional[str] = None) -> bool:
        """Send password reset email with token."""
        if not self.enabled:
            logger.warning(f"Email service disabled. Password reset email not sent to {recipient_email}")
            return False

        if not reset_url:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            reset_url = f"{frontend_url}/reset-password?token={reset_token}"

        subject = "RAG Lab - Password Reset Request"
        body = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>You requested a password reset for your RAG Lab account.</p>
                <p>Click the link below to reset your password (valid for 30 minutes):</p>
                <p><a href="{reset_url}">{reset_url}</a></p>
                <p>If you did not request this reset, please ignore this email.</p>
                <p>Your RAG Lab Team</p>
            </body>
        </html>
        """

        try:
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            logger.error(f"Failed to send password reset email to {recipient_email}: {e}")
            return False

    def send_rate_limit_alert(self, user_email: str, username: str, api_error: str, error_message: str) -> bool:
        """Send alert to admin when 429 rate limit error occurs."""
        if not self.admin_email or not self.enabled:
            logger.warning(f"Email service disabled or admin email not set. Rate limit alert not sent.")
            return False

        subject = f"[RAG Lab Alert] API Rate Limit Exceeded - {api_error}"
        body = f"""
        <html>
            <body>
                <h2>API Rate Limit Exceeded</h2>
                <p><strong>User:</strong> {username} ({user_email})</p>
                <p><strong>Error Type:</strong> {api_error}</p>
                <p><strong>Error Message:</strong> {error_message}</p>
                <p><strong>Action Required:</strong> Please review and rotate API keys if necessary.</p>
                <p>RAG Lab Monitoring System</p>
            </body>
        </html>
        """

        try:
            return self._send_email(self.admin_email, subject, body)
        except Exception as e:
            logger.error(f"Failed to send rate limit alert to admin: {e}")
            return False

    def _send_email(self, recipient: str, subject: str, html_body: str) -> bool:
        """Internal method to send email via SMTP."""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient

            part = MIMEText(html_body, "html")
            message.attach(part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, message.as_string())

            logger.info(f"Email sent successfully to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Error sending email to {recipient}: {e}")
            return False
