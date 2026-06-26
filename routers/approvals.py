from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid
from decimal import Decimal

from database import get_db
from models import (
    User,
    Role,
    Device,
    DeviceStatus,
    Booking,
    BookingStatus,
    ApprovalStep,
    ApprovalRecord,
    ApprovalAction,
    Payment,
    PaymentStatus,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/api/approvals", tags=["预约审批中心"])


def booking_status_label(status):
    mapping = {
        BookingStatus.PENDING_TEACHER: "待指导教师审批",
        BookingStatus.PENDING_ADMIN: "待管理员初审",
        BookingStatus.PENDING_LEADER: "待负责人审批",
        BookingStatus.PENDING_PAYMENT: "待财务缴费",
        BookingStatus.PAYMENT_SUBMITTED: "待管理员确认缴费",
        BookingStatus.APPROVED: "已通过",
        BookingStatus.REJECTED: "已驳回",
        BookingStatus.CANCELLED: "已撤销",
        BookingStatus.COMPLETED: "已完成",
    }
    return mapping.get(status, status.value if status else None)


def parse_role(value: Optional[str]):
    if not value:
        return None

    value = str(value).strip()

    mapping = {
        "admin": Role.ADMIN,
        "labLeader": Role.LAB_LEADER,
        "leader": Role.LAB_LEADER,
        "teacher": Role.TEACHER,
        "student": Role.STUDENT,
        "outside": Role.OUTSIDE,
        "ADMIN": Role.ADMIN,
        "LAB_LEADER": Role.LAB_LEADER,
        "TEACHER": Role.TEACHER,
        "STUDENT": Role.STUDENT,
        "OUTSIDE": Role.OUTSIDE,
    }

    if value not in mapping:
        raise HTTPException(status_code=400, detail=f"角色参数不合法：{value}")

    return mapping[value]


def parse_step(value: Optional[str]):
    if not value:
        return None

    value = str(value).strip()

    mapping = {
        "teacher": ApprovalStep.TEACHER,
        "admin": ApprovalStep.ADMIN,
        "leader": ApprovalStep.LEADER,
        "finance": ApprovalStep.FINANCE,
        "end": ApprovalStep.END,
        "TEACHER": ApprovalStep.TEACHER,
        "ADMIN": ApprovalStep.ADMIN,
        "LEADER": ApprovalStep.LEADER,
        "FINANCE": ApprovalStep.FINANCE,
        "END": ApprovalStep.END,
    }

    if value not in mapping:
        raise HTTPException(status_code=400, detail=f"审批环节参数不合法：{value}")

    return mapping[value]


def parse_status(value: Optional[str]):
    if not value:
        return None

    value = str(value).strip()

    mapping = {
        "pending_teacher": BookingStatus.PENDING_TEACHER,
        "pending_admin": BookingStatus.PENDING_ADMIN,
        "pending_leader": BookingStatus.PENDING_LEADER,
        "pending_payment": BookingStatus.PENDING_PAYMENT,
        "payment_submitted": BookingStatus.PAYMENT_SUBMITTED,
        "approved": BookingStatus.APPROVED,
        "rejected": BookingStatus.REJECTED,
        "cancelled": BookingStatus.CANCELLED,
        "completed": BookingStatus.COMPLETED,

        "待指导教师审批": BookingStatus.PENDING_TEACHER,
        "待管理员初审": BookingStatus.PENDING_ADMIN,
        "待负责人审批": BookingStatus.PENDING_LEADER,
        "待财务缴费": BookingStatus.PENDING_PAYMENT,
        "待管理员确认缴费": BookingStatus.PAYMENT_SUBMITTED,
        "已通过": BookingStatus.APPROVED,
        "负责人已通过": BookingStatus.APPROVED,
        "已驳回": BookingStatus.REJECTED,
        "已撤销": BookingStatus.CANCELLED,
        "已完成": BookingStatus.COMPLETED,

        "PENDING_TEACHER": BookingStatus.PENDING_TEACHER,
        "PENDING_ADMIN": BookingStatus.PENDING_ADMIN,
        "PENDING_LEADER": BookingStatus.PENDING_LEADER,
        "PENDING_PAYMENT": BookingStatus.PENDING_PAYMENT,
        "PAYMENT_SUBMITTED": BookingStatus.PAYMENT_SUBMITTED,
        "APPROVED": BookingStatus.APPROVED,
        "REJECTED": BookingStatus.REJECTED,
        "CANCELLED": BookingStatus.CANCELLED,
        "COMPLETED": BookingStatus.COMPLETED,
    }

    if value not in mapping:
        raise HTTPException(status_code=400, detail=f"预约状态参数不合法：{value}")

    return mapping[value]


def generate_payment_no():
    return "PAY" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()

def device_status_label(status):
    mapping = {
        DeviceStatus.IDLE: "可预约",
        DeviceStatus.USING: "使用中",
        DeviceStatus.MAINTENANCE: "检修中",
        DeviceStatus.SCRAPPED: "已报废",
        DeviceStatus.DISABLED: "已停用",
    }
    return mapping.get(status, status.value if status else "未知")


def add_approval_record(
    db: Session,
    booking: Booking,
    approver_id: Optional[int],
    step: ApprovalStep,
    action: ApprovalAction,
    before_status: Optional[str],
    after_status: Optional[str],
    comment: str
):
    record = ApprovalRecord(
        booking_id=booking.id,
        approver_id=approver_id,
        approval_step=step,
        action=action,
        before_status=before_status,
        after_status=after_status,
        comment=comment,
    )
    db.add(record)


def booking_to_frontend(b: Booking):
    applicant = b.applicant
    device = b.device

    applicant_name = applicant.name if applicant else None
    applicant_username = applicant.username if applicant else None
    applicant_role = applicant.role.value if applicant and applicant.role else None

    device_name = device.model if device else None
    device_code = device.device_code if device else None

    status_text = booking_status_label(b.status)
    status_code = b.status.value if b.status else None
    current_step = b.current_step.value if b.current_step else None

    return {
        "id": b.id,
        "bookingNo": b.booking_no,
        "booking_no": b.booking_no,

        # 申请人信息：驼峰 + 下划线都返回
        "role": applicant_role,
        "applicantName": applicant_name,
        "applicant_name": applicant_name,
        "applicantId": applicant_username,
        "applicant_id": applicant_username,
        "applicantUserId": applicant.id if applicant else None,
        "applicant_user_id": applicant.id if applicant else None,

        "company": applicant.company if applicant else None,
        "college": applicant.college if applicant else None,
        "phone": applicant.phone if applicant else None,

        # 设备信息：驼峰 + 下划线都返回
        "deviceId": b.device_id,
        "device_id": b.device_id,
        "deviceName": device_name,
        "device_name": device_name,
        "deviceCode": device_code,
        "device_code": device_code,

        # 时间信息：驼峰 + 下划线都返回
        "startTime": b.start_time,
        "start_time": b.start_time,
        "endTime": b.end_time,
        "end_time": b.end_time,

        # 用途
        "reason": b.purpose,
        "purpose": b.purpose,

        # 状态
        "status": status_text,
        "statusText": status_text,
        "status_text": status_text,
        "statusCode": status_code,
        "status_code": status_code,

        "currentStep": current_step,
        "current_step": current_step,

        # 费用
        "totalFee": float(b.total_fee or 0),
        "total_fee": float(b.total_fee or 0),
        "isPaid": b.is_paid,
        "is_paid": b.is_paid,

        "cancelReason": b.cancel_reason,
        "cancel_reason": b.cancel_reason,

        "createdAt": b.created_at,
        "created_at": b.created_at,
        "updatedAt": b.updated_at,
        "updated_at": b.updated_at,
    }


@router.get("/")
def get_approvals(
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_step: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="只有设备管理员和实验室负责人可以查看审批中心")

    query = db.query(Booking).join(User, Booking.applicant_id == User.id)

    role_enum = parse_role(role)
    status_enum = parse_status(status)
    step_enum = parse_step(current_step)

    if role_enum:
        query = query.filter(User.role == role_enum)

    if status_enum:
        query = query.filter(Booking.status == status_enum)

    if step_enum:
        query = query.filter(Booking.current_step == step_enum)

    # 实验室负责人默认只看负责人审批环节、待缴费或已完成的校外相关单也可通过参数查看
    if current_user.role == Role.LAB_LEADER and not current_step:
        query = query.filter(
            Booking.current_step.in_([
                ApprovalStep.LEADER,
                ApprovalStep.FINANCE,
                ApprovalStep.END
            ])
        )

    bookings = query.order_by(Booking.created_at.desc()).all()

    return {
        "code": 20000,
        "data": [booking_to_frontend(b) for b in bookings]
    }


@router.put("/{booking_id}/approve")
def approve_workflow(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约单未找到")

    applicant = booking.applicant

    if not applicant:
        raise HTTPException(status_code=400, detail="预约申请人不存在")

    old_status = booking.status.value

    # 设备管理员审批
    if booking.current_step == ApprovalStep.ADMIN and current_user.role == Role.ADMIN:
        if applicant.role in [Role.STUDENT, Role.TEACHER]:
            booking.status = BookingStatus.APPROVED
            booking.current_step = ApprovalStep.END

            comment = "设备管理员审批通过，预约成功"

        elif applicant.role == Role.OUTSIDE:
            booking.status = BookingStatus.PENDING_LEADER
            booking.current_step = ApprovalStep.LEADER

            comment = "设备管理员初审通过，提交实验室负责人审批"

        else:
            raise HTTPException(status_code=400, detail="申请人角色异常")

        add_approval_record(
            db=db,
            booking=booking,
            approver_id=current_user.id,
            step=ApprovalStep.ADMIN,
            action=ApprovalAction.APPROVE,
            before_status=old_status,
            after_status=booking.status.value,
            comment=comment,
        )

    # 实验室负责人审批校外预约
    elif booking.current_step == ApprovalStep.LEADER and current_user.role == Role.LAB_LEADER:
        if applicant.role != Role.OUTSIDE:
            raise HTTPException(status_code=400, detail="负责人只审批校外预约")

        booking.status = BookingStatus.PENDING_PAYMENT
        booking.current_step = ApprovalStep.FINANCE

        add_approval_record(
            db=db,
            booking=booking,
            approver_id=current_user.id,
            step=ApprovalStep.LEADER,
            action=ApprovalAction.APPROVE,
            before_status=old_status,
            after_status=booking.status.value,
            comment="实验室负责人审批通过，等待校外人员缴费",
        )

    else:
        raise HTTPException(status_code=403, detail="您当前无权或单据不在您负责的审批环节")

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "审批通过",
        "data": booking_to_frontend(booking)
    }


@router.put("/{booking_id}/reject")
def reject_workflow(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约单未找到")

    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="您没有权限拒绝该单据")

    if current_user.role == Role.ADMIN and booking.current_step != ApprovalStep.ADMIN:
        raise HTTPException(status_code=400, detail="该预约不在管理员审批环节")

    if current_user.role == Role.LAB_LEADER and booking.current_step != ApprovalStep.LEADER:
        raise HTTPException(status_code=400, detail="该预约不在负责人审批环节")

    old_status = booking.status.value

    booking.status = BookingStatus.REJECTED
    booking.current_step = ApprovalStep.END

    step = ApprovalStep.ADMIN if current_user.role == Role.ADMIN else ApprovalStep.LEADER

    add_approval_record(
        db=db,
        booking=booking,
        approver_id=current_user.id,
        step=step,
        action=ApprovalAction.REJECT,
        before_status=old_status,
        after_status=booking.status.value,
        comment="审批人驳回预约申请",
    )

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "申请已被驳回",
        "data": booking_to_frontend(booking)
    }


