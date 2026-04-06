from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from models import Admin
from security import get_current_admin

from database import get_db
from models import Client, Broadcast, MessageLog
from templates_config import templates

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    month: str = Query(None),
    channel: str = Query(None),
    status: str = Query(None),
    current_admin: Admin = Depends(get_current_admin)
):
    log_query = db.query(MessageLog)

    # existing months in DB (SQLite-friendly)
    month_rows = db.query(
        func.strftime("%Y-%m", MessageLog.created_at).label("month")
    ).filter(
        MessageLog.created_at.isnot(None)
    ).distinct().order_by(
        func.strftime("%Y-%m", MessageLog.created_at).desc()
    ).all()

    available_months = [row.month for row in month_rows if row.month]

    # month filtering
    if month:
        start_date = datetime.strptime(month, "%Y-%m")

        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)

        log_query = log_query.filter(
            MessageLog.created_at >= start_date,
            MessageLog.created_at < end_date
        )

    # channel filter
    if channel:
        log_query = log_query.filter(MessageLog.channel == channel)

    # status filter
    if status:
        log_query = log_query.filter(MessageLog.status == status)

    total_clients = db.query(func.count(Client.id)).filter(
        Client.is_deleted == False
    ).scalar() or 0

    active_clients = db.query(func.count(Client.id)).filter(
        Client.is_deleted == False,
        Client.subscribed == True
    ).scalar() or 0

    total_broadcasts = db.query(func.count(Broadcast.id)).scalar() or 0
    total_logs = log_query.count()

    sent_count = log_query.filter(MessageLog.status == "sent").count()
    failed_count = log_query.filter(MessageLog.status == "failed").count()
    pending_count = log_query.filter(MessageLog.status == "pending").count()
    delivered_count = log_query.filter(MessageLog.status == "delivered").count()

    sms_count = log_query.filter(MessageLog.channel == "sms").count()
    email_count = log_query.filter(MessageLog.channel == "email").count()
    whatsapp_count = log_query.filter(MessageLog.channel == "whatsapp").count()

    recent_broadcasts = db.query(Broadcast).order_by(
        Broadcast.created_at.desc()
    ).limit(5).all()

    recent_failed_logs = log_query.filter(
        MessageLog.status == "failed"
    ).order_by(
        MessageLog.created_at.desc()
    ).limit(10).all()

    channel_labels = ["SMS", "Email", "WhatsApp"]
    channel_values = [sms_count, email_count, whatsapp_count]

    status_labels = ["Sent", "Failed", "Pending", "Delivered"]
    status_values = [sent_count, failed_count, pending_count, delivered_count]

    processing_broadcasts = db.query(func.count(Broadcast.id)).filter(
        (Broadcast.sent_count + Broadcast.failed_count) < Broadcast.queued_count
    ).scalar() or 0

    # chart 3: volume per day for selected month, otherwise last 7 days
    volume_labels = []
    volume_values = []

    if month:
        start_date = datetime.strptime(month, "%Y-%m")
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)

        current_day = start_date
        while current_day < end_date:
            next_day = current_day + timedelta(days=1)

            count = db.query(func.count(MessageLog.id)).filter(
                MessageLog.created_at >= current_day,
                MessageLog.created_at < next_day
            )

            if channel:
                count = count.filter(MessageLog.channel == channel)

            if status:
                count = count.filter(MessageLog.status == status)

            volume_labels.append(current_day.strftime("%d %b"))
            volume_values.append(count.scalar() or 0)

            current_day = next_day
    else:
        for i in range(6, -1, -1):
            day = datetime.utcnow().date() - timedelta(days=i)
            next_day = day + timedelta(days=1)

            count = db.query(func.count(MessageLog.id)).filter(
                MessageLog.created_at >= datetime.combine(day, datetime.min.time()),
                MessageLog.created_at < datetime.combine(next_day, datetime.min.time())
            )

            if channel:
                count = count.filter(MessageLog.channel == channel)

            if status:
                count = count.filter(MessageLog.status == status)

            volume_labels.append(day.strftime("%d %b"))
            volume_values.append(count.scalar() or 0)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "active": "dashboard",
            "total_clients": total_clients,
            "active_clients": active_clients,
            "total_broadcasts": total_broadcasts,
            "total_logs": total_logs,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "pending_count": pending_count,
            "delivered_count": delivered_count,
            "sms_count": sms_count,
            "email_count": email_count,
            "whatsapp_count": whatsapp_count,
            "recent_broadcasts": recent_broadcasts,
            "recent_failed_logs": recent_failed_logs,
            "channel_labels": channel_labels,
            "channel_values": channel_values,
            "status_labels": status_labels,
            "status_values": status_values,
            "volume_labels": volume_labels,
            "volume_values": volume_values,
            "available_months": available_months,
            "month": month,
            "channel": channel,
            "status": status,
            "processing_broadcasts": processing_broadcasts
        }
    )