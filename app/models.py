from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# -------------------------
# CLIENTS
# -------------------------
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    name = Column(String(255), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)

    email = Column(String(255), unique=True, nullable=True)

    stand_number = Column(String(100), nullable=True)
    yard_size = Column(Float, nullable=True)

    password_hash = Column(String(255), nullable=True)

    has_whatsapp = Column(Boolean, default=False)
    subscribed = Column(Boolean, default=True)

    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    
    id_number = Column(String(20))

    beneficiary_name_surname = Column(String(255), nullable=True)
    beneficiary_id_number = Column(String(255), nullable=True)
    beneficiary_cell_number = Column(String(20), nullable=True)

    logs = relationship("MessageLog", back_populates="client")

# -------------------------
# Message Queue
# -------------------------
class MessageQueue(Base):
    __tablename__ = "message_queue"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id"), nullable=False)

    channel = Column(String(20), nullable=False)          # sms / email / whatsapp
    recipient = Column(String(255), nullable=False)       # phone or email
    subject = Column(String(255), nullable=True)          # for email
    message_body = Column(Text, nullable=False)

    status = Column(String(20), default="queued")         # queued / processing / sent / failed
    error_message = Column(Text, nullable=True)

    provider_message_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

# -------------------------
# BROADCAST CAMPAIGNS
# -------------------------
class Broadcast(Base):
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    audience = Column(String(50))  # all / whatsapp / sms

    queued_count = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("MessageLog", back_populates="broadcast")

# -------------------------
# Admin
# -------------------------
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# -------------------------
# Notice Comment
# -------------------------
class NoticeComment(Base):
    __tablename__ = "notice_comments"

    id = Column(Integer, primary_key=True, index=True)
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    broadcast = relationship("Broadcast", backref="comments")

# -------------------------
# MESSAGE LOGS
# -------------------------
class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    broadcast_id = Column(Integer, ForeignKey("broadcasts.id"), nullable=True)

    recipient = Column(String(255), index=True)          # phone or email
    phone_number = Column(String(20), index=True, nullable=True)  # keep for backward compatibility
    email_address = Column(String(255), index=True, nullable=True)

    channel = Column(String(20), index=True)             # sms / email / whatsapp
    provider_message_id = Column(String(255), index=True, nullable=True)

    status = Column(String(30), index=True)              # pending / sent / delivered / received / failed / bounced
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    client = relationship("Client", back_populates="logs")
    broadcast = relationship("Broadcast", back_populates="logs")


# -------------------------
# PERFORMANCE INDEXES
# -------------------------
Index("idx_logs_recipient", MessageLog.recipient)
Index("idx_logs_provider_message_id", MessageLog.provider_message_id)
Index("idx_logs_updated_at", MessageLog.updated_at)