@router.post("/{booking_id}/finance-callback")
def finance_callback(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="只有设备管理员可以确认缴费")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约单未找到")

    if booking.status != BookingStatus.PAYMENT_SUBMITTED:
        raise HTTPException(
            status_code=400,
            detail="校外人员尚未完成缴费提交，不能确认缴费"
        )

    old_status = booking.status.value

    booking.is_paid = True
    booking.status = BookingStatus.APPROVED
    booking.current_step = ApprovalStep.END

    exists_payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()

    if not exists_payment:
        payment = Payment(
            booking_id=booking.id,
            payer_id=booking.applicant_id,
            payment_no=generate_payment_no(),
            amount=Decimal(str(booking.total_fee or 0)),
            payment_method="online_mock",
            payment_status=PaymentStatus.PAID,
            paid_at=datetime.utcnow(),
        )
        db.add(payment)

    add_approval_record(
        db=db,
        booking=booking,
        approver_id=current_user.id,
        step=ApprovalStep.FINANCE,
        action=ApprovalAction.PAYMENT_CONFIRM,
        before_status=old_status,
        after_status=booking.status.value,
        comment="设备管理员确认校外预约缴费完成",
    )

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "缴费确认成功，预约已通过",
        "data": booking_to_frontend(booking)
    }

