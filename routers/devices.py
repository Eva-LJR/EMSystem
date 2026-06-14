from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
# 💡 这里补全了 Approval 和 ApprovalStep 的导入
from models import Device, DeviceStatus, Approval, ApprovalStep, Role,User
from schemas import DeviceCreate, DeviceUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


@router.get("/")
def read_devices(status: Optional[DeviceStatus] = Query(None), db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    query = db.query(Device)
    if status:
        query = query.filter(Device.status == status)
    devices = query.all()
    return {"code": 20000, "data": devices}


@router.post("/")
def create_device(device: DeviceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")
    db_device = Device(**device.dict())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return {"code": 20000, "data": db_device}


@router.put("/{device_id}")
def update_device(device_id: int, device: DeviceUpdate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")
    db_device = db.query(Device).filter(Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="设备未找到")
    for key, value in device.dict(exclude_unset=True).items():
        setattr(db_device, key, value)
    db.commit()
    db.refresh(db_device)
    return {"code": 20000, "data": db_device}


# 💡 完美融入防呆设计的删除接口
@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")
    db_device = db.query(Device).filter(Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="设备未找到")

    # 检查该设备是否有正在进行中的预约单
    active_bookings = db.query(Approval).filter(
        Approval.device_id == device_id,
        Approval.current_step != ApprovalStep.END  # 只要流程没结束
    ).first()

    if active_bookings:
        raise HTTPException(status_code=400, detail="该设备当前有正在进行中的预约流程，严禁删除！")

    db.delete(db_device)
    db.commit()
    return {"code": 20000, "message": "设备物理删除成功"}