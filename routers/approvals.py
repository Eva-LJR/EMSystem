# # from fastapi import APIRouter, Depends, HTTPException, Query
# # from sqlalchemy.orm import Session
# # from typing import List, Optional
# # from datetime import datetime
# #
# # from database import get_db
# # from models import Approval, ApprovalStatus, ApprovalStep, Role
# # from schemas import Approval, ApprovalCreate, ApprovalUpdate
# # from routers.auth import get_current_user
# #
# # router = APIRouter(prefix="/api/approvals", tags=["approvals"])
# #
# # @router.get("/", response_model=dict)
# # def read_approvals(
# #     skip: int = 0,
# #     limit: int = 100,
# #     role: Optional[Role] = Query(None),
# #     status: Optional[ApprovalStatus] = Query(None),
# #     current_step: Optional[ApprovalStep] = Query(None),
# #     db: Session = Depends(get_db),
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     query = db.query(Approval)
# #     if role:
# #         query = query.filter(Approval.role == role)
# #     if status:
# #         query = query.filter(Approval.status == status)
# #     if current_step:
# #         query = query.filter(Approval.current_step == current_step)
# #     approvals = query.order_by(Approval.created_at.desc()).offset(skip).limit(limit).all()
# #     return {
# #         "code": 20000,
# #         "data": approvals
# #     }
# #
# # @router.post("/", response_model=dict)
# # def create_approval(
# #     approval: ApprovalCreate,
# #     db: Session = Depends(get_db),
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     # 根据角色设置初始审批步骤
# #     if approval.role == Role.OUTSIDE:
# #         initial_step = ApprovalStep.ADMIN
# #         initial_status = ApprovalStatus.PENDING_ADMIN
# #     elif approval.role == Role.STUDENT:
# #         initial_step = ApprovalStep.ADMIN # 假设学生也需要管理员初审
# #         initial_status = ApprovalStatus.PENDING_ADMIN
# #     elif approval.role == Role.TEACHER:
# #         initial_step = ApprovalStep.LEADER # 教师直接由负责人审批
# #         initial_status = ApprovalStatus.PENDING_LEADER
# #     else:
# #         raise HTTPException(status_code=400, detail="Invalid role for approval")
# #
# #     db_approval = Approval(
# #         **approval.dict(),
# #         status=initial_status,
# #         current_step=initial_step
# #     )
# #     db.add(db_approval)
# #     db.commit()
# #     db.refresh(db_approval)
# #     return {
# #         "code": 20000,
# #         "data": db_approval
# #     }
# #
# # @router.put("/{approval_id}/approve", response_model=dict)
# # def approve_approval(
# #     approval_id: int,
# #     db: Session = Depends(get_db),
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     db_approval = db.query(Approval).filter(Approval.id == approval_id).first()
# #     if db_approval is None:
# #         raise HTTPException(status_code=404, detail="Approval not found")
# #
# #     # 管理员审批
# #     if db_approval.current_step == ApprovalStep.ADMIN and current_user.role == Role.ADMIN:
# #         db_approval.status = ApprovalStatus.PENDING_LEADER
# #         db_approval.current_step = ApprovalStep.LEADER
# #         db_approval.approver_id = current_user.id
# #     # 负责人审批
# #     elif db_approval.current_step == ApprovalStep.LEADER and current_user.role == Role.LAB_LEADER:
# #         db_approval.status = ApprovalStatus.APPROVED
# #         db_approval.current_step = ApprovalStep.END
# #         db_approval.approver_id = current_user.id
# #     else:
# #         raise HTTPException(status_code=403, detail="Not authorized to approve this step")
# #
# #     db_approval.updated_at = datetime.utcnow()
# #     db.commit()
# #     db.refresh(db_approval)
# #     return {
# #         "code": 20000,
# #         "data": db_approval
# #     }
# #
# # @router.put("/{approval_id}/reject", response_model=dict)
# # def reject_approval(
# #     approval_id: int,
# #     db: Session = Depends(get_db),
# #     current_user: dict = Depends(get_current_user)
# # ):
# #     db_approval = db.query(Approval).filter(Approval.id == approval_id).first()
# #     if db_approval is None:
# #         raise HTTPException(status_code=404, detail="Approval not found")
# #
# #     if db_approval.current_step == ApprovalStep.ADMIN and current_user.role == Role.ADMIN:
# #         db_approval.status = ApprovalStatus.REJECTED_BY_ADMIN
# #     elif db_approval.current_step == ApprovalStep.LEADER and current_user.role == Role.LAB_LEADER:
# #         db_approval.status = ApprovalStatus.REJECTED_BY_LEADER
# #     else:
# #         raise HTTPException(status_code=403, detail="Not authorized to reject this step")
# #
# #     db_approval.current_step = ApprovalStep.END
# #     db_approval.approver_id = current_user.id
# #     db_approval.updated_at = datetime.utcnow()
# #     db.commit()
# #     db.refresh(db_approval)
# #     return {
# #         "code": 20000,
# #         "data": db_approval
# #     }
#
# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from datetime import datetime, timedelta
# from typing import Optional
# from database import get_db
# from models import Approval, Device, User, Role, ApprovalStatus, ApprovalStep, DeviceStatus
# from schemas import ApprovalCreate
# from routers.auth import get_current_user
#
# router = APIRouter(prefix="/api/approvals", tags=["预约审批中心"])
#
#
# # 1. 提交预约申请
# @router.post("/")
# def create_booking(payload: ApprovalCreate, db: Session = Depends(get_db),
#                    current_user: User = Depends(get_current_user)):
#     now = datetime.utcnow()
#
#     # 核心限制(3)：必须提前 1-7 天预约
#     if not (now + timedelta(days=1) <= payload.start_time <= now + timedelta(days=7)):
#         raise HTTPException(status_code=400, detail="根据借用规定：预约必须提前1-7天提交！")
#
#     # 核心限制(2)：每次借用时间单位推荐为 2小时(学时)
#     duration = payload.end_time - payload.start_time
#     if duration.total_seconds() < 7200:
#         raise HTTPException(status_code=400, detail="单次借用时间不得少于2小时")
#
#     # 查验设备冲突与排除检修中状态
#     device = db.query(Device).filter(Device.id == payload.device_id).first()
#     if not device or device.status == DeviceStatus.MAINTENANCE:
#         raise HTTPException(status_code=400, detail="该设备当前正处于检修状态，无法借用")
#
#     # 核心规则：冲突检查 + 校内人员优先原则
#     conflict_bookings = db.query(Approval).filter(
#         Approval.device_id == payload.device_id,
#         Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.PENDING_ADMIN, ApprovalStatus.PENDING_LEADER]),
#         Approval.start_time < payload.end_time,
#         Approval.end_time > payload.start_time
#     ).all()
#
#     if conflict_bookings:
#         if current_user.role in [Role.TEACHER, Role.STUDENT]:
#             # 如果当前申请人是校内人员，可以覆盖或在审批中挤掉校外人员
#             for cb in conflict_bookings:
#                 if cb.role == Role.OUTSIDE:
#                     cb.status = ApprovalStatus.REJECTED_BY_ADMIN
#                     cb.reason = "因校内教学科研任务冲突，校内人员优先使用，系统自动退单"
#         else:
#             raise HTTPException(status_code=400, detail="该时段设备已被借用或已被高优先级校内人员预约申请中")
#
#     # 计算费用：校内人员免费，校外人员付费
#     total_fee = 0.0
#     if current_user.role == Role.OUTSIDE:
#         # 每2小时为一个计费单元
#         hours = duration.total_seconds() / 3600
#         total_fee = (hours / 2) * device.price
#
#     # 决定审批流起始节点
#     init_status = ApprovalStatus.PENDING_ADMIN
#     init_step = ApprovalStep.ADMIN
#
#     if current_user.role == Role.STUDENT:
#         init_status = ApprovalStatus.PENDING_TEACHER
#         init_step = ApprovalStep.TEACHER
#
#     db_approval = Approval(
#         role=current_user.role,
#         device_id=payload.device_id,
#         device_name=payload.device_name,
#         start_time=payload.start_time,
#         end_time=payload.end_time,
#         reason=payload.reason,
#         status=init_status,
#         current_step=init_step,
#         applicant_name=payload.applicant_name,
#         applicant_id=payload.applicant_id,
#         company=payload.company,
#         college=payload.college,
#         teacher_name=payload.teacher_name,
#         total_fee=total_fee,
#         is_paid=False
#     )
#     db.add(db_approval)
#     db.commit()
#     db.refresh(db_approval)
#     return {"code": 20000, "data": db_approval}
#
#
# # 2. 查询审批列表（对接管理员前端教师、学生、校外三个子菜单）
# @router.get("/")
# def get_approvals(role: Optional[Role] = Query(None), db: Session = Depends(get_db),
#                   current_user: User = Depends(get_current_user)):
#     query = db.query(Approval)
#
#     # 【安全修复】如果不是管理员、负责人、老师，普通学生/校外人员只能看自己的单子
#     if current_user.role not in [Role.ADMIN, Role.LAB_LEADER, Role.TEACHER]:
#         query = query.filter(Approval.applicant_id == current_user.username)
#
#     if role:
#         query = query.filter(Approval.role == role)
#     return {"code": 20000, "data": query.order_by(Approval.created_at.desc()).all()}
#
# # 3. 统一审批通过接口（核心流转状态机）
# @router.put("/{approval_id}/approve")
# def approve_workflow(approval_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     booking = db.query(Approval).filter(Approval.id == approval_id).first()
#     if not booking:
#         raise HTTPException(status_code=404, detail="预约单未找到")
#
#     # 步骤 A：指导教师审批学生
#     if booking.current_step == ApprovalStep.TEACHER and current_user.role == Role.TEACHER:
#         booking.status = ApprovalStatus.PENDING_ADMIN
#         booking.current_step = ApprovalStep.ADMIN
#
#     # 步骤 B：设备管理员初审（对应前端三个审核单的审核动作）
#     elif booking.current_step == ApprovalStep.ADMIN and current_user.role == Role.ADMIN:
#         if booking.role in [Role.TEACHER, Role.STUDENT]:
#             # 教师与学生到管理员就终审通过了
#             booking.status = ApprovalStatus.APPROVED
#             booking.current_step = ApprovalStep.END
#         elif booking.role == Role.OUTSIDE:
#             # 校外人员需要流转到负责人
#             booking.status = ApprovalStatus.PENDING_LEADER
#             booking.current_step = ApprovalStep.LEADER
#
#     # 步骤 C：实验室负责人终审（校外人员）
#     elif booking.current_step == ApprovalStep.LEADER and current_user.role == Role.LAB_LEADER:
#         booking.status = ApprovalStatus.PENDING_PAY
#         booking.current_step = ApprovalStep.FINANCE
#
#     else:
#         raise HTTPException(status_code=403, detail="您当前无权或不在当前环节审批此申请单")
#
#     db.commit()
#     return {"code": 20000, "data": booking}
#
#
# # 4. 驳回申请
# @router.put("/{approval_id}/reject")
# def reject_workflow(approval_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     booking = db.query(Approval).filter(Approval.id == approval_id).first()
#     if not booking:
#         raise HTTPException(status_code=404, detail="预约单未找到")
#
#     if current_user.role == Role.TEACHER:
#         booking.status = ApprovalStatus.REJECTED_BY_TEACHER
#     elif current_user.role == Role.ADMIN:
#         booking.status = ApprovalStatus.REJECTED_BY_ADMIN
#     elif current_user.role == Role.LAB_LEADER:
#         booking.status = ApprovalStatus.REJECTED_BY_LEADER
#
#     booking.current_step = ApprovalStep.END
#     db.commit()
#     return {"code": 20000, "message": "申请已被驳回"}
#
#
# # 5. 与财务处自动连接系统的接口回调（需求6.4：自动传回实验室确认）
# @router.post("/{approval_id}/finance-callback")
# def finance_callback(approval_id: int, db: Session = Depends(get_db)):
#     booking = db.query(Approval).filter(Approval.id == approval_id).first()
#     if not booking or booking.status != ApprovalStatus.PENDING_PAY:
#         raise HTTPException(status_code=400, detail="单据状态异常，无法完成财务对账")
#
#     booking.is_paid = True
#     booking.status = ApprovalStatus.APPROVED
#     booking.current_step = ApprovalStep.END
#     db.commit()
#     return {"code": 20000, "message": "学校财务处电子缴费入账成功，自动激活设备预约台账！"}
#
#
# # 6. 用户撤销预约功能（需求4.3：至少提前1天以上，付费退款95%）
# @router.post("/{approval_id}/cancel")
# def cancel_booking(approval_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
#     booking = db.query(Approval).filter(Approval.id == approval_id).first()
#     if not booking:
#         raise HTTPException(status_code=404, detail="单据未找到")
#
#     # 检验时间：必须提前 1 天以上撤销
#     if booking.start_time - datetime.utcnow() < timedelta(days=1):
#         raise HTTPException(status_code=400, detail="不符合撤销规定：距离实验开始时间已不足24小时，无法撤销！")
#
#     booking.status = ApprovalStatus.CANCELLED
#     booking.current_step = ApprovalStep.END
#
#     # 计费退还 95%
#     if booking.role == Role.OUTSIDE and booking.is_paid:
#         booking.refund_amount = booking.total_fee * 0.95
#         message = f"撤销成功！已通知学校财务系统自动执行原路退款，扣除5%手续费，已退还金：{booking.refund_amount}元。"
#     else:
#         message = "校内免费单，预约已成功撤销，不产生任何衍生费用。"
#
#     db.commit()
#     return {"code": 20000, "message": message}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from models import Approval, Device, User, Role, ApprovalStatus, ApprovalStep, DeviceStatus
from schemas import ApprovalCreate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/approvals", tags=["预约审批中心"])


