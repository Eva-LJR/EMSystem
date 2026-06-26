from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal

from database import get_db
from models import (
    User,
    Role,
    Device,
    DeviceStatus,
    Booking,
    BookingStatus,
    Payment
)
from routers.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["统计数据中心"])


def check_stats_permission(current_user: User):
    """
    统计页面只允许设备管理员和实验室负责人查看。
    """
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="只有设备管理员和实验室负责人可以查看统计数据")


def device_status_label(status):
    mapping = {
        DeviceStatus.IDLE: "可预约",
        DeviceStatus.USING: "使用中",
        DeviceStatus.MAINTENANCE: "检修中",
        DeviceStatus.SCRAPPED: "已报废",
        DeviceStatus.DISABLED: "已停用",
    }
    return mapping.get(status, status.value if status else "未知")


def get_start_date(range_type: str):
    now = datetime.utcnow()

    if range_type == "week":
        return now - timedelta(days=7)

    if range_type == "year":
        return now - timedelta(days=365)

    return now - timedelta(days=30)


@router.get("/summary")
def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    数据统计首页顶部卡片 + 设备状态分布。
    """
    check_stats_permission(current_user)

    device_total = db.query(func.count(Device.id)).scalar() or 0
    user_total = db.query(func.count(User.id)).scalar() or 0

    # 预约成功数：只统计真正已经通过的预约
    booking_success_total = db.query(func.count(Booking.id)).filter(
        Booking.status == BookingStatus.APPROVED
    ).scalar() or 0

    # 设备状态分布
    status_rows = db.query(
        Device.status,
        func.count(Device.id)
    ).group_by(Device.status).all()

    status_map = {
        "可预约": 0,
        "使用中": 0,
        "检修中": 0,
        "已报废": 0,
        "已停用": 0
    }

    for status, count in status_rows:
        label = device_status_label(status)
        status_map[label] = count

    return {
        "code": 20000,
        "data": {
            "deviceTotal": device_total,
            "userTotal": user_total,
            "bookingSuccessTotal": booking_success_total,
            "deviceStatus": [
                {"name": "可预约", "value": status_map["可预约"]},
                {"name": "使用中", "value": status_map["使用中"]},
                {"name": "检修中", "value": status_map["检修中"]},
                {"name": "已报废", "value": status_map["已报废"]},
                {"name": "已停用", "value": status_map["已停用"]},
            ]
        }
    }


@router.get("/report")
def get_time_report(
    range_type: str = Query("month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    设备使用报表：按周、月、年统计已通过预约的设备使用次数和收入。
    """
    check_stats_permission(current_user)

    start_date = get_start_date(range_type)

    # 只统计已通过预约
    query = (
        db.query(
            Device.id.label("device_id"),
            Device.model.label("device_name"),
            func.count(Booking.id).label("use_count"),
            func.coalesce(func.sum(Booking.total_fee), 0).label("revenue")
        )
        .join(Booking, Booking.device_id == Device.id)
        .filter(
            Booking.status == BookingStatus.APPROVED,
            Booking.created_at >= start_date
        )
        .group_by(Device.id, Device.model)
        .order_by(func.count(Booking.id).desc())
    )

    rows = query.all()

    device_ranking = []

    for row in rows:
        revenue = row.revenue

        if isinstance(revenue, Decimal):
            revenue = float(revenue)

        device_ranking.append({
            "device_id": row.device_id,
            "device_name": row.device_name,
            "use_count": row.use_count,
            "revenue": revenue or 0
        })

    total_records = sum(item["use_count"] for item in device_ranking)
    total_revenue = sum(item["revenue"] for item in device_ranking)

    return {
        "code": 20000,
        "data": {
            "range_type": range_type,
            "total_records": total_records,
            "total_revenue": total_revenue,
            "device_ranking": device_ranking
        }
    }