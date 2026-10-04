"""
中国象棋几何特征、大局战略与特级大师杀法雷达引擎 (Feature Extractor)
第一性原理实现：
1. 致命绝杀威胁雷达（Mate Threat Detector，防漏杀/防被杀）；
2. 经典杀法模式识别（马后炮、重炮杀、铁门槛、双车错、卧槽马、闷宫杀）；
3. 双方大子动员度量化统计；
4. 战局阶段定性与大局观全景态势。
"""
from typing import List, Dict, Any, Tuple, Optional, Set
from core.cchess import (
    Board, Move, Piece, RED, BLACK,
    ROOK, KNIGHT, BISHOP, ADVISOR, KING, CANNON, PAWN,
    square, square_column, square_row, square_name, SQUARES, between,
    A0, I0, A9, I9, B0, H0, B9, H9, B2, H2, B7, H7
)

PIECE_NAMES_ZH = {
    (RED, ROOK): "俥", (RED, KNIGHT): "傌", (RED, BISHOP): "相",
    (RED, ADVISOR): "仕", (RED, KING): "帥", (RED, CANNON): "炮", (RED, PAWN): "兵",
    (BLACK, ROOK): "車", (BLACK, KNIGHT): "馬", (BLACK, BISHOP): "象",
    (BLACK, ADVISOR): "士", (BLACK, KING): "將", (BLACK, CANNON): "砲", (BLACK, PAWN): "卒",
}


def get_game_phase(fullmove_number: int) -> Tuple[str, str]:
    """判定当前战局阶段与战略主线"""
    if fullmove_number <= 10:
        return "开局布阵阶段", "争先出动主力大子（特别是大车必须尽早开出）、抢占中路与肋道要津、保持子力互相照应"
    elif fullmove_number <= 30:
        return "中局攻防阶段", "组织车马炮多兵种协同作战、聚焦重点线路突破、严密防守自身弱点"
    else:
        return "残局决胜阶段", "兵贵神速、车马炮残局杀法组合、老帅借道助攻"


def get_development_stats(board: Board) -> Dict[str, Any]:
    """量化统计双方主力大子（车马炮）的出动与动员度"""
    red_home_rooks = [A0, I0]
    red_home_knights = [B0, H0]
    black_home_rooks = [A9, I9]
    black_home_knights = [B9, H9]

    red_moved = 0
    red_sleeping = []
    for sq in red_home_rooks:
        p = board.piece_at(sq)
        if not (p and p.color == RED and p.piece_type == ROOK):
            red_moved += 1
        else:
            red_sleeping.append(f"{square_name(sq)}位俥未开出")

    for sq in red_home_knights:
        p = board.piece_at(sq)
        if not (p and p.color == RED and p.piece_type == KNIGHT):
            red_moved += 1
        else:
            red_sleeping.append(f"{square_name(sq)}位傌未起跳")

    for sq in [B2, H2]:
        p = board.piece_at(sq)
        if not (p and p.color == RED and p.piece_type == CANNON):
            red_moved += 1

    black_moved = 0
    black_sleeping = []
    for sq in black_home_rooks:
        p = board.piece_at(sq)
        if not (p and p.color == BLACK and p.piece_type == ROOK):
            black_moved += 1
        else:
            black_sleeping.append(f"{square_name(sq)}位車未开出")

    for sq in black_home_knights:
        p = board.piece_at(sq)
        if not (p and p.color == BLACK and p.piece_type == KNIGHT):
            black_moved += 1
        else:
            black_sleeping.append(f"{square_name(sq)}位馬未起跳")

    for sq in [B7, H7]:
        p = board.piece_at(sq)
        if not (p and p.color == BLACK and p.piece_type == CANNON):
            black_moved += 1

    return {
        "red_rate": round(red_moved / 6.0 * 100),
        "red_sleeping": red_sleeping,
        "black_rate": round(black_moved / 6.0 * 100),
        "black_sleeping": black_sleeping
    }


def get_tactical_capture_opportunities(board: Board) -> List[str]:
    """实时盘点当前局面己方所有可直接吃子的战术战机"""
    captures = []
    for move in board.legal_moves:
        captured_piece = board.piece_at(move.to_square)
        if captured_piece:
            notation = board.move_to_notation(move)
            cap_name = PIECE_NAMES_ZH.get((captured_piece.color, captured_piece.piece_type), "敌子")
            captures.append(f"{notation}可击吃敌方{square_name(move.to_square)}位{cap_name}")
    return captures


