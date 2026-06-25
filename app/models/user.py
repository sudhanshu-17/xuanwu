"""User account — the central identity all other records hang off."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.db.base import GUID, Base, TimestampMixin
from app.models.enums import DEFAULT_ROLE, UserState
from app.utils.uid import generate_uid

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.api_key import APIKey
    from app.models.comment import Comment
    from app.models.data_storage import DataStorage
    from app.models.document import Document
    from app.models.label import Label
    from app.models.phone import Phone
    from app.models.profile import Profile
    from app.models.service_account import ServiceAccount


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=generate_uid)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_digest: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default=DEFAULT_ROLE, index=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    level: Mapped[int] = mapped_column(Integer, default=0)
    otp: Mapped[bool] = mapped_column(Boolean, default=False)
    otp_secret: Mapped[str | None] = mapped_column(EncryptedString(), default=None)  # 2FA seed
    state: Mapped[str] = mapped_column(String(50), default=UserState.pending.value, index=True)
    referral_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    # --- associations ---
    profiles: Mapped[list["Profile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    phones: Mapped[list["Phone"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    labels: Mapped[list["Label"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    data_storages: Mapped[list["DataStorage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="user",
        foreign_keys="Comment.user_id",
        cascade="all, delete-orphan",
    )
    service_accounts: Mapped[list["ServiceAccount"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    activities: Mapped[list["Activity"]] = relationship(back_populates="user")
    api_keys: Mapped[list["APIKey"]] = relationship(
        primaryjoin=(
            "and_(User.id == foreign(APIKey.key_holder_account_id), "
            "APIKey.key_holder_account_type == 'User')"
        ),
        viewonly=True,
    )
