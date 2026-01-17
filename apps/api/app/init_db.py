"""
Script to create database tables.
Run this once to initialize the database schema.

Usage:
    python -m app.init_db
"""
from app.db import engine, Base
from app.models import User, AuthIdentity, RefreshToken, VerificationCode


def init_db():
    """Create all tables in the database."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
