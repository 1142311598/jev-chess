"""
FastAPI 路由接口实现
处理中国象棋对局逻辑、Jev AI 决策、悔棋与 Prompt 实时预览。
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from core.cchess import RED, BLACK
from core.game_manager import GameManager
from core.jev_client import JevClient, JevAPIError
from core.board_renderer import render_board_2d
from core.feature_extractor import describe_position_features, describe_move_intention
from api.schemas import NewGameRequest, MoveRequest, ConfigUpdateRequest, CommonResponse

router = APIRouter(prefix="/api", tags=["Game"])

# 全局单例管理器
game_manager = GameManager(player_color=RED)
jev_client = JevClient()


@router.post("/game/new", response_model=CommonResponse)
def create_new_game(req: NewGameRequest):
    """创建新对局"""
    color = RED if req.player_color.lower() == "red" else BLACK
    game_manager.reset(player_color=color)
    return CommonResponse(
        message="新对局已创建",
        data=game_manager.get_state()
    )


@router.get("/game/state", response_model=CommonResponse)
def get_game_state():
    """获取当前对局完整状态"""
    return CommonResponse(
        data=game_manager.get_state()
    )


@router.post("/game/move", response_model=CommonResponse)
def player_move(req: MoveRequest):
    """玩家执行走棋"""
    try:
        record = game_manager.apply_move(req.uci)
        return CommonResponse(
            message=f"走棋成功: {record['notation']}",
            data={
                "move": record,
                "state": game_manager.get_state()
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/game/ai-move", response_model=CommonResponse)
def ai_move():
    """请求 Jev 决策模型计算并走棋"""
    if game_manager.game_status != "playing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"游戏已结束（{game_manager.status_reason}），无法继续行棋。"
        )

    try:
        # 调用 Jev 模型进行决策（传入历史对弈脉络）
        decision = jev_client.decide_move(game_manager.board, history=game_manager.history)
        best_uci = decision["uci"]

        # 棋盘执行走法并记录 AI 思考信息
        record = game_manager.apply_move(best_uci, ai_info=decision)

        return CommonResponse(
            message=f"Jev 决策完成: {decision['notation']} (置信度: {decision['confidence']:.2f}, 耗时: {decision.get('cost_time', 0):.2f}s)",
            data={
                "move": record,
                "decision": decision,
                "state": game_manager.get_state()
            }
        )
    except JevAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Jev 决策服务异常",
                "message": e.message,
                "status_code": e.status_code
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 行棋发生内部异常: {str(e)}"
        )


@router.post("/game/undo", response_model=CommonResponse)
def undo_move():
    """悔棋"""
    success = game_manager.undo()
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前暂无可以回退的历史着法。")
    return CommonResponse(
        message="悔棋成功",
        data=game_manager.get_state()
    )


@router.get("/prompt/preview", response_model=CommonResponse)
def preview_prompt():
    """
    实时预览当前局面的完整 Prompt 与 Jev Payload。
    展示真实变量替换后的 2D 字符网格、特征说明与全部候选 Criteria 走法。
    """
    board = game_manager.board
    payload = jev_client.build_decision_payload(board, history=game_manager.history)
    count = len(payload["questions"]["next_move"]["criteria"])

    # 另外组织传统纯文本 Prompt 样式供对比参考
    legal_list = []
    for idx, (uci, desc) in enumerate(payload["questions"]["next_move"]["criteria"].items()):
        legal_list.append(f"{idx + 1}. {uci} ({desc})")

    plain_prompt = f"""你是一名中国象棋特级大师。
当前棋局 FEN 为: {board.fen()}

{render_board_2d(board, perspective=RED)}

关键态势特征：
{describe_position_features(board)}

候选合法走法如下（共 {len(legal_list)} 项，已包含全部合法动作）：
""" + "\n".join(legal_list) + """

请评估局面，从中选择你认为胜率最高、最合理的一步走法。"""

    return CommonResponse(
        data={
            "provider": "jev",
            "model": jev_client.model,
            "payload": payload,
            "jev_payload": payload,
            "plain_text_prompt": plain_prompt,
            "legal_count": count,
            "candidates_count": count,
            "current_fen": board.fen()
        }
    )


@router.get("/config", response_model=CommonResponse)
def get_config():
    """获取当前配置状态（屏蔽 Key 内容）"""
    masked_key = ""
    if jev_client.api_key:
        masked_key = (jev_client.api_key[:6] + "..." + jev_client.api_key[-4:]) if len(jev_client.api_key) > 10 else "已配置"
    return CommonResponse(
        data={
            "current_provider": "jev",
            "is_configured": jev_client.is_configured(),
            "model": jev_client.model,
            "base_url": jev_client.base_url,
            "has_key": bool(jev_client.api_key),
            "api_key_masked": masked_key
        }
    )


@router.post("/config", response_model=CommonResponse)
def update_config(req: ConfigUpdateRequest):
    """动态更新 API Key 或 Model"""
    if req.api_key is not None:
        jev_client.api_key = req.api_key.strip()
    if req.model is not None:
        jev_client.model = req.model.strip()
    if req.base_url is not None:
        jev_client.base_url = req.base_url.rstrip("/")

    return CommonResponse(
        message="配置更新成功",
        data={
            "current_provider": "jev",
            "is_configured": jev_client.is_configured(),
            "model": jev_client.model,
            "base_url": jev_client.base_url
        }
    )
