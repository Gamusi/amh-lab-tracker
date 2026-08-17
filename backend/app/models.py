import datetime
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    full_name: str
    username: str
    password_hash: str = ""
    role: str = "technician"  # 'admin' or 'technician'
    is_active: bool = True
    password_reset_required: bool = False
    created_at: Optional[datetime.datetime] = None

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

@dataclass
class UserSession:
    id: int
    user_id: int
    token: str
    expires_at: datetime.datetime
    created_at: Optional[datetime.datetime] = None

@dataclass
class Section:
    id: int
    name: str
    sort_order: int = 0

@dataclass
class Test:
    id: int
    name: str
    section_id: int
    is_tracked: bool = False
    is_active: bool = True
    sort_order: int = 0

@dataclass
class DailyEntry:
    id: int
    entry_date: datetime.date
    test_id: int
    done: int = 0
    positive: Optional[int] = None
    entered_by_user_id: Optional[int] = None
    entered_at: Optional[datetime.datetime] = None
    updated_by_user_id: Optional[int] = None
    updated_at: Optional[datetime.datetime] = None

@dataclass
class AuditLog:
    id: int
    user_id: Optional[int]
    action: str
    detail: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None

@dataclass
class Client:
    id: int
    client_number: str
    full_name: str
    date_of_birth: Optional[datetime.date] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

@dataclass
class TestOrder:
    id: int
    client_id: int
    test_id: int
    ordered_by_user_id: Optional[int] = None
    ordered_at: Optional[datetime.datetime] = None
    status: str = "pending"  # pending, completed, cancelled

@dataclass
class TestResult:
    id: int
    order_id: int
    result_value: Optional[str] = None
    is_positive: Optional[bool] = None
    entered_by_user_id: Optional[int] = None
    entered_at: Optional[datetime.datetime] = None
    verified_by_user_id: Optional[int] = None
    verified_at: Optional[datetime.datetime] = None