def detect_mate_threats(board: Board) -> Dict[str, Any]:
    """
    【绝杀威胁雷达】
    检测对方下一回合是否存在致命绝杀（Checkmate），并计算己方有哪些着法能化解绝杀。
    """
    my_color = board.turn
    opp_color = not my_color

    # 模拟克隆棋盘并切换到对方轮次
    b_clone = board.copy()
    b_clone.turn = opp_color

    threat_moves = []
    for opp_m in b_clone.legal_moves:
        b_clone.push(opp_m)
        if b_clone.is_checkmate():
            notation = b_clone.move_to_notation(opp_m) if hasattr(b_clone, "move_to_notation") else opp_m.uci()
            threat_moves.append((opp_m.uci(), notation))
        b_clone.pop()

    if not threat_moves:
        return {"has_threat": False, "threat_moves": [], "escape_moves": set()}

    # 若对方有致命绝杀，寻找己方能够成功化解绝杀的“解杀逃生着法”
    escape_moves: Set[str] = set()
    for my_m in board.legal_moves:
        board.push(my_m)
        # 走完 my_m 后，观察对方是否还能一步绝杀
        still_mated = False
        for opp_m in board.legal_moves:
            board.push(opp_m)
            if board.is_checkmate():
                still_mated = True
                board.pop()
                break
            board.pop()

        if not still_mated:
            escape_moves.add(my_m.uci())

        board.pop()

    return {
        "has_threat": True,
        "threat_moves": threat_moves,
        "escape_moves": escape_moves
    }


def identify_mating_pattern(board: Board, move: Move) -> Optional[str]:
    """
    【经典杀法模式识别】
    识别该步棋是否属于马后炮、重炮杀、铁门槛、双车错、卧槽马、闷宫杀等经典杀势。
    """
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)
    if not moving_piece:
        return None

    my_color = moving_piece.color
    opp_color = not my_color

    board.push(move)
    is_mate = board.is_checkmate()
    is_check = board.is_check()

    # 寻找对方将帅位置
    king_sq = None
    opp_king_type = KING
    for sq in SQUARES:
        p = board.piece_at(sq)
        if p and p.color == opp_color and p.piece_type == opp_king_type:
            king_sq = sq
            break

    pattern = None

    if is_mate:
        pattern = "【一招绝杀·对局胜出】"
    elif is_check and king_sq is not None:
        # 1. 检验【马后炮】
        # 移动子是炮，且炮与对方将帅之间唯一的炮架是己方马
        if moving_piece.piece_type == CANNON:
            between_bb = between(to_sq, king_sq)
            occupied_between = [sq for sq in SQUARES if (1 << sq) & between_bb & board.occupied]
            if len(occupied_between) == 1:
                mount_piece = board.piece_at(occupied_between[0])
                if mount_piece and mount_piece.color == my_color and mount_piece.piece_type == KNIGHT:
                    pattern = "【经典杀法·马后炮】"
                elif mount_piece and mount_piece.color == my_color and mount_piece.piece_type == CANNON:
                    pattern = "【经典杀法·重炮杀】"

        # 2. 检验【双车错】
        if not pattern and moving_piece.piece_type == ROOK:
            my_rooks = [sq for sq in SQUARES if board.piece_at(sq) and board.piece_at(sq).color == my_color and board.piece_at(sq).piece_type == ROOK]
            if len(my_rooks) >= 2:
                rows = [square_row(sq) for sq in my_rooks]
                if (my_color == RED and (9 in rows or 8 in rows)) or (my_color == BLACK and (0 in rows or 1 in rows)):
                    pattern = "【经典杀法·双车错】"

        # 3. 检验【铁门槛】
        if not pattern and moving_piece.piece_type == ROOK:
            e_col_cannons = [sq for sq in SQUARES if square_column(sq) == 4 and board.piece_at(sq) and board.piece_at(sq).color == my_color and board.piece_at(sq).piece_type == CANNON]
            if e_col_cannons:
                pattern = "【经典杀法·铁门槛】"

        # 4. 检验【卧槽马 / 挂角马】
        if not pattern and moving_piece.piece_type == KNIGHT:
            to_col = square_column(to_sq)
            to_row = square_row(to_sq)
            if (my_color == RED and to_row in [7, 8] and to_col in [2, 3, 5, 6]) or \
               (my_color == BLACK and to_row in [1, 2] and to_col in [2, 3, 5, 6]):
                pattern = "【经典杀法·卧槽/挂角马】"

        # 5. 检验【闷宫杀】
        if not pattern:
            opp_advisors = [sq for sq in SQUARES if board.piece_at(sq) and board.piece_at(sq).color == opp_color and board.piece_at(sq).piece_type == ADVISOR]
            if len(opp_advisors) == 2:
                pattern = "【经典杀法·闷宫威胁】"

    board.pop()
    return pattern


