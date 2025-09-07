from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./cloud_costs.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, index=True)
    service = Column(String, index=True)
    cost = Column(Float)
    timestamp = Column(DateTime, index=True)
    subscription = Column(String, default="", index=True)
    resource_group = Column(String, default="", index=True)
    tags = Column(String, default="")

    __table_args__ = (
        Index("ix_cost_unique", "provider", "service", "timestamp", "subscription", "resource_group"),
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()


class CloudCredential(Base):
    __tablename__ = "cloud_credentials"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, index=True)  # 'AWS' or 'Azure'
    # AWS fields
    aws_access_key_id = Column(String, default="")
    aws_secret_access_key = Column(String, default="")
    # Azure fields
    azure_client_id = Column(String, default="")
    azure_client_secret = Column(String, default="")
    azure_tenant_id = Column(String, default="")
    azure_subscription_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def save_credentials(session: Session, provider: str, **kwargs) -> CloudCredential:
    cred = CloudCredential(provider=provider, **kwargs)
    session.add(cred)
    session.commit()
    session.refresh(cred)
    return cred


def get_latest_credentials(session: Session, provider: str) -> CloudCredential | None:
    return (
        session.query(CloudCredential)
        .filter(CloudCredential.provider == provider)
        .order_by(CloudCredential.created_at.desc())
        .first()
    )

