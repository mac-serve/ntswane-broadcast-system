from fastapi import APIRouter, Request, Depends, Form, Query, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models import Client, Admin
from templates_config import templates
from security import get_current_admin
import re
import pandas as pd
import io
from datetime import datetime
from urllib.parse import urlencode

router = APIRouter()


def clean_text(value: str):
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def clean_phone_number(phone_number: str):
    if not phone_number:
        raise HTTPException(status_code=400, detail="Phone number is required.")

    # keep digits only
    phone_number = re.sub(r"\D", "", phone_number.strip())

    # allows 10 or 11 digits, must start with 0
    if not re.fullmatch(r"0\d{9,10}", phone_number):
        raise HTTPException(
            status_code=400,
            detail="Phone number must start with 0 and contain 10-11 digits only."
        )

    return phone_number

def clean_optional_phone_number(phone_number: str):
    phone_number = clean_text(phone_number)

    if not phone_number:
        return None

    phone_number = re.sub(r"\D", "", phone_number.strip())

    if not re.fullmatch(r"0\d{9,10}", phone_number):
        raise HTTPException(
            status_code=400,
            detail="Beneficiary phone number must start with 0 and contain 10-11 digits only."
        )

    return phone_number


def build_clients_redirect(page=1, per_page=10, search=None):
    params = {
        "page": page,
        "per_page": per_page
    }
    if search:
        params["search"] = search
    return f"/clients?{urlencode(params)}"