def describe_position_features(board: Board) -> str:
    """
    生成融入了【绝杀威胁雷达】与【特级大师大局观】的宏观态势看板文本（写入 Jev State）。
    """
    turn_color = board.turn
    turn_zh = "红方" if turn_color == RED else "黑方"
    fullmove = board.fullmove_number
    phase_name, phase_strategy = get_game_phase(fullmove)
    dev_stats = get_development_stats(board)
    capture_ops = get_tactical_capture_opportunities(board)
    mate_radar = detect_mate_threats(board)

    lines = [
        f"【战局大局观与战术雷达】",
        f"- 当前阶段: {phase_name}（第 {fullmove} 回合，轮到{turn_zh}走棋）",
        f"- 战略主线: {phase_strategy}",
        f"- 双方大子动员度对比:",
        f"    * 红方主力动员率: {dev_stats['red_rate']}%" + (f" ({', '.join(dev_stats['red_sleeping'])})" if dev_stats['red_sleeping'] else "（主力大子已全线开动）"),
        f"    * 黑方主力动员率: {dev_stats['black_rate']}%" + (f" ({', '.join(dev_stats['black_sleeping'])})" if dev_stats['black_sleeping'] else "（主力大子已全线开动）"),
        f"- 己方被将军状态: {'【己方正处于将军危急中，必须优先解将！】' if board.is_check() else '否（帅位安稳）'}"
    ]

    # 绝杀雷达警报（生死存亡最高级别）
    if mate_radar["has_threat"]:
        threat_strs = [f"对方下一回合若走 [{t[1] or t[0]}] 将直接绝杀判胜！" for t in mate_radar["threat_moves"][:2]]
        lines.append(f"- 🚨【最高危机·致命绝杀威胁预警】: {' '.join(threat_strs)}")
        if mate_radar["escape_moves"]:
            escape_notations = []
            for uci in list(mate_radar["escape_moves"])[:4]:
                mv = Move.from_uci(uci)
                zh = board.move_to_notation(mv)
                escape_notations.append(f"{zh}")
            lines.append(f"  --> 唯一解杀生路: 全盘仅有 [{', '.join(escape_notations)}] 能够化解绝杀险情，其余走法均将在下回合立即判负！")
        else:
            lines.append("  --> 局面已成绝命杀势，需严密防守拖延！")
    else:
        lines.append("- 防守安全雷达: 当前盘面敌方暂无直接一步绝杀威胁，防线稳健")

    # 吃子战机盘点
    if capture_ops:
        lines.append(f"- 战术吃子战机盘点: 当前盘面存在 {len(capture_ops)} 项直接吃子机会 -> {', '.join(capture_ops[:4])}")
    else:
        lines.append("- 战术吃子战机盘点: 当前双方暂无直接吃子接触，重在空间要道争夺与阵型布防")

    # 中路控制
    e_pieces = [board.piece_at(square(4, r)) for r in range(10)]
    center_cannons = [p for p in e_pieces if p and p.piece_type == CANNON]
    if center_cannons:
        c_owners = ["红中炮" if p.color == RED else "黑中炮" for p in center_cannons]
        lines.append(f"- 中路要塞: {'、'.join(c_owners)}当头压迫中轴")
    else:
        lines.append("- 中路要塞: 双方均未架中炮，中路兵线对峙")

    return "\n".join(lines)