@router.get("/{booking_id}/availability")
def check_booking_availability(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    设备管理员查看某个预约单对应设备在申请时段内是否可用。
    判断逻辑：
    1. 设备本身不能是检修、停用、报废。
    2. 同一设备在该时间段不能存在其他未结束、未撤销、未驳回的预约。
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="只有设备管理员可以查看设备时段可用性")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约单不存在")

    device = db.query(Device).filter(Device.id == booking.device_id).first()

    if not device:
        raise HTTPException(status_code=404, detail="预约关联设备不存在")

    # 设备基础状态检查
    device_unavailable_status = [
        DeviceStatus.MAINTENANCE,
        DeviceStatus.DISABLED,
        DeviceStatus.SCRAPPED
    ]

    device_status_ok = device.status not in device_unavailable_status

    # 检查同一设备在申请时段内是否有其他未结束预约冲突
    active_statuses = [
        BookingStatus.PENDING_TEACHER,
        BookingStatus.PENDING_ADMIN,
        BookingStatus.PENDING_LEADER,
        BookingStatus.PENDING_PAYMENT,
        BookingStatus.PAYMENT_SUBMITTED,
        BookingStatus.APPROVED,
    ]

    conflict_bookings = db.query(Booking).filter(
        Booking.id != booking.id,
        Booking.device_id == booking.device_id,
        Booking.status.in_(active_statuses),
        Booking.current_step != ApprovalStep.END,
        Booking.start_time < booking.end_time,
        Booking.end_time > booking.start_time
    ).order_by(Booking.start_time.asc()).all()

    conflict_list = []

    for item in conflict_bookings:
        applicant = item.applicant

        conflict_list.append({
            "id": item.id,
            "bookingNo": item.booking_no,
            "applicantName": applicant.name if applicant else None,
            "applicantRole": applicant.role.value if applicant and applicant.role else None,
            "startTime": item.start_time,
            "endTime": item.end_time,
            "status": booking_status_label(item.status),
            "statusCode": item.status.value if item.status else None
        })

    is_available = device_status_ok and len(conflict_list) == 0

    if not device_status_ok:
        message = f"设备当前状态为【{device_status_label(device.status)}】，不可预约"
    elif conflict_list:
        message = "该设备在申请时段内已有其他预约，占用冲突"
    else:
        message = "该设备在申请时段内可用"

    return {
        "code": 20000,
        "data": {
            "available": is_available,
            "message": message,
            "device": {
                "id": device.id,
                "deviceCode": device.device_code,
                "name": device.name,
                "model": device.model,
                "status": device_status_label(device.status),
                "statusCode": device.status.value if device.status else None,
                "location": device.location
            },
            "booking": {
                "id": booking.id,
                "bookingNo": booking.booking_no,
                "startTime": booking.start_time,
                "endTime": booking.end_time,
                "status": booking_status_label(booking.status),
                "statusCode": booking.status.value if booking.status else None
            },
            "conflicts": conflict_list
        }
    }