"""
FastAPI Pydantic 请求与响应数据规范
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class NewGameRequest(BaseModel):
    player_color: str = Field(default="red", description="玩家所持颜色: 'red' (先行执红) 或 'black' (后行执黑)")


class MoveRequest(BaseModel):
    uci: str = Field(..., description="走法坐标，如 'h2e2'")


class ConfigUpdateRequest(BaseModel):
    api_key: Optional[str] = Field(default=None, description="OpenRouter / TypeSafe API Key")
    model: Optional[str] = Field(default=None, description="Jev 模型名称，如 'typesafe/jev-1.13'")
    base_url: Optional[str] = Field(default=None, description="OpenRouter Base URL")


class CommonResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
