import pygame
import sys
import math

# ====================== 配置 ======================
BOARD_SIZE = 15
GRID = 40
MARGIN = 40
MENU_HEIGHT = 28

SCREEN_WIDTH = MARGIN * 2 + GRID * (BOARD_SIZE - 1)
SCREEN_HEIGHT = MENU_HEIGHT + MARGIN * 2 + GRID * (BOARD_SIZE - 1)

# 高级棋盘
BOARD_BG = (194, 154, 84)
LINE_COLOR = (30, 30, 30)
STAR_POINT = (0, 0, 0)

# 菜单
MENU_BAR = (240, 240, 240)
MENU_PANEL = (255, 255, 255)
MENU_HOVER = (0, 0, 128)

# 游戏常量
PLAYER = 1
AI = 2
EMPTY = 0

# 游戏状态
GAME_RUNNING = 0
PLAYER_WIN = 1
AI_WIN = 2
DRAW = 3

# ====================== 音效 ======================
class SoundManager:
    """音效管理器"""
    def __init__(self):
        self.enabled = True
        try:
            # 生成简单的提示音（如果没有音频文件）
            self.click_sound = None
        except:
            self.enabled = False
    
    def play_click(self):
        """播放落子音效"""
        if self.enabled and self.click_sound:
            self.click_sound.play()
    
    def play_win(self):
        """播放胜利音效"""
        pass  # 可以扩展

# ====================== 计时器 ======================
class GameTimer:
    """游戏计时器"""
    def __init__(self):
        self.player_time = 0
        self.ai_time = 0
        self.start_time = 0
        self.is_running = False
    
    def start(self):
        self.start_time = pygame.time.get_ticks()
        self.is_running = True
    
    def stop(self):
        if self.is_running:
            elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0
            if elapsed < 100:  # 防止溢出
                self.player_time += elapsed
        self.is_running = False
    
    def get_player_time(self):
        if self.is_running:
            return self.player_time + (pygame.time.get_ticks() - self.start_time) / 1000.0
        return self.player_time
    
    def reset(self):
        self.player_time = 0
        self.ai_time = 0
        self.is_running = False
    
    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

