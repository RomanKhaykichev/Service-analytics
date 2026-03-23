from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db import Base


class VerificationChannel(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "email"


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="CASCADE"), nullable=True, index=True)  # nullable for pre-registration
    pending_id = Column(UUID(as_uuid=True), ForeignKey("app.pending_registrations.id", ondelete="CASCADE"), nullable=True, index=True)
    channel = Column(SQLEnum(VerificationChannel), nullable=False)
    destination = Column(String(255), nullable=False, index=True)  # phone or email
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="verification_codes")
    pending_registration = relationship("PendingRegistration", back_populates="verification_codes")
