from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str   # 新增 role 字段，取值：manager, leader, student, teacher, outside

@app.post("/vue-admin-template/user/login")
async def login(login_req: LoginRequest):
    # 临时：根据 role 返回不同的 token 和用户角色
    # 实际应查询数据库验证用户名密码，并根据用户角色返回
    role_mapping = {
        "manager": ["manager"],
        "leader": ["leader"],
        "student": ["student"],
        "teacher": ["teacher"],
        "outside": ["outside"]
    }
    roles = role_mapping.get(login_req.role, ["visitor"])
    # 生成一个简单的 token，可以包含 role 信息便于后续解析（实际生产应使用 JWT）
    token = f"fake-token-{login_req.role}"
    return {
        "code": 20000,
        "data": {
            "token": token,
            "roles": roles,
            "name": f"{login_req.role}_user",
            "avatar": "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif"
        }
    }

@app.get("/vue-admin-template/user/info")
async def get_info(token: str):
    # 临时：根据 token 中的 role 返回用户信息
    # 简单解析 token 中的 role（实际应解码 JWT 或查数据库）
    if "manager" in token:
        roles = ["manager"]
        name = "设备管理员"
    elif "leader" in token:
        roles = ["leader"]
        name = "实验室负责人"
    elif "student" in token:
        roles = ["student"]
        name = "学生"
    elif "teacher" in token:
        roles = ["teacher"]
        name = "教师"
    elif "outside" in token:
        roles = ["outside"]
        name = "校外人员"
    else:
        roles = ["visitor"]
        name = "访客"
    return {
        "code": 20000,
        "data": {
            "roles": roles,
            "name": name,
            "avatar": "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif",
            "introduction": "测试用户"
        }
    }

# 登出接口保持不变
@app.post("/vue-admin-template/user/logout")
async def logout():
    return {"code": 20000, "data": "success"}