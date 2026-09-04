# TODO: Validate
import logging

import emails  # type: ignore[import-untyped]

from app.config import settings
from app.schemas import Message
from app.utils.service.email_templates import generate_test_email

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# TODO: Validate
def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    if not settings.emails_enabled:
        msg = "no provided configuration for email variables"
        raise ValueError(msg)

    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info("send email result: %s", response)


# TODO: Validate
def send_test_email(email_to: str) -> Message:
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")
