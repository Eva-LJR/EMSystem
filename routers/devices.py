from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Device, DeviceStatus, Booking, ApprovalStep, Role, User
from schemas import DeviceCreate, DeviceUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


# =========================
# 状态转换工具
# =========================

DEVICE_STATUS_LABELS = {
    DeviceStatus.IDLE: "可预约",
    DeviceStatus.USING: "使用中",
    DeviceStatus.MAINTENANCE: "检修中",
    DeviceStatus.SCRAPPED: "已报废",
    DeviceStatus.DISABLED: "已停用",
}


def parse_device_status(value):
    """
    将前端传来的中文/英文状态统一转换为 models.DeviceStatus。
    解决 MySQL enum 不接受“可预约”等中文值的问题。
    """
    if value is None or value == "":
        return None

    if isinstance(value, DeviceStatus):
        return value

    value = str(value).strip()

    mapping = {
        # 中文
        "可预约": DeviceStatus.IDLE,
        "使用中": DeviceStatus.USING,
        "检修中": DeviceStatus.MAINTENANCE,
        "维修中": DeviceStatus.MAINTENANCE,
        "已报废": DeviceStatus.SCRAPPED,
        "报废": DeviceStatus.SCRAPPED,
        "已停用": DeviceStatus.DISABLED,
        "停用": DeviceStatus.DISABLED,

        # 英文 value
        "idle": DeviceStatus.IDLE,
        "using": DeviceStatus.USING,
        "maintenance": DeviceStatus.MAINTENANCE,
        "scrapped": DeviceStatus.SCRAPPED,
        "disabled": DeviceStatus.DISABLED,

        # 英文 name
        "IDLE": DeviceStatus.IDLE,
        "USING": DeviceStatus.USING,
        "MAINTENANCE": DeviceStatus.MAINTENANCE,
        "SCRAPPED": DeviceStatus.SCRAPPED,
        "DISABLED": DeviceStatus.DISABLED,
    }

    if value not in mapping:
        raise HTTPException(
            status_code=400,
            detail=f"设备状态不合法：{value}"
        )

    return mapping[value]


def device_to_frontend(d: Device):
    """
    统一返回前端需要的字段。
    同时兼容旧前端字段 buyTime、price。
    """
    status_label = DEVICE_STATUS_LABELS.get(d.status, d.status.value if d.status else None)

    return {
        "id": d.id,
        "deviceCode": d.device_code,
        "name": d.name,
        "model": d.model,
        "manufacturer": d.manufacturer,
        "purpose": d.purpose,

        # 新字段
        "purchaseDate": d.purchase_date,
        "purchasePrice": float(d.purchase_price or 0),
        "hourlyPrice": float(d.hourly_price or 0),

        # 兼容旧前端字段
        "buyTime": d.purchase_date,
        "price": float(d.hourly_price or 0),

        # 给前端中文状态，避免显示成 idle 后前端识别失败
        "status": status_label,
        "statusCode": d.status.value if d.status else None,

        "location": d.location,
        "availableTime": d.available_time,
        "description": d.description,
        "createdAt": d.created_at,
        "updatedAt": d.updated_at,
    }


def apply_device_payload(db_device: Device, payload):
    """
    将 DeviceCreate / DeviceUpdate 的字段写入数据库对象。
    兼容旧字段：
    buy_time -> purchase_date
    price -> hourly_price
    """
    data = payload.dict(exclude_unset=True)

    # 兼容旧前端字段
    if "buy_time" in data and data["buy_time"] is not None:
        data["purchase_date"] = data.pop("buy_time")

    if "price" in data and data["price"] is not None:
        data["hourly_price"] = data.pop("price")

    # 如果前端没有传 name，但传了 model，则用 model 作为 name
    if not data.get("name") and data.get("model"):
        data["name"] = data["model"]

    # 如果前端没有传 device_code，新增时自动生成
    if hasattr(db_device, "id") and not data.get("device_code") and not db_device.device_code:
        data["device_code"] = f"DEV-{db_device.id or 'NEW'}"

    # 状态转换
    if "status" in data:
        parsed_status = parse_device_status(data["status"])
        if parsed_status is not None:
            data["status"] = parsed_status
        else:
            data.pop("status", None)

    for key, value in data.items():
        if hasattr(db_device, key):
            setattr(db_device, key, value)


# =========================
# 查询设备列表
# =========================

@router.get("/")
def read_devices(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Device)

    if status:
        parsed_status = parse_device_status(status)
        query = query.filter(Device.status == parsed_status)

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
# 新增设备
# =========================

@router.post("/")
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    db_device = Device(
        device_code="TEMP-CODE",
        name=device.name or device.model,
        model=device.model,
        manufacturer=device.manufacturer,
        purpose=device.purpose,
        purchase_date=device.purchase_date or device.buy_time,
        purchase_price=device.purchase_price or 0,
        hourly_price=device.hourly_price or device.price or 0,
        status=parse_device_status(device.status) or DeviceStatus.IDLE,
        location=device.location,
        available_time=device.available_time,
        description=device.description,
    )

    db.add(db_device)
    db.flush()

    # 如果前端没有传设备编号，则自动生成
    if not device.device_code:
        db_device.device_code = f"DEV-{db_device.id:03d}"
    else:
        db_device.device_code = device.device_code

    db.commit()
    db.refresh(db_device)

    return {
        "code": 20000,
        "message": "设备新增成功",
        "data": device_to_frontend(db_device)
    }


# =========================
# 修改设备
# =========================

@router.put("/{device_id}")
def update_device(
    device_id: int,
    device: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    db_device = db.query(Device).filter(Device.id == device_id).first()

    if not db_device:
        raise HTTPException(status_code=404, detail="设备未找到")

    apply_device_payload(db_device, device)

    db.commit()
    db.refresh(db_device)

    return {
        "code": 20000,
        "message": "设备修改成功",
        "data": device_to_frontend(db_device)
    }


# =========================
# 删除设备：改为逻辑停用
# =========================

@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    db_device = db.query(Device).filter(Device.id == device_id).first()

    if not db_device:
        raise HTTPException(status_code=404, detail="设备未找到")

    active_booking = db.query(Booking).filter(
        Booking.device_id == device_id,
        Booking.current_step != ApprovalStep.END
    ).first()

    if active_booking:
        raise HTTPException(
            status_code=400,
            detail="该设备当前有正在进行中的预约流程，不能停用"
        )

    # 不物理删除，避免破坏历史预约记录
    db_device.status = DeviceStatus.DISABLED

    db.commit()
    db.refresh(db_device)

    return {
        "code": 20000,
        "message": "设备已停用",
        "data": device_to_frontend(db_device)
    }