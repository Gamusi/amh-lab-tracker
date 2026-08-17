from pydantic import BaseModel, Field
from typing import Optional, List, Any
import datetime

class UserBase(BaseModel):
    username: str
    full_name: str
    role: str = "technician"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    password_reset_required: bool = False
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class SectionResponse(BaseModel):
    id: int
    name: str
    sort_order: int

    class Config:
        from_attributes = True

class TestBase(BaseModel):
    name: str
    section_id: int
    is_tracked: bool = False
    sort_order: int = 0

class TestCreate(TestBase):
    pass

class TestResponse(TestBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class DailyEntryItem(BaseModel):
    test_id: int
    done: int = 0
    positive: Optional[int] = None

class DailyLogSaveRequest(BaseModel):
    entry_date: datetime.date # YYYY-MM-DD
    entries: List[DailyEntryItem]

class DailyEntryResponse(BaseModel):
    id: int
    entry_date: str
    test_id: int
    done: int
    positive: Optional[int]
    entered_by_user_id: Optional[int]
    entered_at: Optional[datetime.datetime]
    updated_by_user_id: Optional[int]
    updated_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str] = None
    action: str
    detail: Optional[str]
    timestamp: datetime.datetime

    class Config:
        from_attributes = True

class ReportFilterRequest(BaseModel):
    period_type: str # Day, Week, Month, Quarter, Half-Year, Year, Financial Year
    reference_date: Optional[str] = None # YYYY-MM-DD
    financial_year: Optional[str] = None # e.g. "2026/27"
    month: Optional[str] = None # e.g. "July"

class TrendFilterRequest(BaseModel):
    from_month: str # YYYY-MM
    to_month: str # YYYY-MM

class UserRegister(BaseModel):
    username: str
    full_name: str
    password: str

class UserUpdate(BaseModel):
    role: str
    is_active: bool
    password: Optional[str] = None
