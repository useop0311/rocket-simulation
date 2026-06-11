import pygame
import random
import math

# -------------------------------------------------------------
# 1. UI 컬러 정의 및 디스플레이 기본 상수
# -------------------------------------------------------------
BG_COLOR = (11, 14, 20)           # 메인 우주 배경 색상 (어두운 네이비)
GRID_COLOR = (20, 30, 45)         # 우주 공간의 격자 그리드선 색상
EARTH_BLUE = (30, 75, 175)        # 지구 본체 색상 (파란색)
ATMOSPHERE_COLOR = (8, 145, 178)  # 지구 대기층 및 광륜 표현용 청록색
ROCKET_WHITE = (240, 240, 240)    # 로켓 기본 몸체 색상 (밝은 회색/흰색)
ROCKET_ORANGE = (245, 158, 11)    # 화염 외부 및 활성 상태의 강조색 (오렌지색)
ROCKET_BLUE = (96, 165, 250)      # 2단 로켓 활성화 시 몸체 색상 (하늘색)
ROCKET_GREEN = (52, 211, 153)     # 궤도 안착 성공 시 몸체 및 궤적 색상 (에메랄드/그린)
PATH_COLOR = (16, 185, 129)       # 로켓의 비행 궤적선 기본 색상
HUD_BG = (22, 28, 38)             # 하단 UI HUD 패널 배경색 (어두운 회색)
HUD_CARD_BG = (31, 41, 55)        # HUD 패널 내 개별 수치 카드 배경색
TEXT_COLOR = (209, 213, 219)      # 일반 UI 텍스트 기본 색상
CYAN = (6, 182, 212)              # 수치 강조용 하늘색 (사이언)
RED = (239, 68, 68)               # 경고/중단 등의 중요 버튼 색상 (빨간색)
YELLOW = (234, 179, 8)            # 주의/특이 상태용 노란색
AMBER = (217, 119, 6)             # 엔진 불꽃 내부 표현을 위한 진한 황색
GRAY = (156, 163, 175)            # 비활성 텍스트 및 가이드선용 보조 회색

WIDTH, HEIGHT = 1024, 768         # 창 해상도 (가로 1024픽셀, 세로 768픽셀)
FPS = 60                          # 초당 프레임 수 (60fps)

# -------------------------------------------------------------
# 2. 로켓 화염 이펙트를 위한 파티클 클래스
# -------------------------------------------------------------
class Particle:
    """
    로켓 엔진 분사 시 발생하는 배기 가스와 불꽃 파티클을 표현하는 클래스입니다.
    매 프레임 설정된 속도만큼 이동하고 수명이 다하면 화면에서 소멸합니다.
    """
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: int, lifetime: int):
        self.x = x                      # 파티클의 현재 X 화면 좌표
        self.y = y                      # 파티클의 현재 Y 화면 좌표
        self.vx = vx                    # 초당/프레임당 X축 이동 속도
        self.vy = vy                    # 초당/프레임당 Y축 이동 속도
        self.color = color              # RGB 색상값
        self.size = size                # 원형 파티클의 반지름 크기
        self.lifetime = lifetime        # 파티클의 남은 수명 (프레임 단위)
        self.max_lifetime = lifetime    # 파티클이 생성되었을 때의 최대 수명 (투명도 비율 계산용)

    def update(self):
        """매 프레임 위치를 물리 속도에 따라 이동시키고, 남은 수명을 1씩 감소시킵니다."""
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1

    def draw(self, surface: pygame.Surface):
        """
        화면에 파티클을 그립니다.
        수명이 줄어들수록 알파(투명도) 채널 값을 조절해 서서히 사라지는(Fade-out) 연출을 처리합니다.
        """
        if self.lifetime <= 0:
            return
        # 남은 수명에 비례하여 알파값 계산 (255 = 완전 불투명, 0 = 완전 투명)
        alpha = int((self.lifetime / self.max_lifetime) * 255)
        
        # 알파(투명도) 효과를 내기 위해 투명도 지원 서피스(SRCALPHA)를 생성
        p_surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        # 임시 서피스의 중심에 투명도가 반영된 원을 드로잉
        pygame.draw.circle(p_surf, (*self.color, alpha), (self.size, self.size), self.size)
        # 렌더링할 메인 화면(Surface)에 임시 서피스를 복사(Blit)
        surface.blit(p_surf, (int(self.x - self.size), int(self.y - self.size)))

