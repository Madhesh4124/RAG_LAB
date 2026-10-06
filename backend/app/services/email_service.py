"""Email service for password resets and API error alerts via Brevo or SMTP."""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails via Brevo HTTPS REST API (preferred for cloud hosting) or SMTP."""

    def __init__(self):
        # Brevo API configuration (HTTPS - works on Hugging Face Spaces, Render, Vercel, etc.)
        self.brevo_api_key = os.getenv("BREVO_API_KEY", "").strip()
        self.brevo_sender_email = os.getenv(
            "BREVO_SENDER_EMAIL",
            os.getenv("SMTP_SENDER_EMAIL", "madhesh4124@gmail.com")
        ).strip()
        self.brevo_sender_name = os.getenv("BREVO_SENDER_NAME", "RAG Lab").strip()

        # SMTP configuration (fallback for local dev)
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SMTP_SENDER_EMAIL", "")
        self.sender_password = os.getenv("SMTP_SENDER_PASSWORD", "")
        self.admin_email = os.getenv("ADMIN_EMAIL", "")

        self.enabled = bool(self.brevo_api_key or (self.sender_email and self.sender_password))

    def send_password_reset_email(self, recipient_email: str, reset_token: str, reset_url: Optional[str] = None) -> bool:
        """Send password reset email with token."""
        if not reset_url:
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
            reset_url = f"{frontend_url}/reset-password?token={reset_token}"

        # Guaranteed fallback: Always log reset link so admin/dev can find it in server logs
        logger.info("[AUTH] Password reset requested for %s. Reset link: %s", recipient_email, reset_url)

        if not self.enabled:
            logger.warning("Email service disabled (no BREVO_API_KEY or SMTP credentials). Link logged above.")
            return False

        subject = "RAG Lab - Password Reset Request"
        body = f"""
        <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #111827; padding: 24px; border-radius: 12px; color: #f3f4f6;">
                    <h2 style="margin-top: 0; color: #fbbf24;">RAG Lab — Password Reset</h2>
                    <p style="color: #e5e7eb;">You requested a password reset for your RAG Lab account.</p>
                    <p style="color: #9ca3af; font-size: 14px;">Click the button below to set a new password (valid for 30 minutes):</p>
                    <div style="margin: 25px 0;">
                        <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background-color: #8b5cf6; color: #ffffff; text-decoration: none; font-weight: 600; border-radius: 8px;">Reset Password</a>
                    </div>
                    <p style="font-size: 12px; color: #9ca3af; word-break: break-all;">
                        Or open this link directly in your browser:<br/>
                        <a href="{reset_url}" style="color: #a78bfa;">{reset_url}</a>
                    </p>
                    <hr style="border: none; border-top: 1px solid #374151; margin: 20px 0;" />
                    <p style="font-size: 11px; color: #6b7280; margin-bottom: 0;">If you didn't request this reset, you can safely ignore this email.</p>
                </div>
            </body>
        </html>
        """

        try:
            return self._send_email(recipient_email, subject, body)
        except Exception as e:
            logger.error("Failed to send password reset email to %s: %s", recipient_email, e)
            return False

    def send_rate_limit_alert(self, user_email: str, username: str, api_error: str, error_message: str) -> bool:
        """Send alert to admin when 429 rate limit error occurs."""
        if not self.admin_email or not self.enabled:
            logger.warning("Email service disabled or admin email not set. Rate limit alert not sent.")
            return False

        subject = f"[RAG Lab Alert] API Rate Limit Exceeded - {api_error}"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
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
            logger.error("Failed to send rate limit alert to admin: %s", e)
            return False

    def _send_email(self, recipient: str, subject: str, html_body: str) -> bool:
        """Internal method to send email via Brevo HTTPS REST API (preferred) or SMTP."""
        if self.brevo_api_key:
            return self._send_via_brevo(recipient, subject, html_body)
        return self._send_via_smtp(recipient, subject, html_body)

    def _send_via_brevo(self, recipient: str, subject: str, html_body: str) -> bool:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "api-key": self.brevo_api_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "sender": {
                            "name": self.brevo_sender_name,
                            "email": self.brevo_sender_email,
                        },
                        "to": [
                            {"email": recipient}
                        ],
                        "subject": subject,
                        "htmlContent": html_body,
                    },
                )
                if res.status_code in (200, 201):
                    msg_id = res.json().get("messageId", "ok")
                    logger.info("Email sent successfully to %s via Brevo API (id: %s)", recipient, msg_id)
                    return True
                else:
                    logger.error(
                        "Brevo API error sending email to %s (HTTP %s): %s",
                        recipient,
                        res.status_code,
                        res.text,
                    )
                    return False
        except Exception as exc:
            logger.error("Error connecting to Brevo API for %s: %s", recipient, exc)
            return False

    def _send_via_smtp(self, recipient: str, subject: str, html_body: str) -> bool:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient

            part = MIMEText(html_body, "html")
            message.attach(part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, message.as_string())

            logger.info("Email sent successfully to %s via SMTP", recipient)
            return True
        except Exception as e:
            logger.error("Error sending email via SMTP to %s: %s", recipient, e)
            return False
