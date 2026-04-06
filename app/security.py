from passlib.context import CryptContext
from fastapi import Cookie, HTTPException, Depends
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from database import get_db
from models import Admin
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
RESET_SALT = "admin-password-reset"
serializer = URLSafeTimedSerializer(SECRET_KEY)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_current_admin(
    admin_session_id: int = Cookie(None, alias="admin_id"),
    db: Session = Depends(get_db)
):
    if not admin_session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admin = db.query(Admin).filter(Admin.id == admin_session_id).first()

    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    return admin

def generate_password_reset_token(email: str) -> str:
    return serializer.dumps(email, salt=RESET_SALT)

def verify_password_reset_token(token: str, max_age: int = 3600) -> str:
    try:
        email = serializer.loads(token, salt=RESET_SALT, max_age=max_age)
        return email
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Reset link has expired.")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid reset link.")