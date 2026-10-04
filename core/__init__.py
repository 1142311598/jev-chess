import sys
import os

# 将 core 目录加入 sys.path，保证内部的 cchess 模块可以平滑被导入
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
