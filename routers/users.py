from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import User, Role
from schemas import UserUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def user_to_frontend(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value if user.role else None,
        "roles": [user.role.value] if user.role else [],
        "name": user.name,
        "gender": user.gender,
        "phone": user.phone,
        "avatar": user.avatar,

        # 教师字段
        "title": user.title,

        # 教师/学生共有
        "major": user.major,
        "college": user.college,

        # 学生字段
        "teacherName": user.teacher_name,

        # 校外人员字段
        "company": user.company
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):
    return {
        "code": 20000,
        "data": user_to_frontend(current_user)
    }


@router.put("/me")
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    update_data = payload.dict(exclude_unset=True)

    # 不允许普通用户通过个人中心修改角色、用户名、密码
    forbidden_fields = {"role", "username", "password", "password_hash", "id"}
    for field in forbidden_fields:
        update_data.pop(field, None)

    # Pydantic 里使用 teacherName 时，转为数据库字段 teacher_name
    if "teacherName" in update_data:
        update_data["teacher_name"] = update_data.pop("teacherName")

    for key, value in update_data.items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    return {
        "code": 20000,
        "message": "个人信息更新成功",
        "data": user_to_frontend(current_user)
    }


@router.get("/")
def get_users(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    users = query.all()

    return {"code": 20000, "data": [user_to_frontend(u) for u in users]}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")

    db.delete(user)
    db.commit()

    return {"code": 20000, "message": "删除成功"}

@router.get("/my-students")
def get_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="只有教师可以查看指导学生")

    students = db.query(User).filter(
        User.role == Role.STUDENT,
        User.teacher_name == current_user.name
    ).all()

    data = []

    for s in students:
        data.append({
            "id": s.id,
            "studentId": s.username,
            "username": s.username,
            "name": s.name,
            "gender": s.gender,
            "major": s.major,
            "college": s.college,
            "phone": s.phone,
            "teacherName": s.teacher_name
        })

    return {
        "code": 20000,
        "data": data
    }







# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from typing import Optional
#
# from database import get_db
# from models import User, Role
# from routers.auth import get_current_user
#
# router = APIRouter(prefix="/api/users", tags=["用户管理"])
#
#
# @router.get("/")
# def get_users(
#     role: Optional[str] = Query(None),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
#         raise HTTPException(status_code=403, detail="权限不足")
#
#     query = db.query(User)
#
#     if role:
#         query = query.filter(User.role == role)
#
#     users = query.all()
#
#     return {"code": 20000, "data": users}
#
#
# @router.delete("/{user_id}")
# def delete_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
#         raise HTTPException(status_code=403, detail="权限不足")
#
#     user = db.query(User).filter(User.id == user_id).first()
#
#     if not user:
#         raise HTTPException(status_code=404, detail="用户不存在")
#
#     if user.id == current_user.id:
#         raise HTTPException(status_code=400, detail="不能删除当前登录用户")
#
#     db.delete(user)
#     db.commit()
#
#     return {"code": 20000, "message": "删除成功"}