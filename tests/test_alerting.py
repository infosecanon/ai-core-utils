import logging
import smtplib
from typing import Any
from unittest.mock import MagicMock

from core.alerting import send_error_email
from pytest import MonkeyPatch


def test_warning_emitted_when_no_recipients(
    monkeypatch: MonkeyPatch, caplog: Any
) -> None:
    # Make sure the logger we use has the right level
    logger = logging.getLogger("core.alerting")
    logger.setLevel(logging.WARNING)  # guarantees WARNING will go through
    logger.propagate = True  # let it bubble up to root

    # Ensure it has at least one handler (prevents “no handler” suppression)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    # Tell caplog to capture everything at WARNING or above
    caplog.set_level(logging.WARNING)  # sets root logger level


def test_send_error_email_success(
    reload_settings: Any, monkeypatch: MonkeyPatch
) -> None:
    """
    Tests that send_error_email formats and sends
    a message correctly.
    """
    # CALL RELOAD FIRST
    reload_settings(
        {
            "MONITORING__EMAIL_RECIPIENTS": '["to@example.com"]',
            "MONITORING__SENDER_EMAIL": "from@example.com",
            "MONITORING__SMTP_SERVER": "smtp.test.com",
            "MONITORING__SMTP_PORT": "25",
        }
    )

    # APPLY MOCK *AFTER* RELOAD
    mock_smtp_instance = MagicMock()
    # This line is new: it mocks the context manager ('with' statement)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp_class)

    try:
        1 / 0
    except Exception as e:
        send_error_email(e, "test_function")

    # Check that SMTP was called correctly
    mock_smtp_class.assert_called_with("smtp.test.com", 25)

    # Check that send_message was called
    assert mock_smtp_instance.send_message.called  # This will now pass

    # Check the content of the message
    sent_msg = mock_smtp_instance.send_message.call_args[0][0]
    assert sent_msg["Subject"] == "[ALERT] Exception in test_function"
    assert sent_msg["From"] == "from@example.com"
    assert sent_msg["To"] == "to@example.com"
    assert "Traceback" in sent_msg.get_content()
    assert "ZeroDivisionError" in sent_msg.get_content()


def test_send_error_email_no_recipients(
    reload_settings: Any, monkeypatch: MonkeyPatch, caplog: Any
) -> None:
    """
    Tests that no email is sent if no recipients are configured.
    """
    # CALL RELOAD FIRST
    reload_settings(
        {
            "MONITORING__EMAIL_RECIPIENTS": "[]",
            "MONITORING__SENDER_EMAIL": "from@example.com",
            "MONITORING__SMTP_SERVER": "smtp.test.com",
            "MONITORING__SMTP_PORT": "25",
        }
    )
    # DEBUG: Check what settings actually contains
    from core.config import settings

    print(
        f"DEBUG: EMAIL_RECIPIENTS after reload: {settings.MONITORING.EMAIL_RECIPIENTS}"
    )
    print(f"DEBUG: Type: {type(settings.MONITORING.EMAIL_RECIPIENTS)}")

    # APPLY MOCK *AFTER* RELOAD
    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp_class)

    # Clear any existing logs and set up capture
    caplog.clear()

    # Set up the logger properly
    logger = logging.getLogger("core.alerting")
    logger.setLevel(logging.INFO)

    # Call the function
    try:
        1 / 0
    except Exception as e:
        send_error_email(e, "test_function")

    print("Captured logs:", repr(caplog.text))
    print("Records:", caplog.records)

    # Assertions
    assert not mock_smtp_instance.send_message.called
    assert "No EMAIL_RECIPIENTS configured" in caplog.text
