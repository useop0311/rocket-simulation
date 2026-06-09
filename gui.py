import pygame
import random
import math

# -------------------------------------------------------------
# 1. UI 컬러 정의 및 디스플레이 기본 상수
# -------------------------------------------------------------
BG_COLOR = (11, 14, 20)
GRID_COLOR = (20, 30, 45)
EARTH_BLUE = (30, 75, 175)
ATMOSPHERE_COLOR = (8, 145, 178)
ROCKET_WHITE = (240, 240, 240)
ROCKET_ORANGE = (245, 158, 11)
ROCKET_BLUE = (96, 165, 250)
ROCKET_GREEN = (52, 211, 153)
PATH_COLOR = (16, 185, 129)
HUD_BG = (22, 28, 38)
HUD_CARD_BG = (31, 41, 55)
TEXT_COLOR = (209, 213, 219)
CYAN = (6, 182, 212)
RED = (239, 68, 68)
YELLOW = (234, 179, 8)
AMBER = (217, 119, 6)
GRAY = (156, 163, 175)

WIDTH, HEIGHT = 1024, 768
FPS = 60

# -------------------------------------------------------------
# 2. 로켓 화염 이펙트를 위한 파티클 클래스
# -------------------------------------------------------------
class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: int, lifetime: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, surface: pygame.Surface):
        if self.lifetime <= 0:
            return
        alpha = int((self.lifetime / self.max_lifetime) * 255)
        p_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(p_surf, (int(self.x - self.size), int(self.y - self.size)))

