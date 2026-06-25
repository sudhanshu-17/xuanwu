"""SQLAlchemy models.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and mapper configuration see the full schema.
"""

from app.models.activity import Activity
from app.models.api_key import APIKey
from app.models.comment import Comment
from app.models.data_storage import DataStorage
from app.models.document import Document
from app.models.label import Label
from app.models.level import Level
from app.models.permission import Permission
from app.models.phone import Phone
from app.models.profile import Profile
from app.models.restriction import Restriction
from app.models.service_account import ServiceAccount
from app.models.user import User

__all__ = [
    "APIKey",
    "Activity",
    "Comment",
    "DataStorage",
    "Document",
    "Label",
    "Level",
    "Permission",
    "Phone",
    "Profile",
    "Restriction",
    "ServiceAccount",
    "User",
]
