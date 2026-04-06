import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker

# Setup logger for the database module
logger: Optional[logging.Logger] = None
engine = None
session: Optional[scoped_session] = None

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy production models."""
    pass

def init(config) -> None:
    """Initialize the database connection and session.

    Args:
        config: A configparser instance containing database settings.
    """
    global logger, engine, session
    logger = logging.getLogger(__name__)
    logger.info("Initializing database session...")
    
    # Connection string should be under [database] section as 'connection'
    connection_url = config.get('database', 'connection')
    engine = create_engine(connection_url, pool_recycle=3600, echo=False)
    
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    
    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)
    logger.info("Database initialized successfully.")

class Member(Base):
    """Represents a physical member with door access credentials."""
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    nickname: Mapped[Optional[str]] = mapped_column(String(255))
    fob: Mapped[Optional[str]] = mapped_column('fob_number', String(255))
    last_unlock: Mapped[Optional[datetime]] = mapped_column(DateTime)
    announce: Mapped[bool] = mapped_column(Boolean, default=False)
    director: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    subscriptions: Mapped[List["MemberSubscription"]] = relationship(
        "MemberSubscription", back_populates="member", cascade="all, delete-orphan"
    )

    def get_announce_name(self) -> str:
        """Determines the preferred name for broadcast or logging."""
        if self.nickname and self.nickname.strip():
            return self.nickname
        return self.first_name or "Unknown Member"

    def has_access(self) -> bool:
        """Validates if the member currently has door access permissions."""
        if self.director:
            return True
        return any(sub.is_today_in_range() for sub in self.subscriptions)

class Door(Base):
    """Represents a controlled entry point."""
    __tablename__ = "door_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

class AccessLog(Base):
    """Audit log for all entry attempts."""
    __tablename__ = "access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    member_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('members.id'))
    door_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('door_cache.id'))
    fob: Mapped[Optional[str]] = mapped_column('fob_number', String(255))
    access_permitted: Mapped[bool] = mapped_column(Boolean)
    uploaded: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    member: Mapped[Optional[Member]] = relationship(Member)
    door: Mapped[Optional[Door]] = relationship(Door)

class MemberSubscription(Base):
    """Subscription record verifying paid status for space access."""
    __tablename__ = "member_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"))
    date_from: Mapped[datetime] = mapped_column(DateTime)
    date_to: Mapped[datetime] = mapped_column(DateTime)
    buffer_days: Mapped[int] = mapped_column(Integer, default=0)

    member: Mapped[Member] = relationship(Member, back_populates="subscriptions")

    def is_today_in_range(self) -> bool:
        """Checks if today falls within the subscription or its grace period."""
        now = datetime.now()
        # Direct range check
        if self.date_from <= now <= self.date_to:
            return True
        # Grace period check
        return self.can_be_lenient(self.buffer_days)

    def can_be_lenient(self, extra_days: int) -> bool:
        """Extension check for grace periods."""
        now = datetime.now()
        extended_expiry = self.date_to + timedelta(days=extra_days)
        return self.date_from <= now < extended_expiry

class LegacyFob(Base):
    """Fallback database for legacy systems or offline recovery."""
    __tablename__ = "fallback_fobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    nickname: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    fob_number: Mapped[Optional[str]] = mapped_column(String(255))

