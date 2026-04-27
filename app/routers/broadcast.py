from fastapi import APIRouter, Form, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from templates_config import templates
import os
import time
from database import get_db
from models import Client, Broadcast, MessageLog, MessageQueue
from services.whatsapp_service import send_whatsapp_message
from services.sms_service import send_sms_message
from services.email_service import send_email_message
from models import Admin
from security import get_current_admin

router = APIRouter()

# ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID").strip("'")
# AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN").strip("'")

# twilio_client = TwilioClient(ACCOUNT_SID, AUTH_TOKEN)

# -----------------------
# BROADCAST
# -----------------------
@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast(request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
    ):
    return templates.TemplateResponse(
        request,
        "broadcast.html",
        {
            "active": "broadcast",
        },
    )

@router.post("/broadcast/send")
async def send_broadcast(
    title: str = Form(...),
    content: str = Form(...),
    audience: str = Form(...),
    db: Session = Depends(get_db)
):

    # 1️⃣ Save Broadcast Campaign
    broadcast = Broadcast(
        title=title,
        content=content,
        audience=audience,
        queued_count=0,
        sent_count=0,
        failed_count=0
    )

    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)

    message_body = f"{title}\n\n{content}"

    # 2️⃣ Select Audience
    if audience == "web":
        # No queue, just publish on website
        broadcast.queued_count = 0
        db.commit()
        return RedirectResponse("/broadcast", status_code=303)

    elif audience == "all":
        clients = db.query(Client).filter(
            Client.subscribed == True,
            Client.is_deleted == False
        ).all()

    elif audience == "whatsapp":
        clients = db.query(Client).filter(
            Client.subscribed == True,
            Client.has_whatsapp == True,
            Client.is_deleted == False
        ).all()

    elif audience == "sms":
        clients = db.query(Client).filter(
            Client.subscribed == True,
            #Client.has_whatsapp == False,
            Client.is_deleted == False
        ).all()

    elif audience == "email":
        clients = db.query(Client).filter(
            Client.subscribed == True,
            Client.email.isnot(None),
            Client.email != "",
            Client.is_deleted == False
        ).all()

    else:
        clients = []

    queued_total = 0

    # 3️⃣ Send Messages
    for client in clients:
        phone = client.phone_number
        phone = "+27" + phone[1:] if phone and phone.startswith("0") else phone

        if audience == "all":
            if phone:
                db.add(MessageQueue(
                    client_id=client.id,
                    broadcast_id=broadcast.id,
                    channel="sms",
                    recipient=phone,
                    subject=title,
                    message_body=message_body,
                    status="queued"
                ))
                queued_total += 1

            if client.email:
                db.add(MessageQueue(
                    client_id=client.id,
                    broadcast_id=broadcast.id,
                    channel="email",
                    recipient=client.email,
                    subject=title,
                    message_body=content,
                    status="queued"
                ))
                queued_total += 1

        elif audience == "sms":
            if phone:
                db.add(MessageQueue(
                    client_id=client.id,
                    broadcast_id=broadcast.id,
                    channel="sms",
                    recipient=phone,
                    subject=title,
                    message_body=message_body,
                    status="queued"
                ))
                queued_total += 1

        elif audience == "email":
            if client.email:
                db.add(MessageQueue(
                    client_id=client.id,
                    broadcast_id=broadcast.id,
                    channel="email",
                    recipient=client.email,
                    subject=title,
                    message_body=content,
                    status="queued"
                ))
                queued_total += 1

        elif audience == "whatsapp":
            if phone:
                db.add(MessageQueue(
                    client_id=client.id,
                    broadcast_id=broadcast.id,
                    channel="whatsapp",
                    recipient=phone,
                    subject=title,
                    message_body=message_body,
                    status="queued"
                ))
                queued_total += 1

    broadcast.queued_count = queued_total
    db.commit()
    return RedirectResponse("/broadcast", status_code=303)

@router.get("/broadcast/history", response_class=HTMLResponse)
async def broadcast_history(
    request: Request,
    search: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    allowed_per_page = [10, 25, 50, 100]
    if per_page not in allowed_per_page:
        per_page = 10

    query = db.query(Broadcast)

    if search and search.strip():
        search = search.strip()
        query = query.filter(Broadcast.title.ilike(f"%{search}%"))
    else:
        search = ""

    total = query.count()
    total_pages = max((total + per_page - 1) // per_page, 1)

    if page > total_pages:
        page = total_pages

    broadcasts = (
        query.order_by(Broadcast.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    return templates.TemplateResponse(
        "broadcast_history.html",
        {
            "request": request,
            "active": "history",
            "broadcasts": broadcasts,
            "search": search,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "start_page": start_page,
            "end_page": end_page,
        }
    )