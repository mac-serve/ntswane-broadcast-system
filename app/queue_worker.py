from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

import time
from datetime import datetime

from database import SessionLocal
from models import MessageQueue, MessageLog, Broadcast
from services.sms_service import send_sms_message
from services.email_service import send_email_message
from services.whatsapp_service import send_whatsapp_message


def process_queue():
    while True:
        db = SessionLocal()
        try:
            job = db.query(MessageQueue).filter(
                MessageQueue.status == "queued"
            ).order_by(MessageQueue.created_at.asc()).first()

            if not job:
                time.sleep(3)
                continue

            job.status = "processing"
            db.commit()

            success = False
            error_message = None
            provider_message_id = None

            try:
                if job.channel == "sms":
                    success, error_message, provider_message_id = send_sms_message(
                        job.recipient,
                        job.message_body
                    )

                elif job.channel == "email":
                    success, error_message, provider_message_id = send_email_message(
                        job.recipient,
                        job.subject,
                        job.message_body
                    )

                elif job.channel == "whatsapp":
                    success, error_message = send_whatsapp_message(
                        job.recipient,
                        job.message_body
                    )

                job.status = "sent" if success else "failed"
                job.error_message = error_message
                job.provider_message_id = provider_message_id
                job.processed_at = datetime.utcnow()

                log = MessageLog(
                    client_id=job.client_id,
                    broadcast_id=job.broadcast_id,
                    recipient=job.recipient,
                    channel=job.channel,
                    provider_message_id=provider_message_id,
                    status="sent" if success else "failed",
                    error_message=error_message
                )
                db.add(log)

                broadcast = db.query(Broadcast).filter(
                    Broadcast.id == job.broadcast_id
                ).first()

                if broadcast:
                    if success:
                        broadcast.sent_count = (broadcast.sent_count or 0) + 1
                    else:
                        broadcast.failed_count = (broadcast.failed_count or 0) + 1

                db.commit()

            except Exception as e:
                job.status = "failed"
                job.error_message = str(e)
                job.processed_at = datetime.utcnow()

                log = MessageLog(
                    client_id=job.client_id,
                    broadcast_id=job.broadcast_id,
                    recipient=job.recipient,
                    channel=job.channel,
                    provider_message_id=None,
                    status="failed",
                    error_message=str(e)
                )
                db.add(log)

                broadcast = db.query(Broadcast).filter(
                    Broadcast.id == job.broadcast_id
                ).first()

                if broadcast:
                    broadcast.failed_count = (broadcast.failed_count or 0) + 1

                db.commit()

            time.sleep(0.5)

        finally:
            db.close()


if __name__ == "__main__":
    process_queue()
