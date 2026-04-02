import pygame
import sys
import math
import threading
import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# 导入 GUI 组件
try:
    from gui_components import (
        FadeAnimation,
        ScaleAnimation,
        UIMenuItem,
        UIPopup,
        UINotification,
        PieceAnimation,
        EmojiFont  # Emoji 字体支持
    )
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("警告：gui_components.py 未找到，使用基础 UI")

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
        self.volume = 0.5  # 默认音量 50%
        try:
            pygame.mixer.init()
            # 生成简单的提示音
            self.click_sound = self.generate_click_sound()
            self.win_sound = self.generate_win_sound()
        except:
            self.enabled = False
            self.click_sound = None
            self.win_sound = None
    
    def generate_click_sound(self):
        """生成落子音效（简单频率）"""
        # 简化处理，使用系统声音或静音
        return None
    
    def generate_win_sound(self):
        """生成胜利音效"""
        return None
    
    def play_click(self):
        """播放落子音效"""
        if self.enabled and self.click_sound:
            self.click_sound.set_volume(self.volume)
            self.click_sound.play()
    
    def play_win(self):
        """播放胜利音效"""
        if self.enabled and self.win_sound:
            self.win_sound.set_volume(self.volume)
            self.win_sound.play()
    
    def set_volume(self, volume):
        """设置音量 (0.0-1.0)"""
        self.volume = max(0.0, min(1.0, volume))

# ====================== 计时器 ======================
class GameTimer:
    """游戏计时器"""
    def __init__(self):
        self.player_time = 0
        self.ai_time = 0
        self.start_time = 0
        self.is_running = False
        self.last_move_time = 0  # 最后一步用时
    
    def start(self):
        self.start_time = pygame.time.get_ticks()
        self.is_running = True
    
    def stop(self):
        if self.is_running:
            elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0
            if elapsed < 100:  # 防止溢出
                self.last_move_time = elapsed
                self.player_time += elapsed
        self.is_running = False
    
    def lap(self, is_ai=False):
        """计圈，记录当前步用时"""
        if self.is_running:
            elapsed = (pygame.time.get_ticks() - self.start_time) / 1000.0
            if elapsed < 100:
                self.last_move_time = elapsed
                if is_ai:
                    self.ai_time += elapsed
                else:
                    self.player_time += elapsed
                self.start_time = pygame.time.get_ticks()
    
    def get_player_time(self):
        if self.is_running:
            return self.player_time + (pygame.time.get_ticks() - self.start_time) / 1000.0
        return self.player_time
    
    def reset(self):
        self.player_time = 0
        self.ai_time = 0
        self.last_move_time = 0
        self.is_running = False
    
    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

