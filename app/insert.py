from database import SessionLocal
from models import Admin
from security import hash_password

db = SessionLocal()

admin = Admin(
    full_name="System Admin",
    email="admin@ntswane.co.za",
    password_hash=hash_password("Admin123!")
)

db.add(admin)
db.commit()
db.close()