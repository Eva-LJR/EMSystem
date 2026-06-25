from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
import uuid

from database import get_db
from models import (
    User,
    Device,
    Booking,
    BookingStatus,
    ApprovalStep,
    ApprovalRecord,
    ApprovalAction,
    Role,
    DeviceStatus,
    TeacherStudent,
    Payment,
    Refund,
    RefundStatus,
)
from schemas import ApprovalCreate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/client", tags=["学生教师校外人员端"])


# =========================
# 工具函数
# =========================

def check_client_role(user: User):
    if user.role not in [Role.STUDENT, Role.TEACHER, Role.OUTSIDE]:
        raise HTTPException(status_code=403, detail="仅学生、教师、校外人员可访问")


def generate_booking_no():
    return "BK" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()


def generate_refund_no():
    return "RF" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()


def get_student_teacher_name(db: Session, student_id: int):
    relation = db.query(TeacherStudent).filter(
        TeacherStudent.student_id == student_id,
        TeacherStudent.status == "active"
    ).first()

    if relation and relation.teacher:
        return relation.teacher.name

    return None


def check_teacher_can_approve_student(
    db: Session,
    teacher_id: int,
    student_id: int
):
    relation = db.query(TeacherStudent).filter(
        TeacherStudent.teacher_id == teacher_id,
        TeacherStudent.student_id == student_id,
        TeacherStudent.status == "active"
    ).first()

    return relation is not None


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
        comment=comment
    )
    db.add(record)


def device_status_label(status):
    mapping = {
        DeviceStatus.IDLE: "可预约",
        DeviceStatus.USING: "使用中",
        DeviceStatus.MAINTENANCE: "检修中",
        DeviceStatus.SCRAPPED: "已报废",
        DeviceStatus.DISABLED: "已停用",
    }
    return mapping.get(status, status.value if status else None)


def device_to_frontend(d: Device):
    return {
        "id": d.id,
        "deviceCode": d.device_code,
        "name": d.name,
        "model": d.model,
        "buyTime": d.purchase_date,
        "purchaseDate": d.purchase_date,
        "manufacturer": d.manufacturer,
        "purpose": d.purpose,
        "price": float(d.hourly_price or 0),
        "hourlyPrice": float(d.hourly_price or 0),
        "purchasePrice": float(d.purchase_price or 0),
        "status": device_status_label(d.status),
        "statusCode": d.status.value if d.status else None,
        "location": d.location,
        "availableTime": d.available_time,
        "description": d.description,
        "createdAt": d.created_at,
        "updatedAt": d.updated_at,
    }


def booking_to_frontend(db: Session, b: Booking):
    applicant = b.applicant
    device = b.device

    teacher_name = None
    if applicant and applicant.role == Role.STUDENT:
        teacher_name = get_student_teacher_name(db, applicant.id)

    refund_amount = None
    refund = db.query(Refund).filter(Refund.booking_id == b.id).first()
    if refund:
        refund_amount = float(refund.refund_amount or 0)

    return {
        "id": b.id,
        "bookingNo": b.booking_no,

        # 为兼容旧前端，仍然返回 role、deviceName、reason 等字段
        "role": applicant.role.value if applicant and applicant.role else None,
        "deviceId": b.device_id,
        "deviceName": device.model if device else None,
        "deviceCode": device.device_code if device else None,

        "startTime": b.start_time,
        "endTime": b.end_time,
        "reason": b.purpose,
        "purpose": b.purpose,

        "status": booking_status_label(b.status),
        "statusCode": b.status.value if b.status else None,
        "currentStep": b.current_step.value if b.current_step else None,

        "applicantName": applicant.name if applicant else None,
        "applicantId": applicant.username if applicant else None,
        "applicantUserId": applicant.id if applicant else None,

        "company": applicant.company if applicant else None,
        "college": applicant.college if applicant else None,
        "teacherName": teacher_name,

        "totalFee": float(b.total_fee or 0),
        "isPaid": b.is_paid,
        "refundAmount": refund_amount,
        "cancelReason": b.cancel_reason,

        "createdAt": b.created_at,
        "updatedAt": b.updated_at,
    }


def booking_status_label(status):
    mapping = {
        BookingStatus.PENDING_TEACHER: "待指导教师审批",
        BookingStatus.PENDING_ADMIN: "待管理员初审",
        BookingStatus.PENDING_LEADER: "待负责人审批",
        BookingStatus.PENDING_PAYMENT: "待财务缴费",
        BookingStatus.APPROVED: "已通过",
        BookingStatus.REJECTED: "已驳回",
        BookingStatus.CANCELLED: "已撤销",
        BookingStatus.COMPLETED: "已完成",
    }
    return mapping.get(status, status.value if status else None)


def booking_can_operate_for_teacher(booking: Booking, current_user: User):
    return (
        current_user.role == Role.TEACHER
        and booking.current_step == ApprovalStep.TEACHER
        and booking.status == BookingStatus.PENDING_TEACHER
    )


# =========================
# 1. 查询设备列表
# =========================

