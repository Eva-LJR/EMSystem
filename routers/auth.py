from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import traceback

from database import get_db
from models import User, Role, AccountStatus, TeacherStudent
from schemas import Token, UserInDB, LoginRequest, RegisterRequest
from utils import create_access_token, verify_password, get_password_hash, SECRET_KEY, ALGORITHM

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



@router.post("/vue-admin-template/user/register", response_model=dict)
async def register(register_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册接口：
    1. 学生凭学号注册
    2. 教师凭工号注册
    3. 校外人员凭手机号注册
    """

    role = register_data.role

    # 1. 只允许学生、教师、校外人员注册
    if role not in ["student", "teacher", "outside"]:
        raise HTTPException(
            status_code=400,
            detail="只允许学生、教师和校外人员注册"
        )

    # 2. 根据角色确定 username
    if role in ["student", "teacher"]:
        if not register_data.identity_no:
            raise HTTPException(
                status_code=400,
                detail="学生或教师注册时必须填写学号/工号"
            )

        username = register_data.identity_no.strip()
        identity_no = register_data.identity_no.strip()
        phone = register_data.phone.strip() if register_data.phone else None

    else:
        if not register_data.phone:
            raise HTTPException(
                status_code=400,
                detail="校外人员注册时必须填写手机号"
            )

        username = register_data.phone.strip()
        identity_no = None
        phone = register_data.phone.strip()

    # 3. 基本空值校验
    if not username:
        raise HTTPException(status_code=400, detail="注册账号不能为空")

    if not register_data.name or not register_data.name.strip():
        raise HTTPException(status_code=400, detail="姓名不能为空")

    if not register_data.password or len(register_data.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")

    # 4. 检查 username 是否重复
    exists_username = db.query(User).filter(User.username == username).first()
    if exists_username:
        raise HTTPException(status_code=400, detail="该账号已经注册")

    # 5. 检查学号/工号是否重复
    if identity_no:
        exists_identity = db.query(User).filter(User.identity_no == identity_no).first()
        if exists_identity:
            raise HTTPException(status_code=400, detail="该学号/工号已经注册")

    # 6. 检查手机号是否重复
    if phone:
        exists_phone = db.query(User).filter(User.phone == phone).first()
        if exists_phone:
            raise HTTPException(status_code=400, detail="该手机号已经注册")

    # 7. 检查邮箱是否重复
    email = register_data.email.strip() if register_data.email else None
    if email:
        exists_email = db.query(User).filter(User.email == email).first()
        if exists_email:
            raise HTTPException(status_code=400, detail="该邮箱已经注册")

    # 8. 创建用户
    user = User(
        username=username,
        password_hash=get_password_hash(register_data.password),
        name=register_data.name.strip(),
        role=Role(role),
        gender=register_data.gender.strip() if register_data.gender else None,
        phone=phone,
        email=email,
        identity_no=identity_no,
        college=register_data.college.strip() if register_data.college else None,
        major=register_data.major.strip() if register_data.major else None,
        title=register_data.title.strip() if register_data.title else None,
        company=register_data.company.strip() if register_data.company else None,

        # 如果你想注册后直接能登录，使用 ACTIVE
        account_status=AccountStatus.ACTIVE

        # 如果你想注册后等待管理员审核，改成：
        # account_status=AccountStatus.PENDING
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "code": 20000,
        "message": "注册成功",
        "data": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "name": user.name,
            "phone": user.phone,
            "identityNo": user.identity_no,
            "accountStatus": user.account_status.value
        }
    }

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
        if hasattr(user, "account_status") and user.account_status.value != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号未启用或已被禁用"
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
            "teacherName": None,

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