import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Float, Boolean, ForeignKey
from sqlalchemy.sql import func
from database import Base


# 角色枚举
class Role(str, enum.Enum):
    ADMIN = "admin"  # 设备管理员
    LAB_LEADER = "labLeader"  # 实验室负责人
    TEACHER = "teacher"  # 教师
    STUDENT = "student"  # 学生
    OUTSIDE = "outside"  # 校外人员


# 审批状态枚举
class ApprovalStatus(str, enum.Enum):
    PENDING_TEACHER = "待指导教师审批"
    PENDING_ADMIN = "待管理员初审"
    PENDING_LEADER = "待负责人审批"
    PENDING_PAY = "待财务缴费"
    APPROVED = "负责人已通过"
    CANCELLED = "已撤销"
    REJECTED_BY_TEACHER = "教师已驳回"
    REJECTED_BY_ADMIN = "管理员已驳回"
    REJECTED_BY_LEADER = "负责人已驳回"


# 审批当前所处步骤
class ApprovalStep(str, enum.Enum):
    TEACHER = "teacher"
    ADMIN = "admin"
    LEADER = "leader"
    FINANCE = "finance"
    END = "end"


# 设备可用状态
class DeviceStatus(str, enum.Enum):
    IDLE = "可预约"
    USING = "使用中"
    MAINTENANCE = "检修中"
    DISABLED = "已报废"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    gender = Column(String, nullable=True)

    # 教师台账专属
    title = Column(String, nullable=True)  # 职称

    # 教师/学生共有
    major = Column(String, nullable=True)  # 专业/专业方向
    college = Column(String, nullable=True)  # 所在学院

    # 学生台账专属
    teacher_name = Column(String, nullable=True)  # 指导老师姓名

    # 校外人员台账专属
    company = Column(String, nullable=True)  # 所在单位名称
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String, index=True, nullable=False)  # 设备型号
    buy_time = Column(DateTime)  # 购入时间
    manufacturer = Column(String)  # 生产厂商
    purpose = Column(String)  # 实验用途
    price = Column(Float, default=0.0)  # 租用价格（校外人员计费依据）
    status = Column(Enum(DeviceStatus), default=DeviceStatus.IDLE)  # 状态
    available_time = Column(String)  # 可用时段描述


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(Role), nullable=False)  # 申请人角色
    device_id = Column(Integer, ForeignKey("devices.id"))
    device_name = Column(String, nullable=False)  # 预约设备型号
    start_time = Column(DateTime, nullable=False)  # 借用开始时间
    end_time = Column(DateTime, nullable=False)  # 借用结束时间
    reason = Column(Text)  # 借用用途/原因

    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING_ADMIN)
    current_step = Column(Enum(ApprovalStep), default=ApprovalStep.ADMIN)

    # 申请人快照信息（满足5类书面台账对关联关系及快照的审计需求）
    applicant_name = Column(String, nullable=False)
    applicant_id = Column(String, nullable=False)  # 学号/工号/身份证号
    company = Column(String, nullable=True)  # 单位（校外）
    college = Column(String, nullable=True)  # 学院（师生）
    teacher_name = Column(String, nullable=True)  # 指导老师（学生）

    # 财务与退费相关
    total_fee = Column(Float, default=0.0)  # 总计费用
    is_paid = Column(Boolean, default=False)  # 是否已完成缴费
    refund_amount = Column(Float, default=0.0)  # 退款金额

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())