import pygame
import random
import sys
import os

# ── Constants ──────────────────────────────────────────────────────────────
CELL        = 30
COLS        = 10
ROWS        = 20
SIDEBAR     = 180
WIDTH       = COLS * CELL + SIDEBAR
HEIGHT      = ROWS * CELL
FPS         = 60

BG_FILE     = "Girl Horse No Text.jpg"
LOGO_FILE   = "logo.png"
HEADER      = 70

ANDROID     = hasattr(sys, 'getandroidapilevel') or 'ANDROID_ARGUMENT' in os.environ
BTN_H       = 80 if ANDROID else 0   # touch button bar height on Android

BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
GRAY        = (40,  40,  40)
DARK_GRAY   = (20,  20,  20)
BORDER      = (80,  80,  80)

COLORS = [
    None,
    (0,   240, 240),   # I  - cyan
    (240, 240,   0),   # O  - yellow
    (160,   0, 240),   # T  - purple
    (0,   240,   0),   # S  - green
    (240,   0,   0),   # Z  - red
    (0,    0,  240),   # J  - blue
    (240, 160,   0),   # L  - orange
]

SHAPES = [
    None,
    [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],  # I
    [[2,2],[2,2]],                                # O
    [[0,3,0],[3,3,3],[0,0,0]],                    # T
    [[0,4,4],[4,4,0],[0,0,0]],                    # S
    [[5,5,0],[0,5,5],[0,0,0]],                    # Z
    [[6,0,0],[6,6,6],[0,0,0]],                    # J
    [[0,0,7],[7,7,7],[0,0,0]],                    # L
]

LEVEL_SPEED = [800, 700, 600, 500, 400, 300, 220, 150, 100, 70]


# ── Resource path (works both raw and inside PyInstaller EXE) ──────────────

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


# ── Helpers ────────────────────────────────────────────────────────────────

def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]


def new_bag():
    bag = list(range(1, 8))
    random.shuffle(bag)
    return bag


# ── Board ──────────────────────────────────────────────────────────────────

class Board:
    def __init__(self):
        self.grid = [[0] * COLS for _ in range(ROWS)]

    def valid(self, shape, ox, oy):
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    nx, ny = ox + c, oy + r
                    if nx < 0 or nx >= COLS or ny >= ROWS:
                        return False
                    if ny >= 0 and self.grid[ny][nx]:
                        return False
        return True

    def lock(self, shape, ox, oy, color_id):
        for r, row in enumerate(shape):
            for c, val in enumerate(row):
                if val:
                    self.grid[oy + r][ox + c] = color_id

    def clear_lines(self):
        full = [r for r in range(ROWS) if all(self.grid[r])]
        for r in full:
            del self.grid[r]
            self.grid.insert(0, [0] * COLS)
        return len(full)

    def draw(self, surf):
        for r in range(ROWS):
            for c in range(COLS):
                val = self.grid[r][c]
                rect = pygame.Rect(c * CELL, r * CELL, CELL - 1, CELL - 1)
                if val:
                    pygame.draw.rect(surf, COLORS[val], rect)
                    pygame.draw.rect(surf, WHITE, rect, 1)
                else:
                    # semi-transparent empty cell so background shows
                    cell_surf = pygame.Surface((CELL - 1, CELL - 1), pygame.SRCALPHA)
                    cell_surf.fill((0, 0, 0, 80))
                    surf.blit(cell_surf, rect.topleft)
                    pygame.draw.rect(surf, (60, 60, 60, 120), rect, 1)


# ── Piece ──────────────────────────────────────────────────────────────────