# -----------------------
# CLIENTS PAGE
# -----------------------
@router.get("/clients")
def clients_page(
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

    search = clean_text(search)

    query = db.query(Client).filter(Client.is_deleted == False)

    if search:
        query = query.filter(
            or_(
                Client.name.ilike(f"%{search}%"),
                Client.phone_number.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%"),
                Client.stand_number.ilike(f"%{search}%"),
                Client.id_number.ilike(f"%{search}%"),
                Client.beneficiary_name_surname.ilike(f"%{search}%"),
                Client.beneficiary_id_number.ilike(f"%{search}%"),
                Client.beneficiary_cell_number.ilike(f"%{search}%")
            )
        )

    total = query.count()
    total_pages = max((total + per_page - 1) // per_page, 1)

    if page > total_pages:
        page = total_pages

    clients = (
        query.order_by(Client.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # compact pagination window
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    return templates.TemplateResponse("clients.html", {
        "active": "clients",
        "request": request,
        "clients": clients,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "start_page": start_page,
        "end_page": end_page,
        "search": search or ""
    })


# -----------------------
# ADD CLIENT
# -----------------------
@router.post("/clients/add")
async def add_client(
    name: str = Form(...),
    phone_number: str = Form(...),
    id_number: str = Form(None),
    email: str = Form(None),
    stand_number: str = Form(None),
    yard_size: str = Form(None),
    beneficiary_name_surname: str = Form(None),
    beneficiary_id_number: str = Form(None),
    beneficiary_cell_number: str = Form(None),
    has_whatsapp: str = Form(None),
    page: int = Form(1),
    per_page: int = Form(10),
    search: str = Form(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    name = clean_text(name)
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    phone_number = clean_phone_number(phone_number)
    id_number = clean_text(id_number)
    email = clean_text(email)
    stand_number = clean_text(stand_number)

    beneficiary_name_surname = clean_text(beneficiary_name_surname)
    beneficiary_id_number = clean_text(beneficiary_id_number)
    beneficiary_cell_number = clean_optional_phone_number(beneficiary_cell_number)

    yard_size_value = None
    if yard_size is not None and str(yard_size).strip() != "":
        try:
            yard_size_value = float(yard_size)
        except ValueError:
            raise HTTPException(status_code=400, detail="Yard size must be a valid number.")

    existing = db.query(Client).filter(
        Client.phone_number == phone_number,
        Client.is_deleted == False
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Phone number already exists.")

    has_whatsapp_value = True if has_whatsapp == "true" else False

    new_client = Client(
        name=name,
        phone_number=phone_number,
        id_number=id_number,
        email=email,
        stand_number=stand_number,
        yard_size=yard_size_value,
        beneficiary_name_surname=beneficiary_name_surname,
        beneficiary_id_number=beneficiary_id_number,
        beneficiary_cell_number=beneficiary_cell_number,
        has_whatsapp=has_whatsapp_value,
        subscribed=True,
        created_at=datetime.utcnow()
    )

    db.add(new_client)
    db.commit()

    return RedirectResponse(
        url=build_clients_redirect(page=page, per_page=per_page, search=search),
        status_code=303
    )


# -----------------------
# EDIT CLIENT
# -----------------------
@router.post("/clients/{client_id}/edit")
async def edit_client(
    client_id: int,
    name: str = Form(...),
    phone_number: str = Form(...),
    id_number: str = Form(None),
    email: str = Form(None),
    stand_number: str = Form(None),
    yard_size: str = Form(None),
    beneficiary_name_surname: str = Form(None),
    beneficiary_id_number: str = Form(None),
    beneficiary_cell_number: str = Form(None),
    has_whatsapp: str = Form(None),
    subscribed: str = Form(None),
    page: int = Form(1),
    per_page: int = Form(10),
    search: str = Form(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")

    name = clean_text(name)
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    phone_number = clean_phone_number(phone_number)
    id_number = clean_text(id_number)
    email = clean_text(email)
    stand_number = clean_text(stand_number)

    beneficiary_name_surname = clean_text(beneficiary_name_surname)
    beneficiary_id_number = clean_text(beneficiary_id_number)
    beneficiary_cell_number = clean_optional_phone_number(beneficiary_cell_number)

    yard_size_value = None
    if yard_size is not None and str(yard_size).strip() != "":
        try:
            yard_size_value = float(yard_size)
        except ValueError:
            raise HTTPException(status_code=400, detail="Yard size must be a valid number.")

    duplicate_phone = db.query(Client).filter(
        Client.phone_number == phone_number,
        Client.id != client_id,
        Client.is_deleted == False
    ).first()

    if duplicate_phone:
        raise HTTPException(status_code=400, detail="Phone number already exists.")

    client.name = name
    client.phone_number = phone_number
    client.id_number = id_number
    client.email = email
    client.stand_number = stand_number
    client.yard_size = yard_size_value
    client.beneficiary_name_surname = beneficiary_name_surname
    client.beneficiary_id_number = beneficiary_id_number
    client.beneficiary_cell_number = beneficiary_cell_number
    client.has_whatsapp = True if has_whatsapp == "true" else False
    client.subscribed = True if subscribed == "true" else False

    db.commit()

    return RedirectResponse(
        url=build_clients_redirect(page=page, per_page=per_page, search=search),
        status_code=303
    )


# -----------------------
# TOGGLE SUBSCRIPTION
# -----------------------
@router.get("/clients/{client_id}/toggle")
async def toggle_client(
    client_id: int,
    page: int = Query(1),
    per_page: int = Query(10),
    search: str = Query(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.subscribed = not bool(client.subscribed)
    db.commit()

    return RedirectResponse(
        url=build_clients_redirect(page=page, per_page=per_page, search=search),
        status_code=303
    )


# -----------------------
# SOFT DELETE CLIENT
# -----------------------
@router.get("/clients/{client_id}/delete")
async def delete_client(
    client_id: int,
    page: int = Query(1),
    per_page: int = Query(10),
    search: str = Query(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.is_deleted = True
    db.commit()

    return RedirectResponse(
        url=build_clients_redirect(page=page, per_page=per_page, search=search),
        status_code=303
    )


# -----------------------
# DOWNLOAD CLIENTS
# -----------------------
@router.get("/clients/download")
def download_clients(
    search: str = Query(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    query = db.query(Client).filter(Client.is_deleted == False)

    if search and search.strip():
        search = search.strip()
        query = query.filter(
            (Client.name.ilike(f"%{search}%")) |
            (Client.phone_number.ilike(f"%{search}%")) |
            (Client.email.ilike(f"%{search}%")) |
            (Client.stand_number.ilike(f"%{search}%")) |
            (Client.id_number.ilike(f"%{search}%")) |
            Client.beneficiary_name_surname.ilike(f"%{search}%") |
            Client.beneficiary_id_number.ilike(f"%{search}%") |
            Client.beneficiary_cell_number.ilike(f"%{search}%")
        )

    clients = query.order_by(Client.id.desc()).all()

    data = []
    for c in clients:
        data.append({
            "Name": c.name,
            "Phone Number": c.phone_number,
            "ID Number": c.id_number,
            "Email": c.email,
            "Stand Number": c.stand_number,
            "Yard Size": c.yard_size,
            "Beneficiary Name & Surname": c.beneficiary_name_surname,
            "Beneficiary ID Number": c.beneficiary_id_number,
            "Beneficiary Cell Number": c.beneficiary_cell_number,
            "WhatsApp": c.has_whatsapp,
            "Subscribed": c.subscribed,
            "Created At": c.created_at
        })

    df = pd.DataFrame(data)

    stream = io.BytesIO()
    df.to_excel(stream, index=False, engine="openpyxl")
    stream.seek(0)

    filename = f"clients_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )