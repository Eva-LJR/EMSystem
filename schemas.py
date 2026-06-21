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

# class UserUpdate(BaseModel):
#     name: Optional[str] = None
#     role: Optional[Role] = None
#     avatar: Optional[str] = None
#     college: Optional[str] = None
#     phone: Optional[str] = None
class UserUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    college: Optional[str] = None
    major: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None

    # 教师字段
    title: Optional[str] = None

    # 学生字段，前端用 teacherName
    teacherName: Optional[str] = None

    # 校外人员字段
    company: Optional[str] = None

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
    device_code: Optional[str] = None
    name: Optional[str] = None
    model: str
    purchase_date: Optional[datetime] = None
    buy_time: Optional[datetime] = None  # 兼容旧前端字段
    manufacturer: Optional[str] = None
    purpose: Optional[str] = None
    purchase_price: Optional[float] = None
    hourly_price: Optional[float] = None
    price: Optional[float] = None  # 兼容旧前端字段
    status: Optional[str] = None
    location: Optional[str] = None
    available_time: Optional[str] = None
    description: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    device_code: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    purchase_date: Optional[datetime] = None
    buy_time: Optional[datetime] = None
    manufacturer: Optional[str] = None
    purpose: Optional[str] = None
    purchase_price: Optional[float] = None
    hourly_price: Optional[float] = None
    price: Optional[float] = None
    status: Optional[str] = None
    location: Optional[str] = None
    available_time: Optional[str] = None
    description: Optional[str] = None


class Device(DeviceBase):
    id: int

    model_config = {"from_attributes": True}

# --- 审批相关 ---
# class ApprovalBase(BaseModel):
#     device_id: int
#     role: Role
#     device_name: str
#     start_time: datetime
#     end_time: datetime
#     reason: str
    # applicant_name: str
    # applicant_id: str
    # company: Optional[str] = None
    # college: Optional[str] = None
    # teacher_name: Optional[str] = None
class ApprovalBase(BaseModel):
    device_id: int
    device_name: str
    start_time: datetime
    end_time: datetime
    reason: str

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