from pydantic import BaseModel, Field
from typing import Optional, List, Any
import datetime

class UserBase(BaseModel):
    username: str
    full_name: str
    role: str = "staff"
    cadre: Optional[str] = None

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
    result_type: str = "qualitative"
    default_unit: Optional[str] = None
    options: Optional[str] = None

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
    cadre: Optional[str] = None

class UserUpdate(BaseModel):
    role: str
    is_active: bool
    password: Optional[str] = None
    cadre: Optional[str] = None

class ClinicianBase(BaseModel):
    name: str

class ClinicianCreate(ClinicianBase):
    pass

class ClinicianUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class ClinicianResponse(ClinicianBase):
    id: int
    is_active: bool = True
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class ResultEdit(BaseModel):
    order_id: int
    result_value: Optional[str] = None
    parameter_results: Optional[list] = None
    result_unit: Optional[str] = None
    edit_reason: str

class VisitCreate(BaseModel):
    client_id: int
    clinician_id: Optional[int] = None
    ward_of_origin: Optional[str] = None
    test_ids: List[int]
    sample_id: Optional[str] = None
    order_category: Optional[str] = 'in-house' 

class VisitResponse(BaseModel):
    id: int
    client_id: int
    clinician_id: Optional[int] = None
    ward_of_origin: Optional[str] = None
    lab_number: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class WardBase(BaseModel):
    name: str

class WardCreate(WardBase):
    pass

class WardUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class WardResponse(WardBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class ParameterResultItem(BaseModel):
    parameter_id: int
    result_value: str

class TestResultCreate(BaseModel):
    order_id: int
    result_value: Optional[str] = None
    result_unit: Optional[str] = None
    parameter_results: Optional[List[ParameterResultItem]] = None
    edit_reason: Optional[str] = None

class AddOrdersRequest(BaseModel):
    test_ids: List[int]
    sample_id: Optional[str] = None
    order_category: Optional[str] = "in-house"



