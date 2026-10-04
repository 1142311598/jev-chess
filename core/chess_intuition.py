"""
中国象棋特级大师棋感引擎 (Chess Intuition Engine)
第一性原理实现：
1. 大师经典开局谱库（Opening Book / 定式识别）；
2. 子力位置势能评估矩阵（Piece-Square Tables，PST）；
3. 棋感质量与战略价值智能排序（使高质量正招自然置顶）；
4. 行棋连贯性与战略脉络衔接。
"""
from typing import Dict, Any, List, Optional, Tuple
from core.cchess import (
    Board, Move, Piece, RED, BLACK,
    ROOK, KNIGHT, BISHOP, ADVISOR, KING, CANNON, PAWN,
    square, square_column, square_row, square_name, SQUARES
)

# ==========================================
# 1. 经典大师开局谱库 (Opening Book)
# ==========================================
OPENING_BOOK_RED = {
    "h2e2": "【大师谱招·中炮局】炮二平五 - 象棋首选进攻正招，进驻中轴e路威慑中卒",
    "b2e2": "【大师谱招·中炮局】炮八平五 - 另路中炮进占中心要津，压迫敌方中防",
    "c3c4": "【大师谱招·仙人指路】兵七进一 - 投石问路经典正招，率先活通相马通路",
    "g3g4": "【大师谱招·仙人指路】兵三进一 - 挺三路兵活马，稳健试探求进",
    "b0c2": "【大师谱招·起马局】傌八进七 - 稳健布阵正马开局，进可攻退可守",
    "h0g2": "【大师谱招·起马局】傌二进三 - 屏风正马开局，先固中防",
    "g0e2": "【大师谱招·飞相局】相三进五 - 稳健防守反击，防线严密厚重",
    "c0e2": "【大师谱招·飞相局】相七进五 - 飞相局布阵，阵型完整内敛"
}

OPENING_BOOK_BLACK_VS_CENTRAL_CANNON = {
    "b9c7": "【大师谱招·屏风马迎战】馬8进7 - 经典屏风马正招，巩固中防且通畅右车",
    "h9g7": "【大师谱招·屏风马迎战】馬2进3 - 屏风马稳固防守，护卫中卒",
    "h7e7": "【大师谱招·顺手炮对攻】砲2平5 - 顺手炮以攻对攻，争夺中路对冲",
    "b7e7": "【大师谱招·列手炮搏杀】砲8平5 - 列手炮激烈争锋，主动挑起对攻",
    "c6c5": "【大师谱招·卒底炮准备】卒7进1 - 挺卒活通马路，制约红兵推进",
    "g6g5": "【大师谱招·卒底炮准备】卒3进1 - 挺卒活通马路，两翼舒展"
}

# ==========================================
# 2. 子力位置势能表 (Piece-Square Tables / PST)
# 90 个格子的绝对位置体感评分（红方视角：0在下，9在上）
# ==========================================

# 兵/卒位置势能表 (过河兵价值陡增，逼近九宫最具杀伤力)
PST_PAWN_RED = [
     0,  0,  0,  0,  0,  0,  0,  0,  0, # 0行
     0,  0,  0,  0,  0,  0,  0,  0,  0, # 1行
     0,  0,  0,  0,  0,  0,  0,  0,  0, # 2行
     0,  0,  8,  0, 15,  0,  8,  0,  0, # 3行 (兵位)
     5, 10, 15, 20, 25, 20, 15, 10,  5, # 4行 (河界沿)
    25, 35, 45, 55, 60, 55, 45, 35, 25, # 5行 (过河)
    40, 50, 65, 75, 80, 75, 65, 50, 40, # 6行 (进逼)
    50, 65, 80, 90, 95, 90, 80, 65, 50, # 7行 (压迫九宫)
    40, 55, 70, 80, 85, 80, 70, 55, 40, # 8行
    20, 30, 40, 50, 55, 50, 40, 30, 20  # 9行 (底线老兵微退)
]

# 马位置势能表 (窝心极度危险负分，正马高分，卧槽极高分)
PST_KNIGHT_RED = [
     0, -5,  5,  0,  0,  0,  5, -5,  0, # 0行 (底线马)
     0,  5, 10, 15, 10, 15, 10,  5,  0, # 1行
    10, 20, 35, 25,-40, 25, 35, 20, 10, # 2行 (c2/g2正马+35，e2窝心-40)
    15, 25, 35, 40, 35, 40, 35, 25, 15, # 3行
    20, 35, 45, 50, 45, 50, 45, 35, 20, # 4行 (巡河)
    25, 40, 50, 55, 50, 55, 50, 40, 25, # 5行
    30, 45, 60, 65, 55, 65, 60, 45, 30, # 6行
    35, 55, 75, 70, 60, 70, 75, 55, 35, # 7行 (卧槽/挂角 +75)
    25, 40, 60, 65, 50, 65, 60, 40, 25, # 8行
    10, 20, 30, 35, 30, 35, 30, 20, 10  # 9行
]

