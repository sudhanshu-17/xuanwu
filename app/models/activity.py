"""Activity — immutable audit record (created only, never updated/deleted)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base

if TYPE_CHECKING:
    from app.models.user import User


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    target_uid: Mapped[str | None] = mapped_column(String(32), default=None)
    category: Mapped[str] = mapped_column(String(50))
    user_ip: Mapped[str | None] = mapped_column(String(45), default=None)  # IPv4/IPv6
    user_ip_country: Mapped[str | None] = mapped_column(String(2), default=None)  # GeoIP
    user_agent: Mapped[str | None] = mapped_column(String(255), default=None)
    topic: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(20))  # succeed | failed | denied
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User | None"] = relationship(back_populates="activities")

    __table_args__ = (Index("ix_activities_created_at", "created_at"),)
