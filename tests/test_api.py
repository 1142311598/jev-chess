"""
后端 API 单元与集成测试
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_config():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "is_configured" in data["data"]


def test_game_flow():
    # 1. 创建新对局（红方）
    res = client.post("/api/game/new", json={"player_color": "red"})
    assert res.status_code == 200
    state = res.json()["data"]
    assert state["turn"] == "red"
    assert state["game_status"] == "playing"

    # 2. 预览 Prompt
    res = client.get("/api/prompt/preview")
    assert res.status_code == 200
    prompt_data = res.json()["data"]
    assert "jev_payload" in prompt_data
    assert "plain_text_prompt" in prompt_data
    assert prompt_data["legal_count"] == 44

    # 3. 玩家走棋: 炮二平五 (h2e2)
    res = client.post("/api/game/move", json={"uci": "h2e2"})
    assert res.status_code == 200
    move_data = res.json()["data"]
    assert move_data["move"]["notation"] == "炮二平五"
    assert move_data["state"]["turn"] == "black"

    # 4. 悔棋
    res = client.post("/api/game/undo")
    assert res.status_code == 200
    undo_state = res.json()["data"]
    assert undo_state["turn"] == "red"
