"""
五子棋 GUI 组件库
提供美观的菜单、按钮、弹窗等 UI 组件
"""

import pygame
import os
from typing import Optional, Tuple

# ====================== Emoji 支持 ======================
class EmojiFont:
    """Emoji 字体管理器 - 使用 SimHei 字体（已验证支持 emoji 和中文）"""
    
    _cached_fonts = {}
    
    @classmethod
    def get_font(cls, size=20):
        """获取支持 emoji 的字体"""
        cache_key = f"simhei_{size}"
        if cache_key in cls._cached_fonts:
            return cls._cached_fonts[cache_key]
        
        # 使用 SimHei 字体文件（已验证支持 emoji 和中文，大小合适）
        font_path = r"C:\Windows\Fonts\simhei.ttf"
        
        try:
            if os.path.exists(font_path):
                font = pygame.font.Font(font_path, size)
                # 测试 emoji 渲染
                test = font.render("🎮", True, (0, 0, 0))
                if test.get_width() > 15:  # 确保 emoji 支持良好
                    print(f"✓ 使用 SimHei 字体（大小：{size}）")
                    cls._cached_fonts[cache_key] = font
                    return font
        except Exception as e:
            print(f"⚠️ SimHei 加载失败：{e}")
        
        # 备用方案：使用 SysFont 的 simhei
        try:
            font = pygame.font.SysFont('simhei', size)
            print(f"✓ 使用 SysFont('simhei', {size})")
            cls._cached_fonts[cache_key] = font
            return font
        except:
            pass
        
        # 最后的备用方案
        print(f"⚠️ 使用微软雅黑备用方案（大小：{size}）")
        font = pygame.font.SysFont('microsoft yahei', size)
        cls._cached_fonts[cache_key] = font
        return font
    
    @classmethod
    def render_emoji(cls, text, size=20, color=(0, 0, 0)):
        """渲染文本（尽量支持 emoji）"""
        font = cls.get_font(size)
        return font.render(text, True, color)


class Animation:
    """动画基类"""
    def __init__(self, duration=0.3):
        self.duration = duration
        self.elapsed = 0.0
        self.finished = False
    
    def update(self, dt):
        """更新动画"""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True
            return self.duration
        return self.elapsed
    
    def get_progress(self):
        """获取进度 (0-1)"""
        return min(1.0, self.elapsed / self.duration)
    
    def ease_out(self, value):
        """缓出效果"""
        t = self.get_progress()
        return 1 - pow(1 - t, 3)


class FadeAnimation(Animation):
    """淡入淡出动画"""
    def __init__(self, start_alpha=0, end_alpha=255, duration=0.3):
        super().__init__(duration)
        self.start_alpha = start_alpha
        self.end_alpha = end_alpha
    
    def get_alpha(self):
        """获取当前透明度"""
        progress = self.ease_out(self.get_progress())
        return int(self.start_alpha + (self.end_alpha - self.start_alpha) * progress)


class ScaleAnimation(Animation):
    """缩放动画"""
    def __init__(self, start_scale=0.0, end_scale=1.0, duration=0.3):
        super().__init__(duration)
        self.start_scale = start_scale
        self.end_scale = end_scale
    
    def get_scale(self):
        """获取当前缩放比例"""
        progress = self.ease_out(self.get_progress())
        return self.start_scale + (self.end_scale - self.start_scale) * progress


