from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import traceback

from database import get_db
from models import User
from schemas import Token, UserInDB, LoginRequest
from utils import create_access_token, verify_password, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/api")

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/vue-admin-template/user/login")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/vue-admin-template/user/login")


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")  # 改为获取username而不是id
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()  # 使用username查询
    if user is None:
        raise credentials_exception
    return user


# 登录路由
@router.post("/vue-admin-template/user/login", response_model=dict)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    try:
        # 1. 查询用户
        print(login_data.username,login_data.password)

        user = get_user(db, login_data.username)

        # 2. 检查用户是否存在
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        # 3. 验证密码
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )

        # 4. 创建访问令牌 - 使用用户名作为subject
        access_token = create_access_token(subject=user.username)

        return {
            "code": 20000,
            "data": {
                "token": access_token,
                "tokenType": "bearer"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"登录错误详情: {str(e)}")
        print(f"错误追踪: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误"
        )


# @router.get("/vue-admin-template/user/info", response_model=dict)
# async def read_user_info(current_user: User = Depends(get_current_user)):
#     return {
#         "code": 20000,
#         "data": {
#             "roles": [current_user.role.value],
#             "name": current_user.name,
#             "avatar": current_user.avatar or "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif"
#         }
#     }
@router.get("/vue-admin-template/user/info", response_model=dict)
async def read_user_info(current_user: User = Depends(get_current_user)):
    return {
        "code": 20000,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "roles": [current_user.role.value],
            "role": current_user.role.value,
            "name": current_user.name,
            "gender": current_user.gender,
            "phone": current_user.phone,
            "avatar": current_user.avatar or "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif",

            # 教师/学生字段
            "title": current_user.title,
            "major": current_user.major,
            "college": current_user.college,
            "teacherName": current_user.teacher_name,

            # 校外人员字段
            "company": current_user.company
        }
    }


@router.post("/vue-admin-template/user/logout", response_model=dict)
async def logout():
    return {
        "code": 20000,
        "data": "success"
    }