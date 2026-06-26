# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, devices, approvals, users, stats
from init_db import init_db
from routers import client
from routers import stats


# 1. 核心：必须先实例化 app 对象！(你之前可能漏掉了这一行)
app = FastAPI(
    title="实验室设备管理系统",
    description="后端 API 接口服务",
    version="1.0.0"
)

# 2. 配置跨域（允许 Vue 前端进行跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 实际开发 Vue 建议指定具体端口如 ["http://localhost:9528"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 注册生命周期事件：系统启动时自动创建数据库表并初始化测试数据
@app.on_event("startup")
def on_startup():
    print("正在初始化数据库及基础数据...")
    init_db()
    print("数据库初始化完成！")

# 4. 注册各个模块的路由（必须写在 app = FastAPI() 的下方）
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(approvals.router)
app.include_router(users.router)
app.include_router(stats.router)
app.include_router(client.router)

# 根路由测试
@app.get("/")
def read_root():
    return {"message": "欢迎访问实验室设备管理系统 API 接口服务！"}