# ========================= 1. 提交预约申请 =========================
@router.post("/")
def create_booking(payload: ApprovalCreate, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    now = datetime.utcnow()

    # 核心限制：必须提前 1-7 天预约
    if not (now + timedelta(days=1) <= payload.start_time <= now + timedelta(days=7)):
        raise HTTPException(status_code=400, detail="根据借用规定：预约必须提前1-7天提交！")

    # 核心限制：每次借用时间单位推荐为 2小时(学时)
    duration = payload.end_time - payload.start_time
    if duration.total_seconds() < 7200:
        raise HTTPException(status_code=400, detail="单次借用时间不得少于2小时")

    # 查验设备冲突与排除检修中状态
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device or device.status == DeviceStatus.MAINTENANCE:
        raise HTTPException(status_code=400, detail="该设备当前正处于检修状态，无法借用")

    # 核心规则：冲突检查 + 校内人员优先原则
    conflict_bookings = db.query(Approval).filter(
        Approval.device_id == payload.device_id,
        Approval.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.PENDING_ADMIN, ApprovalStatus.PENDING_LEADER]),
        Approval.start_time < payload.end_time,
        Approval.end_time > payload.start_time
    ).all()

    if conflict_bookings:
        if current_user.role in [Role.TEACHER, Role.STUDENT]:
            # 如果当前申请人是校内人员，可以覆盖或在审批中挤掉校外人员
            for cb in conflict_bookings:
                if cb.role == Role.OUTSIDE:
                    cb.status = ApprovalStatus.REJECTED_BY_ADMIN
                    cb.reason = "因校内教学科研任务冲突，校内人员优先使用，系统自动退单"
        else:
            raise HTTPException(status_code=400, detail="该时段设备已被借用或已被高优先级校内人员预约申请中")

    # 计算费用：校内人员免费，校外人员付费
    total_fee = 0.0
    if current_user.role == Role.OUTSIDE:
        # 每2小时为一个计费单元
        hours = duration.total_seconds() / 3600
        total_fee = (hours / 2) * device.price

    # 决定审批流起始节点
    init_status = ApprovalStatus.PENDING_ADMIN
    init_step = ApprovalStep.ADMIN

    if current_user.role == Role.STUDENT:
        init_status = ApprovalStatus.PENDING_TEACHER
        init_step = ApprovalStep.TEACHER

    db_approval = Approval(
        role=current_user.role,
        device_id=payload.device_id,
        device_name=payload.device_name,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
        status=init_status,
        current_step=init_step,
        applicant_name=payload.applicant_name,
        applicant_id=payload.applicant_id,
        company=payload.company,
        college=payload.college,
        teacher_name=payload.teacher_name,
        total_fee=total_fee,
        is_paid=False
    )
    db.add(db_approval)
    db.commit()
    db.refresh(db_approval)
    return {"code": 20000, "data": db_approval}


