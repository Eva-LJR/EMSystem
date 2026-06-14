from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional

from database import get_db
from models import (
    User,
    Device,
    Approval,
    Role,
    DeviceStatus,
    ApprovalStatus,
    ApprovalStep
)
from schemas import ApprovalCreate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/client", tags=["学生教师校外人员端"])


def approval_to_frontend(a: Approval):
    return {
        "id": a.id,
        "role": a.role.value if a.role else None,
        "deviceId": a.device_id,
        "deviceName": a.device_name,
        "startTime": a.start_time,
        "endTime": a.end_time,
        "reason": a.reason,
        "status": a.status.value if a.status else None,
        "currentStep": a.current_step.value if a.current_step else None,
        "applicantName": a.applicant_name,
        "applicantId": a.applicant_id,
        "company": a.company,
        "college": a.college,
        "teacherName": a.teacher_name,
        "totalFee": a.total_fee,
        "isPaid": a.is_paid,
        "refundAmount": a.refund_amount,
        "createdAt": a.created_at,
    }


def device_to_frontend(d: Device):
    return {
        "id": d.id,
        "model": d.model,
        "buyTime": d.buy_time,
        "manufacturer": d.manufacturer,
        "purpose": d.purpose,
        "price": d.price,
        "status": d.status.value if d.status else None,
        "availableTime": d.available_time,
    }


def check_client_role(user: User):
    if user.role not in [Role.STUDENT, Role.TEACHER, Role.OUTSIDE]:
        raise HTTPException(status_code=403, detail="仅学生、教师、校外人员可访问")