def describe_move_intention(board: Board, move: Move) -> str:
    """
    结合经典杀法识别、绝杀雷达防护与大局战略职能，客观全面生成候选着法语义。
    """
    notation = board.move_to_notation(move)
    from_sq = move.from_square
    to_sq = move.to_square
    moving_piece = board.piece_at(from_sq)
    captured_piece = board.piece_at(to_sq)

    if not moving_piece:
        return notation

    my_color = moving_piece.color
    opp_color = not my_color
    p_name = PIECE_NAMES_ZH.get((my_color, moving_piece.piece_type), "子")

    # 1. 检测是否命中经典杀法（马后炮/双车错/铁门槛/一招绝杀）
    mating_pattern = identify_mating_pattern(board, move)

    # 2. 模拟走棋，观测物理变化
    board.push(move)
    is_check_after = board.is_check()
    under_fire = board.is_attacked_by(opp_color, to_sq)
    defended = board.is_attacked_by(my_color, to_sq)

    attacker_names = []
    if under_fire:
        for a_sq in board.attackers(opp_color, to_sq):
            att_p = board.piece_at(a_sq)
            if att_p:
                attacker_names.append(PIECE_NAMES_ZH.get((att_p.color, att_p.piece_type), square_name(a_sq)))

    defender_names = []
    if defended:
        for d_sq in board.attackers(my_color, to_sq):
            def_p = board.piece_at(d_sq)
            if def_p:
                defender_names.append(PIECE_NAMES_ZH.get((def_p.color, def_p.piece_type), square_name(d_sq)))

    board.pop()

    to_col = square_column(to_sq)
    from_col = square_column(from_sq)
    to_row = square_row(to_sq)
    from_row = square_row(from_sq)
    to_name = square_name(to_sq)

    # 0. 检验是否命中大师经典开局定式
    from core.chess_intuition import match_opening_book, evaluate_move_positional_delta
    opening_desc = match_opening_book(board, move)

    # 设定主要职能标签与基础优先级得分
    priority = 0

    if mating_pattern:
        role_tag = mating_pattern
        if "一招绝杀" in mating_pattern:
            priority += 10000
        else:
            priority += 5000
    elif opening_desc:
        role_tag = opening_desc.split("】")[0] + "】"
        priority += 800
    elif captured_piece:
        role_tag = "【吃子战机】"
        priority += 1200
    elif is_check_after:
        role_tag = "【将军进攻】"
        priority += 600
    else:
        role_tag = "【阵型调动】"

    facts = []

    # 若命中开局定式，插入精妙战略说明
    if opening_desc and not mating_pattern and not captured_piece:
        parts = opening_desc.split(" - ")
        if len(parts) > 1:
            facts.append(parts[1])

    # 吃子与将军事实
    if captured_piece:
        cap_name = PIECE_NAMES_ZH.get((captured_piece.color, captured_piece.piece_type), "敌子")
        facts.append(f"击吃敌方{square_name(to_sq)}位{cap_name}")

    if is_check_after and not mating_pattern:
        facts.append("直接叫将攻击将帅")

    # 3. 几何战略模式识别
    if moving_piece.piece_type == ROOK:
        if ((my_color == RED and from_sq in [A0, I0] and to_row == 1) or
            (my_color == BLACK and from_sq in [A9, I9] and to_row == 8)):
            if not mating_pattern and not opening_desc: role_tag = "【战略起横车】"
            facts.append(f"起横车至{to_name}底二线，激活沉睡大车，准备横移抢占肋道要津")
            priority += 450
        elif to_row in [4, 5]:
            if not mating_pattern and not opening_desc: role_tag = "【直车巡河】"
            facts.append(f"开拔至河沿{to_name}巡河，切断敌方兵卒推进并控制河界")
            priority += 400
        elif to_col in [3, 5]:
            if not mating_pattern and not opening_desc: role_tag = "【车占肋道】"
            facts.append(f"大车挺进肋道{to_name}，瞄准将帅侧翼生命线")
            priority += 420
        elif to_col == 4:
            if not mating_pattern and not opening_desc: role_tag = "【车占中路】"
            facts.append(f"大车进占中轴车道{to_name}，增强中央突破力")
            priority += 380
        else:
            facts.append(f"开动大车至{to_name}")

    elif moving_piece.piece_type == CANNON:
        if to_col == 4 and from_col != 4:
            if not mating_pattern and not opening_desc: role_tag = "【当头炮控中】"
            facts.append("架中炮进驻e路中心，正对敌方中卒实施战略压迫")
            priority += 500
        elif to_row in [4, 5]:
            if not mating_pattern and not opening_desc: role_tag = "【巡河炮控场】"
            facts.append(f"运炮至河界{to_name}，封锁对岸子力开拔")
            priority += 350
        elif from_col == 4 and to_col != 4:
            if not mating_pattern and not opening_desc: role_tag = "【中炮转移】"
            facts.append(f"从中路转移至{to_name}展开侧翼配合")
        elif to_row in [0, 9] and from_row not in [0, 9]:
            facts.append(f"下沉至底线{to_name}")
        else:
            facts.append(f"移炮至{to_name}")

    elif moving_piece.piece_type == KNIGHT:
        if to_col in [2, 6] and to_row in [2, 7]:
            if not mating_pattern and not opening_desc: role_tag = "【屏风正马】"
            facts.append(f"跃正马进驻{to_name}枢纽，护卫中兵并通畅后方车路")
            priority += 420
        elif to_col in [0, 8]:
            if not mating_pattern and not opening_desc: role_tag = "【边马出动】"
            facts.append(f"跃边马至{to_name}避让中路拥塞，护卫边线")
            priority += 150
        elif ((my_color == RED and to_row in [7, 8] and to_col in [2, 6]) or
              (my_color == BLACK and to_row in [1, 2] and to_col in [2, 6])):
            if not mating_pattern: role_tag = "【挂角/卧槽马】"
            facts.append(f"深入九宫侧翼{to_name}，直接威胁九宫核心要害")
            priority += 800
        elif to_row in [4, 5]:
            if not mating_pattern and not opening_desc: role_tag = "【巡河马】"
            facts.append(f"进逼河沿{to_name}争夺制河权")
            priority += 300
        else:
            facts.append(f"跃马至{to_name}")

    elif moving_piece.piece_type == PAWN:
        if (my_color == RED and to_row >= 5) or (my_color == BLACK and to_row <= 4):
            if not mating_pattern and not opening_desc: role_tag = "【过河卒压迫】"
            facts.append(f"过河兵卒前推至{to_name}，压迫敌方防线")
            priority += 400
        elif to_col in [2, 6]:
            if not mating_pattern and not opening_desc: role_tag = "【挺兵通马】"
            facts.append("挺3/7路兵解除马脚羁绊，激活相马联动协同")
            priority += 350
        elif to_col == 4:
            if not mating_pattern and not opening_desc: role_tag = "【挺中兵】"
            facts.append("挺进中兵强化中路阵型厚度")
            priority += 250
        else:
            facts.append(f"挺兵至{to_name}")

    elif moving_piece.piece_type == BISHOP:
        if to_col == 4:
            if not mating_pattern and not opening_desc: role_tag = "【飞相连环】"
            facts.append("飞相进中构筑双相连环屏障，强化中防")
            priority += 300
        else:
            if not mating_pattern and not opening_desc: role_tag = "【边相调整】"
            facts.append(f"调相至边路{to_name}")

    elif moving_piece.piece_type == ADVISOR:
        if not mating_pattern and not opening_desc: role_tag = "【补士安内】"
        facts.append("九宫补士稳固将帅安全防线")
        priority += 200

    elif moving_piece.piece_type == KING:
        if not mating_pattern: role_tag = "【将帅避让】"
        facts.append("将帅九宫内走位规避风险")

    # 4. 落点安危与照应客观事实
    security_facts = []
    if defender_names:
        unique_defs = list(dict.fromkeys(defender_names))[:2]
        security_facts.append(f"受己方{'、'.join(unique_defs)}看护")
    else:
        security_facts.append("落点暂无己方子力看护")
        priority -= 15

    if under_fire:
        unique_atts = list(dict.fromkeys(attacker_names))[:2]
        security_facts.append(f"在敌方{'、'.join(unique_atts)}火力线下")
        priority -= 40

    # 5. 计算子力位置势能变动
    delta, pst_desc = evaluate_move_positional_delta(board, move)
    priority += delta

    desc_text = "，".join(facts)
    if security_facts:
        desc_text += f"（{'；'.join(security_facts)}）"
    if pst_desc:
        desc_text += f" {pst_desc}"

    full_desc = f"{role_tag} {notation} - {desc_text}"
    return full_desc, priority


if __name__ == "__main__":
    b = Board()
    print("=== 全景战略态势 ===")
    print(describe_position_features(b))
    print("\n=== 部分着法战术职能样例 ===")
    for m in list(b.legal_moves)[:10]:
        print(describe_move_intention(b, m))
