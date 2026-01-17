from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db import Base


class AuthProvider(str, enum.Enum):
    EMAIL_PASSWORD = "email_password"
    PHONE_OTP = "phone_otp"


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = {"schema": "app"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(SQLEnum(AuthProvider), nullable=False)
    identifier = Column(String(255), nullable=False, index=True)  # email or phone
    password_hash = Column(String(255), nullable=True)  # null for phone_otp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="auth_identities")
