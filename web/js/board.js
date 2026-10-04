/**
 * 中国象棋前端渲染与交互引擎 (BoardUI)
 * 基于纯矢量 SVG 与高精度几何映射实现。
 */

class BoardUI {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = Object.assign({
      onMove: (uci) => console.log("Move executed:", uci),
      perspective: "red" // "red" 或 "black"
    }, options);

    this.selectedSq = null;
    this.legalMovesMap = {};
    this.boardState = null;
    this.piecesLayer = null;
    this.svgLayer = null;

    this.initLayout();
  }

  initLayout() {
    this.container.innerHTML = "";
    
    // 1. 创建 SVG 网格层
    this.svgLayer = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.svgLayer.setAttribute("class", "board-grid-svg");
    this.container.appendChild(this.svgLayer);

    // 2. 创建棋子与覆盖标记层
    this.piecesLayer = document.createElement("div");
    this.piecesLayer.className = "board-pieces-layer";
    this.container.appendChild(this.piecesLayer);

    // 绘制棋盘几何底图
    this.renderGridSvg();

    // 监听窗口尺寸变化自动重绘
    window.addEventListener("resize", () => {
      this.renderGridSvg();
      if (this.boardState) {
        this.renderPieces();
      }
    });
  }

  getMetrics() {
    const rect = this.container.getBoundingClientRect();
    const width = rect.width || 540;
    const height = rect.height || 600;
    const padX = width * 0.07;
    const padY = height * 0.065;
    const stepX = (width - 2 * padX) / 8;
    const stepY = (height - 2 * padY) / 9;
    return { width, height, padX, padY, stepX, stepY };
  }

  getPos(col, row) {
    const { width, height, padX, padY, stepX, stepY } = this.getMetrics();
    if (this.options.perspective === "red") {
      const x = padX + col * stepX;
      const y = height - padY - row * stepY;
      return { x, y };
    } else {
      const x = width - padX - col * stepX;
      const y = padY + row * stepY;
      return { x, y };
    }
  }

  sqToColRow(sqName) {
    const colNames = ["a", "b", "c", "d", "e", "f", "g", "h", "i"];
    const col = colNames.indexOf(sqName[0]);
    const row = parseInt(sqName[1], 10);
    return { col, row };
  }

  colRowToSq(col, row) {
    const colNames = ["a", "b", "c", "d", "e", "f", "g", "h", "i"];
    return `${colNames[col]}${row}`;
  }

  renderGridSvg() {
    const { width, height, padX, padY, stepX, stepY } = this.getMetrics();
    this.svgLayer.setAttribute("viewBox", `0 0 ${width} ${height}`);
    this.svgLayer.innerHTML = "";

    const lineColor = "#5a3a14";
    const lineWidth = 1.6;

    // 1. 外边框 (双重边线)
    const rectOuter = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rectOuter.setAttribute("x", padX - 8);
    rectOuter.setAttribute("y", padY - 8);
    rectOuter.setAttribute("width", stepX * 8 + 16);
    rectOuter.setAttribute("height", stepY * 9 + 16);
    rectOuter.setAttribute("fill", "none");
    rectOuter.setAttribute("stroke", lineColor);
    rectOuter.setAttribute("stroke-width", "3");
    this.svgLayer.appendChild(rectOuter);

    // 2. 10 条横线
    for (let r = 0; r < 10; r++) {
      const p1 = this.getPos(0, r);
      const p2 = this.getPos(8, r);
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", p1.x);
      line.setAttribute("y1", p1.y);
      line.setAttribute("x2", p2.x);
      line.setAttribute("y2", p2.y);
      line.setAttribute("stroke", lineColor);
      line.setAttribute("stroke-width", lineWidth);
      this.svgLayer.appendChild(line);
    }

    // 3. 9 条竖线（注意：中路楚河汉界 4~5 行断开，两边 0 与 8 穿通）
    for (let c = 0; c < 9; c++) {
      if (c === 0 || c === 8) {
        const p1 = this.getPos(c, 0);
        const p2 = this.getPos(c, 9);
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", p1.x);
        line.setAttribute("y1", p1.y);
        line.setAttribute("x2", p2.x);
        line.setAttribute("y2", p2.y);
        line.setAttribute("stroke", lineColor);
        line.setAttribute("stroke-width", lineWidth);
        this.svgLayer.appendChild(line);
      } else {
        // 下半场 (0~4)
        const pBot1 = this.getPos(c, 0);
        const pBot2 = this.getPos(c, 4);
        const lineBot = document.createElementNS("http://www.w3.org/2000/svg", "line");
        lineBot.setAttribute("x1", pBot1.x);
        lineBot.setAttribute("y1", pBot1.y);
        lineBot.setAttribute("x2", pBot2.x);
        lineBot.setAttribute("y2", pBot2.y);
        lineBot.setAttribute("stroke", lineColor);
        lineBot.setAttribute("stroke-width", lineWidth);
        this.svgLayer.appendChild(lineBot);

        // 上半场 (5~9)
        const pTop1 = this.getPos(c, 5);
        const pTop2 = this.getPos(c, 9);
        const lineTop = document.createElementNS("http://www.w3.org/2000/svg", "line");
        lineTop.setAttribute("x1", pTop1.x);
        lineTop.setAttribute("y1", pTop1.y);
        lineTop.setAttribute("x2", pTop2.x);
        lineTop.setAttribute("y2", pTop2.y);
        lineTop.setAttribute("stroke", lineColor);
        lineTop.setAttribute("stroke-width", lineWidth);
        this.svgLayer.appendChild(lineTop);
      }
    }

    // 4. 九宫斜线
    const drawX = (c1, r1, c2, r2) => {
      const p1 = this.getPos(c1, r1);
      const p2 = this.getPos(c2, r2);
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", p1.x);
      line.setAttribute("y1", p1.y);
      line.setAttribute("x2", p2.x);
      line.setAttribute("y2", p2.y);
      line.setAttribute("stroke", lineColor);
      line.setAttribute("stroke-width", lineWidth);
      this.svgLayer.appendChild(line);
    };

    // 红九宫 (d0~f2)
    drawX(3, 0, 5, 2);
    drawX(5, 0, 3, 2);
    // 黑九宫 (d7~f9)
    drawX(3, 7, 5, 9);
    drawX(5, 7, 3, 9);

    // 5. 楚河汉界大字
    const pCenterRed = this.getPos(2, 4.5);
    const pCenterBlack = this.getPos(6, 4.5);

    const textRed = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textRed.setAttribute("x", pCenterRed.x);
    textRed.setAttribute("y", pCenterRed.y + 6);
    textRed.setAttribute("text-anchor", "middle");
    textRed.setAttribute("font-size", stepY * 0.44);
    textRed.setAttribute("fill", "#68451c");
    textRed.setAttribute("font-family", "Kaiti, STKaiti, SimSun, serif");
    textRed.setAttribute("letter-spacing", "8px");
    textRed.textContent = "楚  河";
    this.svgLayer.appendChild(textRed);

    const textBlack = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textBlack.setAttribute("x", pCenterBlack.x);
    textBlack.setAttribute("y", pCenterBlack.y + 6);
    textBlack.setAttribute("text-anchor", "middle");
    textBlack.setAttribute("font-size", stepY * 0.44);
    textBlack.setAttribute("fill", "#68451c");
    textBlack.setAttribute("font-family", "Kaiti, STKaiti, SimSun, serif");
    textBlack.setAttribute("letter-spacing", "8px");
    textBlack.textContent = "漢  界";
    this.svgLayer.appendChild(textBlack);

    // 6. 炮位与兵位十字花标记
    const markers = [
      // 炮位
      [1, 2], [7, 2], [1, 7], [7, 7],
      // 兵位
      [0, 3], [2, 3], [4, 3], [6, 3], [8, 3],
      [0, 6], [2, 6], [4, 6], [6, 6], [8, 6]
    ];
    markers.forEach(([c, r]) => this.drawCornerMarker(c, r, lineColor));
  }

  drawCornerMarker(c, r, color) {
    const p = this.getPos(c, r);
    const d = 4; // 偏移距离
    const len = 7; // 折线长度
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("stroke", color);
    g.setAttribute("stroke-width", "1.2");
    g.setAttribute("fill", "none");

    const addCorner = (signX, signY) => {
      const x1 = p.x + signX * d;
      const y1 = p.y + signY * (d + len);
      const x2 = p.x + signX * d;
      const y2 = p.y + signY * d;
      const x3 = p.x + signX * (d + len);
      const y3 = p.y + signY * d;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", `M ${x1} ${y1} L ${x2} ${y2} L ${x3} ${y3}`);
      g.appendChild(path);
    };

    if (c > 0) {
      addCorner(-1, -1);
      addCorner(-1, 1);
    }
    if (c < 8) {
      addCorner(1, -1);
      addCorner(1, 1);
    }
    this.svgLayer.appendChild(g);
  }

  updateState(state) {
    this.boardState = state;
    this.legalMovesMap = state.legal_moves_map || {};
    this.selectedSq = null;
    this.renderPieces();
  }

  renderPieces() {
    this.piecesLayer.innerHTML = "";
    if (!this.boardState) return;

    // 1. 渲染上一步移动的高亮标记
    if (this.boardState.last_move) {
      const fromPos = this.sqToColRow(this.boardState.last_move.from);
      const toPos = this.sqToColRow(this.boardState.last_move.to);
      const pFrom = this.getPos(fromPos.col, fromPos.row);
      const pTo = this.getPos(toPos.col, toPos.row);

      const divFrom = document.createElement("div");
      divFrom.className = "highlight-last-from";
      divFrom.style.left = `${pFrom.x}px`;
      divFrom.style.top = `${pFrom.y}px`;
      this.piecesLayer.appendChild(divFrom);

      const divTo = document.createElement("div");
      divTo.className = "highlight-last-to";
      divTo.style.left = `${pTo.x}px`;
      divTo.style.top = `${pTo.y}px`;
      this.piecesLayer.appendChild(divTo);
    }

    // 2. 将军警示光晕
    if (this.boardState.is_check) {
      // 找出当前受将的帅/将位置
      const targetKingSymbol = (this.boardState.turn === "red") ? "K" : "k";
      for (const row of this.boardState.board_grid) {
        for (const item of row) {
          if (item && item.symbol === targetKingSymbol) {
            const pos = this.getPos(item.col, item.row);
            const checkDiv = document.createElement("div");
            checkDiv.className = "check-warning";
            checkDiv.style.left = `${pos.x}px`;
            checkDiv.style.top = `${pos.y}px`;
            this.piecesLayer.appendChild(checkDiv);
            break;
          }
        }
      }
    }

    // 3. 渲染所有棋子
    for (const row of this.boardState.board_grid) {
      for (const item of row) {
        if (!item) continue;
        const pos = this.getPos(item.col, item.row);
        const pieceEl = document.createElement("div");
        pieceEl.className = `chess-piece piece-${item.color}`;
        pieceEl.dataset.sq = item.sq_name;
        pieceEl.style.left = `${pos.x}px`;
        pieceEl.style.top = `${pos.y}px`;

        // 插入矢量 SVG 资产
        const svgContent = PIECES_SVG[item.symbol] || "";
        pieceEl.innerHTML = `<svg viewBox="0 0 100 100">${svgContent}</svg>`;

        // 如果是已选中的棋子
        if (this.selectedSq === item.sq_name) {
          pieceEl.classList.add("selected");
        }

        pieceEl.addEventListener("click", (e) => {
          e.stopPropagation();
          this.handlePieceClick(item.sq_name, item.color);
        });

        this.piecesLayer.appendChild(pieceEl);
      }
    }

    // 4. 如果有选中的棋子，渲染合法落子点圆圈
    if (this.selectedSq && this.legalMovesMap[this.selectedSq]) {
      const moves = this.legalMovesMap[this.selectedSq];
      moves.forEach(m => {
        const targetPos = this.sqToColRow(m.to);
        const p = this.getPos(targetPos.col, targetPos.row);

        const dot = document.createElement("div");
        dot.className = "legal-dot";
        dot.style.left = `${p.x}px`;
        dot.style.top = `${p.y}px`;

        // 检查该目标格是否有对方棋子被吃
        const isEat = this.hasPieceAt(targetPos.col, targetPos.row);
        if (isEat) {
          dot.classList.add("eat-target");
        }

        dot.addEventListener("click", (e) => {
          e.stopPropagation();
          this.executeMove(m.uci);
        });

        this.piecesLayer.appendChild(dot);
      });
    }
  }

  hasPieceAt(col, row) {
    if (!this.boardState || !this.boardState.board_grid) return false;
    for (const r of this.boardState.board_grid) {
      for (const item of r) {
        if (item && item.col === col && item.row === row) {
          return true;
        }
      }
    }
    return false;
  }

  handlePieceClick(sqName, color) {
    if (!this.boardState) return;

    // 只有轮到玩家走棋时才响应选子
    if (!this.boardState.is_player_turn) {
      return;
    }

    // 如果点击的是玩家自己的棋子，且有合法走法
    if (color === this.boardState.player_color) {
      if (this.selectedSq === sqName) {
        this.selectedSq = null;
      } else {
        this.selectedSq = sqName;
      }
      this.renderPieces();
    } else {
      // 点击对方棋子，若当前已选中己方棋子且包含吃子动作，则执行
      if (this.selectedSq && this.legalMovesMap[this.selectedSq]) {
        const targetMove = this.legalMovesMap[this.selectedSq].find(m => m.to === sqName);
        if (targetMove) {
          this.executeMove(targetMove.uci);
        }
      }
    }
  }

  executeMove(uci) {
    this.selectedSq = null;
    this.renderPieces();
    if (this.options.onMove) {
      this.options.onMove(uci);
    }
  }
}

window.BoardUI = BoardUI;
