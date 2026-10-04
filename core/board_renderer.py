"""
中国象棋棋盘 2D 文本视觉矩阵生成器
将 cchess.Board 对象转换为等宽的 9列×10行字符矩阵，为模型提供直观的空间拓扑感知。
"""
from typing import Optional
from core.cchess import Board, RED, BLACK, ROOK, KNIGHT, BISHOP, ADVISOR, KING, CANNON, PAWN, square

# 棋子全角符号映射
RED_SYMBOLS = {
    ROOK: "车",
    KNIGHT: "马",
    BISHOP: "相",
    ADVISOR: "仕",
    KING: "帅",
    CANNON: "炮",
    PAWN: "兵"
}

BLACK_SYMBOLS = {
    ROOK: "車",
    KNIGHT: "馬",
    BISHOP: "象",
    ADVISOR: "士",
    KING: "將",
    CANNON: "砲",
    PAWN: "卒"
}

# 空白交叉点显示符号（半角空格+全角居中点，保证与中文字符等宽）
EMPTY_CELL = "[ ．]"


def render_board_2d(board: Board, perspective: bool = RED) -> str:
    """
    将棋盘渲染为 9列×10行 的 2D 文本矩阵。

    :param board: cchess.Board 实例
    :param perspective: 视角，默认为红方视角（底端为第 0 行，顶端为第 9 行）
    :return: 格式化后的多行纯文本矩阵
    """
    lines = []
    lines.append("当前棋盘空间分布（9列×10行，红方视角）：")
    lines.append("    a   b   c   d   e   f   g   h   i")

    row_range = range(9, -1, -1) if perspective == RED else range(0, 10)

    for row in row_range:
        row_str = f"{row}  "
        cells = []
        for col_idx in range(9):
            sq = square(col_idx, row)
            piece = board.piece_at(sq)
            if piece is None:
                cells.append(EMPTY_CELL)
            else:
                mapping = RED_SYMBOLS if piece.color == RED else BLACK_SYMBOLS
                cells.append(f"[{mapping.get(piece.piece_type, '?')}]")
        row_str += "".join(cells)
        lines.append(row_str)

        # 在第 4 行与第 5 行之间绘制楚河汉界
        if perspective == RED and row == 5:
            lines.append("----------------楚河 汉界----------------")
        elif perspective == BLACK and row == 4:
            lines.append("----------------楚河 汉界----------------")

    return "\n".join(lines)


if __name__ == "__main__":
    b = Board()
    print(render_board_2d(b))
