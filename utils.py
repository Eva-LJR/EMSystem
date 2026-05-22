from datetime import datetime, timedelta
from typing import Any, Union
import hashlib

from jose import jwt
from passlib.context import CryptContext

# 安全设置，实际项目中应放在环境变量中
SECRET_KEY = "your-secret-key-keep-it-safe-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 使用兼容性更好的配置
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",
    bcrypt__rounds=12
)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # 如果验证失败，返回False
        return False


def get_password_hash(password: str) -> str:
    try:
        # 确保密码长度不超过72字节
        if len(password.encode('utf-8')) > 72:
            # 截断到72字节以内
            password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')

        return pwd_context.hash(password)
    except ValueError as e:
        if "password cannot be longer than 72 bytes" in str(e):
            # 强制截断密码
            truncated_password = password[:72] if len(password) > 72 else password
            return pwd_context.hash(truncated_password)
        else:
            raise e


def verify_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    返回 (是否符合要求, 提示信息)
    """
    if len(password) < 6:
        return False, "密码长度至少6位"

    if len(password.encode('utf-8')) > 72:
        return False, "密码过长，超出bcrypt限制（72字节）"

    return True, "密码符合要求"