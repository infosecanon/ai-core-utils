"""
Provides standardized functions for sending alerts, e.g., via email.

This module relies on the MONITORING settings in the global config.
"""

import logging
import smtplib
import traceback
from email.message import EmailMessage

# Import the settings singleton from our config module
from .config import settings

# Get a logger instance for this module
logger = logging.getLogger("core.alerting")


def send_error_email(
    exc: Exception, main_function_name: str, subject_prefix: str = "[ALERT]"
) -> None:
    """
    Sends a formatted error email when an exception occurs.

    Reads all configuration (recipients, SMTP server, etc.)
    from the global `settings` object.

    Args:
        exc: The exception object that was caught.
        main_function_name: The name of the function/script where
                            the error occurred.
        subject_prefix: A prefix for the email subject (e.g., "[ALERT]").
    """
    # --- Check that we have at least one recipient ----------
    recipients = settings.MONITORING.EMAIL_RECIPIENTS

    logger.info(f"Checking recipients: {recipients}")

    if not recipients or all(not r for r in recipients):
        logger.warning("No EMAIL_RECIPIENTS configured")
        return

    # --- Build the message ----------------------------------
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    subject = f"{subject_prefix} Exception in {main_function_name}"
    body = f"An exception occurred in {main_function_name}:\n\n{tb}"
    msg = EmailMessage()
    msg["From"] = settings.MONITORING.SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    logger.info(
        f"Sending the email:\n \
        From: {msg['From']}\n \
        To: {msg['To']}\n \
        Subject: {msg['Subject']}"
    )

    # --- Send the message ------------------------------------
    # Use the correct attribute names – the config provides
    # SMTP_SERVER and SMTP_PORT, not SMTP_HOST.
    with smtplib.SMTP(
        settings.MONITORING.SMTP_SERVER,
        settings.MONITORING.SMTP_PORT,
    ) as server:
        server.send_message(msg)
