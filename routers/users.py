from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import User, Role, TeacherStudent
from schemas import UserUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def get_teacher_name_for_student(db: Session, student_id: int):
    """
    根据 teacher_students 表查询学生的指导教师姓名。
    新版数据库中不再使用 User.teacher_name 字段。
    """
    relation = db.query(TeacherStudent).filter(
        TeacherStudent.student_id == student_id,
        TeacherStudent.status == "active"
    ).first()

    if relation and relation.teacher:
        return relation.teacher.name

    return None


def user_to_frontend(user: User, db: Session = None):
    """
    将数据库 User 对象转换成前端需要的字段格式。
    为兼容旧前端，仍然返回 teacherName，但数据来自 teacher_students 表。
    """
    teacher_name = None

    if db is not None and user.role == Role.STUDENT:
        teacher_name = get_teacher_name_for_student(db, user.id)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value if user.role else None,
        "roles": [user.role.value] if user.role else [],
        "name": user.name,
        "gender": user.gender,
        "phone": user.phone,
        "email": user.email,
        "avatar": user.avatar,

        # 账号状态
        "accountStatus": user.account_status.value if user.account_status else None,

        # 教师字段
        "title": user.title,

        # 教师/学生共有字段
        "major": user.major,
        "college": user.college,

        # 学生字段：新版从 teacher_students 表查询
        "teacherName": teacher_name,

        # 学号、工号、校外编号
        "identityNo": user.identity_no,

        # 校外人员字段
        "company": user.company,

        "createdAt": user.created_at,
        "updatedAt": user.updated_at,
    }


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {
        "code": 20000,
        "data": user_to_frontend(current_user, db)
    }


@router.put("/me")
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    update_data = payload.dict(exclude_unset=True)

    forbidden_fields = {
        "id",
        "role",
        "roles",
        "username",
        "password",
        "password_hash",
        "passwordHash",
        "account_status",
        "accountStatus",
        "identity_no",
        "identityNo"
    }

    for field in forbidden_fields:
        update_data.pop(field, None)

    # 新版数据库没有 teacher_name，前端传 teacherName 时忽略
    update_data.pop("teacherName", None)
    update_data.pop("teacher_name", None)

    # 把所有空字符串转成 None，避免 phone/email 唯一约束冲突
    for key, value in list(update_data.items()):
        if isinstance(value, str) and value.strip() == "":
            update_data[key] = None

    # 手机号重复检查
    if update_data.get("phone"):
        exists = db.query(User).filter(
            User.phone == update_data["phone"],
            User.id != current_user.id
        ).first()

        if exists:
            raise HTTPException(status_code=400, detail="手机号已被其他用户使用")

    # 邮箱重复检查
    if update_data.get("email"):
        exists = db.query(User).filter(
            User.email == update_data["email"],
            User.id != current_user.id
        ).first()

        if exists:
            raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")

    for key, value in update_data.items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)

    return {
        "code": 20000,
        "message": "个人信息更新成功",
        "data": user_to_frontend(current_user, db)
    }


@router.get("/")
def get_users(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    管理员和实验室负责人查看用户列表。
    """
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    query = db.query(User)

    if role:
        try:
            role_enum = Role(role)
        except ValueError:
            raise HTTPException(status_code=400, detail="角色参数不合法")

        query = query.filter(User.role == role_enum)

    users = query.order_by(User.id.asc()).all()

    return {
        "code": 20000,
        "data": [user_to_frontend(u, db) for u in users]
    }


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除用户。
    注意：如果该用户已经有关联预约记录，数据库外键可能阻止删除。
    真实系统更推荐改成禁用账号，而不是物理删除。
    """
    if current_user.role not in [Role.ADMIN, Role.LAB_LEADER]:
        raise HTTPException(status_code=403, detail="权限不足")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")

    db.delete(user)
    db.commit()

    return {
        "code": 20000,
        "message": "删除成功"
    }


@router.get("/my-students")
def get_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    教师查看自己指导的学生。
    新版不再使用 User.teacher_name，而是通过 teacher_students 表查询。
    """
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=403, detail="只有教师可以查看指导学生")

    relations = db.query(TeacherStudent).filter(
        TeacherStudent.teacher_id == current_user.id,
        TeacherStudent.status == "active"
    ).all()

    data = []

    for relation in relations:
        student = relation.student

        if not student:
            continue

        data.append({
            "id": student.id,
            "studentId": student.identity_no or student.username,
            "username": student.username,
            "name": student.name,
            "gender": student.gender,
            "major": student.major,
            "college": student.college,
            "phone": student.phone,
            "email": student.email,
            "teacherName": current_user.name,
            "accountStatus": student.account_status.value if student.account_status else None,
            "createdAt": student.created_at
        })

    return {
        "code": 20000,
        "data": data
    }