# -------------------------------------------------------------
# 3. 미션 제어 버튼 클래스
# -------------------------------------------------------------
class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, font: pygame.font.Font, color: tuple, active_color: tuple, callback_val=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.active_color = active_color
        self.active = False
        self.callback_val = callback_val

    def draw(self, surface: pygame.Surface):
        bg = self.active_color if self.active else self.color
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, (55, 65, 81), self.rect, width=1, border_radius=6)
        
        txt_surf = self.font.render(self.text, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def check_click(self, pos: tuple) -> bool:
        return self.rect.collidepoint(pos)

# -------------------------------------------------------------
# 4. 카메라 줌 드래그 슬라이더 클래스
# -------------------------------------------------------------
class Slider:
    def __init__(self, x: int, y: int, width: int, min_val: float, max_val: float, initial_val: float, label: str):
        self.rect = pygame.Rect(x, y, width, 8)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.label = label
        self.handle_radius = 8
        self.update_handle_rect()
        self.is_dragging = False

    def update_handle_rect(self):
        fraction = (self.val - self.min_val) / (self.max_val - self.min_val)
        handle_x = self.rect.x + int(fraction * self.rect.width)
        self.handle_rect = pygame.Rect(handle_x - self.handle_radius, self.rect.centery - self.handle_radius, self.handle_radius * 2, self.handle_radius * 2)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        pygame.draw.rect(surface, (55, 65, 81), self.rect, border_radius=4)
        fraction = (self.val - self.min_val) / (self.max_val - self.min_val)
        fill_width = int(fraction * self.rect.width)
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(surface, (6, 182, 212), fill_rect, border_radius=4)
        
        color = (6, 182, 212) if self.is_dragging else (209, 213, 219)
        pygame.draw.circle(surface, color, self.handle_rect.center, self.handle_radius)
        pygame.draw.circle(surface, (156, 163, 175), self.handle_rect.center, self.handle_radius, width=1)
        
        lbl_surf = font.render(f"{self.label}: {self.val:.2f}x", True, (209, 213, 219))
        surface.blit(lbl_surf, (self.rect.x, self.rect.y - 18))

    def handle_event(self, event: pygame.event.Event) -> bool:
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                m_pos = event.pos
                clickable_rect = self.rect.inflate(0, 16)
                if self.handle_rect.collidepoint(m_pos) or clickable_rect.collidepoint(m_pos):
                    self.is_dragging = True
                    self.update_value_from_pos(m_pos[0])
                    changed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                m_pos = event.pos
                self.update_value_from_pos(m_pos[0])
                changed = True
        return changed

    def update_value_from_pos(self, mouse_x: int):
        fraction = (mouse_x - self.rect.x) / self.rect.width
        fraction = max(0.0, min(1.0, fraction))
        self.val = self.min_val + fraction * (self.max_val - self.min_val)
        self.update_handle_rect()

# -------------------------------------------------------------
# 5. 투명 서피스 광륜 드로잉 함수
# -------------------------------------------------------------
def draw_transparent_circle(surface: pygame.Surface, color: tuple, center: tuple, radius: int, alpha: int):
    if radius <= 0:
        return
    temp_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(temp_surf, (*color, alpha), (radius, radius), radius)
    surface.blit(temp_surf, (int(center[0] - radius), int(center[1] - radius)))

# -------------------------------------------------------------
# 6. 세련된 구조의 2단 로켓 그리기 함수
# -------------------------------------------------------------
def draw_sleek_rocket(surface: pygame.Surface, cx: float, cy: float, heading: float, sz: float, stage: float, orbit_achieved: bool, has_flame: bool):
    angle_adj = -heading + math.pi/2
    cos_a = math.cos(angle_adj)
    sin_a = math.sin(angle_adj)
    
    def get_gp(px, py):
        return (cx + (px * cos_a - py * sin_a), cy + (px * sin_a + py * cos_a))

    # 1. 엔진 노즐
    if stage == 1:
        n_p = [get_gp(-0.7*sz, 4.0*sz), get_gp(-1.0*sz, 4.6*sz), get_gp(1.0*sz, 4.6*sz), get_gp(0.7*sz, 4.0*sz)]
        pygame.draw.polygon(surface, (60, 63, 70), n_p)
        pygame.draw.polygon(surface, (40, 42, 48), n_p, width=1)
    elif stage == 2:
        n_p = [get_gp(-0.5*sz, 0.5*sz), get_gp(-0.8*sz, 1.1*sz), get_gp(0.8*sz, 1.1*sz), get_gp(0.5*sz, 0.5*sz)]
        pygame.draw.polygon(surface, (60, 63, 70), n_p)
        pygame.draw.polygon(surface, (40, 42, 48), n_p, width=1)

    # 2. 엔진 화염 (Thrust)
    if has_flame:
        flame_len = (8 + random.uniform(0, 4)) * sz
        if stage == 1:
            f_p = [get_gp(-0.8*sz, 4.6*sz), get_gp(0, 4.6*sz + flame_len), get_gp(0.8*sz, 4.6*sz)]
        else:
            f_p = [get_gp(-0.6*sz, 1.1*sz), get_gp(0, 1.1*sz + flame_len), get_gp(0.6*sz, 1.1*sz)]
        pygame.draw.polygon(surface, (249, 115, 22), f_p)
        
        if stage == 1:
            f_inner = [get_gp(-0.4*sz, 4.6*sz), get_gp(0, 4.6*sz + flame_len*0.55), get_gp(0.4*sz, 4.6*sz)]
        else:
            f_inner = [get_gp(-0.3*sz, 1.1*sz), get_gp(0, 1.1*sz + flame_len*0.55), get_gp(0.3*sz, 1.1*sz)]
        pygame.draw.polygon(surface, (254, 240, 138), f_inner)

    # 3. 1단 조종 날개 핀 (Fins)
    if stage == 1:
        w_left = [get_gp(-1.5*sz, 2.5*sz), get_gp(-3.2*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
        w_right = [get_gp(1.5*sz, 2.5*sz), get_gp(3.2*sz, 4.0*sz), get_gp(1.5*sz, 4.0*sz)]
        pygame.draw.polygon(surface, (239, 68, 68), w_left)
        pygame.draw.polygon(surface, (239, 68, 68), w_right)
        pygame.draw.polygon(surface, (185, 28, 28), w_left, width=1)
        pygame.draw.polygon(surface, (185, 28, 28), w_right, width=1)

    # 4. 1단 하부 동체 (Stage 1 Booster)
    if stage == 1:
        s1_p = [get_gp(-1.5*sz, 0.5*sz), get_gp(1.5*sz, 0.5*sz), get_gp(1.5*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
        pygame.draw.polygon(surface, (243, 244, 246), s1_p)
        pygame.draw.polygon(surface, (186, 195, 208), s1_p, width=1)
        pygame.draw.line(surface, (156, 163, 175), get_gp(-1.5*sz, 2.2*sz), get_gp(1.5*sz, 2.2*sz), int(max(1, 1.2*sz)))

    # 5. 2단 상부 동체 (Stage 2 Core)
    s2_color = (243, 244, 246)
    if stage == 2:
        s2_color = (96, 165, 250)
    elif stage == 3 and orbit_achieved:
        s2_color = (52, 211, 153)
        
    s2_p = [get_gp(-1.5*sz, -2.5*sz), get_gp(1.5*sz, -2.5*sz), get_gp(1.5*sz, 0.5*sz), get_gp(-1.5*sz, 0.5*sz)]
    pygame.draw.polygon(surface, s2_color, s2_p)
    pygame.draw.polygon(surface, (209, 213, 219) if stage < 2 else (37, 99, 235), s2_p, width=1)
    pygame.draw.line(surface, (220, 38, 38), get_gp(-1.5*sz, -0.6*sz), get_gp(1.5*sz, -0.6*sz), int(max(1, 1.5*sz)))

    # 6. Nose Cone 페어링 캡슐
    nc_p = [get_gp(0, -5.0*sz), get_gp(-1.5*sz, -2.5*sz), get_gp(1.5*sz, -2.5*sz)]
    pygame.draw.polygon(surface, (75, 85, 99), nc_p)
    pygame.draw.polygon(surface, (55, 65, 81), nc_p, width=1)

# -------------------------------------------------------------
# 7. 분리 낙하하며 텀블링하는 1단 부스터 그리기 함수
# -------------------------------------------------------------
def draw_booster_drop(surface: pygame.Surface, cx: float, cy: float, heading: float, angle_rot: float, sz: float):
    angle_adj = -heading + math.pi/2 + angle_rot
    cos_a = math.cos(angle_adj)
    sin_a = math.sin(angle_adj)
    
    def get_gp(px, py):
        return (cx + (px * cos_a - py * sin_a), cy + (px * sin_a + py * cos_a))

    # 1단 엔진 노즐
    n_p = [get_gp(-0.7*sz, 4.0*sz), get_gp(-1.0*sz, 4.6*sz), get_gp(1.0*sz, 4.6*sz), get_gp(0.7*sz, 4.0*sz)]
    pygame.draw.polygon(surface, (50, 52, 58), n_p)

    # 1단 날개 핀
    w_left = [get_gp(-1.5*sz, 2.5*sz), get_gp(-3.2*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
    w_right = [get_gp(1.5*sz, 2.5*sz), get_gp(3.2*sz, 4.0*sz), get_gp(1.5*sz, 4.0*sz)]
    pygame.draw.polygon(surface, (185, 28, 28), w_left)
    pygame.draw.polygon(surface, (185, 28, 28), w_right)

    # 1단 동체
    s1_p = [get_gp(-1.5*sz, 0.5*sz), get_gp(1.5*sz, 0.5*sz), get_gp(1.5*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
    pygame.draw.polygon(surface, (200, 202, 206), s1_p)
    pygame.draw.polygon(surface, (140, 145, 152), s1_p, width=1)
    pygame.draw.line(surface, (194, 65, 12), get_gp(-1.5*sz, 0.5*sz), get_gp(1.5*sz, 0.5*sz), 2)