# ====================== 战绩统计 ======================
class Statistics:
    """游戏战绩统计"""
    def __init__(self):
        self.games_played = 0
        self.player_wins = 0
        self.ai_wins = 0
        self.draws = 0
        self.total_steps = 0
        self.total_time = 0.0
    
    def record_game(self, result, steps, player_time):
        """记录一局游戏"""
        self.games_played += 1
        self.total_steps += steps
        self.total_time += player_time
        
        if result == PLAYER_WIN:
            self.player_wins += 1
        elif result == AI_WIN:
            self.ai_wins += 1
        else:
            self.draws += 1
    
    def get_win_rate(self):
        """获取胜率"""
        if self.games_played == 0:
            return 0.0
        return (self.player_wins / self.games_played) * 100
    
    def get_avg_steps(self):
        """获取平均步数"""
        if self.games_played == 0:
            return 0
        return self.total_steps / self.games_played
    
    def get_avg_time(self):
        """获取平均每局用时"""
        if self.games_played == 0:
            return 0.0
        return self.total_time / self.games_played
    
    @staticmethod
    def format_time(seconds):
        """格式化时间为 MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'games_played': self.games_played,
            'player_wins': self.player_wins,
            'ai_wins': self.ai_wins,
            'draws': self.draws,
            'total_steps': self.total_steps,
            'total_time': self.total_time
        }
    
    def from_dict(self, data):
        """从字典加载"""
        self.games_played = data.get('games_played', 0)
        self.player_wins = data.get('player_wins', 0)
        self.ai_wins = data.get('ai_wins', 0)
        self.draws = data.get('draws', 0)
        self.total_steps = data.get('total_steps', 0)
        self.total_time = data.get('total_time', 0.0)

# ====================== 配置管理 ======================
# ====================== 配置管理 ======================
class ConfigManager:
    """配置管理器"""
    def __init__(self):
        self.config_file = "config.json"
        self.config = {
            'difficulty': 2,  # 1=简单，2=困难
            'volume': 0.5,    # 音量 0.0-1.0
            'theme': 'classic',  # 主题：classic, bamboo, stone, dark
            'window_size': (SCREEN_WIDTH, SCREEN_HEIGHT),
            'fullscreen': False
        }
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                print(f"✓ 配置已加载：{self.config_file}")
        except Exception as e:
            print(f"✗ 加载配置失败：{e}")
    
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✓ 配置已保存：{self.config_file}")
        except Exception as e:
            print(f"✗ 保存配置失败：{e}")
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)

# ====================== 主题系统 ======================
class ThemeManager:
    """主题管理器"""
    def __init__(self):
        self.themes = {
            'classic': {  # 经典木质
                'name': '经典木质',
                'board_bg': (194, 154, 84),
                'line_color': (30, 30, 30),
                'star_point': (0, 0, 0),
                'piece_black_gradient': True,
                'piece_white_outline': True
            },
            'bamboo': {  # 竹制风格
                'name': '清新竹制',
                'board_bg': (210, 180, 140),
                'line_color': (60, 40, 20),
                'star_point': (80, 50, 20),
                'piece_black_gradient': True,
                'piece_white_outline': False
            },
            'stone': {  # 石制风格
                'name': '古朴石制',
                'board_bg': (128, 128, 128),
                'line_color': (200, 200, 200),
                'star_point': (180, 180, 180),
                'piece_black_gradient': False,
                'piece_white_outline': True
            },
            'dark': {  # 深色主题
                'name': '深色竞技',
                'board_bg': (40, 40, 60),
                'line_color': (200, 200, 220),
                'star_point': (255, 200, 100),
                'piece_black_gradient': True,
                'piece_white_outline': True
            }
        }
        self.current_theme = 'classic'
    
    def set_theme(self, theme_name):
        """切换主题"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            return self.themes[theme_name]
        return self.themes['classic']
    
    def get_current_colors(self):
        """获取当前主题颜色"""
        theme = self.themes[self.current_theme]
        return {
            'board_bg': theme['board_bg'],
            'line_color': theme['line_color'],
            'star_point': theme['star_point']
        }

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
        self.move_records = []  # 棋谱记录
        
        # 新增功能模块
        self.statistics = Statistics()  # 战绩统计
        self.config_manager = ConfigManager()  # 配置管理
        self.theme_manager = ThemeManager()  # 主题管理
        
        # AI 相关
        self.ai_thinking = False
        self.ai_move_result = None
        self.ai_thread = None
        
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
        
        # 字体（强制使用支持 emoji 的字体）
        try:
            from gui_components import EmojiFont
            self.font_large = EmojiFont.get_font(60)
            self.font_menu = EmojiFont.get_font(24)
            self.font_popup = EmojiFont.get_font(32)
            self.font_small = EmojiFont.get_font(18)
            print("✓ 所有字体已使用 EmojiFont")
            
            # 测试 emoji 渲染
            test_surface = self.font_menu.render("测试", True, (0, 0, 0))
            print(f"✓ 字体测试 - 文字渲染宽度：{test_surface.get_width()}")
        except Exception as e:
            print(f"⚠️ EmojiFont 加载失败：{e}，使用备用方案")
            # 备用方案：使用 seguisym
            try:
                self.font_large = pygame.font.SysFont('seguisym', 60)
                self.font_menu = pygame.font.SysFont('seguisym', 24)
                self.font_popup = pygame.font.SysFont('seguisym', 32)
                self.font_small = pygame.font.SysFont('seguisym', 18)
                print("✓ 使用 Segoe UI Symbol 字体")
            except:
                # 最后的备用
                self.font_large = pygame.font.SysFont("microsoft yahei", 60)
                self.font_menu = pygame.font.SysFont("microsoft yahei", 24)
                self.font_popup = pygame.font.SysFont("microsoft yahei", 32)
                self.font_small = pygame.font.SysFont("microsoft yahei", 18)
                print("✓ 使用微软雅黑字体")
        
        # 菜单项
        self.main_menu = [
            {"name": "游戏", "items": [
                {"text": "新游戏", "shortcut": "F2"},
                {"text": "悔棋", "shortcut": "Ctrl+Z"},
                {"text": "-"},  # 分隔线
                {"text": "切换难度", "sub": f"{'困难' if self.ai_difficulty == 2 else '简单'}"},
                {"text": "切换主题", "sub": self.theme_manager.themes[self.theme_manager.current_theme]['name']},
                {"text": "-"},  # 分隔线
                {"text": "保存棋谱"},
                {"text": "查看战绩"},
                {"text": "-"},  # 分隔线
                {"text": "退出", "shortcut": "Alt+F4"}
            ]},
            {"name": "帮助", "items": [
                {"text": "关于"},
                {"text": "操作说明"}
            ]}
        ]
        
        # 菜单动画相关
        self.menu_animation = 0.0  # 0.0-1.0 完成度
        self.menu_animating = False
        self.menu_target_height = 0
        
        # GUI 组件
        self.popup = None  # 精美弹窗
        self.notification = None  # 通知提示
        self.piece_animations = []  # 棋子动画列表
    
    def show_message(self, text, transparent_bg=False, show_new_game=False):
        """显示精美弹窗"""
        self.popup_show = True
        
        if GUI_AVAILABLE:
            # 分割标题和内容
            lines = text.split('\n')
            title = lines[0]
            content = '\n'.join(lines[1:]) if len(lines) > 1 else ""
            
            self.popup = UIPopup(
                self.screen,
                title=title,
                message=content,
                font_large=self.font_popup,
                font_small=self.font_small,
                transparent_bg=transparent_bg,
                show_new_game=show_new_game
            )
        else:
            # 基础版本（向后兼容）
            self.popup_text = text
    
    def close_popup(self):
        """关闭弹窗"""
        self.popup_show = False
    
    def draw_popup(self):
        """绘制弹窗（增强版）"""
        if not self.popup_show:
            return
        
        if GUI_AVAILABLE and hasattr(self, 'popup') and self.popup:
            # 更新并绘制精美弹窗
            dt = self.clock.get_time() / 1000.0
            self.popup.update(dt)
            self.popup.draw(self.screen)
        else:
            # 基础版本（向后兼容）
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
        """绘制菜单栏（带渐变效果）"""
        # 渐变背景
        for y in range(MENU_HEIGHT):
            alpha = int(240 - y * 0.5)
            color = (min(alpha, 255), min(alpha, 255), min(alpha + 20, 255))
            pygame.draw.line(self.screen, color, (0, y), (SCREEN_WIDTH, y))
        
        # 底部边框
        pygame.draw.line(self.screen, (180, 180, 180), (0, MENU_HEIGHT-1), (SCREEN_WIDTH, MENU_HEIGHT-1), 1)
        
        x = 12
        for i, item in enumerate(self.main_menu):
            txt = self.font_menu.render(item["name"], True, (0, 0, 0))
            
            # 悬停效果
            txt_rect = txt.get_rect(topleft=(x, 4))
            is_hover = txt_rect.collidepoint(self.mouse_pos)
            
            if self.active_menu == i or is_hover:
                # 圆角矩形背景
                padding = 6
                bg_rect = pygame.Rect(
                    x - padding, 
                    2, 
                    txt.get_width() + padding * 2, 
                    24
                )
                
                # 渐变背景
                if self.active_menu == i:
                    # 选中状态：蓝色渐变
                    for gy in range(24):
                        color_intensity = int(100 + 155 * (gy / 24))
                        pygame.draw.line(self.screen, (0, 0, color_intensity), 
                                       (bg_rect.left, bg_rect.top + gy), 
                                       (bg_rect.right, bg_rect.top + gy))
                else:
                    # 悬停状态：浅灰色
                    pygame.draw.rect(self.screen, (230, 230, 250), bg_rect, border_radius=4)
                
                # 边框
                pygame.draw.rect(self.screen, (100, 100, 150) if self.active_menu == i else (200, 200, 200), 
                               bg_rect, 1, border_radius=4)
                
                # 文字（选中时白色，否则黑色）
                text_color = (255, 255, 255) if self.active_menu == i else (0, 0, 0)
                text_surf = self.font_menu.render(item["name"], True, text_color)
                self.screen.blit(text_surf, (x, 4))
            else:
                self.screen.blit(txt, (x, 4))
            
            x += txt.get_width() + 28
    
    def draw_drop_menus(self):
        """绘制下拉菜单（带动画和图标）"""
        if self.active_menu is None or not self.menu_open:
            return
        
        items = self.main_menu[self.active_menu]["items"]
        x0 = 12 + self.active_menu * 85
        y0 = MENU_HEIGHT
        mw, mh = 200, len(items) * 32 + 10
        
        # 阴影效果
        for shadow_x in range(3, 0, -1):
            shadow_surface = pygame.Surface((mw + shadow_x * 2, mh + shadow_x * 2), pygame.SRCALPHA)
            alpha = int(30 * (1 - shadow_x / 3))
            pygame.draw.rect(shadow_surface, (0, 0, 0, alpha), 
                           (shadow_x * 2, shadow_x * 2, mw, mh), border_radius=5)
            self.screen.blit(shadow_surface, (x0 - shadow_x * 2, y0 + shadow_x * 2))
        
        # 主菜单背景
        pygame.draw.rect(self.screen, (255, 255, 255), (x0, y0, mw, mh), border_radius=5)
        
        # 边框
        pygame.draw.rect(self.screen, (150, 150, 150), (x0, y0, mw, mh), 2, border_radius=5)
        
        # 顶部标题栏
        title_y = y0 + 5
        pygame.draw.line(self.screen, (200, 200, 200), (x0 + 10, title_y), (x0 + mw - 10, title_y), 1)
        
        for i, item_data in enumerate(items):
            if item_data["text"] == "-":
                # 分隔线
                sep_y = y0 + 8 + i * 32
                pygame.draw.line(self.screen, (220, 220, 220), (x0 + 10, sep_y + 14), 
                               (x0 + mw - 10, sep_y + 14), 1)
                continue
            
            tx, ty = x0 + 15, y0 + 8 + i * 32
            
            # 检查是否悬停
            r = pygame.Rect(x0 + 5, ty - 2, mw - 10, 30)
            is_hover = r.collidepoint(self.mouse_pos)
            
            if is_hover:
                # 悬停高亮
                hover_surface = pygame.Surface((mw - 10, 30), pygame.SRCALPHA)
                pygame.draw.rect(hover_surface, (230, 240, 255, 180), (0, 0, mw - 10, 30), border_radius=3)
                self.screen.blit(hover_surface, (x0 + 5, ty - 2))
            
            # 绘制文字
            text_color = (0, 0, 0) if is_hover else (30, 30, 30)
            text_surf = self.font_menu.render(item_data["text"], True, text_color)
            self.screen.blit(text_surf, (tx, ty))
            
            # 绘制子菜单提示或快捷键
            rx = x0 + mw - 15
            if "sub" in item_data:
                sub_surf = self.font_small.render(item_data["sub"], True, (100, 100, 100))
                self.screen.blit(sub_surf, (rx - sub_surf.get_width(), ty + 2))
            elif "shortcut" in item_data:
                shortcut_surf = self.font_small.render(item_data["shortcut"], True, (150, 150, 150))
                self.screen.blit(shortcut_surf, (rx - shortcut_surf.get_width(), ty + 2))
    
    def check_menu_click(self, pos):
        """检查菜单点击（支持分隔线和更多功能）"""
        x, y = pos
        if y > MENU_HEIGHT:
            if self.active_menu is not None and self.menu_open:
                x0 = 12 + self.active_menu * 85
                items = self.main_menu[self.active_menu]["items"]
                for i, item_data in enumerate(items):
                    if item_data["text"] == "-":
                        continue  # 跳过分隔线
                    item_rect = pygame.Rect(x0 + 5, MENU_HEIGHT + 8 + i * 32 - 2, 190, 30)
                    if item_rect.collidepoint(pos):
                        self.menu_act(self.active_menu, i, item_data)
                        self.menu_open = False
                        self.active_menu = None
                        return True
            self.menu_open = False
            self.active_menu = None
            return False
        
        cx = 12
        for i, m in enumerate(self.main_menu):
            w = self.font_menu.size(m["name"])[0]
            if pygame.Rect(cx - 6, 2, w + 12, 24).collidepoint(pos):
                self.active_menu = i
                self.menu_open = not self.menu_open
                return True
            cx += w + 28
        
        self.active_menu = None
        self.menu_open = False
        return False
    
    def menu_act(self, m, i, item_data):
        """执行菜单动作（增强版）"""
        try:
            action = item_data["text"]
            
            if m == 0:  # 游戏菜单
                if action == "新游戏":
                    self.restart()
                elif action == "悔棋":
                    self.undo()
                elif action == "切换难度":
                    self.toggle_difficulty()
                    # 更新菜单显示
                    self.main_menu[0]["items"][3]["sub"] = "困难" if self.ai_difficulty == 2 else "简单"
                elif action == "切换主题":
                    self.toggle_theme()
                    # 更新菜单显示
                    current_theme_name = self.theme_manager.themes[self.theme_manager.current_theme]['name']
                    self.main_menu[0]["items"][5]["sub"] = current_theme_name
                elif action == "保存棋谱":
                    self.save_game_record()
                elif action == "查看战绩":
                    self.show_statistics()
                elif action == "退出":
                    pygame.quit()
                    sys.exit()
            elif m == 1:  # 帮助菜单
                if action == "关于":
                    self.show_about()
                elif action == "操作说明":
                    self.show_help()
        except Exception as e:
            print(f"菜单操作出错：{type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.show_message(f"❌ 操作失败\n{type(e).__name__}\n{str(e)}")
    
    def toggle_theme(self):
        """切换主题"""
        themes = list(self.theme_manager.themes.keys())
        current_index = themes.index(self.theme_manager.current_theme)
        next_index = (current_index + 1) % len(themes)
        next_theme = themes[next_index]
        
        self.theme_manager.set_theme(next_theme)
        colors = self.theme_manager.get_current_colors()
        
        # 更新全局颜色
        global BOARD_BG, LINE_COLOR, STAR_POINT
        BOARD_BG = colors['board_bg']
        LINE_COLOR = colors['line_color']
        STAR_POINT = colors['star_point']
        
        theme_name = self.theme_manager.themes[next_theme]['name']
        self.show_message(f"✓ 已切换主题\n\n{theme_name}")
    
    def show_statistics(self):
        """显示战绩统计"""
        stats = self.statistics
        win_rate = stats.get_win_rate()
        avg_steps = stats.get_avg_steps()
        avg_time = stats.format_time(stats.get_avg_time()) if hasattr(stats, 'format_time') else f"{avg_time:.1f}秒"
        
        stat_text = (
            f"战绩统计\n\n"
            f"总对局：{stats.games_played} 场\n"
            f"胜：{stats.player_wins} 场\n"
            f"负：{stats.ai_wins} 场\n"
            f"平：{stats.draws} 场\n\n"
            f"胜率：{win_rate:.1f}%\n"
            f"平均步数：{avg_steps:.1f}\n"
            f"平均用时：{avg_time}"
        )
        self.show_message(stat_text)
    
    def show_help(self):
        """显示操作说明"""
        help_text = (
            f"操作说明\n\n"
            f"【基本操作】\n"
            f"• 鼠标左键点击棋盘落子\n"
            f"• 黑棋（玩家）先行\n\n"
            f"【快捷键】\n"
            f"• F2 - 新游戏\n"
            f"• Ctrl+Z - 悔棋\n"
            f"• Alt+F4 - 退出\n\n"
            f"【菜单功能】\n"
            f"• 可以切换难度和主题\n"
            f"• 自动保存每局棋谱\n"
            f"• 随时查看战绩统计"
        )
        self.show_message(help_text)
    
    def toggle_difficulty(self):
        """切换难度"""
        self.ai_difficulty = 2 if self.ai_difficulty == 1 else 1
        diff_text = "困难" if self.ai_difficulty == 2 else "简单"
        self.show_message(f"当前难度：{diff_text}")
    
    def show_about(self):
        """显示关于信息"""
        self.show_message("五子棋 v2.0\n作者：AI 助手\n\n功能：人机对战、悔棋、难度选择\n       保存棋谱、思考时间显示")
    
    def auto_save_record(self, force_save=False):
        """自动保存棋谱（静默保存，不显示提示）
        
        Args:
            force_save: 是否强制保存（游戏结束时使用）
        """
        if not self.move_records:
            return
        
        # 游戏进行中不保存，只在游戏结束时保存
        if not force_save and self.game_state == GAME_RUNNING:
            return
        
        try:
            import os
            import time
            
            # 使用时间戳文件名，格式：gomoku_20240402_143052.txt
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(os.getcwd(), f"gomoku_{timestamp}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("╔══════════════════════════════════════════╗\n")
                f.write("║               五子棋棋谱                  ║\n")
                f.write("╚══════════════════════════════════════════╝\n\n")
                f.write(f"对局时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总步数：{self.step}\n")
                result_text = '玩家获胜' if self.game_state == PLAYER_WIN else 'AI 获胜' if self.game_state == AI_WIN else '平局'
                f.write(f"结果：{result_text}\n")
                f.write(f"玩家用时：{self.timer.format_time(self.timer.player_time)}\n")
                f.write(f"AI 用时：{self.timer.format_time(self.timer.ai_time)}\n")
                f.write(f"难度：{'困难' if self.ai_difficulty == 2 else '简单'}\n")
                f.write(f"保存时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n" + "═" * 50 + "\n\n")
                
                for i, record in enumerate(self.move_records, 1):
                    move_type = "● 玩家" if record['player'] == PLAYER else "○ AI"
                    time_used = record.get('time', 0)
                    f.write(f"第{i:3d}步 {move_type:6s} -> {record['coord']:4s} "
                           f"(用时：{time_used:>5.2f}秒)\n")
            
            # 只在控制台输出，不弹窗提示
            print(f"[自动保存] 对局结束 -> {filename.split(os.sep)[-1]}")
            
        except Exception as e:
            # 自动保存失败不弹窗，只记录日志
            print(f"[自动保存失败] {type(e).__name__}: {str(e)}")
    
    def save_game_record(self):
        """手动保存棋谱到文件（带提示）"""
        if not self.move_records:
            self.show_message("还没有落子记录\n请先开始游戏")
            return
        
        try:
            import os
            import time
            
            # 生成带时间戳的文件名，格式：gomoku_20240402_143052.txt
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(os.getcwd(), f"gomoku_{timestamp}.txt")
            
            print(f"准备保存棋谱到：{filename}")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("╔══════════════════════════════════════════╗\n")
                f.write("║          五子棋棋谱                      ║\n")
                f.write("╚══════════════════════════════════════════╝\n\n")
                f.write(f"对局时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总步数：{self.step}\n")
                result_text = '玩家获胜' if self.game_state == PLAYER_WIN else 'AI 获胜' if self.game_state == AI_WIN else '平局'
                f.write(f"结果：{result_text}\n")
                f.write(f"玩家用时：{self.timer.format_time(self.timer.player_time)}\n")
                f.write(f"AI 用时：{self.timer.format_time(self.timer.ai_time)}\n")
                f.write(f"难度：{'困难' if self.ai_difficulty == 2 else '简单'}\n")
                f.write("\n" + "═" * 50 + "\n\n")
                
                for i, record in enumerate(self.move_records, 1):
                    move_type = "● 玩家" if record['player'] == PLAYER else "○ AI"
                    time_used = record.get('time', 0)
                    f.write(f"第{i:3d}步 {move_type:6s} -> {record['coord']:4s} "
                           f"(用时：{time_used:>5.2f}秒)\n")
            
            # 关闭弹窗，避免重复显示
            self.popup_show = False
            
            # 使用精美通知（不阻塞游戏）
            if GUI_AVAILABLE:
                self.notification = UINotification(
                    self.screen,
                    "💾 棋谱已保存",
                    position='bottom-center',
                    duration=2.0
                )
            else:
                self.show_message("✓ 保存成功！")
            
            print(f"✓ 棋谱已保存到：{filename}")
            
        except PermissionError as e:
            error_msg = f"❌ 保存失败\n\n没有写入权限\n请检查文件夹权限设置"
            self.show_message(error_msg)
            print(f"✗ 保存棋谱失败（权限错误）：{str(e)}")
        except FileNotFoundError as e:
            error_msg = f"❌ 保存失败\n\n路径不存在\n{str(e)}"
            self.show_message(error_msg)
            print(f"✗ 保存棋谱失败（路径错误）：{str(e)}")
        except Exception as e:
            error_msg = f"❌ 保存失败\n\n{type(e).__name__}\n{str(e)}"
            self.show_message(error_msg)
            print(f"✗ 保存棋谱失败（未知错误）：{str(e)}")
            import traceback
            traceback.print_exc()

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
        
        # 绘制棋子（静态）
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if self.board[y][x] != EMPTY:
                    cx = MARGIN + x * GRID
                    cy = oy + MARGIN + y * GRID
                    r = GRID // 2 - 2
                    
                    if self.board[y][x] == PLAYER:  # 黑子
                        # 渐变效果
                        for i in range(r, 0, -1):
                            k = int(255 * (i / r) * 0.5)
                            pygame.draw.circle(self.screen, (k, k, k), (cx, cy), i)
                        # 高光
                        pygame.draw.circle(self.screen, (255, 255, 255), 
                                         (cx - r//3, cy - r//3), r//4)
                    else:  # 白子
                        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), r)
                        pygame.draw.circle(self.screen, (160, 160, 160), (cx, cy), r, 1)
        
        # 绘制棋子动画（动态）
        if GUI_AVAILABLE:
            dt = self.clock.get_time() / 1000.0
            for anim in self.piece_animations[:]:
                anim.update(dt)
                anim.draw(self.screen, grid_size=GRID)
                if anim.finished:
                    self.piece_animations.remove(anim)

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
        """AI 决策落子位置（可在后台运行）"""
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
    
    def calculate_ai_move_async(self):
        """在后台线程中计算 AI 落子"""
        self.ai_move_result = self.ai_move(self.board)
        self.ai_thinking = False
    
    def restart(self):
        """重新开始游戏"""
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.history = []
        self.move_records = []
        self.game_state = GAME_RUNNING
        self.current_player = PLAYER
        self.step = 0
        self.winner = EMPTY
        self.timer.reset()
        self.ai_thinking = False
        self.ai_move_result = None
        self.ai_thread = None
        
        # 更新菜单中的难度显示
        self.main_menu[0]["items"][3]["sub"] = "困难" if self.ai_difficulty == 2 else "简单"
        
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
        """绘制胜利信息（已禁用，使用弹窗代替）"""
        # 不再显示，改用透明背景弹窗
        pass
    
    def draw_info(self):
        """绘制游戏信息（步数、时间）"""
        # 精简显示格式，避免溢出
        player_time_str = self.timer.format_time(self.timer.get_player_time())
        ai_time_str = self.timer.format_time(self.timer.ai_time)
        
        info_text = f"步数:{self.step} | 玩家:{player_time_str} | AI:{ai_time_str}"
        info_surf = self.font_small.render(info_text, True, (0, 0, 0))
        
        # 动态调整位置，确保不溢出
        text_width = info_surf.get_width()
        x_pos = max(10, SCREEN_WIDTH - text_width - 10)
        self.screen.blit(info_surf, (x_pos, SCREEN_HEIGHT - 20))
        
        # 显示最后一步用时（左侧）
        if self.move_records:
            last_record = self.move_records[-1]
            player_name = '玩家' if last_record['player'] == PLAYER else 'AI'
            time_text = f"上步:{player_name} {last_record['time']:.1f}秒"
            time_surf = self.font_small.render(time_text, True, (0, 0, 0))
            self.screen.blit(time_surf, (10, SCREEN_HEIGHT - 20))

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
                
                # 处理游戏结束弹窗显示
                if event.type == pygame.USEREVENT + 1:
                    if self.game_state in [PLAYER_WIN, AI_WIN, DRAW]:
                        if self.game_state == PLAYER_WIN:
                            self.show_message("获胜！\n\n恭喜您赢得了比赛！\n\n", transparent_bg=False, show_new_game=True)
                        elif self.game_state == AI_WIN:
                            self.show_message("失败！\n\nAI 赢得了比赛！\n\n", transparent_bg=False, show_new_game=True)
                        else:  # DRAW
                            self.show_message("平局！\n\n双方握手言和！\n\n", transparent_bg=False, show_new_game=True)
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # 关闭定时器
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 检查是否点击了弹窗
                    if self.popup_show and GUI_AVAILABLE and hasattr(self, 'popup') and self.popup:
                        result = self.popup.handle_click(event.pos)
                        if result == 'ok':
                            # 点击查看棋谱 - 关闭弹窗即可（棋谱已自动保存）
                            self.close_popup()
                            continue
                        elif result == 'new_game':
                            # 点击新游戏，重新开始
                            self.restart()
                            continue
                        elif result is True:  # 兼容旧的返回值
                            self.close_popup()
                            continue
                    elif self.popup_show:
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
                        self.timer.lap(is_ai=False)
                        move_time = self.timer.last_move_time
                        
                        self.step += 1
                        self.board[y][x] = PLAYER
                        self.history.append((x, y))
                        self.sound_manager.play_click()
                        
                        # 添加棋子动画
                        if GUI_AVAILABLE:
                            cx = MARGIN + x * GRID
                            cy = MENU_HEIGHT + MARGIN + y * GRID
                            anim = PieceAnimation(cx, cy, is_black=True)
                            self.piece_animations.append(anim)
                        
                        coord = f"{chr(65 + x)}{y + 1}"
                        record = {
                            'step': self.step,
                            'player': PLAYER,
                            'coord': coord,
                            'time': move_time
                        }
                        self.move_records.append(record)
                        print(f"第 {self.step} 步：玩家 -> {coord} (用时：{move_time:.2f}秒)")
                        
                        # 自动保存棋谱
                        self.auto_save_record()
                        
                        if self.check_win(self.board, x, y, PLAYER):
                            self.game_state = PLAYER_WIN
                            self.winner = PLAYER
                            self.timer.stop()
                            # 游戏结束，自动保存完整棋谱
                            self.auto_save_record(force_save=True)
                            # 显示获胜弹窗（延迟一点显示，让玩家看到最后一步）
                            pygame.time.set_timer(pygame.USEREVENT + 1, 500)  # 500ms 后显示
                        elif self.step == BOARD_SIZE * BOARD_SIZE:
                            self.game_state = DRAW
                            self.timer.stop()
                            # 游戏结束，自动保存完整棋谱
                            self.auto_save_record(force_save=True)
                            pygame.time.set_timer(pygame.USEREVENT + 1, 500)
                        else:
                            self.current_player = AI
            
            # AI 回合 - 使用后台计算，不阻塞界面
            if self.game_state == GAME_RUNNING and self.current_player == AI and not self.ai_thinking:
                if self.ai_move_result is None:
                    # 开始后台计算
                    self.ai_thinking = True
                    self.ai_thread = threading.Thread(target=self.calculate_ai_move_async)
                    self.ai_thread.start()
                elif not self.ai_thinking and self.ai_move_result is not None:
                    # 计算完成，执行落子
                    ax, ay = self.ai_move_result
                    self.timer.lap(is_ai=True)
                    move_time = self.timer.last_move_time
                    
                    self.step += 1
                    self.board[ay][ax] = AI
                    self.history.append((ax, ay))
                    self.sound_manager.play_click()
                    
                    # 添加棋子动画
                    if GUI_AVAILABLE:
                        cx = MARGIN + ax * GRID
                        cy = MENU_HEIGHT + MARGIN + ay * GRID
                        anim = PieceAnimation(cx, cy, is_black=False)
                        self.piece_animations.append(anim)
                    
                    coord = f"{chr(65 + ax)}{ay + 1}"
                    record = {
                        'step': self.step,
                        'player': AI,
                        'coord': coord,
                        'time': move_time
                    }
                    self.move_records.append(record)
                    print(f"第 {self.step} 步：AI -> {coord} (用时：{move_time:.2f}秒)")
                    
                    # 自动保存棋谱
                    self.auto_save_record()
                    
                    if self.check_win(self.board, ax, ay, AI):
                        self.game_state = AI_WIN
                        self.winner = AI
                        self.timer.stop()
                        # 游戏结束，自动保存完整棋谱
                        self.auto_save_record(force_save=True)
                        # 显示获胜弹窗（延迟一点显示）
                        pygame.time.set_timer(pygame.USEREVENT + 1, 500)
                    elif self.step == BOARD_SIZE * BOARD_SIZE:
                        self.game_state = DRAW
                        self.timer.stop()
                        # 游戏结束，自动保存完整棋谱
                        self.auto_save_record(force_save=True)
                        pygame.time.set_timer(pygame.USEREVENT + 1, 500)
                    else:
                        self.current_player = PLAYER
                    
                    # 重置 AI 状态
                    self.ai_move_result = None
            
            # 绘制
            self.draw_board()
            
            # 绘制所有棋子
            for y in range(BOARD_SIZE):
                for x in range(BOARD_SIZE):
                    if self.board[y][x] == PLAYER:
                        self.draw_piece(x, y, True)
                    elif self.board[y][x] == AI:
                        self.draw_piece(x, y, False)
            
            # 绘制高亮（鼠标悬停）和 AI 思考提示
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
            
            # AI 思考中的提示
            if self.ai_thinking:
                think_text = "AI 思考中..."
                think_surf = self.font_small.render(think_text, True, (255, 0, 0))
                # 居中显示在顶部
                text_rect = think_surf.get_rect(center=(SCREEN_WIDTH // 2, MENU_HEIGHT + 10))
                pygame.draw.rect(self.screen, (255, 255, 255), text_rect.inflate(20, 10))
                self.screen.blit(think_surf, text_rect)
            
            self.draw_win()
            self.draw_info()
            self.draw_menu_bar()
            self.draw_drop_menus()
            self.draw_popup()
            
            # 绘制通知
            if GUI_AVAILABLE and hasattr(self, 'notification') and self.notification:
                dt = self.clock.get_time() / 1000.0
                self.notification.update(dt)
                self.notification.draw(self.screen)
                if not self.notification.visible:
                    self.notification = None
            
            pygame.display.flip()
            self.clock.tick(30)


# ====================== 主程序入口 ======================
if __name__ == "__main__":
    game = GomokuGame()
    game.run()