"""
静态文件与前端资源端到端测试
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_static_files():
    # 1. 首页
    res = client.get("/")
    assert res.status_code == 200
    assert "Jev 中国象棋" in res.text

    # 2. CSS
    res = client.get("/css/style.css")
    assert res.status_code == 200
    assert ".board-wrapper" in res.text

    # 3. 矢量棋子
    res = client.get("/js/pieces_svg.js")
    assert res.status_code == 200
    assert "PIECES_SVG" in res.text

    # 4. 棋盘与控制逻辑
    res = client.get("/js/board.js")
    assert res.status_code == 200
    assert "class BoardUI" in res.text

    res = client.get("/js/app.js")
    assert res.status_code == 200
    assert "handlePlayerMove" in res.text


def test_prompt_preview_endpoint():
    res = client.get("/api/prompt/preview")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "jev_payload" in data
    assert "criteria" in data["jev_payload"]["questions"]["next_move"]
    # 确保全部 44 种候选选项完整送入，未被筛选
    assert data["legal_count"] == 44
    assert len(data["jev_payload"]["questions"]["next_move"]["criteria"]) == 44
