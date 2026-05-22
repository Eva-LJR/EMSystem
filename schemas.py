from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    LAB_LEADER = "labLeader"
    TEACHER = "teacher"
    STUDENT = "student"
    OUTSIDE = "outside"

class ApprovalStatus(str, Enum):
    PENDING_TEACHER = "待指导教师审批"
    PENDING_ADMIN = "待管理员初审"
    PENDING_LEADER = "待负责人审批"
    PENDING_PAY = "待财务缴费"
    APPROVED = "负责人已通过"
    CANCELLED = "已撤销"
    REJECTED_BY_TEACHER = "教师已驳回"
    REJECTED_BY_ADMIN = "管理员已驳回"
    REJECTED_BY_LEADER = "负责人已驳回"

class ApprovalStep(str, Enum):
    TEACHER = "teacher"
    ADMIN = "admin"
    LEADER = "leader"
    FINANCE = "finance"
    END = "end"

class DeviceStatus(str, Enum):
    IDLE = "可预约"
    USING = "使用中"
    MAINTENANCE = "检修中"
    DISABLED = "已报废"

# --- 用户相关 ---
class UserBase(BaseModel):
    username: str
    name: str
    role: Role

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[Role] = None
    avatar: Optional[str] = None
    college: Optional[str] = None
    phone: Optional[str] = None

class UserInDB(UserBase):
    id: int
    avatar: Optional[str] = None
    college: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}

# ⚠️ 注意：下面这一行必须绝对靠左顶格，前面不能有任何空格！
# --- 认证相关 ---
class Token(BaseModel):
    token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[int] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# --- 设备相关 ---
class DeviceBase(BaseModel):
    model: str
    buy_time: Optional[datetime] = None
    manufacturer: Optional[str] = None
    purpose: Optional[str] = None
    price: Optional[float] = None
    status: DeviceStatus = DeviceStatus.IDLE
    available_time: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    model: Optional[str] = None
    buy_time: Optional[datetime] = None
    manufacturer: Optional[str] = None
    purpose: Optional[str] = None
    price: Optional[float] = None
    status: Optional[DeviceStatus] = None
    available_time: Optional[str] = None

class Device(DeviceBase):
    id: int

    model_config = {"from_attributes": True}

# --- 审批相关 ---
class ApprovalBase(BaseModel):
    role: Role
    device_name: str
    start_time: datetime
    end_time: datetime
    reason: str
    applicant_name: str
    applicant_id: str
    company: Optional[str] = None
    college: Optional[str] = None
    teacher_name: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    pass

class ApprovalUpdate(BaseModel):
    status: Optional[ApprovalStatus] = None
    current_step: Optional[ApprovalStep] = None
    approver_id: Optional[int] = None

class Approval(ApprovalBase):
    id: int
    status: ApprovalStatus
    current_step: ApprovalStep
    created_at: datetime

    model_config = {"from_attributes": True}

# --- 统计相关 ---
class StatResponse(BaseModel):
    total_devices: int
    total_approvals: int
    pending_approvals: int
    approved_approvals: int