"""
Jev 中国象棋对弈系统后端主入口
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router as api_router

load_dotenv()

app = FastAPI(
    title="Jev Chinese Chess",
    description="基于 Jev 结构化决策模型的中国象棋人机对弈系统",
    version="1.0.0"
)

# 允许跨域（方便本地开发）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router)

# 静态网页资源挂载
static_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Jev Chinese Chess server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
