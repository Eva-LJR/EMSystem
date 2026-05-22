# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from typing import List, Optional  # 这里修复了！
#
# from database import get_db
# from models import User, Role
# from schemas import UserInDB, UserCreate, UserUpdate
# from routers.auth import get_current_user
# from utils import get_password_hash
#
# router = APIRouter(prefix="/api/users", tags=["users"])
#
# @router.get("/", response_model=dict)
# def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     role: Optional[Role] = None,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     # 只有管理员可以查看所有用户
#     if current_user.role != Role.ADMIN:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     query = db.query(User)
#     if role:
#         query = query.filter(User.role == role)
#     users = query.offset(skip).limit(limit).all()
#     return {
#         "code": 20000,
#         "data": users
#     }
#
# @router.post("/", response_model=dict)
# def create_user(
#     user: UserCreate,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     if current_user.role != Role.ADMIN:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     db_user = db.query(User).filter(User.username == user.username).first()
#     if db_user:
#         raise HTTPException(status_code=400, detail="Username already registered")
#     hashed_password = get_password_hash(user.password)
#     new_user = User(
#         username=user.username,
#         password_hash=hashed_password,
#         name=user.name,
#         role=user.role
#     )
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#     return {
#         "code": 20000,
#         "data": new_user
#     }
#
# @router.put("/{user_id}", response_model=dict)
# def update_user(
#     user_id: int,
#     user: UserUpdate,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     # 管理员可以更新所有用户，普通用户只能更新自己
#     if current_user.role != Role.ADMIN and current_user.id != user_id:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     db_user = db.query(User).filter(User.id == user_id).first()
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     update_data = user.dict(exclude_unset=True)
#     for key, value in update_data.items():
#         setattr(db_user, key, value)
#     db.commit()
#     db.refresh(db_user)
#     return {
#         "code": 20000,
#         "data": db_user
#     }
#
# @router.delete("/{user_id}", response_model=dict)
# def delete_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user)
# ):
#     if current_user.role != Role.ADMIN:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     db_user = db.query(User).filter(User.id == user_id).first()
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     # 禁止删除自己
#     if db_user.id == current_user.id:
#         raise HTTPException(status_code=400, detail="Cannot delete yourself")
#     db.delete(db_user)
#     db.commit()
#     return {
#         "code": 20000,
#         "data": "User deleted successfully"
#     }

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
# 💡 请确保这里引入了你的 User 模型，如果你的表名不叫 User，请修改为对应的名称
from models import User
from routers.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["用户管理"])

# 1. 获取用户列表接口
@router.get("/")
def get_users(role: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        query = db.query(User)
        if role:
            query = query.filter(User.role == role)
        users = query.all()
        return {"code": 20000, "data": users}
    except Exception as e:
        print(f"后端报错详情: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

# 2. 删除用户接口 (匹配你前端的 delete 请求)
@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return {"code": 20000, "message": "删除成功"}