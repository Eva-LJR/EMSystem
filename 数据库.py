# add_user.py
from database import SessionLocal
from models import User, Role
from utils import get_password_hash

db = SessionLocal()
# 创建用户
new_user = User(
    username="admin",
    password_hash=get_password_hash("111111"), # 确保密码经过了哈希处理
    name="管理员",
    role=Role.ADMIN
)
db.add(new_user)
db.commit()
print("用户 admin 已添加，密码为 111111")
db.close()