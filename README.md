# Jev Chinese Chess

基于Jev模型的中国象棋人机对弈系统。用Jev和你下象棋！

---

## 快速启动

### 1. 克隆与安装依赖
```bash
git clone https://github.com/1142311598/jev-chess.git
cd jev-chess

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置密钥
从示例创建配置：
```bash
cp .env.example .env
```
编辑 `.env` 文件，填入你的 OpenRouter API Key：
```ini
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
TYPESAFE_MODEL=typesafe/jev-1.13
TYPESAFE_BASE_URL=https://openrouter.ai/api
HOST=0.0.0.0
PORT=8000
```

### 3. 启动并对弈
```bash
PYTHONPATH=. python main.py
```
在浏览器打开 **http://localhost:8000** 即可开始对弈。

---

## 工作原理

1. **结构化选择**：
   - 传统生成式大模型下棋经常走出违规着法或解析失败；
   - 本项目使用 Jev 的 `Choice` 原语，后端使用 `cchess` 规则库计算当前局面全部合法走法（如开局 44 种），由 Jev 对每个合法选项打分，模型只能在合法走法中做决策，保证 100% 规则合规。

2. **盘面感知与态势输入**：
   - **2D 字符网格**：将棋盘排布为 9×10 文本矩阵（带楚河汉界），直接提供空间几何信息；
   - **中文记谱映射**：将 UCI 坐标（如 `h2e2`）映射为中文四字记谱法（如 `炮二平五`）；
   - **位置势能与排序**：内置经典开局谱库与子力位置势能表（PST），走法按质量降序传给 Jev（保留全部选项，不裁剪）；
   - **绝杀威胁检测**：检测对手下一回合是否存在直接将死威胁，优先探查解杀走法。

3. **决策可视化**：
   - 网页右侧实时展示 Jev 的置信度与 Top 候选走法概率分布柱状图；
   - 支持在界面一键预览发送给 Jev 的完整 Prompt / Payload。

---

## 目录结构

```text
jev-chess/
├── core/
│   ├── cchess/              # 纯 Python 象棋规则引擎
│   ├── board_renderer.py    # 2D 文本棋盘渲染
│   ├── chess_intuition.py   # 开局谱库与子力位置势能表 (PST)
│   ├── feature_extractor.py # 绝杀威胁检测与战术特征
│   ├── jev_client.py        # Jev API 客户端 (含连接池与重试)
│   └── game_manager.py      # 对局状态机与悔棋逻辑
├── api/                     # FastAPI 路由与模型定义
├── web/                     # 前端单页应用 (纯矢量 SVG 棋盘)
├── tests/                   # 自动化测试
├── main.py                  # 服务启动入口
├── requirements.txt         # 依赖清单
└── .env.example             # 环境变量模板
```

---

## 常用命令

- **运行测试**：`PYTHONPATH=. pytest tests/`
- **实时查看 Jev Prompt**：浏览器访问 `http://localhost:8000/api/prompt/preview`

## License
[MIT](LICENSE)
