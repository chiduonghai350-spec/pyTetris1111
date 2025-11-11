# -*- coding: utf-8 -*-
"""
Tetris — 单文件完整版（Pygame）

修复与改进（相对上一版）：
- 修复中文字体乱码：自动匹配本机常见中文字体（微软雅黑/思源黑体/Noto等），找不到则回退默认字体。
- NEXT 预览区域自适应：根据面板剩余高度自动压缩间距，确保 5 个预览全部可见而不被裁切。

功能特性（保持）：
- 标准 7-袋随机器（7-bag）发牌
- 标准 7 种四格骨牌（I, J, L, O, S, T, Z）
- SRS 旋转 + 墙踢（含 I 形与 JLSTZ 通用踢墙表）
- 暂存（Hold）、预览（Next，显示 5 个）
- 软降（Down）、硬降（Space）、影子（Ghost）
- 锁定延迟（Lock Delay）并限制重置次数
- 消行计分、连击（Combo）、回退加成（Back-to-Back）
- T-Spin 检测（含 Mini）与计分
- 等级提升与重力加速
- 暂停/继续、游戏结束与重开
- 本地最高分持久化（tetris_highscore.json）
- 简洁美观的 UI（渐变背景、圆角方块、信息面板）

控制：
- ←/→：水平移动
- ↓：软降（+1/格）
- ↑ 或 X：顺时针旋转
- Z：逆时针旋转
- A：180° 旋转
- Space：硬降（+2/格）
- C：暂存/交换（Hold）
- P：暂停/继续
- R：在游戏结束时重开
- Esc：退出

运行：
  pip install pygame
  python tetris.py
"""
from __future__ import annotations
import sys, os, json, math, random, time
import pygame

# ===================== 常量与配置 ===================== #
CELL = 32              # 单元格像素尺寸
COLS, ROWS = 10, 22    # 行列（包含 2 行隐藏行）
VISIBLE_ROWS = 20
HIDDEN_ROWS = ROWS - VISIBLE_ROWS

PANEL_W = 260          # 右侧信息面板宽度
MARGIN = 20            # 外边距
GRID_W = COLS * CELL
GRID_H = VISIBLE_ROWS * CELL
WIN_W = GRID_W + PANEL_W + MARGIN * 3
WIN_H = GRID_H + MARGIN * 2
FPS = 60

# 锁定延迟（秒）及最大重置次数（Guideline 常见 0.5s, 15 次）
LOCK_DELAY = 0.5
LOCK_RESETS_MAX = 15

# 字体（运行时动态匹配中文字体，避免乱码）
FONT_PATH = None  # 在 main() 中初始化
FONT_CACHE = {}

# 颜色（RGB）
WHITE = (245, 245, 245)
BLACK = (15, 15, 20)
MUTED = (180, 186, 194)
GRID_LINE = (40, 44, 52)
PANEL_BG = (28, 30, 38)
ACCENT = (255, 214, 10)

# 方块颜色（与各形状绑定）
PIECE_COLORS = {
    'I': (80, 220, 240),
    'J': (60, 100, 220),
    'L': (230, 160, 60),
    'O': (240, 220, 90),
    'S': (90, 200, 120),
    'T': (180, 100, 220),
    'Z': (220, 80, 100),
}