@router.get("/devices")
def client_devices(
    keyword: Optional[str] = Query(None),
    status: Optional[DeviceStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    query = db.query(Device)

    if status:
        query = query.filter(Device.status == status)

    if keyword:
        query = query.filter(Device.model.contains(keyword))

    devices = query.all()

    return {
        "code": 20000,
        "data": [device_to_frontend(d) for d in devices]
    }


@router.get("/bookings")
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    bookings = db.query(Approval).filter(
        Approval.applicant_id == current_user.username
    ).order_by(Approval.created_at.desc()).all()

    return {
        "code": 20000,
        "data": [approval_to_frontend(a) for a in bookings]
    }


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

    if device.status in [DeviceStatus.MAINTENANCE, DeviceStatus.DISABLED]:
        raise HTTPException(status_code=400, detail="该设备当前不可预约")

    db_start_time = start_time.replace(tzinfo=None)
    db_end_time = end_time.replace(tzinfo=None)

    conflict_bookings = db.query(Approval).filter(
        Approval.device_id == payload.device_id,
        Approval.current_step != ApprovalStep.END,
        Approval.start_time < db_end_time,
        Approval.end_time > db_start_time
    ).all()

    if conflict_bookings:
        if current_user.role in [Role.STUDENT, Role.TEACHER]:
            for cb in conflict_bookings:
                if cb.role == Role.OUTSIDE:
                    cb.status = ApprovalStatus.REJECTED_BY_ADMIN
                    cb.current_step = ApprovalStep.END
                    cb.reason = "因校内人员优先使用，系统自动退单"
                else:
                    raise HTTPException(status_code=400, detail="该时段设备已被预约")
        else:
            raise HTTPException(status_code=400, detail="该时段设备已被预约")

    total_fee = 0.0

    if current_user.role == Role.OUTSIDE:
        hours = duration.total_seconds() / 3600
        total_fee = hours * (device.price or 0)

    init_status = ApprovalStatus.PENDING_ADMIN
    init_step = ApprovalStep.ADMIN

    if current_user.role == Role.STUDENT:
        init_status = ApprovalStatus.PENDING_TEACHER
        init_step = ApprovalStep.TEACHER

    booking = Approval(
        role=current_user.role,
        device_id=device.id,
        device_name=device.model,
        start_time=db_start_time,
        end_time=db_end_time,
        reason=payload.reason,
        status=init_status,
        current_step=init_step,

        applicant_name=current_user.name,
        applicant_id=current_user.username,
        company=current_user.company,
        college=current_user.college,
        teacher_name=current_user.teacher_name,

        total_fee=total_fee,
        is_paid=False
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "预约申请提交成功",
        "data": approval_to_frontend(booking)
    }


# @router.post("/bookings/{booking_id}/cancel")
# def cancel_my_booking(
#     booking_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     check_client_role(current_user)
#
#     booking = db.query(Approval).filter(Approval.id == booking_id).first()
#
#     if not booking:
#         raise HTTPException(status_code=404, detail="预约不存在")
#
#     if booking.applicant_id != current_user.username:
#         raise HTTPException(status_code=403, detail="只能撤销自己的预约")
#
#     if booking.current_step == ApprovalStep.END:
#         raise HTTPException(status_code=400, detail="该预约已结束，不能撤销")
#
#     if booking.start_time - datetime.utcnow() < timedelta(days=1):
#         raise HTTPException(status_code=400, detail="距离开始时间不足24小时，不能撤销")
#
#     booking.status = ApprovalStatus.CANCELLED
#     booking.current_step = ApprovalStep.END
#
#     if booking.role == Role.OUTSIDE and booking.is_paid:
#         booking.refund_amount = booking.total_fee * 0.95
#
#     db.commit()
#     db.refresh(booking)
#
#     return {
#         "code": 20000,
#         "message": "撤销成功",
#         "data": approval_to_frontend(booking)
#     }

@router.post("/bookings/{booking_id}/cancel")
def cancel_my_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_client_role(current_user)

    booking = db.query(Approval).filter(Approval.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    if booking.applicant_id != current_user.username:
        raise HTTPException(status_code=403, detail="只能撤销自己的预约")

    if booking.status == ApprovalStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="该预约已经撤销")

    if booking.status in [
        ApprovalStatus.REJECTED_BY_TEACHER,
        ApprovalStatus.REJECTED_BY_ADMIN,
        ApprovalStatus.REJECTED_BY_LEADER
    ]:
        raise HTTPException(status_code=400, detail="已驳回的预约不能撤销")

    if booking.start_time - datetime.utcnow() < timedelta(days=1):
        raise HTTPException(
            status_code=400,
            detail="不符合撤销规定：距离实验开始时间不足24小时，无法撤销"
        )

    booking.status = ApprovalStatus.CANCELLED
    booking.current_step = ApprovalStep.END

    message = "预约已成功撤销"

    if booking.role == Role.OUTSIDE and booking.is_paid:
        booking.refund_amount = booking.total_fee * 0.95
        message = f"撤销成功，付费预约退还95%，退款金额：{booking.refund_amount}元"

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": message,
        "data": approval_to_frontend(booking)
    }


@router.get("/student-approvals")
def teacher_student_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可查看学生预约审批")

    approvals = db.query(Approval).filter(
        Approval.role == Role.STUDENT,
        Approval.teacher_name == current_user.name,
        Approval.current_step == ApprovalStep.TEACHER
    ).order_by(Approval.created_at.desc()).all()

    return {
        "code": 20000,
        "data": [approval_to_frontend(a) for a in approvals]
    }


@router.put("/student-approvals/{booking_id}/approve")
def approve_student_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可审批")

    booking = db.query(Approval).filter(Approval.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    if booking.role != Role.STUDENT:
        raise HTTPException(status_code=400, detail="只能审批学生预约")

    if booking.teacher_name != current_user.name:
        raise HTTPException(status_code=403, detail="无权审批非本人指导学生")

    if booking.current_step != ApprovalStep.TEACHER:
        raise HTTPException(status_code=400, detail="该预约不在教师审批环节")

    booking.status = ApprovalStatus.PENDING_ADMIN
    booking.current_step = ApprovalStep.ADMIN

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "已通过，提交管理员审批",
        "data": approval_to_frontend(booking)
    }


@router.put("/student-approvals/{booking_id}/reject")
def reject_student_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="仅教师可审批")

    booking = db.query(Approval).filter(Approval.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    if booking.role != Role.STUDENT:
        raise HTTPException(status_code=400, detail="只能审批学生预约")

    if booking.teacher_name != current_user.name:
        raise HTTPException(status_code=403, detail="无权审批非本人指导学生")

    if booking.current_step != ApprovalStep.TEACHER:
        raise HTTPException(status_code=400, detail="该预约不在教师审批环节")

    booking.status = ApprovalStatus.REJECTED_BY_TEACHER
    booking.current_step = ApprovalStep.END

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "已驳回学生预约",
        "data": approval_to_frontend(booking)
    }


@router.post("/bookings/{booking_id}/pay")
def pay_outside_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.OUTSIDE:
        raise HTTPException(status_code=403, detail="仅校外人员可缴费")

    booking = db.query(Approval).filter(Approval.id == booking_id).first()

    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")

    if booking.applicant_id != current_user.username:
        raise HTTPException(status_code=403, detail="只能支付自己的预约")

    if booking.status != ApprovalStatus.PENDING_PAY:
        raise HTTPException(status_code=400, detail="该预约当前不处于待缴费状态")

    booking.is_paid = True
    booking.status = ApprovalStatus.APPROVED
    booking.current_step = ApprovalStep.END

    db.commit()
    db.refresh(booking)

    return {
        "code": 20000,
        "message": "缴费成功，预约已通过",
        "data": approval_to_frontend(booking)
    }