# -------------------------------------------------------------
# 3. 미션 제어 버튼 클래스
# -------------------------------------------------------------
class Button:
    """
    시뮬레이션 조작(시작, 단 분리, 궤도 형성 등)을 위해 클릭 가능한 화면 상의 버튼 UI 객체입니다.
    """
    def __init__(self, x: int, y: int, width: int, height: int, text: str, font: pygame.font.Font, color: tuple, active_color: tuple, callback_val=None):
        self.rect = pygame.Rect(x, y, width, height)  # 버튼의 클릭 감지 영역 (사각형 사양)
        self.text = text                              # 버튼에 표기할 문자열
        self.font = font                              # 텍스트 렌더링에 적용할 Pygame Font 객체
        self.color = color                            # 기본 상태(마우스 미접촉 등)의 버튼 색상
        self.active_color = active_color              # 마우스 오버 또는 활성화 상태의 버튼 색상
        self.active = False                           # 버튼의 상태 토글 또는 활성화 여부 플래그
        self.callback_val = callback_val              # 버튼 클릭 시 전달할 커스텀 콜백 데이터

    def draw(self, surface: pygame.Surface):
        """버튼을 화면에 렌더링합니다. 테두리 및 가운데 정렬 텍스트를 함께 그립니다."""
        # 마우스 오버나 활성화 여부에 맞춰 배경색 결정
        bg = self.active_color if self.active else self.color
        
        # 둥근 모퉁이(border_radius=6)의 사각형 버튼 채우기
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        # 회색 계열의 외곽선 테두리 그리기
        pygame.draw.rect(surface, (55, 65, 81), self.rect, width=1, border_radius=6)
        
        # 버튼 영역의 정중앙에 맞춰 텍스트 이미지 렌더링
        txt_surf = self.font.render(self.text, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def check_click(self, pos: tuple) -> bool:
        """입력된 마우스 클릭 좌표(pos)가 버튼의 사각형 영역 내에 있는지 판별하여 충돌 유무를 반환합니다."""
        return self.rect.collidepoint(pos)

# -------------------------------------------------------------
# 4. 카메라 줌 드래그 슬라이더 클래스
# -------------------------------------------------------------
class Slider:
    """
    화면 내 행성 및 우주의 카메라 시야 줌 배율을 조절할 수 있도록 하는 슬라이더 UI 클래스입니다.
    """
    def __init__(self, x: int, y: int, width: int, min_val: float, max_val: float, initial_val: float, label: str):
        self.rect = pygame.Rect(x, y, width, 8)       # 슬라이더 레일(바)의 영역 (두께 8픽셀의 얇은 바)
        self.min_val = min_val                        # 슬라이더가 가질 수 있는 최소 값
        self.max_val = max_val                        # 슬라이더가 가질 수 있는 최대 값
        self.val = initial_val                        # 현재 선택되어 설정된 실제 슬라이더 수치
        self.label = label                            # 슬라이더 상단에 기재할 설명 문구 (예: "Zoom")
        self.handle_radius = 8                        # 사용자가 잡고 끄는 조절 원형 손잡이의 반지름
        self.update_handle_rect()                     # 초기 값 비율에 맞춰 조절 손잡이의 화면 위치 설정
        self.is_dragging = False                      # 마우스 드래그가 진행 중인지 판별하는 플래그

    def update_handle_rect(self):
        """현재 값(val)의 비율을 계산하여 손잡이(원)를 둘러싸는 사각형 범위(handle_rect)의 위치를 최신화합니다."""
        # 전체 조절 구간(min~max) 내에서 현재 값이 속하는 위치를 0.0 ~ 1.0 비율로 산출
        fraction = (self.val - self.min_val) / (self.max_val - self.min_val)
        # 슬라이더 트랙 상에서의 손잡이 가로 좌표(X) 결정
        handle_x = self.rect.x + int(fraction * self.rect.width)
        # 손잡이 충돌 감지를 위해 원을 둘러싸는 사각형 객체 갱신
        self.handle_rect = pygame.Rect(handle_x - self.handle_radius, self.rect.centery - self.handle_radius, self.handle_radius * 2, self.handle_radius * 2)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """슬라이더 레일 배경, 설정 완료 범위 하이라이트선, 조절 원 및 수치 라벨을 렌더링합니다."""
        # 1. 기본 배경 트랙선 (어두운 회색)
        pygame.draw.rect(surface, (55, 65, 81), self.rect, border_radius=4)
        
        # 2. 시작점부터 현재 설정값 위치까지 진행도를 드러내는 내부 트랙선 채우기 (하늘색)
        fraction = (self.val - self.min_val) / (self.max_val - self.min_val)
        fill_width = int(fraction * self.rect.width)
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(surface, (6, 182, 212), fill_rect, border_radius=4)
        
        # 3. 조절 원형 손잡이 그리기 (드래그 조작 중이면 하늘색, 대기 상태이면 밝은 회색)
        color = (6, 182, 212) if self.is_dragging else (209, 213, 219)
        pygame.draw.circle(surface, color, self.handle_rect.center, self.handle_radius)
        pygame.draw.circle(surface, (156, 163, 175), self.handle_rect.center, self.handle_radius, width=1)
        
        # 4. 슬라이더 바 상단 영역에 레이블 이름과 현재 배율 값(소수점 둘째 자리까지) 표시
        lbl_surf = font.render(f"{self.label}: {self.val:.2f}x", True, (209, 213, 219))
        surface.blit(lbl_surf, (self.rect.x, self.rect.y - 18))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """마우스 클릭 및 이동 이벤트를 가로채 조작 상태와 슬라이더 수치를 업데이트하고 변화 유무를 반환합니다."""
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 마우스 왼쪽 버튼 클릭
                m_pos = event.pos
                # 손잡이를 꼭 정확히 누르지 않아도 트랙 주변 위아래 16px 이내를 누르면 인식하도록 확장 범위 설정
                clickable_rect = self.rect.inflate(0, 16)
                if self.handle_rect.collidepoint(m_pos) or clickable_rect.collidepoint(m_pos):
                    self.is_dragging = True
                    self.update_value_from_pos(m_pos[0]) # 클릭된 좌표로 값 즉시 설정
                    changed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging = False # 드래그 조작 완료(해제)
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                m_pos = event.pos
                self.update_value_from_pos(m_pos[0]) # 움직인 마우스 X 좌표에 따라 실시간 갱신
                changed = True
        return changed

    def update_value_from_pos(self, mouse_x: int):
        """마우스 드래그 가로 좌표(X)를 슬라이더 내부 비율로 역산해 실제 설정값을 계산 및 동기화합니다."""
        # 슬라이더 바 내에서 마우스 좌표가 차지하는 상대적 위치 비율 계산
        fraction = (mouse_x - self.rect.x) / self.rect.width
        # 0.0보다 작아지거나 1.0보다 커지지 않도록 한계 범위 제한(클램핑)
        fraction = max(0.0, min(1.0, fraction))
        # 비율을 최소~최대 값 사이의 값으로 선형 보간하여 최종 수치 대입
        self.val = self.min_val + fraction * (self.max_val - self.min_val)
        self.update_handle_rect() # 조정된 수치에 대응해 손잡이 원의 화면 위치도 자동 정렬

# -------------------------------------------------------------
# 5. 투명 서피스 광륜 드로잉 함수
# -------------------------------------------------------------
def draw_transparent_circle(surface: pygame.Surface, color: tuple, center: tuple, radius: int, alpha: int):
    """
    화면에 알파 채널 투명도가 균일하게 스며든 원을 렌더링합니다.
    주로 지구 대기나 태양 광원 등의 뿌옇게 번지는 글로우(Glow) 효과를 낼 때 유용합니다.
    기본 pygame.draw.circle은 투명 채널이 결여되어 동작하므로, 별도로 생성한 임시 투명 서피스에 그리고 복사합니다.
    """
    if radius <= 0:
        return
    # 투명 채널(SRCALPHA)이 활성화되고 원 크기와 같은 정사각형 모양의 버퍼 서피스 생성
    temp_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    # 임시 버퍼 서피스의 정중앙(radius, radius)에 알파 값이 포함된 원 드로잉
    pygame.draw.circle(temp_surf, (*color, alpha), (radius, radius), radius)
    # 메인 표면에 임시 버퍼 서피스를 지정 좌표(원 중심이 오도록 보정)에 합성
    surface.blit(temp_surf, (int(center[0] - radius), int(center[1] - radius)))

# -------------------------------------------------------------
# 6. 세련된 구조의 2단 로켓 그리기 함수
# -------------------------------------------------------------
def draw_sleek_rocket(surface: pygame.Surface, cx: float, cy: float, heading: float, sz: float, stage: float, orbit_achieved: bool, has_flame: bool):
    """
    회전각과 축척이 적용된, 그래픽이 부드러운 다단계 로켓을 화면에 그립니다.
    
    cx, cy         : 로켓의 정중앙에 위치할 화면상 2D 좌표
    heading        : 로켓의 진행(비행) 방향 각도 (라디안 단위, 0 = 우측 수평 방향)
    sz             : 로켓 그래픽 요소의 전체 배율 크기 (기본 스케일 계수)
    stage          : 로켓 비행 단계 (1 = 1단+2단 전체 상태, 2 = 2단 본체 단독 비행 상태, 3 = 페어링 분리 상태 등)
    orbit_achieved : 위성 궤도 정밀 정착 완료 여부 (성공 시 로켓 도색을 활기찬 색상으로 변경 피드백)
    has_flame      : 추력 방출 점화 상태 여부 (True일 경우 후미에 흔들리는 분사 불꽃을 동적으로 그림)
    """
    # 1단계: Pygame의 반전된 Y축 좌표계 및 기본 0도 각도 차이를 메꾸기 위해 물리 헤딩 조정 계산
    # 물리 연산 각도에 대해 90도만큼(math.pi/2) 돌려 기본 로켓 축이 직진 위를 향하게 조정
    angle_adj = -heading + math.pi/2
    cos_a = math.cos(angle_adj)
    sin_a = math.sin(angle_adj)
    
    def get_gp(px, py):
        """
        로켓 고유의 로컬 상대 좌표(px, py)를 받아 
        로켓의 비행 방향(angle_adj)만큼 회전하고, 중심점(cx, cy)으로 평행이동시켜
        최종 Pygame 화면상의 픽셀 좌표 (x, y)로 환산하는 이너 유틸리티 함수입니다.
        """
        return (cx + (px * cos_a - py * sin_a), cy + (px * sin_a + py * cos_a))

    # 1. 엔진 노즐 드리기 (어두운 금속질 다각형)
    if stage == 1:
        # 1단 로켓용 넓은 엔진 노즐 꼭짓점 지정
        n_p = [get_gp(-0.7*sz, 4.0*sz), get_gp(-1.0*sz, 4.6*sz), get_gp(1.0*sz, 4.6*sz), get_gp(0.7*sz, 4.0*sz)]
        pygame.draw.polygon(surface, (60, 63, 70), n_p)
        pygame.draw.polygon(surface, (40, 42, 48), n_p, width=1)
    elif stage == 2:
        # 2단 단독 비행용 작고 좁은 모양의 엔진 노즐 꼭짓점 지정
        n_p = [get_gp(-0.5*sz, 0.5*sz), get_gp(-0.8*sz, 1.1*sz), get_gp(0.8*sz, 1.1*sz), get_gp(0.5*sz, 0.5*sz)]
        pygame.draw.polygon(surface, (60, 63, 70), n_p)
        pygame.draw.polygon(surface, (40, 42, 48), n_p, width=1)

    # 2. 점화 엔진 화염 (Thrust Flow) 그리기
    if has_flame:
        # 분사 화염이 리얼하게 거칠어지고 떨리는 플리커링 효과를 위해 노이즈 랜덤 길이 산정
        flame_len = (8 + random.uniform(0, 4)) * sz
        if stage == 1:
            # 1단 메인 노즐 후방의 큼직한 불꽃 형상 꼬리
            f_p = [get_gp(-0.8*sz, 4.6*sz), get_gp(0, 4.6*sz + flame_len), get_gp(0.8*sz, 4.6*sz)]
        else:
            # 2단 마이크로 노즐 후방의 날렵한 불꽃 형상 꼬리
            f_p = [get_gp(-0.6*sz, 1.1*sz), get_gp(0, 1.1*sz + flame_len), get_gp(0.6*sz, 1.1*sz)]
        pygame.draw.polygon(surface, (249, 115, 22), f_p) # 오렌지색 외부 화염 분출구 그리기
        
        # 엔진 내부의 극고온 연소 중심부를 시뮬레이션하기 위한 더 밝은 노란색 내부 불꽃 오버레이
        if stage == 1:
            f_inner = [get_gp(-0.4*sz, 4.6*sz), get_gp(0, 4.6*sz + flame_len*0.55), get_gp(0.4*sz, 4.6*sz)]
        else:
            f_inner = [get_gp(-0.3*sz, 1.1*sz), get_gp(0, 1.1*sz + flame_len*0.55), get_gp(0.3*sz, 1.1*sz)]
        pygame.draw.polygon(surface, (254, 240, 138), f_inner) # 노란색 속불꽃 그리기

    # 3. 1단 조종 날개 핀 (Wings/Fins) 그리기 (1단 부착 상태인 stage == 1 에서만 표현)
    if stage == 1:
        # 양 날개 바깥쪽으로 예리하게 각진 삼각 윙 핀 지정
        w_left = [get_gp(-1.5*sz, 2.5*sz), get_gp(-3.2*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
        w_right = [get_gp(1.5*sz, 2.5*sz), get_gp(3.2*sz, 4.0*sz), get_gp(1.5*sz, 4.0*sz)]
        pygame.draw.polygon(surface, (239, 68, 68), w_left) # 좌측 빨간 날개
        pygame.draw.polygon(surface, (239, 68, 68), w_right) # 우측 빨간 날개
        pygame.draw.polygon(surface, (185, 28, 28), w_left, width=1) # 외곽 테두리선
        pygame.draw.polygon(surface, (185, 28, 28), w_right, width=1)

    # 4. 1단 하부 부스터 동체 (Stage 1 Booster Body) 그리기
    if stage == 1:
        # 사각형 구조의 견고한 1단 추진 부스터 몸통 라인
        s1_p = [get_gp(-1.5*sz, 0.5*sz), get_gp(1.5*sz, 0.5*sz), get_gp(1.5*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
        pygame.draw.polygon(surface, (243, 244, 246), s1_p)
        pygame.draw.polygon(surface, (186, 195, 208), s1_p, width=1)
        # 1단 몸체 세부 띠 모양 데칼 장식선 (로켓 그래픽 퀄리티를 위해 얇은 가로선 삽입)
        pygame.draw.line(surface, (156, 163, 175), get_gp(-1.5*sz, 2.2*sz), get_gp(1.5*sz, 2.2*sz), int(max(1, 1.2*sz)))

    # 5. 2단 상부 추진체 및 코어 동체 (Stage 2 Core Body) 그리기
    # 게임 상태 진행에 따라 2단 몸체의 칼라 도색이 변하도록 분기
    s2_color = (243, 244, 246) # 1단 추진 도중에는 일반적인 화이트
    if stage == 2:
        s2_color = (96, 165, 250) # 1단 분리 후 2단 추진 시에는 푸른색 활성화
    elif stage == 3 and orbit_achieved:
        s2_color = (52, 211, 153) # 완전히 안전한 궤도 비행에 진입하면 성공을 알리는 그린/연두색 피드백
        
    s2_p = [get_gp(-1.5*sz, -2.5*sz), get_gp(1.5*sz, -2.5*sz), get_gp(1.5*sz, 0.5*sz), get_gp(-1.5*sz, 0.5*sz)]
    pygame.draw.polygon(surface, s2_color, s2_p)
    pygame.draw.polygon(surface, (209, 213, 219) if stage < 2 else (37, 99, 235), s2_p, width=1)
    # 1단과 2단 사이 분리 영역을 나타내는 조인트 경계선 빨간 띠
    pygame.draw.line(surface, (220, 38, 38), get_gp(-1.5*sz, -0.6*sz), get_gp(1.5*sz, -0.6*sz), int(max(1, 1.5*sz)))

    # 6. 최상단 Nose Cone 및 위성 페어링 캡슐 그리기
    # 탄두 부위와 같이 공기역학적인 원뿔 형상 디자인
    nc_p = [get_gp(0, -5.0*sz), get_gp(-1.5*sz, -2.5*sz), get_gp(1.5*sz, -2.5*sz)]
    pygame.draw.polygon(surface, (75, 85, 99), nc_p) # 강철 회색 노즈콘 탑승
    pygame.draw.polygon(surface, (55, 65, 81), nc_p, width=1)

# -------------------------------------------------------------
# 7. 분리 낙하하며 텀블링하는 1단 부스터 그리기 함수
# -------------------------------------------------------------
def draw_booster_drop(surface: pygame.Surface, cx: float, cy: float, heading: float, angle_rot: float, sz: float):
    """
    1단 부스터가 본체에서 분리된 직후, 우주 및 고고도에서 추진력을 상실하고
    지상을 향해 빙글빙글 공중제비(Tumbling) 돌며 떨어지는 잔해를 사실적으로 연출하여 그리는 함수입니다.
    
    cx, cy    : 분리되어 떨어지는 부스터 잔해의 현재 2D 위치 좌표
    heading   : 분리된 당시 로켓이 보던 원래 비행 정렬각
    angle_rot : 분리 후에 자체적인 각속도로 돌아가는 실시간 텀블링 회전각
    sz        : 크기 비율 축적 파라미터
    """
    # 원 비행방향에 텀블링 누적 각도(`angle_rot`)를 추가해 계속 회전하는 앵글 변환값 유도
    angle_adj = -heading + math.pi/2 + angle_rot
    cos_a = math.cos(angle_adj)
    sin_a = math.sin(angle_adj)
    
    def get_gp(px, py):
        """자유낙하 잔해용 로컬-글로벌 좌표 2D 변환 헬퍼 함수"""
        return (cx + (px * cos_a - py * sin_a), cy + (px * sin_a + py * cos_a))

    # 1. 분리된 어두운 엔진 노즐 (연소가 정지되어 차갑게 굳어버린 느낌의 다크 그레이)
    n_p = [get_gp(-0.7*sz, 4.0*sz), get_gp(-1.0*sz, 4.6*sz), get_gp(1.0*sz, 4.6*sz), get_gp(0.7*sz, 4.0*sz)]
    pygame.draw.polygon(surface, (50, 52, 58), n_p)

    # 2. 조종 날개 핀 (동일하게 하단에 배치된 삼각 날개)
    w_left = [get_gp(-1.5*sz, 2.5*sz), get_gp(-3.2*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
    w_right = [get_gp(1.5*sz, 2.5*sz), get_gp(3.2*sz, 4.0*sz), get_gp(1.5*sz, 4.0*sz)]
    pygame.draw.polygon(surface, (185, 28, 28), w_left)
    pygame.draw.polygon(surface, (185, 28, 28), w_right)

    # 3. 1단 동체 부품 (2단이 떨어져 나간 채 몸체만 낙하함)
    s1_p = [get_gp(-1.5*sz, 0.5*sz), get_gp(1.5*sz, 0.5*sz), get_gp(1.5*sz, 4.0*sz), get_gp(-1.5*sz, 4.0*sz)]
    pygame.draw.polygon(surface, (200, 202, 206), s1_p)
    pygame.draw.polygon(surface, (140, 145, 152), s1_p, width=1)
    
    # 4. 단 분리가 절단된 단면의 디테일선 (주황색/그을린 가로선으로 절단부를 렌더링)
    pygame.draw.line(surface, (194, 65, 12), get_gp(-1.5*sz, 0.5*sz), get_gp(1.5*sz, 0.5*sz), 2)