class Piece:
    def __init__(self, piece_id):
        self.id    = piece_id
        self.shape = [row[:] for row in SHAPES[piece_id]]
        self.x     = COLS // 2 - len(self.shape[0]) // 2
        self.y     = 0

    def draw(self, surf, ghost_y=None):
        if ghost_y is not None:
            for r, row in enumerate(self.shape):
                for c, val in enumerate(row):
                    if val:
                        rect = pygame.Rect((self.x + c) * CELL, (ghost_y + r) * CELL, CELL - 1, CELL - 1)
                        gs = pygame.Surface((CELL - 1, CELL - 1), pygame.SRCALPHA)
                        gs.fill((255, 255, 255, 40))
                        surf.blit(gs, rect.topleft)
                        pygame.draw.rect(surf, BORDER, rect, 1)
        for r, row in enumerate(self.shape):
            for c, val in enumerate(row):
                if val:
                    rect = pygame.Rect((self.x + c) * CELL, (self.y + r) * CELL, CELL - 1, CELL - 1)
                    pygame.draw.rect(surf, COLORS[val], rect)
                    pygame.draw.rect(surf, WHITE, rect, 1)

    def draw_preview(self, surf, px, py):
        bw = max(len(row) for row in self.shape)
        bh = len(self.shape)
        ox = px + (4 * CELL - bw * CELL) // 2
        oy = py + (4 * CELL - bh * CELL) // 2
        for r, row in enumerate(self.shape):
            for c, val in enumerate(row):
                if val:
                    rect = pygame.Rect(ox + c * CELL, oy + r * CELL, CELL - 1, CELL - 1)
                    pygame.draw.rect(surf, COLORS[val], rect)
                    pygame.draw.rect(surf, WHITE, rect, 1)