# ====================== 游戏类 ======================
class GomokuGame:
    """五子棋游戏主类"""
    
    def __init__(self):
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.history = []
        self.game_state = GAME_RUNNING
        self.current_player = PLAYER
        self.step = 0
        self.winner = EMPTY
        self.ai_difficulty = 2  # 1=简单，2=困难
        
        self.sound_manager = SoundManager()
        self.timer = GameTimer()
        
        # UI 相关
        self.popup_show = False
        self.popup_text = ""
        self.menu_open = False
        self.active_menu = None
        self.mouse_pos = (0, 0)
        self.hover_pos = None  # 鼠标悬停位置
        
        # 初始化 Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("五子棋 - 人机对战")
        self.clock = pygame.time.Clock()
        
        # 字体
        self.font_large = pygame.font.SysFont("simhei", 60)
        self.font_menu = pygame.font.SysFont("simhei", 24)
        self.font_popup = pygame.font.SysFont("simhei", 32)
        self.font_small = pygame.font.SysFont("simhei", 18)
        
        # 菜单项
        self.main_menu = [
            {"name": "游戏", "items": ["新游戏", "悔棋", "难度", "退出"]},
            {"name": "帮助", "items": ["关于"]}
        ]
    
    def show_message(self, text):
        """显示弹窗消息"""
        self.popup_text = text
        self.popup_show = True
    
    def close_popup(self):
        """关闭弹窗"""
        self.popup_show = False
    
    def draw_popup(self):
        """绘制弹窗"""
        if not self.popup_show:
            return
        w, h = 300, 130
        x = (SCREEN_WIDTH - w) // 2
        y = (SCREEN_HEIGHT - h) // 2
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, w, h))
        pygame.draw.rect(self.screen, (0, 0, 0), (x, y, w, h), 2)
        
        txt = self.font_popup.render(self.popup_text, True, (0, 0, 0))
        ok = self.font_popup.render("确定", True, (0, 0, 0))
        
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, y + 45)))
        self.screen.blit(ok, ok.get_rect(center=(SCREEN_WIDTH // 2, y + 90)))

    def draw_menu_bar(self):
        """绘制菜单栏"""
        pygame.draw.rect(self.screen, MENU_BAR, (0, 0, SCREEN_WIDTH, MENU_HEIGHT))
        x = 8
        for i, item in enumerate(self.main_menu):
            txt = self.font_menu.render(item["name"], True, (0, 0, 0))
            if self.active_menu == i:
                pygame.draw.rect(self.screen, MENU_HOVER, (x - 3, 2, txt.get_width() + 6, 24))
                self.screen.blit(self.font_menu.render(item["name"], True, (255, 255, 255)), (x, 4))
            else:
                self.screen.blit(txt, (x, 4))
            x += txt.get_width() + 22
    
    def draw_drop_menus(self):
        """绘制下拉菜单"""
        if self.active_menu is None or not self.menu_open:
            return
        items = self.main_menu[self.active_menu]["items"]
        x0 = 8 + self.active_menu * 70
        y0 = MENU_HEIGHT
        mw, mh = 150, len(items) * 26
        pygame.draw.rect(self.screen, MENU_PANEL, (x0, y0, mw, mh))
        pygame.draw.rect(self.screen, (0, 0, 0), (x0, y0, mw, mh), 1)
        for i, txt in enumerate(items):
            tx, ty = x0 + 10, y0 + 4 + i * 26
            r = pygame.Rect(x0 + 2, ty - 2, mw - 4, 24)
            if r.collidepoint(self.mouse_pos):
                pygame.draw.rect(self.screen, MENU_HOVER, r)
                self.screen.blit(self.font_menu.render(txt, True, (255, 255, 255)), (tx, ty))
            else:
                self.screen.blit(self.font_menu.render(txt, True, (0, 0, 0)), (tx, ty))
    
    def check_menu_click(self, pos):
        """检查菜单点击"""
        x, y = pos
        if y > MENU_HEIGHT:
            if self.active_menu is not None and self.menu_open:
                x0 = 8 + self.active_menu * 70
                for i in range(len(self.main_menu[self.active_menu]["items"])):
                    if pygame.Rect(x0 + 2, MENU_HEIGHT + i * 26, 146, 24).collidepoint(pos):
                        self.menu_act(self.active_menu, i)
                        self.menu_open = False
                        self.active_menu = None
                        return True
            self.menu_open = False
            self.active_menu = None
            return False
        cx = 8
        for i, m in enumerate(self.main_menu):
            w = self.font_menu.size(m["name"])[0]
            if pygame.Rect(cx - 3, 2, w + 6, 24).collidepoint(pos):
                self.active_menu = i
                self.menu_open = not self.menu_open
                return True
            cx += w + 22
        self.active_menu = None
        self.menu_open = False
        return False
    
    def menu_act(self, m, i):
        """执行菜单动作"""
        if m == 0:  # 游戏菜单
            if i == 0:  # 新游戏
                self.restart()
            elif i == 1:  # 悔棋
                self.undo()
            elif i == 2:  # 难度
                self.toggle_difficulty()
            elif i == 3:  # 退出
                pygame.quit()
                sys.exit()
        elif m == 1:  # 帮助菜单
            if i == 0:  # 关于
                self.show_about()
    
    def toggle_difficulty(self):
        """切换难度"""
        self.ai_difficulty = 2 if self.ai_difficulty == 1 else 1
        diff_text = "困难" if self.ai_difficulty == 2 else "简单"
        self.show_message(f"当前难度：{diff_text}")
    
    def show_about(self):
        """显示关于信息"""
        self.show_message("五子棋 v2.0\n作者：AI 助手\n\n功能：人机对战、悔棋、难度选择")

    def draw_piece(self, x, y, is_black):
        """绘制棋子（带立体效果）"""
        ox = MENU_HEIGHT
        cx = MARGIN + x * GRID
        cy = ox + MARGIN + y * GRID
        r = GRID // 2 - 2
        
        if is_black:
            # 黑子：渐变立体效果
            for i in range(r, 0, -1):
                k = int(255 * (i / r) * 0.5)
                pygame.draw.circle(self.screen, (k, k, k), (cx, cy), i)
            pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy), r)
            # 高光
            pygame.draw.circle(self.screen, (80, 80, 80), (cx - r//3, cy - r//3), r//4)
        else:
            # 白子：描边效果
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), r)
            pygame.draw.circle(self.screen, (160, 160, 160), (cx, cy), r, 1)
            # 高光
            pygame.draw.circle(self.screen, (255, 255, 255), (cx - r//3, cy - r//3), r//4)
    
    def draw_board(self):
        """绘制棋盘"""
        oy = MENU_HEIGHT
        self.screen.fill(BOARD_BG)
        
        # 绘制网格线
        for i in range(BOARD_SIZE):
            pygame.draw.line(self.screen, LINE_COLOR, 
                           (MARGIN, oy + MARGIN + i * GRID), 
                           (SCREEN_WIDTH - MARGIN, oy + MARGIN + i * GRID), 1)
            pygame.draw.line(self.screen, LINE_COLOR, 
                           (MARGIN + i * GRID, oy + MARGIN), 
                           (MARGIN + i * GRID, oy + MARGIN + GRID * (BOARD_SIZE - 1)), 1)
        
        # 绘制星位点
        for x, y in [(7, 7), (3, 3), (3, 11), (11, 3), (11, 11)]:
            pygame.draw.circle(self.screen, STAR_POINT, 
                             (MARGIN + x * GRID, oy + MARGIN + y * GRID), 4)
        
        # 绘制最后一步标记
        if self.history:
            last_x, last_y = self.history[-1]
            cx = MARGIN + last_x * GRID
            cy = oy + MARGIN + last_y * GRID
            pygame.draw.circle(self.screen, (255, 0, 0), (cx, cy), 5, 2)

    def check_win(self, b, x, y, p):
        """检查是否获胜"""
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dx, dy in directions:
            count = 1
            # 正向检查
            for i in range(1, 5):
                nx, ny = x + dx * i, y + dy * i
                if 0 <= nx < 15 and 0 <= ny < 15 and b[ny][nx] == p:
                    count += 1
                else:
                    break
            # 反向检查
            for i in range(1, 5):
                nx, ny = x - dx * i, y - dy * i
                if 0 <= nx < 15 and 0 <= ny < 15 and b[ny][nx] == p:
                    count += 1
                else:
                    break
            if count >= 5:
                return True
        return False
    
    # 评分权重
    SCORE = {
        "FIVE": 1000000,      # 连五
        "FOUR": 100000,       # 活四
        "THREE": 10000,       # 活三
        "TWO": 1000,          # 活二
        "BLOCK_FOUR": 90000,  # 冲四
        "BLOCK_THREE": 9000,  # 眠三
        "BLOCK_TWO": 900      # 眠二
    }
    
    def evaluate_position(self, b, x, y, player):
        """评估某个位置的分数"""
        if b[y][x] != EMPTY:
            return -1
        
        my_score = 0
        opp_score = 0
        opponent = 3 - player
        
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        
        for dx, dy in directions:
            # 评估己方
            count, open_ends = self.count_line(b, x, y, dx, dy, player)
            my_score += self.get_line_score(count, open_ends, "my")
            
            # 评估对方
            count, open_ends = self.count_line(b, x, y, dx, dy, opponent)
            opp_score += self.get_line_score(count, open_ends, "opp")
        
        return my_score + opp_score
    
    def count_line(self, b, x, y, dx, dy, player):
        """统计某条线上的连续棋子数和开放端数"""
        count = 0
        open_ends = 0
        
        # 正向
        for i in range(1, 5):
            nx, ny = x + dx * i, y + dy * i
            if not (0 <= nx < 15 and 0 <= ny < 15):
                break
            if b[ny][nx] == player:
                count += 1
            elif b[ny][nx] == EMPTY:
                open_ends += 1
                break
            else:
                break
        
        # 反向
        for i in range(1, 5):
            nx, ny = x - dx * i, y - dy * i
            if not (0 <= nx < 15 and 0 <= ny < 15):
                break
            if b[ny][nx] == player:
                count += 1
            elif b[ny][nx] == EMPTY:
                open_ends += 1
                break
            else:
                break
        
        return count, open_ends
    
    def get_line_score(self, count, open_ends, side):
        """根据连子数和开放端获取分数"""
        if count >= 4:
            return self.SCORE["FOUR"] if open_ends >= 2 else self.SCORE["BLOCK_FOUR"]
        elif count == 3:
            if open_ends >= 2:
                return self.SCORE["THREE"]
            elif open_ends == 1:
                return self.SCORE["BLOCK_THREE"]
        elif count == 2:
            if open_ends >= 2:
                return self.SCORE["TWO"]
            elif open_ends == 1:
                return self.SCORE["BLOCK_TWO"]
        return 0

    def ai_move(self, b):
        """AI 决策落子位置"""
        best_score = -1
        best_x, best_y = 7, 7
        candidates = set()
        
        # 根据难度确定搜索范围
        search_radius = 2 if self.ai_difficulty == 2 else 1
        
        # 收集候选点
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if b[y][x] != EMPTY:
                    for dx in range(-search_radius, search_radius + 1):
                        for dy in range(-search_radius, search_radius + 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and b[ny][nx] == EMPTY:
                                candidates.add((nx, ny))
        
        # 如果没有候选点，下中心
        if not candidates:
            return 7, 7
        
        # 评估每个候选点
        for x, y in candidates:
            score = self.evaluate_position(b, x, y, AI)
            if score > best_score:
                best_score = score
                best_x, best_y = x, y
        
        return best_x, best_y
    
    def restart(self):
        """重新开始游戏"""
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.history = []
        self.game_state = GAME_RUNNING
        self.current_player = PLAYER
        self.step = 0
        self.winner = EMPTY
        self.timer.reset()
        print("=== 新游戏开始 ===")
    
    def undo(self):
        """悔棋"""
        if self.game_state != GAME_RUNNING or len(self.history) < 2:
            self.show_message("无法悔棋")
            return
        
        # 撤销两步（玩家和 AI 各一步）
        for _ in range(2):
            if self.history:
                x, y = self.history.pop()
                self.board[y][x] = EMPTY
        
        self.step -= 2
        self.current_player = PLAYER
        print(f"悔棋成功，当前步数：{self.step}")
    
    def draw_win(self):
        """绘制胜利信息"""
        if self.game_state != PLAYER_WIN and self.game_state != AI_WIN:
            return
        
        if self.game_state == PLAYER_WIN:
            text = "你赢了！"
            color = (0, 180, 0)
        else:
            text = "AI 赢了！"
            color = (220, 0, 0)
        
        surf = self.font_large.render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        pygame.draw.rect(self.screen, (255, 255, 255), rect.inflate(40, 20))
        pygame.draw.rect(self.screen, (0, 0, 0), rect.inflate(40, 20), 2)
        self.screen.blit(surf, rect)
    
    def draw_info(self):
        """绘制游戏信息（步数、时间）"""
        info_text = f"步数：{self.step}  |  用时：{self.timer.format_time(self.timer.get_player_time())}"
        info_surf = self.font_small.render(info_text, True, (0, 0, 0))
        self.screen.blit(info_surf, (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 20))

    def run(self):
        """游戏主循环"""
        self.restart()
        self.timer.start()
        
        while True:
            self.mouse_pos = pygame.mouse.get_pos()
            
            # 事件处理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.popup_show:
                        self.close_popup()
                        continue
                    
                    if self.check_menu_click(event.pos):
                        continue
                
                # 玩家落子
                if self.game_state == GAME_RUNNING and self.current_player == PLAYER and event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if my < MENU_HEIGHT:
                        continue
                    
                    x = round((mx - MARGIN) / GRID)
                    y = round((my - MENU_HEIGHT - MARGIN) / GRID)
                    
                    if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE and self.board[y][x] == EMPTY:
                        # 玩家落子
                        self.step += 1
                        self.board[y][x] = PLAYER
                        self.history.append((x, y))
                        self.sound_manager.play_click()
                        
                        coord = f"{chr(65 + x)}{y + 1}"
                        print(f"第 {self.step} 步：玩家 -> {coord}")
                        
                        if self.check_win(self.board, x, y, PLAYER):
                            self.game_state = PLAYER_WIN
                            self.winner = PLAYER
                            self.timer.stop()
                            print("*** 玩家获胜！ ***")
                        elif self.step == BOARD_SIZE * BOARD_SIZE:
                            self.game_state = DRAW
                            self.timer.stop()
                            print("*** 平局！ ***")
                        else:
                            self.current_player = AI
            
            # AI 回合
            if self.game_state == GAME_RUNNING and self.current_player == AI:
                ax, ay = self.ai_move(self.board)
                self.step += 1
                self.board[ay][ax] = AI
                self.history.append((ax, ay))
                self.sound_manager.play_click()
                
                coord = f"{chr(65 + ax)}{ay + 1}"
                print(f"第 {self.step} 步：AI -> {coord}")
                
                if self.check_win(self.board, ax, ay, AI):
                    self.game_state = AI_WIN
                    self.winner = AI
                    self.timer.stop()
                    print("*** AI 获胜！ ***")
                elif self.step == BOARD_SIZE * BOARD_SIZE:
                    self.game_state = DRAW
                    self.timer.stop()
                    print("*** 平局！ ***")
                else:
                    self.current_player = PLAYER
            
            # 绘制
            self.draw_board()
            
            # 绘制所有棋子
            for y in range(BOARD_SIZE):
                for x in range(BOARD_SIZE):
                    if self.board[y][x] == PLAYER:
                        self.draw_piece(x, y, True)
                    elif self.board[y][x] == AI:
                        self.draw_piece(x, y, False)
            
            # 绘制高亮（鼠标悬停）
            if self.game_state == GAME_RUNNING and self.current_player == PLAYER:
                mx, my = self.mouse_pos
                if my >= MENU_HEIGHT + MARGIN:
                    hx = round((mx - MARGIN) / GRID)
                    hy = round((my - MENU_HEIGHT - MARGIN) / GRID)
                    if 0 <= hx < BOARD_SIZE and 0 <= hy < BOARD_SIZE and self.board[hy][hx] == EMPTY:
                        # 半透明预览
                        cx = MARGIN + hx * GRID
                        cy = MENU_HEIGHT + MARGIN + hy * GRID
                        s = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
                        pygame.draw.circle(s, (0, 0, 0, 100), (GRID // 2, GRID // 2), GRID // 2 - 2)
                        self.screen.blit(s, (cx - GRID // 2, cy - GRID // 2))
            
            self.draw_win()
            self.draw_info()
            self.draw_menu_bar()
            self.draw_drop_menus()
            self.draw_popup()
            
            pygame.display.flip()
            self.clock.tick(30)


# ====================== 主程序入口 ======================
if __name__ == "__main__":
    game = GomokuGame()
    game.run()