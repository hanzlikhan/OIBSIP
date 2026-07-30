"""
Email Action module.
Implements secure email sending via SMTP and a dry-run local outbox simulator.
"""

import os
import time
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from actions.base import BaseAction
from config.settings import settings
from core.nlu import INTENT_EMAIL

class EmailSenderAction(BaseAction):
    @property
    def name(self) -> str:
        return INTENT_EMAIL

    def execute(self, entities: dict) -> dict:
        recipient = entities.get("recipient", "").strip()
        body = entities.get("body", "").strip()

        # Input validations
        if not recipient:
            return {
                "speech": "Who would you like me to send the email to? Please specify a recipient name or email address.",
                "ui_data": {"status": "error", "message": "Missing recipient"}
            }
        
        if not body:
            return {
                "speech": f"What is the message you want to send to {recipient}?",
                "ui_data": {"status": "error", "message": "Missing body", "recipient": recipient}
            }

        # Subject line defaults
        subject = "Spoken Message via Nova Voice Assistant"

        # Check simulation mode (Local outbox fallback)
        if settings.DEBUG_MODE:
            return self._simulate_email(recipient, subject, body)
        else:
            return self._send_live_email(recipient, subject, body)

    def _simulate_email(self, recipient: str, subject: str, body: str) -> dict:
        """Simulates email transmission by writing files to a local outbox directory."""
        filename = f"email_{int(time.time())}_{recipient.replace('@', '_at_')}.txt"
        file_path = settings.OUTBOX_DIR / filename
        
        email_content = (
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S local')}\n"
            f"From: {settings.SMTP_FROM_EMAIL or 'nova-assistant-simulation@local'}\n"
            f"To: {recipient}\n"
            f"Subject: {subject}\n"
            f"-----------------------------------------\n"
            f"Body:\n{body}\n"
        )
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(email_content)
                
            speech_text = f"I've simulated sending the email to {recipient} and saved it to the local outbox directory."
            return {
                "speech": speech_text,
                "ui_data": {
                    "status": "simulated",
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "file_path": str(file_path.resolve())
                }
            }
        except Exception as e:
            print(f"Failed to write simulated email: {e}", file=sys.stderr)
            return {
                "speech": "I encountered an error writing the simulated email to the local outbox directory.",
                "ui_data": {"status": "error", "message": str(e)}
            }

    def _send_live_email(self, recipient: str, subject: str, body: str) -> dict:
        """Sends a live email using smtplib and settings credentials."""
        # Simple email validation
        if "@" not in recipient or "." not in recipient:
            return {
                "speech": f"The recipient '{recipient}' does not appear to be a valid email address. SMTP sending requires a full address.",
                "ui_data": {"status": "error", "message": "Invalid email format"}
            }

        # Check if settings are missing
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            return {
                "speech": "SMTP email credentials are not configured in the environment settings file. I cannot send live emails.",
                "ui_data": {"status": "error", "message": "SMTP credentials missing"}
            }

        try:
            # Construct mime message
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Connect and send
            print(f"Connecting to SMTP server {settings.SMTP_SERVER}:{settings.SMTP_PORT}...")
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10)
            server.starttls()  # Upgrade connection to secure TLS
            
            print(f"Logging in as {settings.SMTP_USER}...")
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            print("Sending mail payload...")
            server.sendmail(msg["From"], recipient, msg.as_string())
            server.quit()
            
            speech_text = f"I have successfully sent the email to {recipient}."
            return {
                "speech": speech_text,
                "ui_data": {
                    "status": "sent",
                    "recipient": recipient,
                    "subject": subject,
                    "body": body
                }
            }
        except smtplib.SMTPAuthenticationError:
            return {
                "speech": "Email authentication failed. Please verify your SMTP password or use an app-specific password.",
                "ui_data": {"status": "error", "message": "SMTPAuthenticationError"}
            }
        except smtplib.SMTPConnectError:
            return {
                "speech": f"Could not connect to the SMTP server at {settings.SMTP_SERVER}. Check port configuration and internet connection.",
                "ui_data": {"status": "error", "message": "SMTPConnectError"}
            }
        except Exception as e:
            print(f"SMTP error: {e}", file=sys.stderr)
            return {
                "speech": "I had an unexpected problem trying to send that email.",
                "ui_data": {"status": "error", "message": str(e)}
            }