# ── Game ───────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.board     = Board()
        self.bag       = new_bag()
        self.next_bag  = new_bag()
        self.piece     = Piece(self.bag.pop())
        self.next_id   = self._pop_next()
        self.held_id   = None
        self.can_hold  = True
        self.score     = 0
        self.lines     = 0
        self.level     = 0
        self.over      = False
        self.paused    = False
        self.drop_timer = 0
        self.lock_timer = 0
        self.locking   = False

    def _pop_next(self):
        if not self.bag:
            self.bag = self.next_bag
            self.next_bag = new_bag()
        return self.bag.pop()

    def _spawn(self, piece_id):
        p = Piece(piece_id)
        if not self.board.valid(p.shape, p.x, p.y):
            self.over = True
        return p

    def _ghost_y(self):
        gy = self.piece.y
        while self.board.valid(self.piece.shape, self.piece.x, gy + 1):
            gy += 1
        return gy

    def hold(self):
        if not self.can_hold:
            return
        self.can_hold = False
        if self.held_id is None:
            self.held_id = self.piece.id
            nid = self.next_id
            self.next_id = self._pop_next()
            self.piece = self._spawn(nid)
        else:
            self.held_id, old = self.piece.id, self.held_id
            self.piece = self._spawn(old)
        self.locking = False

    def move(self, dx):
        nx = self.piece.x + dx
        if self.board.valid(self.piece.shape, nx, self.piece.y):
            self.piece.x = nx
            self.locking = False

    def rotate_piece(self):
        rot = rotate(self.piece.shape)
        kicks = [0, -1, 1, -2, 2]
        for k in kicks:
            if self.board.valid(rot, self.piece.x + k, self.piece.y):
                self.piece.shape = rot
                self.piece.x += k
                self.locking = False
                break

    def soft_drop(self):
        if self.board.valid(self.piece.shape, self.piece.x, self.piece.y + 1):
            self.piece.y += 1
            self.score += 1
            self.locking = False
        else:
            self.locking = True

    def hard_drop(self):
        gy = self._ghost_y()
        self.score += (gy - self.piece.y) * 2
        self.piece.y = gy
        self._lock()

    def _lock(self):
        self.board.lock(self.piece.shape, self.piece.x, self.piece.y, self.piece.id)
        cleared = self.board.clear_lines()
        pts = [0, 100, 300, 500, 800]
        self.score += pts[cleared] * (self.level + 1)
        self.lines += cleared
        self.level  = min(self.lines // 10, 9)
        nid = self.next_id
        self.next_id = self._pop_next()
        self.piece = self._spawn(nid)
        self.can_hold = True
        self.locking  = False
        self.lock_timer = 0

    def update(self, dt):
        if self.over or self.paused:
            return
        speed = LEVEL_SPEED[self.level]
        self.drop_timer += dt
        if self.drop_timer >= speed:
            self.drop_timer = 0
            if self.board.valid(self.piece.shape, self.piece.x, self.piece.y + 1):
                self.piece.y += 1
                self.locking = False
            else:
                self.locking = True

        if self.locking:
            self.lock_timer += dt
            if self.lock_timer >= 500:
                self._lock()
                self.lock_timer = 0
        else:
            self.lock_timer = 0


# ── Drawing ────────────────────────────────────────────────────────────────

def draw_sidebar(surf, game, font, small_font):
    bx = COLS * CELL + 10
    w  = SIDEBAR - 20

    # dark sidebar background
    sidebar_bg = pygame.Surface((SIDEBAR, HEIGHT), pygame.SRCALPHA)
    sidebar_bg.fill((0, 0, 0, 180))
    surf.blit(sidebar_bg, (COLS * CELL, 0))

    def label(text, y):
        surf.blit(small_font.render(text, True, (180, 180, 180)), (bx, y))

    def value(text, y):
        surf.blit(font.render(text, True, WHITE), (bx, y))

    label("NEXT", 10)
    pygame.draw.rect(surf, DARK_GRAY, (bx, 30, w, 4 * CELL + 4))
    Piece(game.next_id).draw_preview(surf, bx, 32)

    label("HOLD", 170)
    pygame.draw.rect(surf, DARK_GRAY, (bx, 190, w, 4 * CELL + 4))
    if game.held_id:
        p = Piece(game.held_id)
        if not game.can_hold:
            orig = COLORS[game.held_id]
            COLORS[game.held_id] = (80, 80, 80)
        p.draw_preview(surf, bx, 192)
        if not game.can_hold:
            COLORS[game.held_id] = orig

    label("SCORE", 340)
    value(str(game.score), 358)
    label("LEVEL", 400)
    value(str(game.level + 1), 418)
    label("LINES", 460)
    value(str(game.lines), 478)

    hints = ["Z  Rotate", "X  Hold", "Space HD", "P  Pause", "R  Restart"]
    for i, h in enumerate(hints):
        surf.blit(small_font.render(h, True, (100, 100, 100)), (bx, 530 + i * 18))


def draw_overlay(surf, text, sub, font, small_font):
    overlay = pygame.Surface((COLS * CELL, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surf.blit(overlay, (0, 0))
    tw = font.size(text)[0]
    surf.blit(font.render(text, True, WHITE), (COLS * CELL // 2 - tw // 2, HEIGHT // 2 - 30))
    sw = small_font.size(sub)[0]
    surf.blit(small_font.render(sub, True, (200, 200, 200)), (COLS * CELL // 2 - sw // 2, HEIGHT // 2 + 10))


# ── Touch buttons ─────────────────────────────────────────────────────────

BTN_LABELS  = ["<", "v", ">", "ROT", "HOLD", "DROP"]
BTN_ACTIONS = ["left", "down", "right", "rotate", "hold", "hard_drop"]

def _btn_rects(y):
    w = WIDTH // len(BTN_LABELS)
    return [pygame.Rect(i * w, y, w - 2, BTN_H - 2) for i in range(len(BTN_LABELS))]

def draw_touch_buttons(surf, font, y):
    pygame.draw.rect(surf, (20, 20, 20), (0, y, WIDTH, BTN_H))
    for rect, label in zip(_btn_rects(y), BTN_LABELS):
        pygame.draw.rect(surf, (60, 60, 60), rect, border_radius=8)
        pygame.draw.rect(surf, (120, 120, 120), rect, 2, border_radius=8)
        tw, th = font.size(label)
        surf.blit(font.render(label, True, WHITE),
                  (rect.centerx - tw // 2, rect.centery - th // 2))

def handle_touch(pos, game):
    x, y = pos
    btn_y = HEIGHT + HEADER
    if y < btn_y:
        return
    w = WIDTH // len(BTN_LABELS)
    idx = x // w
    if idx >= len(BTN_ACTIONS):
        return
    action = BTN_ACTIONS[idx]
    if action == "left":       game.move(-1)
    elif action == "right":    game.move(1)
    elif action == "down":     game.soft_drop()
    elif action == "rotate":   game.rotate_piece()
    elif action == "hold":     game.hold()
    elif action == "hard_drop": game.hard_drop()


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + HEADER + BTN_H))
    pygame.display.set_caption("Tetris Kars4Kids")
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("consolas", 22, bold=True)
    small  = pygame.font.SysFont("consolas", 14)

    # Load and scale background
    try:
        bg_raw = pygame.image.load(resource_path(BG_FILE)).convert()
        background = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
    except Exception:
        background = None

    # Load logo for header
    try:
        logo_raw = pygame.image.load(resource_path(LOGO_FILE)).convert_alpha()
        logo_h   = HEADER - 10
        logo_w   = int(logo_raw.get_width() * logo_h / logo_raw.get_height())
        logo     = pygame.transform.smoothscale(logo_raw, (logo_w, logo_h))
    except Exception:
        logo = None

    # Separate surface for the game area (so header doesn't shift coordinates)
    game_surf = pygame.Surface((WIDTH, HEIGHT))

    game = Game()

    das_delay  = 170
    das_repeat = 50
    das_left   = das_right = 0
    key_left   = key_right = False

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    game.paused = not game.paused
                if event.key == pygame.K_r:
                    game = Game()
                    key_left = key_right = False

                if not game.over and not game.paused:
                    if event.key == pygame.K_LEFT:
                        key_left = True; das_left = 0; game.move(-1)
                    if event.key == pygame.K_RIGHT:
                        key_right = True; das_right = 0; game.move(1)
                    if event.key == pygame.K_DOWN:
                        game.soft_drop()
                    if event.key == pygame.K_UP or event.key == pygame.K_z:
                        game.rotate_piece()
                    if event.key == pygame.K_SPACE:
                        game.hard_drop()
                    if event.key == pygame.K_x:
                        game.hold()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:  key_left  = False
                if event.key == pygame.K_RIGHT: key_right = False

            if ANDROID and event.type == pygame.MOUSEBUTTONDOWN:
                if not game.over and not game.paused:
                    handle_touch(event.pos, game)

        if not game.over and not game.paused:
            if key_left:
                das_left += dt
                if das_left >= das_delay + das_repeat:
                    game.move(-1); das_left -= das_repeat
            if key_right:
                das_right += dt
                if das_right >= das_delay + das_repeat:
                    game.move(1); das_right -= das_repeat

        game.update(dt)

        # Draw game onto game_surf
        if background:
            game_surf.blit(background, (0, 0))
        else:
            game_surf.fill(BLACK)

        game.board.draw(game_surf)
        if not game.over:
            gy = game._ghost_y()
            game.piece.draw(game_surf, ghost_y=gy if gy != game.piece.y else None)
        pygame.draw.rect(game_surf, BORDER, (0, 0, COLS * CELL, HEIGHT), 1)
        draw_sidebar(game_surf, game, font, small)

        if game.paused and not game.over:
            draw_overlay(game_surf, "PAUSED", "Press P to resume", font, small)
        if game.over:
            draw_overlay(game_surf, "GAME OVER", f"Score: {game.score}   Press R to restart", font, small)

        # Draw header
        screen.fill((255, 255, 255))
        pygame.draw.line(screen, (220, 220, 220), (0, HEADER - 1), (WIDTH, HEADER - 1), 2)
        if logo:
            lx = (WIDTH - logo.get_width()) // 2
            screen.blit(logo, (lx, 5))

        # Blit game below header
        screen.blit(game_surf, (0, HEADER))

        # Touch buttons (Android only)
        if ANDROID:
            draw_touch_buttons(screen, font, HEIGHT + HEADER)

        pygame.display.flip()


if __name__ == "__main__":
    main()
