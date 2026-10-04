"""
中国象棋对局管理器 (GameManager)
负责维护棋盘规则状态、走棋/悔棋、终局判定与向前端提供序列化数据结构。
"""
from typing import Dict, Any, List, Optional
from core.cchess import (
    Board, Move, Piece, RED, BLACK,
    ROOK, KNIGHT, BISHOP, ADVISOR, KING, CANNON, PAWN,
    square, square_column, square_row, square_name, SQUARES
)
from core.board_renderer import render_board_2d
from core.feature_extractor import PIECE_NAMES_ZH


class GameManager:
    def __init__(self, player_color: bool = RED):
        self.player_color = player_color  # 玩家所持颜色，默认红方先行
        self.board = Board()
        self.history: List[Dict[str, Any]] = []
        self.last_ai_thought: Optional[Dict[str, Any]] = None
        self._update_status()

    def reset(self, player_color: bool = RED) -> None:
        """重置对局"""
        self.player_color = player_color
        self.board = Board()
        self.history.clear()
        self.last_ai_thought = None
        self._update_status()

    def _update_status(self) -> None:
        """检查并更新对局终局状态"""
        if self.board.is_checkmate():
            # 被将死的一方输，当前轮到的一方被将死
            winner = "black_win" if self.board.turn == RED else "red_win"
            self.game_status = winner
            self.status_reason = f"{'黑方' if self.board.turn == RED else '红方'}绝杀胜出！"
        elif self.board.is_stalemate():
            # 困毙（无合法走子判负）
            winner = "black_win" if self.board.turn == RED else "red_win"
            self.game_status = winner
            self.status_reason = f"{'红方' if self.board.turn == RED else '黑方'}困毙无子可走，判负！"
        elif self.board.is_insufficient_material():
            self.game_status = "draw"
            self.status_reason = "双方子力均不足以成杀，和棋！"
        elif self.board.is_sixty_moves():
            self.game_status = "draw"
            self.status_reason = "达到自然限着（六十回合无吃子），和棋！"
        else:
            self.game_status = "playing"
            self.status_reason = "对弈进行中"

    def apply_move(self, uci_str: str, ai_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行一步走棋（UCI格式，如 'h2e2'）。
        进行合法性校验并更新历史与状态。
        """
        if self.game_status != "playing":
            raise ValueError(f"游戏已结束（{self.status_reason}），无法继续走棋。")

        try:
            move = Move.from_uci(uci_str)
        except Exception:
            raise ValueError(f"无效的着法格式: '{uci_str}'")

        if move not in self.board.legal_moves:
            raise ValueError(f"着法 '{uci_str}' 不符合中国象棋走子规则，属于非法走法！")

        from_sq = move.from_square
        to_sq = move.to_square
        moving_piece = self.board.piece_at(from_sq)
        captured_piece = self.board.piece_at(to_sq)
        notation = self.board.move_to_notation(move)
        turn_color = self.board.turn

        # 执行走棋
        self.board.push(move)

        move_record = {
            "step": len(self.history) + 1,
            "turn": "red" if turn_color == RED else "black",
            "uci": uci_str,
            "notation": notation,
            "from": square_name(from_sq),
            "to": square_name(to_sq),
            "piece": moving_piece.symbol() if moving_piece else None,
            "captured": captured_piece.symbol() if captured_piece else None,
            "captured_name": PIECE_NAMES_ZH.get((captured_piece.color, captured_piece.piece_type)) if captured_piece else None,
            "fen_after": self.board.fen(),
            "ai_info": ai_info
        }
        self.history.append(move_record)

        if ai_info:
            self.last_ai_thought = ai_info

        self._update_status()
        return move_record

    def undo(self) -> bool:
        """
        悔棋：回退对局。
        如果当前轮到玩家走，说明 AI 刚刚走过，需要连续回退两步（AI的一步 + 玩家的一步）；
        如果是玩家走完 AI 还没走，则回退一步。
        """
        if not self.history:
            return False

        # 如果轮到玩家走棋且历史至少有2步，回退两步
        current_turn = self.board.turn
        if current_turn == self.player_color and len(self.history) >= 2:
            self.board.pop()
            self.history.pop()
            self.board.pop()
            self.history.pop()
            self._update_status()
            return True
        elif len(self.history) >= 1:
            self.board.pop()
            self.history.pop()
            self._update_status()
            return True

        return False

    def get_board_grid(self) -> List[List[Optional[Dict[str, Any]]]]:
        """
        生成前端直观渲染所需的 10行×9列 棋盘二维网格。
        从第 9 行到第 0 行，每行从 a 列到 i 列。
        """
        grid = []
        for row in range(9, -1, -1):
            row_items = []
            for col in range(9):
                sq = square(col, row)
                piece = self.board.piece_at(sq)
                if piece:
                    row_items.append({
                        "sq_name": square_name(sq),
                        "row": row,
                        "col": col,
                        "piece_type": piece.piece_type,
                        "symbol": piece.symbol(),
                        "color": "red" if piece.color == RED else "black",
                        "zh": PIECE_NAMES_ZH.get((piece.color, piece.piece_type), piece.symbol())
                    })
                else:
                    row_items.append(None)
            grid.append(row_items)
        return grid

    def get_legal_moves_map(self) -> Dict[str, List[Dict[str, str]]]:
        """
        按起始格（如 'h2'）分组返回当前全部合法走法，便于前端点击选子时秒速点亮所有可行落点。
        """
        moves_map: Dict[str, List[Dict[str, str]]] = {}
        for m in self.board.legal_moves:
            from_name = square_name(m.from_square)
            to_name = square_name(m.to_square)
            if from_name not in moves_map:
                moves_map[from_name] = []
            moves_map[from_name].append({
                "uci": m.uci(),
                "to": to_name,
                "notation": self.board.move_to_notation(m)
            })
        return moves_map

    def get_state(self) -> Dict[str, Any]:
        """打包全局状态供 API 返回"""
        last_move = self.history[-1] if self.history else None
        current_turn = "red" if self.board.turn == RED else "black"
        player_color_str = "red" if self.player_color == RED else "black"

        return {
            "fen": self.board.fen(),
            "turn": current_turn,
            "player_color": player_color_str,
            "is_player_turn": (self.board.turn == self.player_color),
            "is_check": self.board.is_check(),
            "game_status": self.game_status,
            "status_reason": self.status_reason,
            "board_grid": self.get_board_grid(),
            "legal_moves_map": self.get_legal_moves_map(),
            "last_move": last_move,
            "history": self.history,
            "last_ai_thought": self.last_ai_thought,
            "board_2d": render_board_2d(self.board, perspective=RED)
        }


if __name__ == "__main__":
    gm = GameManager(player_color=RED)
    print("初始状态:", gm.game_status, "当前轮次:", gm.board.turn)
    # 模拟走一步炮二平五
    move_rec = gm.apply_move("h2e2")
    print("走棋后:", move_rec["notation"], "FEN:", gm.board.fen())
    # 悔棋
    undone = gm.undo()
    print("悔棋结果:", undone, "FEN:", gm.board.fen())