# ========================= 2. 统一查询审批列表（安全隔离版） =========================
@router.get("/")
def get_approvals(
        role: Optional[Role] = Query(None, description="按申请人角色筛选"),
        status: Optional[ApprovalStatus] = Query(None, description="按单据状态筛选"),
        current_step: Optional[ApprovalStep] = Query(None, description="按当前审批环节筛选"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    对接所有前端页面（包括学生、老师、管理员、实验室负责人）。
    通过加入多维度 Query 参数和数据沙箱，确保各司其职，且不越权。
    """
    query = db.query(Approval)

    # 【数据隔离沙箱】
    # 1. 如果是学生或校外人员，强制只能看自己提交的单子
    if current_user.role in [Role.STUDENT, Role.OUTSIDE]:
        query = query.filter(Approval.applicant_id == current_user.username)
    # 2. 如果是指导老师，默认能看到自己名下学生的申请单
    elif current_user.role == Role.TEACHER:
        query = query.filter(
            (Approval.teacher_name == current_user.name) | (Approval.applicant_id == current_user.username))
    # 3. 管理员（admin）和负责人（labLeader）拥有全局审计视野，不做强制过滤，依赖动态参数隔离

    # 【动态条件筛选】
    if role:
        query = query.filter(Approval.role == role)
    if status:
        query = query.filter(Approval.status == status)
    if current_step:
        query = query.filter(Approval.current_step == current_step)

    return {"code": 20000, "data": query.order_by(Approval.created_at.desc()).all()}


# ========================= 3. 统一审批通过接口（核心流转状态机） =========================
@router.put("/{approval_id}/approve")
def approve_workflow(approval_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Approval).filter(Approval.id == approval_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="预约单未找到")

    # 环节 A：指导教师审批学生
    if booking.current_step == ApprovalStep.TEACHER and current_user.role == Role.TEACHER:
        booking.status = ApprovalStatus.PENDING_ADMIN
        booking.current_step = ApprovalStep.ADMIN

    # 环节 B：设备管理员初审（【100%保留您的原始逻辑】）
    elif booking.current_step == ApprovalStep.ADMIN and current_user.role == Role.ADMIN:
        if booking.role in [Role.TEACHER, Role.STUDENT]:
            # 教师与学生到管理员就终审通过了
            booking.status = ApprovalStatus.APPROVED
            booking.current_step = ApprovalStep.END
        elif booking.role == Role.OUTSIDE:
            # 校外人员需要流转到负责人环节
            booking.status = ApprovalStatus.PENDING_LEADER
            booking.current_step = ApprovalStep.LEADER

    # 环节 C：实验室负责人终审（完美接入 lableader 前端动作！）
    elif booking.current_step == ApprovalStep.LEADER and current_user.role == Role.LAB_LEADER:
        # 负责人点击通过后，校外单进入“待缴费”财务环节
        booking.status = ApprovalStatus.PENDING_PAY
        booking.current_step = ApprovalStep.FINANCE

    else:
        raise HTTPException(status_code=403, detail="您当前无权或单据不在您负责的审批环节")

    db.commit()
    db.refresh(booking)
    return {"code": 20000, "data": booking}


# ========================= 4. 统一驳回申请 =========================
@router.put("/{approval_id}/reject")
def reject_workflow(approval_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Approval).filter(Approval.id == approval_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="预约单未找到")

    # 根据不同的操作人角色，赋予不同的驳回终态
    if current_user.role == Role.TEACHER:
        booking.status = ApprovalStatus.REJECTED_BY_TEACHER
    elif current_user.role == Role.ADMIN:
        booking.status = ApprovalStatus.REJECTED_BY_ADMIN
    elif current_user.role == Role.LAB_LEADER:
        booking.status = ApprovalStatus.REJECTED_BY_LEADER
    else:
        raise HTTPException(status_code=403, detail="您没有权限拒绝该单据")

    booking.current_step = ApprovalStep.END
    db.commit()
    return {"code": 20000, "message": "申请已被驳回"}


# ========================= 5. 财务回调与用户撤销（保留您的优秀核心逻辑） =========================
@router.post("/{approval_id}/finance-callback")
def finance_callback(approval_id: int, db: Session = Depends(get_db)):
    booking = db.query(Approval).filter(Approval.id == approval_id).first()
    if not booking or booking.status != ApprovalStatus.PENDING_PAY:
        raise HTTPException(status_code=400, detail="单据状态异常，无法完成财务对账")

    booking.is_paid = True
    booking.status = ApprovalStatus.APPROVED
    booking.current_step = ApprovalStep.END
    db.commit()
    return {"code": 20000, "message": "学校财务处电子缴费入账成功，自动激活设备预约台账！"}


@router.post("/{approval_id}/cancel")
def cancel_booking(approval_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Approval).filter(Approval.id == approval_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="单据未找到")

    if booking.start_time - datetime.utcnow() < timedelta(days=1):
        raise HTTPException(status_code=400, detail="不符合撤销规定：距离实验开始时间已不足24小时，无法撤销！")

    booking.status = ApprovalStatus.CANCELLED
    booking.current_step = ApprovalStep.END

    if booking.role == Role.OUTSIDE and booking.is_paid:
        booking.refund_amount = booking.total_fee * 0.95
        message = f"撤销成功！已通知学校财务系统自动执行原路退款，扣除5%手续费，已退还金额：{booking.refund_amount}元。"
    else:
        message = "校内免费单，预约已成功撤销，不产生任何衍生费用。"

    db.commit()
    return {"code": 20000, "message": message}