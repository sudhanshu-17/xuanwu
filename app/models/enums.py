"""Centralized string-valued enums.

The stored value is always the literal string (e.g. ``"pending"``); columns are
plain ``String`` so the database keeps exactly these values.
"""

import enum


class UserState(str, enum.Enum):
    pending = "pending"
    active = "active"
    banned = "banned"
    deleted = "deleted"


class AccountState(str, enum.Enum):
    pending = "pending"
    active = "active"
    disabled = "disabled"


class LabelScope(str, enum.Enum):
    public = "public"
    private = "private"


class ActivityResult(str, enum.Enum):
    succeed = "succeed"
    failed = "failed"
    denied = "denied"


class PermissionAction(str, enum.Enum):
    accept = "ACCEPT"
    drop = "DROP"
    audit = "AUDIT"


class RestrictionScope(str, enum.Enum):
    ip = "ip"
    ip_subnet = "ip_subnet"
    country = "country"
    continent = "continent"
    all = "all"


class RestrictionCategory(str, enum.Enum):
    whitelist = "whitelist"
    blacklist = "blacklist"
    blocklogin = "blocklogin"
    maintenance = "maintenance"


class RestrictionState(str, enum.Enum):
    enabled = "enabled"
    disabled = "disabled"


class APIKeyState(str, enum.Enum):
    active = "active"
    disabled = "disabled"


DEFAULT_ROLE = "member"
DEFAULT_SERVICE_ACCOUNT_ROLE = "service_account"
DEFAULT_API_KEY_ALGORITHM = "HS256"