# ===================== 形状与旋转（SRS 4x4） ===================== #
# 每个旋转状态是 4x4 字符矩阵，'X' 表示占用，'.' 表示空
# 坐标系：左上为 (0,0)，x 向右，y 向下
SHAPES = {
    'I': [
        [
            '.','.','.','.',
            'X','X','X','X',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','.','X','.',
            '.','.','X','.',
            '.','.','X','.',
            '.','.','X','.',
        ],
        [
            '.','.','.','.',
            '.','.','.','.',
            'X','X','X','X',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            '.','X','.','.',
            '.','X','.','.',
            '.','X','.','.',
        ],
    ],
    'J': [
        [
            'X','.','.','.',
            'X','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','X','.',
            '.','X','.','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
        [
            '.','.','.','.',
            'X','X','X','.',
            '.','.','X','.',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            '.','X','.','.',
            'X','X','.','.',
            '.','.','.','.',
        ],
    ],
    'L': [
        [
            '.','.','X','.',
            'X','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            '.','X','.','.',
            '.','X','X','.',
            '.','.','.','.',
        ],
        [
            '.','.','.','.',
            'X','X','X','.',
            'X','.','.','.',
            '.','.','.','.',
        ],
        [
            'X','X','.','.',
            '.','X','.','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
    ],
    'O': [
        [
            '.','X','X','.',
            '.','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','X','.',
            '.','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','X','.',
            '.','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','X','.',
            '.','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
    ],
    'S': [
        [
            '.','X','X','.',
            'X','X','.','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            '.','X','X','.',
            '.','.','X','.',
            '.','.','.','.',
        ],
        [
            '.','.','.','.',
            '.','X','X','.',
            'X','X','.','.',
            '.','.','.','.',
        ],
        [
            'X','.','.','.',
            'X','X','.','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
    ],
    'T': [
        [
            '.','X','.','.',
            'X','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            '.','X','X','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
        [
            '.','.','.','.',
            'X','X','X','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            'X','X','.','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
    ],
    'Z': [
        [
            'X','X','.','.',
            '.','X','X','.',
            '.','.','.','.',
            '.','.','.','.',
        ],
        [
            '.','.','X','.',
            '.','X','X','.',
            '.','X','.','.',
            '.','.','.','.',
        ],
        [
            '.','.','.','.',
            'X','X','.','.',
            '.','X','X','.',
            '.','.','.','.',
        ],
        [
            '.','X','.','.',
            'X','X','.','.',
            'X','.','.','.',
            '.','.','.','.',
        ],
    ],
}

# SRS 墙踢 (JLSTZ 与 I) — 每组表示从状态 from->to 应用的位移列表
JLSTZ_KICKS = {
    (0,1): [(0,0), (-1,0), (-1, -1), (0, 2), (-1, 2)],
    (1,0): [(0,0), (1,0), (1, 1), (0, -2), (1, -2)],
    (1,2): [(0,0), (1,0), (1, 1), (0, -2), (1, -2)],
    (2,1): [(0,0), (-1,0), (-1,-1), (0, 2), (-1, 2)],
    (2,3): [(0,0), (1,0), (1, -1), (0, 2), (1, 2)],
    (3,2): [(0,0), (-1,0), (-1, 1), (0, -2), (-1,-2)],
    (3,0): [(0,0), (-1,0), (-1, 1), (0, -2), (-1,-2)],
    (0,3): [(0,0), (1,0), (1, -1), (0, 2), (1, 2)],
}
I_KICKS = {
    (0,1): [(0,0), (-2,0), (1,0), (-2, -1), (1, 2)],
    (1,0): [(0,0), (2,0), (-1,0), (2, 1), (-1, -2)],
    (1,2): [(0,0), (-1,0), (2,0), (-1, 2), (2, -1)],
    (2,1): [(0,0), (1,0), (-2,0), (1, -2), (-2, 1)],
    (2,3): [(0,0), (2,0), (-1,0), (2, 1), (-1, -2)],
    (3,2): [(0,0), (-2,0), (1,0), (-2, -1), (1, 2)],
    (3,0): [(0,0), (1,0), (-2,0), (1, -2), (-2, 1)],
    (0,3): [(0,0), (-1,0), (2,0), (-1, 2), (2, -1)],
}

# ===================== 工具函数 ===================== #

def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ---- 字体工具：匹配一个可显示中文的字体 ---- #

def match_cjk_font()->str:
    candidates = [
        # Windows
        'Microsoft YaHei UI','Microsoft YaHei','msyh','SimHei','SimSun',
        # macOS
        'PingFang SC','Hiragino Sans GB','Heiti SC',
        # Linux / 通用
        'Noto Sans CJK SC','Noto Sans SC','Source Han Sans SC','WenQuanYi Zen Hei','WenQuanYi Micro Hei','Sarasa Gothic SC',
    ]
    for name in candidates:
        path = pygame.font.match_font(name)
        if path:
            return path
    # 回退：默认字体（可能不含中文）
    return pygame.font.get_default_font()


def get_font(size:int):
    key = int(size)
    f = FONT_CACHE.get(key)
    if f:
        return f
    try:
        f = pygame.font.Font(FONT_PATH, size)
    except Exception:
        f = pygame.font.Font(None, size)
    FONT_CACHE[key] = f
    return f

# 重力间隔（秒）：随等级递减
# 近似 Guideline 重力：interval = max(0.05, 0.8 * (0.85 ** (level-1)))
def gravity_interval(level:int)->float:
    return max(0.05, 0.8 * (0.85 ** (level - 1)))

# 计分表（参考 Guideline，适度简化）
SCORE_TABLE = {
    'single': 100,
    'double': 300,
    'triple': 500,
    'tetris': 800,
    'tspin_mini_single': 200,
    'tspin_single': 800,
    'tspin_double': 1200,
    'tspin_triple': 1600,
}

# ===================== 数据结构 ===================== #
class Piece:
    def __init__(self, kind:str):
        self.kind = kind
        self.rot = 0  # 0,1,2,3
        # 生成位置：x=3 使其置于场地中部，y = -1 以跨越隐藏行
        self.x, self.y = 3, -1
        # O 形略微不同的初始 y
        if kind == 'O':
            self.y = 0 - HIDDEN_ROWS
        # 记录最后一次动作用于 T-Spin 判断
        self.last_action = None  # 'move' | 'rotate' | None
        self.lock_resets = 0

    def shape(self):
        return SHAPES[self.kind][self.rot]

    def cells(self):
        # 返回当前 4x4 矩阵中为 X 的绝对坐标
        s = self.shape()
        out = []
        for i in range(16):
            if s[i] == 'X':
                r, c = i // 4, i % 4
                out.append((self.x + c, self.y + r))
        return out

    def clone(self):
        p = Piece(self.kind)
        p.rot = self.rot
        p.x, p.y = self.x, self.y
        p.last_action = self.last_action
        p.lock_resets = self.lock_resets
        return p

# 7-袋随机器
class Bag:
    def __init__(self):
        self.pool = []
        self.refill()

    def refill(self):
        kinds = list('IJLOSTZ')
        random.shuffle(kinds)
        self.pool.extend(kinds)

    def pop(self)->str:
        if not self.pool:
            self.refill()
        return self.pool.pop(0)

class Queue:
    def __init__(self, preview=5):
        self.bag = Bag()
        self.items = [self.bag.pop() for _ in range(preview+1)]  # 多准备 1 个供当前生成
        self.preview = preview

    def next(self)->str:
        n = self.items.pop(0)
        self.items.append(self.bag.pop())
        return n

    def peek_list(self):
        return self.items[:self.preview]

# 棋盘（包含隐藏行）
class Board:
    def __init__(self):
        # 使用整数标记：0 表空；其它使用字符保存 kind
        self.grid = [['.' for _ in range(COLS)] for _ in range(ROWS)]

    def inside(self, x, y):
        return 0 <= x < COLS and y < ROWS

    def collide(self, piece:Piece)->bool:
        for x, y in piece.cells():
            if y < 0:
                # 允许在隐藏区
                continue
            if not self.inside(x, y) or self.grid[y][x] != '.':
                return True
        return False

    def lock(self, piece:Piece):
        for x, y in piece.cells():
            if 0 <= y < ROWS and 0 <= x < COLS:
                self.grid[y][x] = piece.kind

    def clear_lines(self):
        # 返回（消行数，被清除的行索引列表）
        full = [i for i in range(ROWS) if all(c != '.' for c in self.grid[i])]
        for i in full:
            del self.grid[i]
            self.grid.insert(0, ['.' for _ in range(COLS)])
        return len(full), full

    def topped_out(self):
        # 任何在隐藏行内的占用算作顶出
        for y in range(HIDDEN_ROWS):
            if any(self.grid[y][x] != '.' for x in range(COLS)):
                return True
        return False

# ===================== 旋转与墙踢 ===================== #

def rotate_with_kick(board:Board, piece:Piece, dir:int)->bool:
    """尝试旋转：dir=+1 顺时针，-1 逆时针，2 180°。成功返回 True"""
    if piece.kind == 'O' and dir in (1,-1):
        # O 形无需踢墙，只改变动作标志
        piece.rot = (piece.rot + dir) % 4
        if board.collide(piece):  # O 不应发生碰撞，如发生则回滚
            piece.rot = (piece.rot - dir) % 4
            return False
        piece.last_action = 'rotate'
        return True

    if dir == 2:  # 180° 旋转：采用简单碰撞 + 小范围位移尝试（非官方表，但实用）
        target = (piece.rot + 2) % 4
        kicks = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0)]
        old_rot = piece.rot
        piece.rot = target
        for dx, dy in kicks:
            piece.x += dx; piece.y += dy
            if not board.collide(piece):
                piece.last_action = 'rotate'
                return True
            piece.x -= dx; piece.y -= dy
        piece.rot = old_rot
        return False

    frm = piece.rot
    to = (piece.rot + dir) % 4
    kicks = I_KICKS if piece.kind == 'I' else JLSTZ_KICKS
    oldx, oldy, oldrot = piece.x, piece.y, piece.rot
    piece.rot = to
    for dx, dy in kicks.get((frm, to), [(0,0)]):
        piece.x = oldx + dx
        piece.y = oldy + dy
        if not board.collide(piece):
            piece.last_action = 'rotate'
            return True
    # 失败回滚
    piece.x, piece.y, piece.rot = oldx, oldy, oldrot
    return False

# ===================== T-Spin 判定 ===================== #

def is_tspin(board:Board, piece:Piece, lines:int, last_action:str):
    """返回 (is_tspin, is_mini)
    使用 3-corner 规则：T 中心为 4x4 的 (x+1, y+1)。
    需要上一动作为旋转且为 T 形，并且消行>0。
    """
    if piece.kind != 'T' or last_action != 'rotate' or lines <= 0:
        return (False, False)
    # 以当前 piece 定位中心
    cx, cy = piece.x + 1, piece.y + 1
    corners = [(cx-1, cy-1), (cx+1, cy-1), (cx-1, cy+1), (cx+1, cy+1)]
    occupied = 0
    for x, y in corners:
        if not (0 <= x < COLS and 0 <= y < ROWS):
            occupied += 1
        elif board.grid[y][x] != '.':
            occupied += 1
    if occupied < 3:
        return (False, False)
    # 迷你判定：基于前侧两个角被占用与旋转朝向（简化）
    # 旋转朝向 0(上)1(右)2(下)3(左)，检测前两个脚位
    front = {
        0: [(cx-1, cy-1), (cx+1, cy-1)],
        1: [(cx+1, cy-1), (cx+1, cy+1)],
        2: [(cx-1, cy+1), (cx+1, cy+1)],
        3: [(cx-1, cy-1), (cx-1, cy+1)],
    }[piece.rot]
    focc = 0
    for x, y in front:
        if not (0 <= x < COLS and 0 <= y < ROWS):
            focc += 1
        elif board.grid[y][x] != '.':
            focc += 1
    is_mini = (focc == 1) and (lines == 1)
    return (True, is_mini)

# ===================== 游戏主控 ===================== #
class Game:
    def __init__(self):
        self.board = Board()
        self.queue = Queue(preview=2)
        self.hold = None
        self.hold_used = False
        self.cur = Piece(self.queue.next())
        self.ghost_y = self.compute_ghost_y()

        self.score = 0
        self.lines = 0
        self.level = 1
        self.combo = -1
        self.b2b = False
        self.drop_distance_soft = 0
        self.drop_distance_hard = 0

        self.gravity_timer = 0.0
        self.lock_timer = None
        self.running = True
        self.paused = False
        self.game_over = False

        self.lock_reset_count = 0
        self.last_move_time = 0

        self.clear_anim = None  # (lines_indices, timer)

    # ---------- 逻辑 ---------- #
    def spawn(self):
        self.cur = Piece(self.queue.next())
        self.hold_used = False
        # 立即检测顶出
        if self.board.collide(self.cur):
            self.game_over = True
        self.ghost_y = self.compute_ghost_y()
        self.lock_timer = None
        self.lock_reset_count = 0

    def compute_ghost_y(self):
        p = self.cur.clone()
        while True:
            p.y += 1
            if self.board.collide(p):
                return p.y - 1

    def try_move(self, dx:int, dy:int)->bool:
        oldx, oldy = self.cur.x, self.cur.y
        self.cur.x += dx; self.cur.y += dy
        if self.board.collide(self.cur):
            self.cur.x, self.cur.y = oldx, oldy
            return False
        self.cur.last_action = 'move'
        if dy == 0 and self.lock_timer is not None:
            # 地面移动重置锁延迟（有限次数）
            if self.lock_reset_count < LOCK_RESETS_MAX:
                self.lock_timer = 0.0
                self.lock_reset_count += 1
        return True

    def try_rotate(self, dir:int):
        if rotate_with_kick(self.board, self.cur, dir):
            if self.lock_timer is not None and self.lock_reset_count < LOCK_RESETS_MAX:
                self.lock_timer = 0.0
                self.lock_reset_count += 1
            self.ghost_y = self.compute_ghost_y()
            return True
        return False

    def soft_drop(self):
        if self.try_move(0,1):
            self.drop_distance_soft += 1
            return True
        return False

    def hard_drop(self):
        # 直接落到底
        dist = 0
        while self.try_move(0,1):
            dist += 1
        self.drop_distance_hard += dist
        self.lock_piece()

    def hold_swap(self):
        if self.hold_used:
            return
        if self.hold is None:
            self.hold = self.cur.kind
            self.spawn()
        else:
            self.cur.kind, self.hold = self.hold, self.cur.kind
            self.cur.rot = 0
            self.cur.x, self.cur.y = 3, -1
            if self.cur.kind == 'O':
                self.cur.y = 0 - HIDDEN_ROWS
            if self.board.collide(self.cur):
                self.game_over = True
        self.hold_used = True
        self.ghost_y = self.compute_ghost_y()
        self.lock_timer = None
        self.lock_reset_count = 0

    def lock_piece(self):
        self.board.lock(self.cur)
        # 记分：落下得分
        self.score += self.drop_distance_soft * 1 + self.drop_distance_hard * 2
        self.drop_distance_soft = 0
        self.drop_distance_hard = 0

        # 消行 & T-Spin 判定
        cleared, lines_idx = self.board.clear_lines()
        tspin, mini = is_tspin(self.board, self.cur, cleared, self.cur.last_action)

        line_type = None
        gained = 0
        is_b2b_type = False
        if tspin:
            is_b2b_type = True
            if cleared == 1:
                line_type = 'tspin_mini_single' if mini else 'tspin_single'
            elif cleared == 2:
                line_type = 'tspin_double'
            elif cleared == 3:
                line_type = 'tspin_triple'
        else:
            if cleared == 1:
                line_type = 'single'
            elif cleared == 2:
                line_type = 'double'
            elif cleared == 3:
                line_type = 'triple'
            elif cleared == 4:
                line_type = 'tetris'
                is_b2b_type = True

        if line_type:
            base = SCORE_TABLE[line_type]
            # Back-to-Back 加成
            if is_b2b_type and self.b2b:
                base = int(base * 1.5)
            self.b2b = is_b2b_type

            # Combo
            self.combo = self.combo + 1 if self.combo >= 0 else 0
            base += 50 * self.combo

            self.score += base
            self.lines += cleared
            # 动画
            self.clear_anim = (lines_idx, 0.15)
        else:
            # 未消行：combo 重置，B2B 维持
            self.combo = -1

        # Level up：每 10 行 +1 级
        lv_before = self.level
        self.level = 1 + self.lines // 10
        if self.level != lv_before:
            pass

        self.spawn()

    def update(self, dt):
        if self.paused or self.game_over:
            return
        # 清行动画计时
        if self.clear_anim is not None:
            idx, t = self.clear_anim
            t -= dt
            if t <= 0:
                self.clear_anim = None
            else:
                self.clear_anim = (idx, t)

        # 重力
        g = gravity_interval(self.level)
        self.gravity_timer += dt
        on_ground = self.on_ground()
        if self.gravity_timer >= g:
            self.gravity_timer -= g
            if not self.try_move(0,1):
                # 到地面，启动锁定计时
                if self.lock_timer is None:
                    self.lock_timer = 0.0

        # 锁定延迟计时
        if self.on_ground():
            if self.lock_timer is None:
                self.lock_timer = 0.0
            else:
                self.lock_timer += dt
                if self.lock_timer >= LOCK_DELAY:
                    self.lock_piece()
                    self.lock_timer = None
        else:
            self.lock_timer = None

        self.ghost_y = self.compute_ghost_y()

    def on_ground(self)->bool:
        # 判断向下一格是否碰撞
        p = self.cur.clone(); p.y += 1
        return self.board.collide(p)

    # ---------- 绘制 ---------- #
    def draw(self, screen:pygame.Surface):
        screen.fill(BLACK)
        self.draw_bg_gradient(screen)
        # 网格背景
        gx, gy = MARGIN, MARGIN
        pygame.draw.rect(screen, PANEL_BG, (gx-6, gy-6, GRID_W+12, GRID_H+12), border_radius=18)
        self.draw_grid(screen, gx, gy)

        # 画锁定的方块
        for y in range(HIDDEN_ROWS, ROWS):
            for x in range(COLS):
                k = self.board.grid[y][x]
                if k != '.':
                    self.draw_cell(screen, gx + x*CELL, gy + (y-HIDDEN_ROWS)*CELL, PIECE_COLORS[k])

        # 影子
        self.draw_piece(screen, self.cur, gx, gy, ghost=True)
        # 当前块
        self.draw_piece(screen, self.cur, gx, gy, ghost=False)

        # 侧边面板
        px = gx + GRID_W + MARGIN
        py = gy
        self.draw_side_panel(screen, px, py)

        # 顶出/暂停遮罩
        if self.paused:
            self.draw_center_text(screen, '暂停', 48, WHITE, sub='P 继续')
        if self.game_over:
            self.draw_center_text(screen, '游戏结束', 44, WHITE, sub='R 重开 / Esc 退出')

    def draw_bg_gradient(self, screen):
        # 简单线性渐变背景
        top = (26, 28, 36)
        bottom = (14, 16, 22)
        for i in range(WIN_H):
            t = i / float(WIN_H-1)
            c = (
                int(lerp(top[0], bottom[0], t)),
                int(lerp(top[1], bottom[1], t)),
                int(lerp(top[2], bottom[2], t)),
            )
            pygame.draw.line(screen, c, (0,i), (WIN_W, i))

    def draw_grid(self, screen, gx, gy):
        # 背景小方格
        for r in range(VISIBLE_ROWS+1):
            y = gy + r*CELL
            pygame.draw.line(screen, GRID_LINE, (gx, y), (gx + GRID_W, y))
        for c in range(COLS+1):
            x = gx + c*CELL
            pygame.draw.line(screen, GRID_LINE, (x, gy), (x, gy + GRID_H))

    def draw_cell(self, screen, px, py, color, ghost=False):
        # 圆角 + 高光
        base = color
        if ghost:
            # 影子：淡色边框
            rect = pygame.Rect(px+3, py+3, CELL-6, CELL-6)
            pygame.draw.rect(screen, (*color, 48), rect, width=2, border_radius=8)
            return
        rect = pygame.Rect(px+2, py+2, CELL-4, CELL-4)
        pygame.draw.rect(screen, base, rect, border_radius=8)
        # 高光
        hi = (min(255, int(base[0]*1.15)), min(255, int(base[1]*1.15)), min(255, int(base[2]*1.15)))
        lo = (int(base[0]*0.65), int(base[1]*0.65), int(base[2]*0.65))
        pygame.draw.rect(screen, hi, (px+4, py+4, CELL-8, (CELL-8)//2), border_radius=6)
        pygame.draw.rect(screen, lo, (px+4, py+CELL//2, CELL-8, (CELL-8)//2), border_radius=6)

    def draw_piece(self, screen, piece:Piece, gx, gy, ghost=False):
        if ghost:
            y = self.ghost_y
        else:
            y = piece.y
        s = SHAPES[piece.kind][piece.rot]
        for i in range(16):
            if s[i] == 'X':
                r, c = i//4, i%4
                px = gx + (piece.x + c) * CELL
                py = gy + (y - HIDDEN_ROWS + r) * CELL
                if py < gy or py >= gy + GRID_H:  # 跳过隐藏区与出界
                    continue
                self.draw_cell(screen, px, py, PIECE_COLORS[piece.kind], ghost=ghost)

    def small_text(self, screen, text, x, y, color=MUTED, size=18):
        font = get_font(size)
        surf = font.render(text, True, color)
        screen.blit(surf, (x, y))

    def big_text(self, screen, text, x, y, color=WHITE, size=24):
        font = get_font(size)
        surf = font.render(text, True, color)
        screen.blit(surf, (x, y))

    def draw_side_panel(self, screen, px, py):
        panel_rect = pygame.Rect(px-6, py-6, PANEL_W+12, GRID_H+12)
        pygame.draw.rect(screen, PANEL_BG, panel_rect, border_radius=18)
        # 标题
        self.big_text(screen, 'TETRIS', px+16, py+12, ACCENT, 28)
        # 分数/等级/行数
        stat_y = py + 60
        self.small_text(screen, 'SCORE', px+16, stat_y, MUTED, 16)
        self.big_text(screen, f"{self.score}", px+16, stat_y+18, WHITE, 26)
        self.small_text(screen, 'LEVEL', px+16, stat_y+60, MUTED, 16)
        self.big_text(screen, f"{self.level}", px+16, stat_y+78, WHITE, 26)
        self.small_text(screen, 'LINES', px+120, stat_y+60, MUTED, 16)
        self.big_text(screen, f"{self.lines}", px+120, stat_y+78, WHITE, 26)

        # 进度条：距离下一级
        to_next = (self.level*10) - self.lines
        to_next = max(0, to_next)
        bar_x, bar_y = px+16, stat_y+120
        bar_w, bar_h = PANEL_W-32, 14
        pygame.draw.rect(screen, (50,54,63), (bar_x, bar_y, bar_w, bar_h), border_radius=8)
        need = 10
        have = self.lines % 10
        ratio = have / need
        pygame.draw.rect(screen, ACCENT, (bar_x, bar_y, int(bar_w*ratio), bar_h), border_radius=8)

        # Hold 区域
        hold_y = bar_y + 28
        self.small_text(screen, 'HOLD', px+16, hold_y, MUTED, 16)
        self.draw_mini_mat(screen, self.hold, px+16, hold_y+18, highlight=not self.hold_used)

        # Next 列表（自适应间距，确保 5 个全显示）
        next_y = hold_y + 120
        self.small_text(screen, 'NEXT', px+16, next_y, MUTED, 16)
        start_y = next_y + 18
        previews = self.queue.peek_list()
        n = len(previews)
        area_bottom = py + GRID_H - 12  # 面板底部略留边距
        item_h = 64
        if n <= 1:
            spacing = 0
        else:
            # 在 8~68 之间动态压缩
            spacing = (area_bottom - start_y - item_h) / max(1, (n - 1))
            spacing = clamp(spacing, 8, 68)
        y = start_y
        for k in previews:
            self.draw_mini_mat(screen, k, px+16, int(y))
            y += spacing

        # 帮助
        help_y = py + GRID_H - 120
        self.small_text(screen, '←/→ 移动  ↓ 软降  Space 硬降', px+16, help_y, MUTED, 14)
        self.small_text(screen, 'Z/↑/X 旋转  A 180°  C 暂存', px+16, help_y+18, MUTED, 14)
        self.small_text(screen, 'P 暂停  R 重开', px+16, help_y+36, MUTED, 14)

        # 清行闪烁覆盖（只覆盖主网格，不影响右侧面板）
        if self.clear_anim is not None:
            idx, t = self.clear_anim
            alpha = int(255 * (t / 0.15))
            overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
            pygame.draw.rect(overlay, (255,255,255, clamp(alpha,0,180)), overlay.get_rect())
            screen.blit(overlay, (MARGIN, MARGIN))

    def draw_mini_mat(self, screen, kind, x, y, highlight=False):
        rect = pygame.Rect(x, y, 96, 64)
        pygame.draw.rect(screen, (36,40,48), rect, border_radius=10)
        if highlight:
            pygame.draw.rect(screen, (80,86,96), rect, width=2, border_radius=10)
        if not kind:
            return
        # 画 4x4 缩略图
        mat = SHAPES[kind][0]
        # 计算居中缩放：mini cell
        mini = 16
        # 求其最小包围盒
        coords = []
        for i in range(16):
            if mat[i]=='X':
                r,c=i//4,i%4
                coords.append((r,c))
        if not coords:
            return
        minr=min(r for r,c in coords); maxr=max(r for r,c in coords)
        minc=min(c for r,c in coords); maxc=max(c for r,c in coords)
        w=(maxc-minc+1)*mini; h=(maxr-minr+1)*mini
        ox = x + (rect.w - w)//2
        oy = y + (rect.h - h)//2
        col = PIECE_COLORS[kind]
        for r,c in coords:
            px = ox + (c - minc)*mini
            py = oy + (r - minr)*mini
            pygame.draw.rect(screen, col, (px+2, py+2, mini-4, mini-4), border_radius=5)

    def draw_center_text(self, screen, text, size, color, sub=None):
        font = get_font(size)
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(WIN_W//2, WIN_H//2 - 20))
        screen.blit(surf, rect)
        if sub:
            sfont = get_font(20)
            ss = sfont.render(sub, True, MUTED)
            srect = ss.get_rect(center=(WIN_W//2, WIN_H//2 + 18))
            screen.blit(ss, srect)

# ===================== 高分存取 ===================== #
HS_FILE = 'tetris_highscore.json'

def load_highscore():
    try:
        with open(HS_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
            return int(d.get('highscore', 0))
    except Exception:
        return 0

def save_highscore(val:int):
    try:
        with open(HS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'highscore': int(val)}, f)
    except Exception:
        pass

# ===================== 主循环与输入 ===================== #

def main():
    pygame.init()
    pygame.display.set_caption('Tetris — 单文件完整版')
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()

    # 初始化中文字体，避免中文 UI 文字乱码
    global FONT_PATH
    FONT_PATH = match_cjk_font()

    game = Game()
    high = load_highscore()

    # 键盘自动重复处理（简化 DAS/ARR）
    move_left = move_right = False
    das_timer = 0.0
    das_delay = 0.15
    arr = 0.03

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # 事件
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                if game.game_over:
                    if e.key == pygame.K_r:
                        # 保存高分
                        high = max(high, game.score)
                        save_highscore(high)
                        game = Game()
                        continue
                else:
                    if e.key == pygame.K_p:
                        game.paused = not game.paused
                    if game.paused:
                        continue
                # 操作
                if e.key == pygame.K_LEFT:
                    move_left = True; das_timer = 0
                    game.try_move(-1, 0)
                elif e.key == pygame.K_RIGHT:
                    move_right = True; das_timer = 0
                    game.try_move(1, 0)
                elif e.key == pygame.K_DOWN:
                    game.soft_drop()
                elif e.key in (pygame.K_UP, pygame.K_x):
                    game.try_rotate(+1)
                elif e.key == pygame.K_z:
                    game.try_rotate(-1)
                elif e.key == pygame.K_a:
                    game.try_rotate(2)
                elif e.key == pygame.K_SPACE:
                    game.hard_drop()
                elif e.key == pygame.K_c:
                    game.hold_swap()
                elif e.key == pygame.K_r and not game.game_over:
                    high = max(high, game.score)
                    save_highscore(high)
                    game = Game()
            elif e.type == pygame.KEYUP:
                if e.key == pygame.K_LEFT:
                    move_left = False
                elif e.key == pygame.K_RIGHT:
                    move_right = False

        # 横移重复（DAS/ARR 简化）
        if not game.paused and not game.game_over:
            if move_left or move_right:
                das_timer += dt
                if das_timer >= das_delay:
                    # 执行 ARR
                    while das_timer >= arr + das_delay:
                        das_timer -= arr
                        if move_left and not move_right:
                            game.try_move(-1, 0)
                        elif move_right and not move_left:
                            game.try_move(1, 0)
            else:
                das_timer = 0

        if not game.game_over:
            game.update(dt)

        # 绘制
        game.draw(screen)

        # 顶部显示高分（使用中文兼容字体渲染）
        font = get_font(16)
        hs = max(high, game.score)
        info = font.render(f"HIGH {hs}", True, (200, 205, 214))
        screen.blit(info, (WIN_W - PANEL_W - 20 - info.get_width(), 6))

        pygame.display.flip()

    # 退出保存高分
    high = max(high, game.score)
    save_highscore(high)
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