@router.get("/devices")
def client_devices(
    keyword: Optional[str] = Query(None),
    status: Optional[DeviceStatus] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    query = db.query(Device)

    if status:
        query = query.filter(Device.status == status)

    if keyword:
        query = query.filter(
            (Device.name.contains(keyword)) |
            (Device.model.contains(keyword)) |
            (Device.device_code.contains(keyword)) |
            (Device.manufacturer.contains(keyword))
        )

    total = query.count()

    devices = (
        query
        .order_by(Device.id.asc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )

    return {
        "code": 20000,
        "data": {
            "items": [device_to_frontend(d) for d in devices],
            "total": total,
            "page": page,
            "pageSize": pageSize
        }
    }


# =========================
# 2. 查询我的预约
# =========================

@router.get("/bookings")
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    bookings = db.query(Booking).filter(
        Booking.applicant_id == current_user.id
    ).order_by(Booking.created_at.desc()).all()

    return {
        "code": 20000,
        "data": [booking_to_frontend(db, b) for b in bookings]
    }


# =========================
# 3. 提交预约
# =========================

@router.post("/bookings")
def create_my_booking(
    payload: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    now = datetime.now(timezone.utc)

    start_time = payload.start_time
    end_time = payload.end_time

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    if not (now + timedelta(days=1) <= start_time <= now + timedelta(days=7)):
        raise HTTPException(status_code=400, detail="预约必须提前1-7天提交")

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

    duration = end_time - start_time

    if duration.total_seconds() < 7200:
        raise HTTPException(status_code=400, detail="单次借用时间不得少于2小时")

    if duration.total_seconds() % 7200 != 0:
        raise HTTPException(status_code=400, detail="借用时间必须是2小时的整数倍")

    device = db.query(Device).filter(Device.id == payload.device_id).first()

    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    if device.status in [
        DeviceStatus.MAINTENANCE,
        DeviceStatus.DISABLED,
        DeviceStatus.SCRAPPED
    ]:
        raise HTTPException(status_code=400, detail="该设备当前不可预约")

    db_start_time = start_time.replace(tzinfo=None)
    db_end_time = end_time.replace(tzinfo=None)

    # 查询冲突预约：流程未结束且时间重叠
    conflict_bookings = db.query(Booking).filter(
        Booking.device_id == payload.device_id,
        Booking.current_step != ApprovalStep.END,
        Booking.status.in_([
            BookingStatus.PENDING_TEACHER,
            BookingStatus.PENDING_ADMIN,
            BookingStatus.PENDING_LEADER,
            BookingStatus.PENDING_PAYMENT,
            BookingStatus.APPROVED,
        ]),
        Booking.start_time < db_end_time,
        Booking.end_time > db_start_time
    ).all()

    if conflict_bookings:
        # 校内人员可以挤掉校外人员的未完成预约
        if current_user.role in [Role.STUDENT, Role.TEACHER]:
            for cb in conflict_bookings:
                if cb.applicant and cb.applicant.role == Role.OUTSIDE:
                    old_status = cb.status.value
                    cb.status = BookingStatus.REJECTED
                    cb.current_step = ApprovalStep.END

                    add_approval_record(
                        db=db,
                        booking=cb,
                        approver_id=current_user.id,
                        step=ApprovalStep.END,
                        action=ApprovalAction.SYSTEM_REJECT,
                        before_status=old_status,
                        after_status=cb.status.value,
                        comment="因校内教学科研任务冲突，校内人员优先使用，系统自动退单"
                    )
                else:
                    raise HTTPException(status_code=400, detail="该时段设备已被预约")
        else:
            raise HTTPException(status_code=400, detail="该时段设备已被预约")

    total_fee = Decimal("0.00")

    if current_user.role == Role.OUTSIDE:
        hours = Decimal(str(duration.total_seconds() / 3600))
        total_fee = hours * Decimal(str(device.hourly_price or 0))

    init_status = BookingStatus.PENDING_ADMIN
    init_step = ApprovalStep.ADMIN

    if current_user.role == Role.STUDENT:
        # 学生必须存在指导教师关系
        relation = db.query(TeacherStudent).filter(
            TeacherStudent.student_id == current_user.id,
            TeacherStudent.status == "active"
        ).first()

        if not relation:
            raise HTTPException(status_code=400, detail="当前学生未绑定指导教师，无法提交预约")

        init_status = BookingStatus.PENDING_TEACHER
        init_step = ApprovalStep.TEACHER

    booking = Booking(
        booking_no=generate_booking_no(),
        applicant_id=current_user.id,
        device_id=device.id,
        start_time=db_start_time,
        end_time=db_end_time,
        purpose=payload.reason,
        status=init_status,
        current_step=init_step,
        total_fee=total_fee,
        is_paid=False
    )

    db.add(booking)
    db.flush()

    add_approval_record(
        db=db,
        booking=booking,
        approver_id=current_user.id,
        step=init_step,
        action=ApprovalAction.SUBMIT,
        before_status=None,
        after_status=booking.status.value,
        comment="用户提交设备预约申请"
    )

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "预约申请提交成功",
        "data": booking_to_frontend(db, booking)
    }


# =========================
# 4. 撤销我的预约
# =========================

@router.post("/bookings/{booking_id}/cancel")
def cancel_my_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    if booking.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能撤销自己的预约")

    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="该预约已经撤销")

    if booking.status in [
        BookingStatus.REJECTED,
        BookingStatus.COMPLETED
    ]:
        raise HTTPException(status_code=400, detail="当前状态的预约不能撤销")

    if booking.start_time - datetime.utcnow() < timedelta(days=1):
        raise HTTPException(
            status_code=400,
            detail="不符合撤销规定：距离实验开始时间不足24小时，无法撤销"
        )

    old_status = booking.status.value
    booking.status = BookingStatus.CANCELLED
    booking.current_step = ApprovalStep.END
    booking.cancel_reason = "用户主动撤销预约"

    message = "预约已成功撤销"

    # 校外用户已缴费，则生成退款记录
    if current_user.role == Role.OUTSIDE and booking.is_paid:
        payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()

        if payment:
            total_fee = Decimal(str(booking.total_fee or 0))
            refund_amount = total_fee * Decimal("0.95")
            service_fee = total_fee - refund_amount

            refund = Refund(
                payment_id=payment.id,
                booking_id=booking.id,
                refund_no=generate_refund_no(),
                refund_amount=refund_amount,
                service_fee=service_fee,
                refund_reason="用户提前撤销预约，按规定退还95%",
                refund_status=RefundStatus.SUCCESS,
                refunded_at=datetime.utcnow()
            )

            db.add(refund)

            message = f"撤销成功，付费预约退还95%，退款金额：{float(refund_amount)}元"

    add_approval_record(
        db=db,
        booking=booking,
        approver_id=current_user.id,
        step=ApprovalStep.END,
        action=ApprovalAction.CANCEL,
        before_status=old_status,
        after_status=booking.status.value,
        comment=booking.cancel_reason
    )

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": message,
        "data": booking_to_frontend(db, booking)
    }


