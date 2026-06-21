# init_db.py
from database import engine, SessionLocal
from models import User, Base, Role  # 注入 Role 枚举
from utils import get_password_hash


def init_db():
    # 1. 创建所有表（如果不存在）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    # 2. 检查是否已有用户
    if not db.query(User).first():
        test_users = [
            {"username": "admin", "password": "123456", "role": "admin", "name": "设备管理员"},
            {"username": "leader", "password": "123456", "role": "labLeader", "name": "实验室负责人"},
            {"username": "student", "password": "123456", "role": "student", "name": "学生张三"},
            {"username": "teacher", "password": "123456", "role": "teacher", "name": "教师李四"},
            {"username": "outside", "password": "123456", "role": "outside", "name": "校外王五"},
        ]
        for u in test_users:
            hashed = get_password_hash(u["password"])
            user = User(
                username=u["username"],
                password_hash=hashed,
                role=u["role"],
                name=u["name"]
            )
            db.add(user)
        db.commit()
        print("测试用户创建成功")
    else:
        print("用户表已有数据，跳过初始化")
    db.close()


if __name__ == "__main__":
    init_db()