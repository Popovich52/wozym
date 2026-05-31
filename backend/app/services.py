from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import utcnow
from app.models import AuditEvent


logger = logging.getLogger("wozym")


def send_email(to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(message)


def log_phone_code(phone: str, code: str) -> None:
    if settings.phone_verification_dev_mode:
        logger.warning("PHONE_VERIFICATION_CODE phone=%s code=%s", phone, code)


def add_audit(
    db: Session,
    action: str,
    user_id: int | None,
    ip_address: str | None,
    metadata: dict[str, Any] | None = None,
    team_id: int | None = None,
    connection_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> None:
    event = AuditEvent(
        user_id=user_id,
        team_id=team_id,
        connection_id=connection_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        meta=metadata or {},
        ip_address=ip_address,
        created_at=utcnow(),
    )
    db.add(event)

