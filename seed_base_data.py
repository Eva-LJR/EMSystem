from datetime import datetime

from database import SessionLocal
from models import (
    Device,
    DeviceStatus,
    Role,
    TeacherStudent,
    User,
)


def seed_base_data():
    db = SessionLocal()

    try:
        # 1. 查询测试教师和学生
        teacher = db.query(User).filter(
            User.username == "teacher",
            User.role == Role.TEACHER
        ).first()

        student = db.query(User).filter(
            User.username == "student",
            User.role == Role.STUDENT
        ).first()

        if not teacher:
            raise RuntimeError("测试教师 teacher 不存在")

        if not student:
            raise RuntimeError("测试学生 student 不存在")

        # 2. 创建师生关系
        relation = db.query(TeacherStudent).filter(
            TeacherStudent.student_id == student.id
        ).first()

        if not relation:
            relation = TeacherStudent(
                teacher_id=teacher.id,
                student_id=student.id,
                status="active"
            )
            db.add(relation)
            print("师生关系创建成功")
        else:
            print("师生关系已存在，跳过")

        # 3. 创建测试设备
        device = db.query(Device).filter(
            Device.device_code == "DEV-001"
        ).first()

        if not device:
            device = Device(
                device_code="DEV-001",
                name="高分辨率显微镜",
                model="ZEISS 高分辨率显微镜",
                manufacturer="蔡司",
                purpose="材料结构观察、显微成像、实验教学与科研测试",
                purchase_price=200000.00,
                hourly_price=100.00,
                purchase_date=datetime(2024, 9, 1),
                status=DeviceStatus.IDLE,
                location="实验楼 A305",
                available_time="周一至周五 08:00-18:00",
                description="用于学生实验、教师科研和校外检测服务"
            )
            db.add(device)
            print("测试设备创建成功")
        else:
            print("测试设备已存在，跳过")

        db.commit()
        print("基础测试数据初始化完成")

    except Exception as e:
        db.rollback()
        print("初始化失败：", e)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_base_data()