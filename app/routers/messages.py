from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime

from database import get_db
from models import MessageLog
from templates_config import templates
from models import Admin
from security import get_current_admin

router = APIRouter()


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    db: Session = Depends(get_db),
    month: str = Query(None),
    channel: str = Query(None),
    status: str = Query(None),
    recipient: str = Query(None),
    page: int = Query(1),
    per_page: int = Query(25),
    current_admin: Admin = Depends(get_current_admin)
):
    query = db.query(MessageLog)

    month_rows = db.query(
        func.strftime("%Y-%m", MessageLog.created_at).label("month")
    ).filter(
        MessageLog.created_at.isnot(None)
    ).distinct().order_by(
        func.strftime("%Y-%m", MessageLog.created_at).desc()
    ).all()

    available_months = [row.month for row in month_rows if row.month]

    if month:
        start_date = datetime.strptime(month, "%Y-%m")
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)

        query = query.filter(
            MessageLog.created_at >= start_date,
            MessageLog.created_at < end_date
        )

    if channel:
        query = query.filter(MessageLog.channel == channel)

    if status:
        query = query.filter(MessageLog.status == status)

    if recipient:
        query = query.filter(
            or_(
                MessageLog.recipient.ilike(f"%{recipient}%"),
                MessageLog.phone_number.ilike(f"%{recipient}%"),
                MessageLog.email_address.ilike(f"%{recipient}%")
            )
        )

    total_logs = query.count()

    sent_count = query.filter(MessageLog.status == "sent").count()
    delivered_count = query.filter(MessageLog.status == "delivered").count()
    failed_count = query.filter(MessageLog.status == "failed").count()

    logs = query.order_by(
        MessageLog.created_at.desc()
    ).offset(
        (page - 1) * per_page
    ).limit(
        per_page
    ).all()

    total_pages = (total_logs + per_page - 1) // per_page

    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "active": "logs",
            "logs": logs,
            "total_logs": total_logs,
            "sent_count": sent_count,
            "delivered_count": delivered_count,
            "failed_count": failed_count,
            "available_months": available_months,
            "month": month,
            "channel": channel,
            "status": status,
            "recipient": recipient,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    )