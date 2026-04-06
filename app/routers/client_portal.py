from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Client
from templates_config import templates
import re

router = APIRouter()


def clean_text(value: str):
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def clean_phone_number(phone_number: str):
    if not phone_number:
        return None

    phone_number = re.sub(r"\D", "", phone_number.strip())

    if not re.fullmatch(r"0\d{9,10}", phone_number):
        return None

    return phone_number


def get_logged_in_client(request: Request, db: Session):
    client_id = request.session.get("client_portal_client_id")
    if not client_id:
        return None

    return db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    ).first()


# -----------------------
# LOGIN PAGE
# -----------------------
@router.get("/update-my-info")
def client_login_page(request: Request):
    error = request.session.pop("client_portal_error", None)
    success = request.session.pop("client_portal_success", None)

    return templates.TemplateResponse("client_portal/login.html", {
        "request": request,
        "error": error,
        "success": success
    })


# -----------------------
# LOGIN ACTION
# -----------------------
@router.post("/update-my-info/login")
def client_login(
    request: Request,
    phone_number: str = Form(...),
    id_number: str = Form(...),
    db: Session = Depends(get_db)
):
    cleaned_phone = clean_phone_number(phone_number)
    id_number = clean_text(id_number)

    if not cleaned_phone or not id_number:
        request.session["client_portal_error"] = "Please enter a valid phone number and ID number."
        return RedirectResponse("/update-my-info", status_code=303)

    client = db.query(Client).filter(
        Client.is_deleted == False,
        Client.phone_number == cleaned_phone,
        Client.id_number == id_number
    ).first()

    if not client:
        request.session["client_portal_error"] = "We could not find your details. Please check your phone number and ID number."
        return RedirectResponse("/update-my-info", status_code=303)

    request.session["client_portal_client_id"] = client.id

    return RedirectResponse("/update-my-info/profile", status_code=303)


# -----------------------
# PROFILE PAGE
# -----------------------
@router.get("/update-my-info/profile")
def client_profile_page(
    request: Request,
    db: Session = Depends(get_db)
):
    client = get_logged_in_client(request, db)

    if not client:
        request.session["client_portal_error"] = "Please log in first."
        return RedirectResponse("/update-my-info", status_code=303)

    error = request.session.pop("client_portal_error", None)
    success = request.session.pop("client_portal_success", None)

    return templates.TemplateResponse("client_portal/profile.html", {
        "request": request,
        "client": client,
        "error": error,
        "success": success
    })


# -----------------------
# PROFILE UPDATE
# -----------------------
@router.post("/update-my-info/profile")
def client_profile_update(
    request: Request,
    name: str = Form(...),
    phone_number: str = Form(...),
    id_number: str = Form(...),
    email: str = Form(None),
    stand_number: str = Form(None),
    yard_size: str = Form(None),
    has_whatsapp: str = Form(None),
    db: Session = Depends(get_db)
):
    client = get_logged_in_client(request, db)

    if not client:
        request.session["client_portal_error"] = "Please log in first."
        return RedirectResponse("/update-my-info", status_code=303)

    name = clean_text(name)
    cleaned_phone = clean_phone_number(phone_number)
    id_number = clean_text(id_number)
    email = clean_text(email)
    stand_number = clean_text(stand_number)

    if not name:
        request.session["client_portal_error"] = "Full name is required."
        return RedirectResponse("/update-my-info/profile", status_code=303)

    if not cleaned_phone:
        request.session["client_portal_error"] = "Please enter a valid phone number."
        return RedirectResponse("/update-my-info/profile", status_code=303)

    if not id_number:
        request.session["client_portal_error"] = "ID number is required."
        return RedirectResponse("/update-my-info/profile", status_code=303)

    yard_size_value = None
    if yard_size is not None and str(yard_size).strip() != "":
        try:
            yard_size_value = float(yard_size)
        except ValueError:
            request.session["client_portal_error"] = "Yard size must be a valid number."
            return RedirectResponse("/update-my-info/profile", status_code=303)

    duplicate_phone = db.query(Client).filter(
        Client.phone_number == cleaned_phone,
        Client.id != client.id,
        Client.is_deleted == False
    ).first()

    if duplicate_phone:
        request.session["client_portal_error"] = "That phone number already belongs to another client."
        return RedirectResponse("/update-my-info/profile", status_code=303)

    client.name = name
    client.phone_number = cleaned_phone
    client.id_number = id_number
    client.email = email
    client.stand_number = stand_number
    client.yard_size = yard_size_value
    client.has_whatsapp = True if has_whatsapp == "true" else False

    db.commit()

    # keep session valid even if phone/id changed
    request.session["client_portal_client_id"] = client.id
    request.session["client_portal_success"] = "Your information has been updated successfully."

    return RedirectResponse("/update-my-info/profile", status_code=303)


# -----------------------
# LOGOUT
# -----------------------
@router.get("/update-my-info/logout")
def client_logout(request: Request):
    request.session.pop("client_portal_client_id", None)
    request.session["client_portal_success"] = "You have been logged out."
    return RedirectResponse("/update-my-info", status_code=303)