# =========================
# 5. 教师查看待审批学生预约
# =========================

@router.get("/student-approvals")
def teacher_student_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可查看学生预约审批")

    student_ids = db.query(TeacherStudent.student_id).filter(
        TeacherStudent.teacher_id == current_user.id,
        TeacherStudent.status == "active"
    )

    approvals = db.query(Booking).filter(
        Booking.applicant_id.in_(student_ids),
        Booking.current_step == ApprovalStep.TEACHER,
        Booking.status == BookingStatus.PENDING_TEACHER
    ).order_by(Booking.created_at.desc()).all()

    return {
        "code": 20000,
        "data": [booking_to_frontend(db, b) for b in approvals]
    }


# =========================
# 6. 教师通过学生预约
# =========================

@router.put("/student-approvals/{booking_id}/approve")
def approve_student_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可审批")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    applicant = booking.applicant

    if not applicant or applicant.role != Role.STUDENT:
        raise HTTPException(status_code=400, detail="只能审批学生预约")

    if not check_teacher_can_approve_student(db, current_user.id, booking.applicant_id):
        raise HTTPException(status_code=403, detail="无权审批非本人指导学生")

    if booking.current_step != ApprovalStep.TEACHER:
        raise HTTPException(status_code=400, detail="该预约不在教师审批环节")

    old_status = booking.status.value

    booking.status = BookingStatus.PENDING_ADMIN
    booking.current_step = ApprovalStep.ADMIN

    add_approval_record(
        db=db,
        booking=booking,
        approver_id=current_user.id,
        step=ApprovalStep.TEACHER,
        action=ApprovalAction.APPROVE,
        before_status=old_status,
        after_status=booking.status.value,
        comment="指导教师审批通过，提交设备管理员审批"
    )

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "已通过，提交管理员审批",
        "data": booking_to_frontend(db, booking)
    }


# =========================
# 7. 教师驳回学生预约
# =========================

@router.put("/student-approvals/{booking_id}/reject")
def reject_student_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可审批")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    applicant = booking.applicant

    if not applicant or applicant.role != Role.STUDENT:
        raise HTTPException(status_code=400, detail="只能审批学生预约")

    if not check_teacher_can_approve_student(db, current_user.id, booking.applicant_id):
        raise HTTPException(status_code=403, detail="无权审批非本人指导学生")

    if booking.current_step != ApprovalStep.TEACHER:
        raise HTTPException(status_code=400, detail="该预约不在教师审批环节")

    old_status = booking.status.value

    booking.status = BookingStatus.REJECTED
    booking.current_step = ApprovalStep.END

    add_approval_record(
        db=db,
        booking=booking,
        approver_id=current_user.id,
        step=ApprovalStep.TEACHER,
        action=ApprovalAction.REJECT,
        before_status=old_status,
        after_status=booking.status.value,
        comment="指导教师驳回学生预约"
    )

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "已驳回学生预约",
        "data": booking_to_frontend(db, booking)
    }