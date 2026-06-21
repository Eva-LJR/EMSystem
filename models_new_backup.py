import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


# =========================================================
# 枚举
# =========================================================

class Role(str, enum.Enum):
    ADMIN = "admin"
    LAB_LEADER = "labLeader"
    TEACHER = "teacher"
    STUDENT = "student"
    OUTSIDE = "outside"


class AccountStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    REJECTED = "rejected"


class DeviceStatus(str, enum.Enum):
    IDLE = "idle"
    USING = "using"
    MAINTENANCE = "maintenance"
    SCRAPPED = "scrapped"
    DISABLED = "disabled"


class BookingStatus(str, enum.Enum):
    PENDING_TEACHER = "pending_teacher"
    PENDING_ADMIN = "pending_admin"
    PENDING_LEADER = "pending_leader"
    PENDING_PAYMENT = "pending_payment"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ApprovalStep(str, enum.Enum):
    TEACHER = "teacher"
    ADMIN = "admin"
    LEADER = "leader"
    FINANCE = "finance"
    END = "end"


class ApprovalAction(str, enum.Enum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"
    PAYMENT_CONFIRM = "payment_confirm"
    SYSTEM_REJECT = "system_reject"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ProcessStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceStatus(str, enum.Enum):
    REPORTED = "reported"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =========================================================
# 1. 用户表
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    name = Column(String(50), nullable=False)
    role = Column(Enum(Role), nullable=False, index=True)

    gender = Column(String(10))
    phone = Column(String(20), unique=True)
    email = Column(String(100), unique=True)
    identity_no = Column(String(50), unique=True)

    college = Column(String(100))
    major = Column(String(100))
    title = Column(String(50))
    company = Column(String(150))
    avatar = Column(String(255))

    account_status = Column(
        Enum(AccountStatus),
        nullable=False,
        default=AccountStatus.ACTIVE
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    bookings = relationship(
        "Booking",
        back_populates="applicant",
        foreign_keys="Booking.applicant_id"
    )


# =========================================================
# 2. 师生关系表
# =========================================================

class TeacherStudent(Base):
    __tablename__ = "teacher_students"

    id = Column(Integer, primary_key=True, autoincrement=True)

    teacher_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())

    teacher = relationship(
        "User",
        foreign_keys=[teacher_id]
    )
    student = relationship(
        "User",
        foreign_keys=[student_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "student_id",
            name="uk_teacher_student"
        ),
    )


# =========================================================
# 3. 设备表
# =========================================================

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_code = Column(String(50), unique=True, nullable=False)

    name = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    manufacturer = Column(String(100))
    purpose = Column(Text)

    purchase_price = Column(Numeric(10, 2), default=0)
    hourly_price = Column(Numeric(10, 2), default=0)
    purchase_date = Column(DateTime)

    status = Column(
        Enum(DeviceStatus),
        nullable=False,
        default=DeviceStatus.IDLE
    )

    location = Column(String(100))
    available_time = Column(String(255))
    description = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    bookings = relationship("Booking", back_populates="device")


# =========================================================
# 4. 预约表
# =========================================================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_no = Column(String(50), unique=True, nullable=False)

    applicant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    purpose = Column(Text, nullable=False)

    status = Column(
        Enum(BookingStatus),
        nullable=False
    )
    current_step = Column(
        Enum(ApprovalStep),
        nullable=False
    )

    total_fee = Column(Numeric(10, 2), nullable=False, default=0)
    is_paid = Column(Boolean, nullable=False, default=False)
    cancel_reason = Column(String(255))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    applicant = relationship(
        "User",
        back_populates="bookings",
        foreign_keys=[applicant_id]
    )
    device = relationship("Device", back_populates="bookings")

    approval_records = relationship(
        "ApprovalRecord",
        back_populates="booking",
        cascade="all, delete-orphan"
    )

    payment = relationship(
        "Payment",
        back_populates="booking",
        uselist=False
    )


# =========================================================
# 5. 审批记录表
# =========================================================

class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    approver_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    approval_step = Column(Enum(ApprovalStep), nullable=False)
    action = Column(Enum(ApprovalAction), nullable=False)

    comment = Column(String(500))
    before_status = Column(String(50))
    after_status = Column(String(50))

    created_at = Column(DateTime, server_default=func.now())

    booking = relationship(
        "Booking",
        back_populates="approval_records"
    )
    approver = relationship("User", foreign_keys=[approver_id])


# =========================================================
# 6. 缴费记录表
# =========================================================

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True
    )
    payer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    payment_no = Column(String(50), unique=True, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    payment_method = Column(String(30))
    payment_status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING
    )

    paid_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    booking = relationship("Booking", back_populates="payment")
    payer = relationship("User", foreign_keys=[payer_id])

    refund = relationship(
        "Refund",
        back_populates="payment",
        uselist=False
    )


# =========================================================
# 7. 退款记录表
# =========================================================

class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, autoincrement=True)

    payment_id = Column(
        Integer,
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True
    )
    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False
    )

    refund_no = Column(String(50), unique=True, nullable=False)
    refund_amount = Column(Numeric(10, 2), nullable=False)
    service_fee = Column(Numeric(10, 2), nullable=False, default=0)

    refund_reason = Column(String(255))
    refund_status = Column(
        Enum(RefundStatus),
        nullable=False,
        default=RefundStatus.PENDING
    )

    refunded_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    payment = relationship("Payment", back_populates="refund")
    booking = relationship("Booking")


# =========================================================
# 8. 采购记录表
# =========================================================

class Procurement(Base):
    __tablename__ = "procurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    procurement_no = Column(String(50), unique=True, nullable=False)

    device_name = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    manufacturer = Column(String(100))

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    supplier = Column(String(150))

    applicant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL")
    )

    status = Column(
        Enum(ProcessStatus),
        nullable=False,
        default=ProcessStatus.PENDING
    )

    purchase_date = Column(DateTime)
    remark = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    applicant = relationship(
        "User",
        foreign_keys=[applicant_id]
    )
    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id]
    )


# =========================================================
# 9. 维修记录表
# =========================================================

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False
    )
    reporter_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL")
    )

    fault_description = Column(Text, nullable=False)
    maintenance_company = Column(String(150))
    maintenance_cost = Column(Numeric(10, 2), default=0)

    start_time = Column(DateTime)
    end_time = Column(DateTime)
    result = Column(Text)

    status = Column(
        Enum(MaintenanceStatus),
        nullable=False,
        default=MaintenanceStatus.REPORTED
    )

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    device = relationship("Device")
    reporter = relationship("User", foreign_keys=[reporter_id])


# =========================================================
# 10. 报废记录表
# =========================================================

class ScrapRecord(Base):
    __tablename__ = "scrap_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False
    )
    applicant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL")
    )

    scrap_reason = Column(Text, nullable=False)

    status = Column(
        Enum(ProcessStatus),
        nullable=False,
        default=ProcessStatus.PENDING
    )

    review_comment = Column(Text)
    applied_at = Column(DateTime, server_default=func.now())
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    device = relationship("Device")
    applicant = relationship(
        "User",
        foreign_keys=[applicant_id]
    )
    reviewer = relationship(
        "User",
        foreign_keys=[reviewer_id]
    )