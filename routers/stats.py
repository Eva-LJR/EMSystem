from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from database import get_db
from models import Approval, ApprovalStatus, Device
from routers.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["统计数据中心"])

@router.get("/report")
def get_time_report(range_type: str = "month", db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    根据前端传参 range_type (week/month/year) 生成对应的周报表、月报表、年报表
    """
    now = datetime.utcnow()
    if range_type == "week":
        start_date = now - timedelta(days=7)
    elif range_type == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30) # 默认为月报表

    # 1. 期间内总预约成功执行数
    total_approved = db.query(func.count(Approval.id)).filter(
        Approval.status == ApprovalStatus.APPROVED,
        Approval.created_at >= start_date
    ).scalar()

    # 2. 设备借用率排行（统计高频使用型号）
    rank_list = db.query(
        Approval.device_name,
        func.count(Approval.id).label("count"),
        func.sum(Approval.total_fee).label("revenue")
    ).filter(
        Approval.status == ApprovalStatus.APPROVED,
        Approval.created_at >= start_date
    ).group_by(Approval.device_name).order_by(func.count(Approval.id).desc()).all()

    formatted_rank = []
    for item in rank_list:
        formatted_rank.append({
            "device_name": item[0],
            "use_count": item[1],
            "revenue": item[2] or 0.0
        })

    return {
        "code": 20000,
        "data": {
            "range_type": range_type,
            "total_records": total_approved,
            "device_ranking": formatted_rank
        }
    }