class UIMenuItem:
    """菜单项组件"""
    def __init__(self, x, y, width, height, text, icon="", shortcut="", font=None, small_font=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.icon = icon
        self.shortcut = shortcut
        # 使用支持 emoji 的字体
        if font is None:
            self.font = EmojiFont.get_font(20)
        else:
            self.font = font
        
        if small_font is None:
            self.small_font = EmojiFont.get_font(14)
        else:
            self.small_font = small_font
        
        self.is_separator = (text == "-")
        self.hover = False
        
    def update(self, mouse_pos):
        """更新悬停状态"""
        self.hover = self.rect.collidepoint(mouse_pos) and not self.is_separator
        return self.hover
    
    def draw(self, screen):
        """绘制菜单项"""
        if self.is_separator:
            # 分隔线
            y = self.rect.centery
            pygame.draw.line(screen, (220, 220, 220), 
                           (self.rect.left + 10, y), 
                           (self.rect.right - 10, y), 1)
            return
        
        # 悬停背景
        if self.hover:
            hover_surface = pygame.Surface((self.rect.width - 10, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(hover_surface, (230, 240, 255, 200), 
                           (0, 0, self.rect.width - 10, self.rect.height), border_radius=4)
            screen.blit(hover_surface, (self.rect.left + 5, self.rect.top))
        
        # 图标
        if self.icon:
            icon_surf = self.font.render(self.icon, True, (0, 0, 0))
            screen.blit(icon_surf, (self.rect.left + 15, self.rect.top + 4))
        
        # 文字
        text_color = (0, 0, 0) if self.hover else (30, 30, 30)
        text_surf = self.font.render(self.text, True, text_color)
        text_x = self.rect.left + 40 if self.icon else self.rect.left + 15
        screen.blit(text_surf, (text_x, self.rect.top + 4))
        
        # 快捷键或子菜单提示
        if self.shortcut:
            shortcut_surf = self.small_font.render(self.shortcut, True, (120, 120, 120))
            screen.blit(shortcut_surf, (self.rect.right - shortcut_surf.get_width() - 15, 
                                       self.rect.top + 6))


class UIPopup:
    """精美的弹窗组件"""
    def __init__(self, screen, title, message, font_large=None, font_small=None, transparent_bg=False, show_new_game=False):
        self.screen = screen
        self.title = title
        self.message = message
        self.transparent_bg = transparent_bg  # 透明背景模式
        self.show_new_game = show_new_game  # 是否显示新游戏按钮
        # 使用支持 emoji 的字体
        if font_large is None:
            self.font_large = EmojiFont.get_font(36)
        else:
            self.font_large = font_large
        
        if font_small is None:
            self.font_small = EmojiFont.get_font(20)
        else:
            self.font_small = font_small
        
        self.animation = FadeAnimation(0, 255, 0.3)
        self.visible = True
        
        # 根据内容计算尺寸
        self.width = 450
        self._calculate_dimensions()
        self.x = (screen.get_width() - self.width) // 2
        self.y = (screen.get_height() - self.height) // 2
    
    def _calculate_dimensions(self):
        """根据文本内容计算弹窗高度"""
        # 标题高度
        title_height = self.font_large.get_height()
        
        # 内容文本行数
        lines = self.message.split('\n')
        line_height = self.font_small.get_height()
        line_spacing = 2  # 行间距
        content_height = len(lines) * (line_height + line_spacing)
        
        # 按钮高度
        button_height = 35
        
        # 总高度 = 上边距 + 标题区域 + 内容区域 + 按钮区域 + 下边距
        self.height = 60 + title_height + content_height + button_height + 40
        
        # 限制最小和最大高度
        self.height = max(200, min(self.height, 500))
        
    def update(self, dt):
        """更新动画"""
        self.animation.update(dt)
    
    def draw(self, screen):
        """绘制弹窗"""
        if not self.visible:
            return
        
        alpha = self.animation.get_alpha()
        
        if not self.transparent_bg:
            # 半透明遮罩（非透明背景模式）
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha // 3))
            screen.blit(overlay, (0, 0))
            
            # 弹窗背景（带阴影）
            for i in range(5, 0, -1):
                shadow_rect = pygame.Rect(self.x + i, self.y + i, self.width, self.height)
                shadow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                pygame.draw.rect(shadow_surface, (0, 0, 0, alpha // (i * 3)), 
                               (0, 0, self.width, self.height), border_radius=10)
                screen.blit(shadow_surface, (self.x + i, self.y + i))
            
            # 主弹窗（实心背景）
            popup_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            pygame.draw.rect(screen, (255, 255, 255), popup_rect, border_radius=10)
            pygame.draw.rect(screen, (180, 180, 180), popup_rect, 2, border_radius=10)
        else:
            # 透明背景模式 - 只绘制边框和文字（更透明）
            # 弹窗边框（带轻微阴影）
            for i in range(3, 0, -1):
                shadow_rect = pygame.Rect(self.x + i, self.y + i, self.width, self.height)
                shadow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                pygame.draw.rect(shadow_surface, (0, 0, 0, alpha // (i * 4)), 
                               (0, 0, self.width, self.height), border_radius=10)
                screen.blit(shadow_surface, (self.x + i, self.y + i))
            
            # 主弹窗（透明背景，只有细边框）
            popup_rect = pygame.Rect(self.x, self.y, self.width, self.height)
            pygame.draw.rect(screen, (255, 255, 255, 150), popup_rect, border_radius=10, width=1)
        
        # 标题（动态位置）
        title_surf = self.font_large.render(self.title, True, (30, 30, 30))
        title_rect = title_surf.get_rect(center=(self.x + self.width // 2, self.y + 45))
        screen.blit(title_surf, title_rect)
        
        # 内容（支持多行文本，动态位置）
        lines = self.message.split('\n')
        line_height = self.font_small.get_height()
        line_spacing = 2
        start_y = self.y + 85  # 标题下方的起始位置
        
        for i, line in enumerate(lines):
            message_surf = self.font_small.render(line, True, (60, 60, 60))
            message_rect = message_surf.get_rect(center=(self.x + self.width // 2, start_y + i * (line_height + line_spacing)))
            screen.blit(message_surf, message_rect)
        
        # 按钮（动态位置，在内容下方）
        button_y = self.y + self.height - 60
        
        if self.show_new_game:
            # 双按钮模式：查看棋谱和新游戏
            ok_rect = pygame.Rect(self.x + 80, button_y, 120, 35)
            new_game_rect = pygame.Rect(self.x + self.width - 200, button_y, 120, 35)
            
            # 查看棋谱按钮
            pygame.draw.rect(screen, (70, 130, 180), ok_rect, border_radius=6)
            ok_text = self.font_small.render("查看棋谱", True, (255, 255, 255))
            ok_text_rect = ok_text.get_rect(center=ok_rect.center)
            screen.blit(ok_text, ok_text_rect)
            
            # 新游戏按钮
            pygame.draw.rect(screen, (70, 180, 100), new_game_rect, border_radius=6)
            new_game_text = self.font_small.render("新游戏", True, (255, 255, 255))
            new_game_text_rect = new_game_text.get_rect(center=new_game_rect.center)
            screen.blit(new_game_text, new_game_text_rect)
            
            return (ok_rect, new_game_rect)
        else:
            # 单按钮模式：只有确定
            ok_rect = pygame.Rect(self.x + self.width // 2 - 50, button_y, 100, 35)
            pygame.draw.rect(screen, (70, 130, 180), ok_rect, border_radius=6)
            ok_text = self.font_small.render("确定", True, (255, 255, 255))
            ok_text_rect = ok_text.get_rect(center=ok_rect.center)
            screen.blit(ok_text, ok_text_rect)
            
            return ok_rect
    
    def handle_click(self, pos):
        """处理点击"""
        button_y = self.y + self.height - 60
        
        if self.show_new_game:
            # 双按钮模式
            ok_rect = pygame.Rect(self.x + 80, button_y, 120, 35)
            new_game_rect = pygame.Rect(self.x + self.width - 200, button_y, 120, 35)
            
            if ok_rect.collidepoint(pos):
                self.visible = False
                return 'ok'
            elif new_game_rect.collidepoint(pos):
                self.visible = False
                return 'new_game'
            return None
        else:
            # 单按钮模式
            ok_rect = pygame.Rect(self.x + self.width // 2 - 50, button_y, 100, 35)
            if ok_rect.collidepoint(pos):
                self.visible = False
                return True
            return False


class UINotification:
    """通知提示组件"""
    def __init__(self, screen, message, position='top-right', duration=2.0):
        self.screen = screen
        self.message = message
        self.position = position
        self.duration = duration
        self.animation = FadeAnimation(0, 255, 0.3)
        self.timer = 0.0
        self.visible = True
        
        # 使用支持 emoji 的字体
        self.font = EmojiFont.get_font(18)
        self.padding = 15
        self.border_radius = 8
        
        # 渲染文字
        self.text_surf = self.font.render(message, True, (255, 255, 255))
        self.width = self.text_surf.get_width() + self.padding * 2
        self.height = self.text_surf.get_height() + self.padding
        
        # 根据位置计算坐标
        if position == 'top-right':
            self.x = screen.get_width() - self.width - 20
            self.y = 60
        elif position == 'top-center':
            self.x = (screen.get_width() - self.width) // 2
            self.y = 60
        elif position == 'bottom-center':
            self.x = (screen.get_width() - self.width) // 2
            self.y = screen.get_height() - self.height - 60
    
    def update(self, dt):
        """更新通知"""
        self.timer += dt
        if self.timer >= self.duration:
            self.visible = False
    
    def draw(self, screen):
        """绘制通知"""
        if not self.visible:
            return
        
        alpha = self.animation.get_alpha()
        
        # 背景渐变
        bg_color = (70, 130, 180)  # 钢蓝色
        
        # 绘制背景（带圆角）
        notify_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, bg_color, notify_rect, border_radius=self.border_radius)
        
        # 边框
        pygame.draw.rect(screen, (255, 255, 255), notify_rect, 1, border_radius=self.border_radius)
        
        # 文字居中
        text_rect = self.text_surf.get_rect(center=notify_rect.center)
        screen.blit(self.text_surf, text_rect)


class PieceAnimation:
    """棋子落下动画"""
    def __init__(self, x, y, is_black):
        self.x = x
        self.y = y
        self.is_black = is_black
        self.scale_anim = ScaleAnimation(0.0, 1.0, 0.3)
        self.fade_anim = FadeAnimation(0, 255, 0.3)
        self.finished = False
    
    def update(self, dt):
        """更新动画"""
        self.scale_anim.update(dt)
        self.fade_anim.update(dt)
        self.finished = self.scale_anim.finished and self.fade_anim.finished
    
    def draw(self, screen, grid_size=40):
        """绘制带动画的棋子"""
        scale = self.scale_anim.get_scale()
        alpha = self.fade_anim.get_alpha()
        
        cx = self.x
        cy = self.y
        r = int((grid_size // 2 - 2) * scale)
        
        if r <= 0:
            return
        
        if self.is_black:
            # 黑子
            for i in range(r, 0, -1):
                k = int(255 * (i / r) * 0.5)
                color = (min(k + alpha, 255), min(k + alpha, 255), min(k + alpha, 255))
                pygame.draw.circle(screen, color, (cx, cy), i)
        else:
            # 白子
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), r)
            pygame.draw.circle(screen, (160, 160, 160), (cx, cy), r, 1)
        
        # 高光
        if scale > 0.5:
            highlight_r = r // 4
            pygame.draw.circle(screen, (255, 255, 255), 
                             (cx - r//3, cy - r//3), highlight_r)
