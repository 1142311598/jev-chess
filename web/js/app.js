/**
 * Jev 中国象棋业务控制逻辑与状态机 (App)
 * 专门面向 TypeSafe Jev 结构化决策模型
 */

document.addEventListener("DOMContentLoaded", () => {
  let boardUI = null;
  let currentState = null;
  let isAiThinking = false;

  // DOM 元素引用
  const elStatusBanner = document.getElementById("status-banner");
  const elPlayerBoxRed = document.getElementById("player-box-red");
  const elPlayerBoxBlack = document.getElementById("player-box-black");
  const elHistoryList = document.getElementById("history-list");
  const elConfidenceText = document.getElementById("confidence-text");
  const elConfidenceFill = document.getElementById("confidence-fill");
  const elProbList = document.getElementById("prob-list");
  const elBtnUndo = document.getElementById("btn-undo");
  const elBtnAiMove = document.getElementById("btn-ai-move");
  const elBtnNewGame = document.getElementById("btn-new-game");
  const elBtnPreview = document.getElementById("btn-preview-prompt");
  const elBtnSettings = document.getElementById("btn-settings");
  const elKeyStatusBadge = document.getElementById("key-status-badge");

  // 模态弹窗相关
  const elModalPreview = document.getElementById("modal-preview");
  const elModalSettings = document.getElementById("modal-settings");
  const elPreviewContent = document.getElementById("preview-content");
  const elInputApiKey = document.getElementById("input-api-key");
  const elInputModel = document.getElementById("input-model");
  const elInputBaseUrl = document.getElementById("input-base-url");
  const elBtnSaveSettings = document.getElementById("btn-save-settings");

  // 初始化棋盘
  boardUI = new BoardUI("chess-board", {
    onMove: async (uci) => {
      await handlePlayerMove(uci);
    }
  });

  // 获取后端配置与初始状态
  initApp();

  async function initApp() {
    try {
      await checkConfig();
      await fetchGameState();
    } catch (e) {
      console.error("Init failed:", e);
      showStatus("后端服务连接失败，请确认服务已启动", "error");
    }
  }

  async function checkConfig() {
    try {
      const res = await fetch("/api/config");
      const json = await res.json();
      if (json.data) {
        const d = json.data;
        if (d.is_configured) {
          elKeyStatusBadge.className = "badge-tag active";
          elKeyStatusBadge.textContent = `Jev 在线 (${d.model})`;
        } else {
          elKeyStatusBadge.className = "badge-tag error";
          elKeyStatusBadge.textContent = "未配置 API Key";
        }
        if (elInputModel) elInputModel.value = d.model || "typesafe/jev-1.13";
        if (elInputBaseUrl) elInputBaseUrl.value = d.base_url || "https://openrouter.ai/api";
      }
    } catch (e) {
      elKeyStatusBadge.className = "badge-tag error";
      elKeyStatusBadge.textContent = "服务离线";
    }
  }

  async function fetchGameState() {
    const res = await fetch("/api/game/state");
    const json = await res.json();
    if (json.data) {
      updateUI(json.data);
    }
  }

  function updateUI(state) {
    currentState = state;
    boardUI.updateState(state);

    // 1. 状态栏更新
    const isRedTurn = state.turn === "red";
    elPlayerBoxRed.classList.toggle("active-turn", isRedTurn);
    elPlayerBoxBlack.classList.toggle("active-turn", !isRedTurn);

    if (state.game_status !== "playing") {
      showStatus(state.status_reason, "check");
      elBtnAiMove.disabled = true;
      elBtnUndo.disabled = false;
    } else if (state.is_check) {
      const whoCheck = isRedTurn ? "红方【被将军】！请应将" : "黑方【被将军】！请应将";
      showStatus(whoCheck, "check");
    } else {
      const turnTxt = isRedTurn ? "轮到红方走棋" : "轮到黑方走棋";
      showStatus(turnTxt);
    }

    // 2. 按钮禁用控制
    elBtnUndo.disabled = isAiThinking || (state.history.length === 0);
    elBtnAiMove.disabled = isAiThinking || (state.game_status !== "playing") || state.is_player_turn;

    // 3. 历史记录更新
    renderHistory(state.history);

    // 4. Jev 决策观测面板更新
    if (state.last_ai_thought) {
      renderAiThought(state.last_ai_thought);
    }
  }

  function showStatus(text, type = "normal") {
    elStatusBanner.textContent = text;
    elStatusBanner.className = "game-status-banner";
    if (type === "check") {
      elStatusBanner.classList.add("check");
    }
  }

  function renderHistory(history) {
    elHistoryList.innerHTML = "";
    if (!history || history.length === 0) {
      elHistoryList.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 10px;">暂无历史着法</div>';
      return;
    }

    for (let i = 0; i < history.length; i += 2) {
      const stepNum = Math.floor(i / 2) + 1;
      const redMove = history[i];
      const blackMove = history[i + 1];

      const row = document.createElement("div");
      row.className = "history-item";
      row.innerHTML = `
        <span class="history-step">${stepNum}.</span>
        <span class="history-red" style="color: #ff9191;">${redMove ? redMove.notation : ""}</span>
        <span class="history-black" style="color: #dfd8cb;">${blackMove ? blackMove.notation : ""}</span>
      `;
      elHistoryList.appendChild(row);
    }
    elHistoryList.scrollTop = elHistoryList.scrollHeight;
  }

  function renderAiThought(thought) {
    if (!thought) return;

    // 置信度
    const confPct = Math.round((thought.confidence || 0) * 100);
    elConfidenceText.textContent = `${confPct}%`;
    elConfidenceFill.style.width = `${confPct}%`;

    // 候选走法概率分布（按概率降序排前 7 项）
    elProbList.innerHTML = "";
    
    let displayList = [];
    if (thought.top_moves && thought.top_moves.length > 0) {
      displayList = thought.top_moves;
    } else {
      const probs = thought.probabilities || {};
      displayList = Object.entries(probs)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 7)
        .map(([uci, prob]) => ({ uci, notation: uci, probability: prob, intention: "" }));
    }

    if (displayList.length === 0) {
      elProbList.innerHTML = '<div style="color: var(--text-secondary);">暂无分布数据</div>';
      return;
    }

    displayList.forEach((item) => {
      const uci = item.uci;
      const notation = item.notation || uci;
      const prob = item.probability || 0;
      const pct = (prob * 100).toFixed(1);
      const isChosen = (uci === thought.uci);
      const intention = item.intention ? ` title="${item.intention.replace(/"/g, '&quot;')}"` : '';

      const el = document.createElement("div");
      el.className = "prob-item";
      el.innerHTML = `
        <div class="prob-meta"${intention} style="cursor: help;">
          <span class="prob-notation" style="${isChosen ? 'color: var(--accent-gold-light); font-weight: bold;' : ''}">
            ${isChosen ? '★ ' : ''}${notation} <span style="font-size: 0.8em; opacity: 0.7;">(${uci})</span>
          </span>
          <span class="prob-pct">${pct}%</span>
        </div>
        <div class="prob-bar-bg">
          <div class="prob-bar-fill" style="width: ${pct}%;"></div>
        </div>
      `;
      elProbList.appendChild(el);
    });
  }

  // 玩家走棋处理
  async function handlePlayerMove(uci) {
    if (isAiThinking) return;

    try {
      const res = await fetch("/api/game/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uci })
      });
      const json = await res.json();
      if (!res.ok) {
        alert(json.detail || "走棋失败");
        return;
      }

      updateUI(json.data.state);

      // 若对弈仍在进行且轮到电脑，自动触发 AI 走子
      if (json.data.state.game_status === "playing" && !json.data.state.is_player_turn) {
        setTimeout(triggerAiMove, 300);
      }
    } catch (e) {
      alert("走棋网络请求失败: " + e.message);
    }
  }

  // 触发 AI 行棋
  async function triggerAiMove() {
    if (isAiThinking) return;
    isAiThinking = true;
    elBtnAiMove.disabled = true;
    elBtnUndo.disabled = true;
    showStatus("Jev 深度决策模型正在全盘扫描中...", "normal");

    // 添加思考中动效
    elConfidenceText.innerHTML = '<span class="ai-thinking-pulse"></span> 思考中';

    try {
      const res = await fetch("/api/game/ai-move", { method: "POST" });
      const json = await res.json();
      if (!res.ok) {
        const errMsg = json.detail ? (json.detail.message || JSON.stringify(json.detail)) : "Jev 请求失败";
        alert("Jev 决策异常: " + errMsg);
        showStatus("Jev 决策失败: " + errMsg, "check");
        return;
      }

      updateUI(json.data.state);
    } catch (e) {
      alert("Jev 走棋网络异常: " + e.message);
      showStatus("网络请求异常", "check");
    } finally {
      isAiThinking = false;
      elBtnAiMove.disabled = false;
      elBtnUndo.disabled = false;
    }
  }

  // 悔棋
  elBtnUndo.addEventListener("click", async () => {
    if (isAiThinking) return;
    try {
      const res = await fetch("/api/game/undo", { method: "POST" });
      const json = await res.json();
      if (!res.ok) {
        alert(json.detail || "悔棋失败");
        return;
      }
      updateUI(json.data);
    } catch (e) {
      alert("悔棋网络请求失败: " + e.message);
    }
  });

  // 让电脑走棋
  elBtnAiMove.addEventListener("click", () => {
    triggerAiMove();
  });

  // 新建对局
  elBtnNewGame.addEventListener("click", async () => {
    if (isAiThinking) return;
    const playColor = confirm("点击【确定】由你执红先行，点击【取消】由 Jev 执红先行。") ? "red" : "black";
    try {
      const res = await fetch("/api/game/new", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_color: playColor })
      });
      const json = await res.json();
      updateUI(json.data);

      // 如果玩家选黑，电脑执红立即走第一步
      if (playColor === "black") {
        setTimeout(triggerAiMove, 300);
      }
    } catch (e) {
      alert("新建对局失败: " + e.message);
    }
  });

  // 实时预览 Prompt
  elBtnPreview.addEventListener("click", async () => {
    try {
      elPreviewContent.textContent = "正在生成当前局面的完整 Jev Prompt 预览...";
      elModalPreview.classList.add("active");
      const res = await fetch("/api/prompt/preview");
      const json = await res.json();
      if (json.data) {
        const text = `=== 1. Jev 原生 Decision Payload ===\n${JSON.stringify(json.data.payload || json.data.jev_payload, null, 2)}\n\n=== 2. 传统纯文本 Prompt 样式 ===\n${json.data.plain_text_prompt}`;
        elPreviewContent.textContent = text;
      }
    } catch (e) {
      elPreviewContent.textContent = "获取预览失败: " + e.message;
    }
  });

  // 打开设置模态框
  elBtnSettings.addEventListener("click", () => {
    elModalSettings.classList.add("active");
  });

  // 保存设置
  elBtnSaveSettings.addEventListener("click", async () => {
    const key = elInputApiKey ? elInputApiKey.value.trim() : "";
    const model = elInputModel ? elInputModel.value.trim() : "";
    const url = elInputBaseUrl ? elInputBaseUrl.value.trim() : "";

    const body = {};
    if (key) body.api_key = key;
    if (model) body.model = model;
    if (url) body.base_url = url;

    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const json = await res.json();
      if (!res.ok) {
        alert("保存失败: " + (json.detail || "未知错误"));
        return;
      }
      alert("Jev 模型配置已保存！");
      elModalSettings.classList.remove("active");
      await checkConfig();
    } catch (e) {
      alert("保存设置网络异常: " + e.message);
    }
  });

  // 关闭模态弹窗
  document.querySelectorAll(".close-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      elModalPreview.classList.remove("active");
      elModalSettings.classList.remove("active");
    });
  });

  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  });
});
