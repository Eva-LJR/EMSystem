from database import SessionLocal
from models import Approval, ApprovalStatus, ApprovalStep, Role, Device, DeviceStatus
from datetime import datetime, timedelta


def seed_data():
    db = SessionLocal()
    now = datetime.utcnow()

    print("开始生成测试预约单数据...")

    # 1. 确保数据库里至少有一台测试设备，如果没有则自动创建
    device = db.query(Device).first()
    if not device:
        device = Device(
            model="ZEISS 高分辨率显微镜",
            manufacturer="蔡司",
            price=200.0,
            status=DeviceStatus.IDLE
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        print(f"已自动生成测试设备: {device.model}")

    # 准备 7 条覆盖全场景的测试数据
    mock_approvals = [
        # ==================== 场景 1 & 2：专门给【设备管理员】测试的单子 ====================
        Approval(
            role=Role.STUDENT,
            device_id=device.id, device_name=device.model,
            start_time=now + timedelta(days=1), end_time=now + timedelta(days=1, hours=2),
            reason="材料物理性能观测",
            status=ApprovalStatus.PENDING_ADMIN, current_step=ApprovalStep.ADMIN,
            applicant_name="学生张三", applicant_id="S2023001", college="理学院",
            total_fee=0.0, is_paid=False
        ),
        Approval(
            role=Role.OUTSIDE,
            device_id=device.id, device_name=device.model,
            start_time=now + timedelta(days=2), end_time=now + timedelta(days=2, hours=4),
            reason="企业新产品晶圆检测",
            status=ApprovalStatus.PENDING_ADMIN, current_step=ApprovalStep.ADMIN,
            applicant_name="校外王五", applicant_id="W10086", company="江南科技公司",
            total_fee=400.0, is_paid=False
        ),

        # ==================== 场景 3：专门给【实验室负责人】测试的单子 ====================
        Approval(
            role=Role.OUTSIDE,
            device_id=device.id, device_name=device.model,
            start_time=now + timedelta(days=3), end_time=now + timedelta(days=3, hours=6),
            reason="外包横向课题实验",
            status=ApprovalStatus.PENDING_LEADER, current_step=ApprovalStep.LEADER,  # 注意：已经在负责人环节
            applicant_name="校外赵六", applicant_id="W10087", company="无锡某新材料公司",
            total_fee=600.0, is_paid=False
        ),

        # ==================== 场景 4 & 5：专门给【数据统计页】补充数据的成功单 ====================
        Approval(
            role=Role.OUTSIDE,
            device_id=device.id, device_name=device.model,
            start_time=now - timedelta(days=5), end_time=now - timedelta(days=5, hours=2),
            reason="已完成的历史订单",
            status=ApprovalStatus.APPROVED, current_step=ApprovalStep.END,  # 已经彻底通过
            applicant_name="校外李总", applicant_id="W10088", company="苏州某科技",
            total_fee=200.0, is_paid=True
        ),
        Approval(
            role=Role.TEACHER,
            device_id=device.id, device_name=device.model,
            start_time=now - timedelta(days=2), end_time=now - timedelta(days=2, hours=4),
            reason="本科生教学实验演示",
            status=ApprovalStatus.APPROVED, current_step=ApprovalStep.END,  # 已经彻底通过
            applicant_name="教师李四", applicant_id="T199901", college="机械学院",
            total_fee=0.0, is_paid=False
        ),

        # ==================== 场景 6 & 7：各种被驳回的历史记录（测试状态标签展示） ====================
        Approval(
            role=Role.OUTSIDE,
            device_id=device.id, device_name=device.model,
            start_time=now + timedelta(days=4), end_time=now + timedelta(days=4, hours=2),
            reason="随便看看",
            status=ApprovalStatus.REJECTED_BY_ADMIN, current_step=ApprovalStep.END,  # 被管理员驳回
            applicant_name="校外测试A", applicant_id="W10089", company="不明企业",
            total_fee=200.0, is_paid=False
        ),
        Approval(
            role=Role.OUTSIDE,
            device_id=device.id, device_name=device.model,
            start_time=now + timedelta(days=5), end_time=now + timedelta(days=5, hours=2),
            reason="高危化学品实验",
            status=ApprovalStatus.REJECTED_BY_LEADER, current_step=ApprovalStep.END,  # 被负责人驳回
            applicant_name="校外测试B", applicant_id="W10090", company="高危化工",
            total_fee=200.0, is_paid=False
        )
    ]

    for approval in mock_approvals:
        db.add(approval)

    db.commit()
    print(f"✅ 成功插入 {len(mock_approvals)} 条测试预约单！现在可以去前端测试了。")
    db.close()


if __name__ == "__main__":
    seed_data()