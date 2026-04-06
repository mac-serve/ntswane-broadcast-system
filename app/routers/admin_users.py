from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Admin
from templates_config import templates
from security import get_current_admin, hash_password
from datetime import datetime

router = APIRouter()


def clean_text(value: str):
    if value is None:
        return None
    value = value.strip()
    return value if value else None


@router.get("/admin-users")
def admin_users_page(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    if not current_admin.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to manage admin users.")

    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "admins": admins,
        "current_admin": current_admin
    })


@router.post("/admin-users/add")
def add_admin_user(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    is_super_admin: str = Form(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    if not current_admin.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to create admin users.")

    full_name = clean_text(full_name)
    email = clean_text(email)

    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required.")

    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    email = email.lower()

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    existing_admin = db.query(Admin).filter(Admin.email == email).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="An admin with this email already exists.")

    new_admin = Admin(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        is_super_admin=True if is_super_admin == "true" else False,
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.add(new_admin)
    db.commit()

    return RedirectResponse("/admin-users", status_code=303)


@router.post("/admin-users/{admin_id}/edit")
def edit_admin_user(
    admin_id: int,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(None),
    confirm_password: str = Form(None),
    is_super_admin: str = Form(None),
    is_active: str = Form(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    if not current_admin.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to edit admin users.")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found.")

    full_name = clean_text(full_name)
    email = clean_text(email)

    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required.")

    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    email = email.lower()

    existing_admin = db.query(Admin).filter(
        Admin.email == email,
        Admin.id != admin_id
    ).first()
    if existing_admin:
        raise HTTPException(status_code=400, detail="Another admin with this email already exists.")

    admin.full_name = full_name
    admin.email = email
    admin.is_super_admin = True if is_super_admin == "true" else False
    admin.is_active = True if is_active == "true" else False

    # prevent current super admin from removing own super admin accidentally
    if admin.id == current_admin.id and not admin.is_super_admin:
        raise HTTPException(status_code=400, detail="You cannot remove your own super admin access.")

    # optional password change
    if password and password.strip():
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
        if password != (confirm_password or ""):
            raise HTTPException(status_code=400, detail="Passwords do not match.")
        admin.password_hash = hash_password(password)

    db.commit()

    return RedirectResponse("/admin-users", status_code=303)


@router.get("/admin-users/{admin_id}/toggle")
def toggle_admin_user(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    if not current_admin.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update admin users.")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin user not found.")

    if admin.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")

    admin.is_active = not bool(admin.is_active)
    db.commit()

    return RedirectResponse("/admin-users", status_code=303)