# 车位置势能表 (底线未动为0，起横车+25，肋道+45，巡河+40)
PST_ROOK_RED = [
     0, 15, 15, 25, 20, 25, 15, 15,  0, # 0行 (原位角车0分)
    25, 30, 35, 45, 40, 45, 35, 30, 25, # 1行 (起横车+25，肋道+45)
    20, 25, 30, 40, 35, 40, 30, 25, 20, # 2行
    25, 30, 35, 45, 40, 45, 35, 30, 25, # 3行
    35, 40, 45, 55, 50, 55, 45, 40, 35, # 4行 (巡河)
    40, 45, 50, 60, 55, 60, 50, 45, 40, # 5行 (骑河)
    45, 50, 55, 65, 60, 65, 55, 50, 45, # 6行
    50, 55, 60, 70, 65, 70, 60, 55, 50, # 7行
    55, 60, 65, 75, 70, 75, 65, 60, 55, # 8行
    50, 55, 60, 70, 65, 70, 60, 55, 50  # 9行 (沉底破宫)
]

# 炮位置势能表 (当头炮+35，巡河+30，卡马脚负分)
PST_CANNON_RED = [
     5,  5,  5, 15, 20, 15,  5,  5,  5, # 0行
     0,  5, 10, 20, 25, 20, 10,  5,  0, # 1行
     5, 15, 10, 25, 40, 25, 10, 15,  5, # 2行 (e2当头炮 +40)
    10, 20, 15, 25, 35, 25, 15, 20, 10, # 3行
    25, 30, 35, 40, 45, 40, 35, 30, 25, # 4行 (巡河炮)
    25, 30, 35, 40, 45, 40, 35, 30, 25, # 5行
    20, 25, 30, 35, 40, 35, 30, 25, 20, # 6行
    15, 20, 25, 30, 35, 30, 25, 20, 15, # 7行
    10, 15, 20, 25, 30, 25, 20, 15, 10, # 8行
    20, 25, 30, 35, 40, 35, 30, 25, 20  # 9行 (沉底重炮)
]


# 子力基础价值（分值参考：车90，炮45，马40，象/仕20，兵15）
PIECE_BASE_VALUES = {
    ROOK: 90,
    CANNON: 45,
    KNIGHT: 40,
    BISHOP: 20,
    ADVISOR: 20,
    PAWN: 15,
    KING: 1000
}


def mirror_square(sq: int) -> int:
    """垂直镜像翻转格子（用于黑方势能查表）"""
    col = square_column(sq)
    row = square_row(sq)
    return square(col, 9 - row)


def evaluate_move_positional_delta(board: Board, move: Move) -> Tuple[int, str]:
    """
    计算该步走法带来的【位置势能变动】（Positional Delta）。
    返回势能得分变动值以及客观评定描述。
    """
    from_sq = move.from_square
    to_sq = move.to_square
    piece = board.piece_at(from_sq)
    if not piece:
        return 0, ""

    is_red = (piece.color == RED)
    pt = piece.piece_type

    # 查表索引（黑方转为镜像坐标）
    idx_from = from_sq if is_red else mirror_square(from_sq)
    idx_to = to_sq if is_red else mirror_square(to_sq)

    delta = 0
    if pt == PAWN:
        delta = PST_PAWN_RED[idx_to] - PST_PAWN_RED[idx_from]
    elif pt == KNIGHT:
        delta = PST_KNIGHT_RED[idx_to] - PST_KNIGHT_RED[idx_from]
    elif pt == ROOK:
        delta = PST_ROOK_RED[idx_to] - PST_ROOK_RED[idx_from]
    elif pt == CANNON:
        delta = PST_CANNON_RED[idx_to] - PST_CANNON_RED[idx_from]

    # 吃子基础收益加成
    captured = board.piece_at(to_sq)
    if captured:
        cap_val = PIECE_BASE_VALUES.get(captured.piece_type, 15)
        delta += cap_val

    # 格式化客观势能评价
    if delta >= 30:
        desc = f"[局势势能大幅跃升: +{delta}]"
    elif delta >= 15:
        desc = f"[局势势能稳步增强: +{delta}]"
    elif delta >= 5:
        desc = f"[局势势能略有增益: +{delta}]"
    elif delta <= -25:
        desc = f"[局势势能明显受损: {delta}]"
    elif delta <= -10:
        desc = f"[局势势能有所退步: {delta}]"
    else:
        desc = "[局势势能平稳微调]"

    return delta, desc


def match_opening_book(board: Board, move: Move) -> Optional[str]:
    """
    匹配中国象棋大师经典开局定式。
    """
    if board.fullmove_number > 3:
        return None

    uci = move.uci()
    if board.turn == RED:
        return OPENING_BOOK_RED.get(uci)
    else:
        # 黑方应对（根据红方中路是否有炮）
        e_pieces = [board.piece_at(square(4, r)) for r in range(10)]
        has_red_cannon = any(p and p.color == RED and p.piece_type == CANNON for p in e_pieces)
        if has_red_cannon and uci in OPENING_BOOK_BLACK_VS_CENTRAL_CANNON:
            return OPENING_BOOK_BLACK_VS_CENTRAL_CANNON[uci]

    return None
