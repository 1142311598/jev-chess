"""
Jev 决策模型客户端
基于 OpenRouter / TypeSafe Decisions API 实现中国象棋走法选择。
严格遵循用户要求：
1. 必须配置 API Key，不要兜底；
2. 将当前局面的全部合法选项完整发送给 Jev，不筛选。
"""
import os
import time
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

from core.cchess import Board, Move, RED, BLACK
from core.board_renderer import render_board_2d
from core.feature_extractor import describe_position_features, describe_move_intention

load_dotenv()


class JevAPIError(Exception):
    """Jev API 调用异常，包含明确的错误原因与解决指引"""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class JevClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        # 优先读取传入参数，其次读取环境变量
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("TYPESAFE_API_KEY")
        self.model = model or os.getenv("TYPESAFE_MODEL", "typesafe/jev-1.13")
        self.base_url = (base_url or os.getenv("TYPESAFE_BASE_URL", "https://openrouter.ai/api")).rstrip("/")
        # 持久长连接会话（复用 TCP/TLS 握手与连接池）
        self.client = httpx.Client(
            timeout=httpx.Timeout(connect=15.0, read=45.0, write=15.0, pool=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            trust_env=True
        )

    def is_configured(self) -> bool:
        """检查 API Key 是否已配置"""
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"))

    def build_decision_payload(self, board: Board, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        构建发送给 Jev 的完整状态（State）与问题定义（Questions）。
        全部合法选项均完整作为 criteria 传入，并按特级大师棋感与战略优先级智能降序排列（高质量走法排在前列）。
        """
        turn_zh = "红方" if board.turn == RED else "黑方"
        fen = board.fen()
        board_2d = render_board_2d(board, perspective=RED)
        features_desc = describe_position_features(board)

        # 整理近期对弈脉络（连贯性感知）
        history_summary = ""
        if history:
            recent_moves = history[-3:]
            move_descs = []
            for h in recent_moves:
                side = "红方" if h.get("turn") == "red" else "黑方"
                notation = h.get("notation", h.get("uci", ""))
                move_descs.append(f"{side}{notation}")
            history_summary = f"- 近期对战交锋脉络: {' -> '.join(move_descs)}\n"

        # 组织 State 文本
        state_text = f"""【中国象棋对弈棋局】
当前执子走棋方: {turn_zh}
当前棋局 FEN: {fen}

{board_2d}

局面核心态势:
{features_desc}
{history_summary}"""

        # 组织全部合法选项的 Criteria
        # 严格按照要求：全部合法走法发给 Jev，不进行任何剔除或截断
        # 第一性原理：按棋感优先度进行高质量降序排序，引导注意力优先考量正招与杀法
        candidate_moves = []
        for move in board.legal_moves:
            uci = move.uci()
            full_desc, priority = describe_move_intention(board, move)
            candidate_moves.append((uci, full_desc, priority))

        # 按特级大师棋感与战略优先级降序排序（高价值走法自然排列在最前面，但全部走法完整保留）
        candidate_moves.sort(key=lambda x: x[2], reverse=True)

        criteria: Dict[str, str] = {uci: desc for uci, desc, _ in candidate_moves}

        instructions = (
            "你是一名深谙棋理与大局战略的中国象棋特级大师。请根据当前 2D 棋盘空间结构与大局观全景态势，遵循特级大师四层思维链自主决断："
            "1. 绝杀生死第一：若盘面出现【一招绝杀·对局胜出】或标有【经典杀法】（如马后炮、重炮杀、铁门槛、双车错）的致胜招法，必须毫不犹豫予以执行；若 State 出现【🚨 致命绝杀威胁】，必须优先选择能够化解绝杀险情的解杀生路，严禁走无用虚步自寻死路；"
            "2. 战机敏感：密切注视盘面【吃子战机】，若有可消灭敌方大子或破坏敌方关键子力的良机，务必优先权衡；"
            "3. 大局争先：根据战局阶段与大子动员度，开局阶段【大师谱招】、【战略起横车】、【屏风正马】、【当头炮控中】、【挺兵通马】等大子动员招法具有极高战略价值，切莫任由大车在底线沉睡；"
            "4. 攻守平衡：谨慎涉足在敌方火力线下且无自身掩护的孤立险地，确保子力协同有根。"
            "请通盘权衡全局战略与战术得失，从上述全部候选合法走法中，选出你认为最合理、最具长远杀伤力与胜率的一项最佳走法。"
        )

        payload = {
            "model": self.model,
            "state": state_text,
            "questions": {
                "next_move": {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": criteria
                }
            }
        }
        return payload

    def decide_move(self, board: Board, history: Optional[List[Dict[str, Any]]] = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        调用 Jev 模型决定下一步走棋。
        采用指数退避重试（1s -> 2s -> 4s）自动应对跨境网络抖动和 Connection Reset。
        返回包含最佳着法、置信度、全部走法概率分布及调试信息的字典。
        """
        if not self.is_configured():
            raise JevAPIError(
                "未配置有效 API Key！请在项目 .env 文件中设置 OPENROUTER_API_KEY（或 TYPESAFE_API_KEY）。"
            )

        legal_moves_list = list(board.legal_moves)
        if not legal_moves_list:
            raise JevAPIError("当前盘面无合法走法（已分胜负或困毙）。")

        payload = self.build_decision_payload(board, history=history)
        endpoint = f"{self.base_url}/v1/systemone"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jev-chess",
            "X-Title": "Jev Chinese Chess"
        }

        retry_delays = [1.0, 2.0, 4.0]
        last_exception = None
        response = None
        start_time = time.time()

        for attempt in range(max_retries + 1):
            try:
                response = self.client.post(endpoint, json=payload, headers=headers)
                # 若遇到服务端 502/503/504 瞬时故障，也触发重试
                if response.status_code in [502, 503, 504] and attempt < max_retries:
                    delay = retry_delays[attempt]
                    print(f"[JevClient] OpenRouter 返回临时状态码 {response.status_code}，将在 {delay} 秒后进行第 {attempt + 1}/{max_retries} 次重试...")
                    time.sleep(delay)
                    continue
                break
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.NetworkError, ConnectionResetError) as e:
                last_exception = e
                if attempt < max_retries:
                    delay = retry_delays[attempt]
                    print(f"[JevClient] 请求遇到网络抖动 ({type(e).__name__}: {str(e)})，将在 {delay} 秒后进行第 {attempt + 1}/{max_retries} 次重试...")
                    time.sleep(delay)
                else:
                    print(f"[JevClient] 连续重试 {max_retries} 次后依然发生网络异常。")
                    break
            except Exception as e:
                last_exception = e
                break

        cost_time = round(time.time() - start_time, 3)

        if response is None:
            raise JevAPIError(f"请求 OpenRouter 发生网络异常 (已自动重试 {max_retries} 次): {str(last_exception)}")

        if response.status_code != 200:
            err_msg = f"Jev 模型请求返回状态码 {response.status_code}"
            try:
                err_json = response.json()
                if "error" in err_json:
                    err_msg += f": {err_json['error'].get('message', err_json['error'])}"
                elif "message" in err_json:
                    err_msg += f": {err_json['message']}"
            except Exception:
                err_msg += f": {response.text[:200]}"

            if response.status_code == 402:
                err_msg = "OpenRouter 账户余额不足 (402 Insufficient credits)，请前往 openrouter.ai/settings/credits 充值后继续对弈。"
            elif response.status_code == 401:
                err_msg = "OpenRouter API Key 无效或未授权 (401 Unauthorized)，请检查 .env 中的 Key 配置。"

            raise JevAPIError(err_msg, status_code=response.status_code)

        try:
            res_data = response.json()
            # 兼容 OpenRouter 的 systemone / decisions 响应格式
            answers = res_data.get("answers", {})
            next_move_ans = answers.get("next_move", {})
            best_uci = next_move_ans.get("choice")
            probabilities = next_move_ans.get("probabilities", {})
            confidence = next_move_ans.get("confidence", 0.0)
            usage = res_data.get("usage", {})

            if not best_uci:
                # 尝试从选择字典中兜底找概率最高者
                if probabilities:
                    best_uci = max(probabilities.items(), key=lambda x: x[1])[0]
                else:
                    raise ValueError(f"响应中未找到有效的 choice 或 probabilities: {res_data}")

            # 校验最佳走法是否确实是合法走法
            valid_ucis = {m.uci() for m in legal_moves_list}
            if best_uci not in valid_ucis:
                raise ValueError(f"Jev 模型返回的着法 {best_uci} 不在当前合法着法列表中！")

            best_move = Move.from_uci(best_uci)
            best_notation = board.move_to_notation(best_move)

            # 丰富 Top 候选着法的中文记谱与意图，便于前端可视化直观展示特级大师思维分布
            top_moves = []
            criteria_dict = payload["questions"]["next_move"]["criteria"]
            for u, p in sorted(probabilities.items(), key=lambda x: x[1], reverse=True)[:7]:
                try:
                    mv = Move.from_uci(u)
                    notat = board.move_to_notation(mv)
                except Exception:
                    notat = u
                top_moves.append({
                    "uci": u,
                    "notation": notat,
                    "probability": p,
                    "intention": criteria_dict.get(u, "")
                })

            return {
                "uci": best_uci,
                "notation": best_notation,
                "confidence": confidence,
                "probabilities": probabilities,
                "top_moves": top_moves,
                "cost_time": cost_time,
                "usage": usage,
                "model": res_data.get("model", self.model),
                "state_preview": payload["state"],
                "criteria_count": len(payload["questions"]["next_move"]["criteria"])
            }
        except Exception as e:
            raise JevAPIError(f"解析 Jev 模型响应失败: {str(e)}", details=response.text)


if __name__ == "__main__":
    client = JevClient()
    b = Board()
    print("API Key 配置状态:", client.is_configured())
    payload = client.build_decision_payload(b)
    print("State 字符长度:", len(payload["state"]))
    print("全部合法走法数量 (Criteria count):", len(payload["questions"]["next_move"]["criteria"]))
    print("部分 Criteria 样例:")
    for k in list(payload["questions"]["next_move"]["criteria"].keys())[:5]:
        print(f"  {k}: {payload['questions']['next_move']['criteria'][k]}")
