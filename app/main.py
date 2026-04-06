from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI, Request, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from templates_config import templates
from database import engine, get_db
from models import Base, Client
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from collections import defaultdict

from routers import dashboard
from routers import clients
from routers import broadcast
from routers import messages as logs
from models import Broadcast, NoticeComment
from models import Admin
from security import verify_password
from security import get_current_admin
from routers import client_portal
from routers import admin_users
from security import generate_password_reset_token, verify_password_reset_token, hash_password
from services.email_service import send_admin_reset_email

app = FastAPI()
Base.metadata.create_all(bind=engine)

# Static files (optional for CSS/JS later)
app.mount("/static", StaticFiles(directory="static"), name="static")

SECRET_KEY = os.getenv("SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(clients.router)
app.include_router(broadcast.router)
app.include_router(dashboard.router)
app.include_router(logs.router)
app.include_router(client_portal.router)
app.include_router(admin_users.router)

def clean_text(value: str):
    if value is None:
        return None
    value = value.strip()
    return value if value else None

# -----------------------
# LOGIN
# -----------------------
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request}
    )

@app.post("/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(Admin).filter(
        Admin.email == email,
        Admin.is_active == True
    ).first()

    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Invalid email or password"
            },
            status_code=400
        )

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="admin_id", value=str(admin.id), httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("admin_id")
    return response

@app.get("/", response_class=HTMLResponse)
async def public_home(request: Request, db: Session = Depends(get_db)):
    notices = db.query(Broadcast).order_by(Broadcast.created_at.desc()).limit(7).all()
    notice_ids = [notice.id for notice in notices]

    comments_by_notice = defaultdict(list)
    all_comments_by_notice = defaultdict(list)

    if notice_ids:
        comments = db.query(NoticeComment).filter(
            NoticeComment.broadcast_id.in_(notice_ids),
            NoticeComment.is_deleted == False
        ).order_by(NoticeComment.created_at.desc()).all()

        for comment in comments:
            all_comments_by_notice[comment.broadcast_id].append(comment)

        for notice_id, items in all_comments_by_notice.items():
            comments_by_notice[notice_id] = items[:2]

    return templates.TemplateResponse(
        request,
        "community.html",
        {
            "notices": notices,
            "comments_by_notice": comments_by_notice,
            "all_comments_by_notice": all_comments_by_notice,
        }
    )

@app.post("/notice/{broadcast_id}/comment")
async def add_notice_comment(
    broadcast_id: int,
    name: str = Form(...),
    comment: str = Form(...),
    db: Session = Depends(get_db)
):
    name = name.strip()
    comment = comment.strip()

    if not name or not comment:
        return RedirectResponse("/#notices", status_code=303)

    notice = db.query(Broadcast).filter(Broadcast.id == broadcast_id).first()
    if not notice:
        return RedirectResponse("/#notices", status_code=303)

    new_comment = NoticeComment(
        broadcast_id=broadcast_id,
        name=name,
        comment=comment
    )

    db.add(new_comment)
    db.commit()

    return RedirectResponse("/#notices", status_code=303)

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request
        }
    )


@app.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    email = clean_text(email)

    if not email:
        return templates.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "error": "Email is required."
            }
        )

    email = email.lower()
    admin = db.query(Admin).filter(Admin.email == email).first()

    success_message = "If that email exists in the system, a reset link has been sent."

    if admin:
        token = generate_password_reset_token(admin.email)
        base_url = str(request.base_url).rstrip("/")
        reset_link = f"{base_url}/reset-password?token={token}"
        reset_link = reset_link.replace("http://", "https://")  # optional safety for production

        sent, error_message, provider_message_id = send_admin_reset_email(admin.email, reset_link)

        if not sent:
            return templates.TemplateResponse(
                "forgot_password.html",
                {
                    "request": request,
                    "error": f"Unable to send reset email. {error_message}",
                    "debug_reset_link": reset_link
                }
            )

    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "success": success_message
        }
    )


@app.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str
):
    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "token": token
        }
    )


@app.post("/reset-password", response_class=HTMLResponse)
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if len(password) < 6:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Password must be at least 6 characters long."
            }
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Passwords do not match."
            }
        )

    try:
        email = verify_password_reset_token(token)
    except Exception as e:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "token": token,
                "error": str(e.detail) if hasattr(e, "detail") else "Invalid or expired reset link."
            }
        )

    admin = db.query(Admin).filter(Admin.email == email.lower()).first()

    if not admin:
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Admin account not found."
            }
        )

    admin.password_hash = hash_password(password)
    db.commit()

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "success": "Your password has been reset successfully. You can now log in."
        }
    )