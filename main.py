import pygame
import sys
import math
import random
import numpy as np

# -------------------------------------------------------------
# 1. 분리된 물리 엔진, GUI 및 분석 모듈 임포트
# -------------------------------------------------------------
from physics import *
from gui import *
from analysis import plot_rocket_analysis

# -------------------------------------------------------------
# 2. 디폴트 로켓 제원 (실행 전 수정 가능)
# -------------------------------------------------------------
DEFAULT_STAGE_1 = {
    "dry_mass": 10000.0,    # kg (1단 구조체 질량)
    "fuel_mass": 30000.0,   # kg (1단 초기 연료 질량)
    "m_dot": 300.0,        # kg/s (초당 연료 소모율 M_DOT)
    "v_e": 3500.0,         # m/s (연료 분사 속도 V_E)
    "c_d": 0.6,             # 공기저항 계수 C_D
    "area": 8.0,            # 단면적 AREA (m^2)
}

DEFAULT_STAGE_2 = {
    "dry_mass": 5000.0,    # kg
    "fuel_mass": 20000.0,   # kg-연료
    "m_dot": 50.0,         # kg/s
    "v_e": 6000.0,         # m/s
    "c_d": 0.4,             # 공기저항
    "area": 5.0,            # 단면적
}

DEFAULT_PAYLOAD_MASS = 1500.0      # kg (위성 및 페어링 질량)

# -------------------------------------------------------------
# 3. Pygame 실시간 시뮬레이션 제어 루프 함수
# -------------------------------------------------------------
def run_pygame_simulation(stage_1: dict = None, stage_2: dict = None, payload_mass: float = None) -> dict:
    # pygame 초기화
    pygame.init()
    pygame.font.init()

    # pygame 화면 설정, 시계 초기화
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("2단 로켓 시뮬레이터 - 단 분리 & 궤도 안착")
    clock = pygame.time.Clock()
    
    # 폰트 에러 방지용 안전 정의
    try:
        font_main = pygame.font.SysFont("AppleGothic", 15) if sys.platform == "darwin" else pygame.font.SysFont("malgungothic", 14)
    except:
        font_main = pygame.font.SysFont("arial", 14)
        
    try:
        font_large = pygame.font.SysFont("AppleGothic", 22, bold=True) if sys.platform == "darwin" else pygame.font.SysFont("malgungothic", 20, bold=True)
    except:
        font_large = pygame.font.SysFont("arial", 20, bold=True)
        
    try:
        font_hud_title = pygame.font.SysFont("AppleGothic", 11) if sys.platform == "darwin" else pygame.font.SysFont("malgungothic", 10)
    except:
        font_hud_title = pygame.font.SysFont("arial", 10)
        
    font_hud_val = pygame.font.SysFont("Courier", 20, bold=True)
    
    # 전달받은 제원 또는 디폴트 제원 적용 (딕셔너리를 복사하여 원본을 보호하고 단면적 기준 자동 검증 수행)
    s1 = stage_1.copy() if stage_1 is not None else DEFAULT_STAGE_1.copy()
    s2 = stage_2.copy() if stage_2 is not None else DEFAULT_STAGE_2.copy()
    p_mass = payload_mass if payload_mass is not None else DEFAULT_PAYLOAD_MASS
    
    # 단면적 기반 최대 동체 및 연료 질량 제한 검증 및 자동 조정 (비정상적인 스케일링 방지)
    s1_area_val = s1.get("area", DEFAULT_STAGE_1["area"])
    s1_max_dry = 1250.0 * s1_area_val
    s1_max_fuel = 10000.0 * s1_area_val
    if s1.get("dry_mass", 0) > s1_max_dry:
        print(f"⚠️ Warning: 1단 구조체 질량이 단면적 대비 너무 큽니다. {s1_max_dry:.1f} kg으로 자동 조정됩니다.")
        s1["dry_mass"] = s1_max_dry
    if s1.get("fuel_mass", 0) > s1_max_fuel:
        print(f"⚠️ Warning: 1단 연료 질량이 단면적 대비 너무 큽니다. {s1_max_fuel:.1f} kg으로 자동 조정됩니다.")
        s1["fuel_mass"] = s1_max_fuel

    s2_area_val = s2.get("area", DEFAULT_STAGE_2["area"])
    s2_max_dry = 5000.0 * s2_area_val
    s2_max_fuel = 5000.0 * s2_area_val
    if s2.get("dry_mass", 0) > s2_max_dry:
        print(f"⚠️ Warning: 2단 구조체 질량이 단면적 대비 너무 큽니다. {s2_max_dry:.1f} kg으로 자동 조정됩니다.")
        s2["dry_mass"] = s2_max_dry
    if s2.get("fuel_mass", 0) > s2_max_fuel:
        print(f"⚠️ Warning: 2단 연료 질량이 단면적 대비 너무 큽니다. {s2_max_fuel:.1f} kg으로 자동 조정됩니다.")
        s2["fuel_mass"] = s2_max_fuel
    
    # 시뮬레이션 상태
    x = 0.0
    y = R_E
    vx = 0.0
    vy = 0.0
    thrust = 0.0
    heading = math.pi / 2 # 로켓의 방위각 초기화 (수직)
    r_current = R_E
    h_current = 0.0
    v_current = 0.0
    v_orbit_req = math.sqrt(GM / R_E)

    # 연료 설정
    fuel_1 = s1["fuel_mass"]
    fuel_2 = s2["fuel_mass"]
    
    dt = 0.01  # 물리 계산 초정밀 스텝 간격
    current_time = 0.0 # 현재시간 초기화
    last_logged_time = -0.1 # 이전 로그 시간 초기화
    
    stage = 1 # 1단으로 시작
    sep_timer = 0.0 # 분리 타이머 초기화
    orbit_achieved = False # 궤도 안착 플래그
    mission_failed = False # 미션 실패(추락) 감지 플래그
    
    # 피치오버(각도 트는거) 설정
    pitchover_alt = 2000.0 # 피치오버 고도
    pitchover_window = 1000.0 # 수행하는 고도 기간
    target_pitchover_deg = 80.0 # 수행하는 각도
    
    history_pts = []
    particles = []
    
    # Matplotlib 분석 연동을 위한 데이터 저장소
    history = {
        "time": [], "x": [], "y": [], "vx": [], "vy": [],
        "altitude": [], "speed": [], "g_force": [], "q": [],
        "fuel_1": [], "fuel_2": [], "stage": [], "events": []
    }
    
    current_event = "비행 대기 중 (Space 또는 PLAY를 눌러 시작)"
    
    pitchover_triggered = False
    
    # 1단 분리 부스터 낙하 애니메이션 연출용 변수
    booster_active = False
    booster_x, booster_y = 0.0, 0.0
    booster_vx, booster_vy = 0.0, 0.0
    booster_rot = 0.0
    booster_heading = 0.0
    
    # 게임 컨트롤
    is_playing = False
    speed_multiplier = 5  # 기본 5x 배속
    camera_mode = "earth"  # "earth" 혹은 "rocket"
    
    # 배경 우주 별자리 생성
    stars = [{"x": random.randint(0, 700), "y": random.randint(0, 768), "size": random.random()*1.5} for _ in range(80)]
    
    # UI 버튼 설정
    buttons = []
    btn_play = Button(790, 480, 100, 40, "PLAY (Space)", font_main, (2, 132, 199), (217, 119, 6), "play") # 플레이 버튼
    btn_camera = Button(900, 480, 110, 40, "카메라: 지구", font_main, (75, 85, 99), (8, 145, 178), "camera")  # 카메라 버튼
    btn_reset = Button(790, 530, 220, 40, "RESET (R)", font_main, (55, 65, 81), (239, 68, 68), "reset") # 리셋 버튼
    
    buttons.extend([btn_play, btn_camera, btn_reset]) # 버튼 추가
    
    speed_btns = [
        Button(790 + i*43, 630, 40, 30, f"{s}x", font_main, (55, 65, 81), (8, 145, 178), f"speed_{s}")
        for i, s in enumerate([1, 5, 20, 50, 100])
    ] # 속도 조절 버튼
    buttons.extend(speed_btns) # 버튼 추가

    # print(buttons)
    
    # 카메라 줌 조절 슬라이더 추가 (최소 0.1배 ~ 최대 10배, 기본 1.0배)
    zoom_slider = Slider(785, 458, 220, 0.1, 10.0, 1.0, "카메라 줌 (Zoom)")
    
    # 기본 스피드 버튼 활성화
    for b in speed_btns:
        if b.callback_val == f"speed_{speed_multiplier}":
            b.active = True
            
    history["events"].append({"time": 0.0, "x": x, "y": y, "name": "Launch"}) # 제일 처음 초기 기록
            
    running = True
    while running:
        # 이벤트 루프
        for event in pygame.event.get():
            zoom_slider.handle_event(event) # 슬라이더 입력 반응 처리
            
            if event.type == pygame.QUIT:
                running = False # 나가기 감지시 꺼버리기
                
            elif event.type == pygame.KEYDOWN: # 키 누르면
                if event.key == pygame.K_SPACE: # 스페이스 누르면
                    if not mission_failed: # 실패한게 아니라면
                        is_playing = not is_playing # 실행 상태 반전
                elif event.key == pygame.K_ESCAPE: # ESC라면
                    running = False # 꺼버리기(분석시작)
                elif event.key == pygame.K_c: # c 누르면
                    camera_mode = "rocket" if camera_mode == "earth" else "earth" # 카메라 상태 반전
                elif event.key == pygame.K_r: # r 누르면
                    # 리셋 초기화
                    x, y, vx, vy = 0.0, R_E, 0.0, 0.0
                    r_current = R_E
                    h_current = 0.0
                    v_current = 0.0
                    v_orbit_req = math.sqrt(GM / R_E)
                    fuel_1 = s1["fuel_mass"]
                    fuel_2 = s2["fuel_mass"]
                    current_time = 0.0
                    last_logged_time = -0.1
                    stage = 1
                    sep_timer = 0.0
                    orbit_achieved = False
                    pitchover_triggered = False
                    booster_active = False
                    booster_rot = 0.0
                    booster_heading = 0.0
                    thrust = 0.0
                    heading = math.pi / 2
                    mission_failed = False
                    history_pts = []
                    particles = []
                    zoom_slider.val = 1.0
                    zoom_slider.update_handle_rect()
                    history = {
                        "time": [], "x": [], "y": [], "vx": [], "vy": [],
                        "altitude": [], "speed": [], "g_force": [], "q": [],
                        "fuel_1": [], "fuel_2": [], "stage": [], "events": []
                    }
                    history["events"].append({"time": 0.0, "x": x, "y": y, "name": "Launch"})
                    current_event = "시뮬레이션 초기화 완료"
                    is_playing = False
                elif event.key == pygame.K_UP: # 위 화살표 누르면
                    speeds = [1, 5, 20, 50, 100] # 이 속도들 중에
                    idx = speeds.index(speed_multiplier) # 지금 속도가 이거고
                    if idx < len(speeds) - 1: # 다음 속도가 존재하면
                        speed_multiplier = speeds[idx + 1] # 속도 바꾸고
                        for b in speed_btns:
                            b.active = (b.callback_val == f"speed_{speed_multiplier}") # UI에 선택된 속도 바꾸기
                elif event.key == pygame.K_DOWN: # 위 화살표와 동일하게 아래 화살표도 작동
                    speeds = [1, 5, 20, 50, 100]
                    idx = speeds.index(speed_multiplier)
                    if idx > 0:
                        speed_multiplier = speeds[idx - 1]
                        for b in speed_btns:
                            b.active = (b.callback_val == f"speed_{speed_multiplier}")
                        
            elif event.type == pygame.MOUSEBUTTONDOWN: # 마우스 누르면
                if event.button == 1:  # 좌클릭
                    m_pos = pygame.mouse.get_pos() # 위치 구하기
                    for btn in buttons: # 버튼마다 반복
                        if btn.check_click(m_pos): # 버튼이 눌렸으면
                            cb = btn.callback_val # 버튼 이름 찾기
                            if mission_failed and cb != "reset":
                                continue # 추락 실패 시에는 RESET 외의 타 버튼 클릭 비활성화
                            if cb == "play": # 플레이 버튼이면
                                is_playing = not is_playing # 플레이 상태 반전
                            elif cb == "camera": # 카메라 버튼이면
                                camera_mode = "rocket" if camera_mode == "earth" else "earth" # 카메라 상태 반전
                            elif cb == "reset": # 리셋 버튼이면
                                # 버튼 상태 변경
                                x, y, vx, vy = 0.0, R_E, 0.0, 0.0
                                r_current = R_E
                                h_current = 0.0
                                v_current = 0.0
                                v_orbit_req = math.sqrt(GM / R_E)
                                fuel_1 = s1["fuel_mass"]
                                fuel_2 = s2["fuel_mass"]
                                current_time = 0.0
                                last_logged_time = -0.1
                                stage = 1
                                sep_timer = 0.0
                                orbit_achieved = False
                                pitchover_triggered = False
                                booster_active = False
                                booster_rot = 0.0
                                booster_heading = 0.0
                                thrust = 0.0
                                heading = math.pi / 2
                                mission_failed = False
                                history_pts = []
                                particles = []
                                zoom_slider.val = 1.0
                                zoom_slider.update_handle_rect()
                                history = {
                                    "time": [], "x": [], "y": [], "vx": [], "vy": [],
                                    "altitude": [], "speed": [], "g_force": [], "q": [],
                                    "fuel_1": [], "fuel_2": [], "stage": [], "events": []
                                }
                                history["events"].append({"time": 0.0, "x": x, "y": y, "name": "Launch"})
                                current_event = "시뮬레이션 초기화 완료"
                                is_playing = False
                            elif cb.startswith("speed_"): # 스피드로 시작하는 버튼이면
                                speed_multiplier = int(cb.split("_")[1]) # 그걸로 바꾸기
                                for b in speed_btns:
                                    b.active = (b.callback_val == cb) # 화면도 바꾸기
                                    
        # 버튼 UI 상태 동기화
        btn_play.active = is_playing
        btn_play.text = "PAUSE" if is_playing else "PLAY"
        btn_camera.active = (camera_mode == "rocket")
        btn_camera.text = "카메라: 로켓" if camera_mode == "rocket" else "카메라: 지구"
        
        # 물리 시뮬레이션 계산 업데이트 루프
        if is_playing and not mission_failed: # 실행중이고 실패 안했으면
            ticks = speed_multiplier * 10 # 한번에 계산할 틱 계산하고
            
            for _ in range(ticks): # 한번에 연산할 만큼 정한만큼 연산하기
                # 실시간 물리 상태 변수 최신화
                r_current = math.sqrt(x**2 + y**2)
                h_current = r_current - R_E
                v_current = math.sqrt(vx**2 + vy**2)
                v_orbit_req = math.sqrt(GM / r_current)
        
                # 비행 방위 계산
                phi = math.atan2(y, x) # 지구 중심 기준 로켓의 위상각(방위각) 계산
                horizon_angle = phi - math.pi / 2 # 로켓 위치에서의 수평선 각도 계산
                
                if v_current > 0: # 속도가 있는 경우에만
                    phi_v = math.atan2(vy, vx) # 속도 벡터의 각도 계산
                    vel_pitch = phi_v - horizon_angle # 수평선 기준 속도 벡터의 피치각 계산
                    vel_pitch = (vel_pitch + math.pi) % (2 * math.pi) - math.pi # 각도 범위를 -pi에서 pi 사이로 정규화
                else: # 속도가 없으면 (정지 상태)
                    vel_pitch = math.pi / 2 # 수직 방향(90도)으로 설정
                    
                thrust = 0.0 # 엔진 추력 초기화
                active_c_d = 0.0 # 활성화된 공기저항 계수 초기화
                active_area = 0.0 # 활성화된 단면적 초기화
                
                if not orbit_achieved: # 궤도 안착에 성공하지 못한 비행 중일 때
                    if stage == 1: # 1단 연소 단계인 경우
                        active_c_d = s1["c_d"] # 1단 공기저항 계수 적용
                        active_area = s1["area"] # 1단 단면적 적용
                        m_dot = s1["m_dot"] # 1단 연료 소모율
                        v_e = s1["v_e"] # 1단 연료 분사 속도
                        thrust = m_dot * v_e # 1단 엔진 추력 계산 (T = m_dot * v_e)
                        
                        if h_current < pitchover_alt: # 피치오버 고도 도달 전이면
                            pitch_deg = 90.0 # 수직 상승 유지 (90도)
                        elif h_current >= pitchover_alt and h_current < pitchover_alt + pitchover_window: # 피치오버 구간에 진입하면
                            if not pitchover_triggered: # 아직 피치오버 이벤트 기록이 없으면
                                current_event = "🔄 Pitchover: 서서히 동쪽으로 기동 시작" # 이벤트 메시지 갱신
                                history["events"].append({"time": current_time, "x": x, "y": y, "name": "Pitchover"}) # 이벤트 로그 추가
                                pitchover_triggered = True # 피치오버 플래그 활성화
                            frac = (h_current - pitchover_alt) / pitchover_window # 피치오버 구간 내 진행 비율 계산 (0 ~ 1)
                            pitch_deg = 90.0 - (90.0 - target_pitchover_deg) * frac # 목표 피치각까지 서서히 기울이기
                        else: # 피치오버 완료 후에는
                            pitch_deg = math.degrees(vel_pitch) # 비행 속도 벡터 방향과 정렬 (중력 턴 모드)
                            pitch_deg = max(20.0, min(85.0, pitch_deg)) # 각도 하한/상한선 제한 (안전을 위해 20도 ~ 85도)
                            
                        dm = m_dot * dt # 루프 단위 스텝(dt) 동안 소모되는 연료 질량
                        if fuel_1 >= dm: # 1단 연료가 남아있으면
                            fuel_1 -= dm # 연료 소모
                        else: # 1단 연료가 다 떨어졌으면 (연료 전소)
                            fuel_1 = 0.0 # 0으로 고정
                            stage = 1.5 # 1.5단 단계(단 분리 과도기)로 진입
                            sep_timer = 1.5 # 단 분리 대기 타이머 설정 (1.5초)
                            current_event = "💥 Stage 1 Separation: 1단 부스터 탈거" # 이벤트 메시지 갱신
                            history["events"].append({"time": current_time, "x": x, "y": y, "name": "Stage 1 Separation"}) # 이벤트 로그 추가
                            
                            # 부스터 연출 이식
                            booster_active = True # 낙하 부스터 그래픽 활성화
                            booster_x, booster_y = x, y # 부스터 초기 위치 설정 (현재 로켓 위치)
                            booster_vx = vx - 15.0 * (x/r_current) # 분리 충격으로 인한 수평 반동 속도 반영 (속도 감소 방향)
                            booster_vy = vy - 15.0 * (y/r_current) # 분리 충격으로 인한 수직 반동 속도 반영 (속도 감소 방향)
                            booster_rot = 0.0 # 부스터 회전각 초기화
                            booster_heading = math.atan2(vy, vx) if (vx != 0 or vy != 0) else math.pi/2 # 부스터 진행 방향 설정
                            
                            # 단 분리 충격파 화염 & 가스 파티클 대량 방출
                            for _ in range(40): # 파티클 40개 생성
                                p_ang = random.uniform(0, 2*math.pi) # 무작위 분사 방향 각도
                                p_spd = random.uniform(8, 24) # 무작위 파티클 분사 속도
                                p_vx = vx + p_spd * math.cos(p_ang) # 파티클 x 속도 성분
                                p_vy = vy + p_spd * math.sin(p_ang) # 파티클 y 속도 성분
                                particles.append(Particle( # 파티클 목록에 추가
                                    x, y, p_vx, p_vy,
                                    color=random.choice([(255, 120, 10), (255, 230, 20), (243, 244, 246), (100, 110, 120)]), # 화염 및 연기 색상 무작위 선택
                                    size=random.randint(3, 8), # 무작위 크기
                                    lifetime=random.randint(15, 45) # 무작위 수명
                                ))
                            
                    elif stage == 1.5: # 단 분리 대기 단계인 경우 (엔진 정지 상태)
                        thrust = 0.0 # 엔진 추력 0
                        active_c_d = s2["c_d"] # 2단 공기저항 계수 적용
                        active_area = s2["area"] # 2단 단면적 적용
                        sep_timer -= dt # 타이머 차감
                        if sep_timer <= 0: # 대기 시간이 끝나면
                            stage = 2 # 2단 점화 단계로 이행
                            sep_alt = h_current # 분리 시점의 고도 기록
                            sep_pitch = math.degrees(vel_pitch) # 분리 시점의 피치각 기록
                            current_event = "🔥 Stage 2 Ignition: 2단 엔진 시동 완료!" # 이벤트 메시지 갱신
                            history["events"].append({"time": current_time, "x": x, "y": y, "name": "Stage 2 Ignition"}) # 이벤트 로그 추가
                            
                    elif stage == 2: # 2단 추진 단계인 경우
                        active_c_d = s2["c_d"] # 2단 공기저항 계수
                        active_area = s2["area"] # 2단 단면적
                        m_dot = s2["m_dot"] # 2단 연료 소모율
                        v_e = s2["v_e"] # 2단 연료 분사 속도
                        thrust = m_dot * v_e # 2단 엔진 추력 계산
                        
                        h_target = 200000.0 # 목표 원궤도 진입 고도 (200km)
                        frac = (h_current - sep_alt) / (h_target - sep_alt) # 2단 점화 후 목표 고도까지 진행률 계산 (0 ~ 1)
                        frac = max(0.0, min(1.0, frac)) # 범위를 0.0 ~ 1.0으로 가둠
                        target_pitch_deg = sep_pitch * (1.0 - frac) # 목표 고도에 가까워질수록 피치각을 서서히 0도(수평)로 조절
                        pitch_deg = target_pitch_deg # 각도 적용
                        
                        dm = m_dot * dt # 2단 연료 소모량
                        if fuel_2 >= dm: # 2단 연료가 남아있으면
                            fuel_2 -= dm # 연료 소모
                        else: # 연료가 다 떨어졌으면
                            fuel_2 = 0.0 # 0으로 고정
                            stage = 3 # 3단(비추진/페이로드 자유 비행) 단계로 진입
                            current_event = "⚠️ Stage 2 Burnout: 연료 전소!" # 이벤트 메시지 갱신
                            is_playing = False # 시뮬레이션 일시정지
                            break # 계산 루프 탈출
                            
                    thrust_angle_rad = horizon_angle + math.radians(pitch_deg) # 수평 기준 추진 방향 각도(라디안) 계산
                else: # 궤도 안착에 성공한 경우
                    thrust = 0.0 # 엔진 정지
                    stage = 3 # 자유 비행 단계로 설정
                    pitch_deg = 0.0 # 피치각 0도 (수평 유지)
                    thrust_angle_rad = horizon_angle # 수평선 방향으로 각도 설정
                    active_c_d = s2["c_d"] # 2단 공기저항
                    active_area = s2["area"] # 2단 단면적
                    
                if stage == 1: # 1단 작동 중일 때는 전체 질량 합산 (1단 + 2단 + 페이로드)
                    total_mass = s1["dry_mass"] + fuel_1 + s2["dry_mass"] + fuel_2 + p_mass
                else: # 1단 분리 후에는 2단과 페이로드 질량만 합산
                    total_mass = s2["dry_mass"] + fuel_2 + p_mass
                    
                # 물리 스텝 수행
                res = calculate_next_step(x, y, vx, vy, total_mass, thrust, thrust_angle_rad, dt, active_c_d, active_area)
                
                # 상태 갱신
                x, y, vx, vy = res["x"], res["y"], res["vx"], res["vy"] # 위치 및 속도 최신화
                current_time += dt # 시뮬레이션 시간 증가
                
                # 물리 스텝 이후 정보 갱신
                r_current = math.sqrt(x**2 + y**2)
                h_current = r_current - R_E
                v_current = math.sqrt(vx**2 + vy**2)
                v_orbit_req = math.sqrt(GM / r_current)
                
                # 지표면 추락 검사
                if h_current <= 0.0 and current_time > 1.0:
                    mission_failed = True
                    current_event = "💥 Mission Failed: 로켓이 지표면에 추락하였습니다."
                    history["events"].append({"time": current_time, "x": x, "y": y, "name": "Crash"})
                    is_playing = False
                    break
                    
                # 궤도 진입 성공 여부 검사 (근지점 고도 계산을 통한 물리적 안착 판정)
                if not orbit_achieved:
                    # 궤도 역학 에너지 및 각운동량 계산
                    energy = (v_current**2) / 2.0 - GM / r_current
                    if energy < 0:  # 닫힌 궤도(타원 또는 원)인 경우에만 판정
                        angular_momentum = x * vy - y * vx
                        ecc_sq = 1.0 + (2.0 * energy * (angular_momentum**2)) / (GM**2)
                        ecc = math.sqrt(max(0.0, ecc_sq))
                        
                        # 장반경 및 근지점(periapsis) 고도 계산
                        semi_major = -GM / (2.0 * energy)
                        r_periapsis = semi_major * (1.0 - ecc)
                        h_periapsis = r_periapsis - R_E
                        
                        # 근지점 고도가 120km 이상이면 대기권 영향이 미미한 안정한 궤도 진입으로 판정
                        if h_periapsis >= 120000.0:
                            orbit_achieved = True
                            current_event = f"🎉 Orbit Achieved: 궤도 안착 성공! (근지점 고도: {h_periapsis/1000:.1f}km)"
                            history["events"].append({"time": current_time, "x": x, "y": y, "name": "Orbit Achieved"})
                
                # Falling Booster Gravity
                if booster_active: # 떨어지는 부스터가 활성화 상태인 경우
                    br = math.sqrt(booster_x**2 + booster_y**2) # 지구 중심으로부터 부스터까지의 거리
                    bh = br - R_E # 부스터 고도
                    if bh <= 0: # 고도가 0 이하이면 (지표면 충돌)
                        booster_active = False # 낙하 부스터 상태 종료
                    else: # 공중에 있을 때
                        bg_acc = G0 * (R_E / br)**2 # 고도에 따른 중력 가속도 계산
                        bgx = -bg_acc * (booster_x / br) # 중력 가속도 x 성분
                        bgy = -bg_acc * (booster_y / br) # 중력 가속도 y 성분
                        
                        if bh < 100000.0: # 100km 대기권 내에 있는 경우 공기 밀도 계산
                            brho = RHO_0 * math.exp(-bh / H_SCALE) # 부스터 위치의 공기 밀도
                        else: # 외기권은 공기 밀도 0
                            brho = 0.0
                            
                        b_speed = math.sqrt(booster_vx**2 + booster_vy**2) # 부스터 속도
                        bdrag_x, bdrag_y = 0.0, 0.0 # 부스터 항력 초기화
                        if b_speed > 0: # 속도가 있을 때 항력 성분 계산
                            bdrag = 0.5 * brho * (b_speed**2) * s1["c_d"] * s1["area"] # 항력 공식 (F_D = 0.5 * rho * v^2 * C_d * A)
                            bdrag_x = -bdrag * (booster_vx / b_speed) # 속도 반대 방향 항력 x
                            bdrag_y = -bdrag * (booster_vy / b_speed) # 속도 반대 방향 항력 y
                            
                        b_ax = (bdrag_x / s1["dry_mass"]) + bgx # 항력과 중력을 반영한 부스터 가속도 x
                        b_ay = (bdrag_y / s1["dry_mass"]) + bgy # 항력과 중력을 반영한 부스터 가속도 y
                        
                        booster_vx += b_ax * dt # 부스터 속도 x 업데이트
                        booster_vy += b_ay * dt # 부스터 속도 y 업데이트
                        booster_x += booster_vx * dt # 부스터 위치 x 업데이트
                        booster_y += booster_vy * dt # 부스터 위치 y 업데이트
                        # 부스터 낙하 시 서서히 자이로 텀블링 회전 적용
                        booster_rot += 0.015 # 회전각 누적
                        
                # 0.1초 마다 텔레메트리 누적 기록
                if abs(current_time - last_logged_time) >= 0.1: # 0.1초 간격으로 검사
                    last_logged_time = current_time # 이전 로그 기록 시간 업데이트
                    history["time"].append(current_time) # 시간 저장
                    history["x"].append(x) # 위치 x 저장
                    history["y"].append(y) # 위치 y 저장
                    history["vx"].append(vx) # 속도 vx 저장
                    history["vy"].append(vy) # 속도 vy 저장
                    history["altitude"].append(h_current) # 고도 저장
                    history["speed"].append(v_current) # 속도 크기 저장
                    history["g_force"].append(res["g_force"]) # 중력가속도 크기 저장
                    history["q"].append(res["q"]) # 대기 동압 저장
                    history["fuel_1"].append(fuel_1) # 1단 연료량 저장
                    history["fuel_2"].append(fuel_2) # 2단 연료량 저장
                    history["stage"].append(stage) # 단 단계 저장
                    
                    history_pts.append((x, y)) # 궤적 표시용 점 추가
                    
                # 실시간 배기 파티클 생성
                if thrust > 0: # 추력이 있을 때만 파티클 생성
                    particle_vx = -30.0 * math.cos(thrust_angle_rad) + random.uniform(-5, 5) # 분사 방향 역방향 속도 x (+ 오차)
                    particle_vy = 30.0 * math.sin(thrust_angle_rad) + random.uniform(-5, 5) # 분사 방향 역방향 속도 y (+ 오차)
                    
                    particles.append(Particle( # 엔진 분사 가스 파티클 추가
                        x, y, particle_vx, particle_vy,
                        color=random.choice([(255, 230, 20), (255, 120, 10), (239, 68, 68)]), # 불꽃 색상 조합
                        size=random.randint(2, 6), # 무작위 파티클 크기
                        lifetime=random.randint(15, 30) # 무작위 수명
                    ))
                    
        # 파티클 업데이트
        for p in particles:
            p.update() # 모든 활성 파티클 이동 및 수명 차감
        particles = [p for p in particles if p.lifetime > 0] # 수명이 다한 파티클은 제거
        
        # heading 갱신 (속도가 있을 때만 업데이트하여 충돌 순간 각도 보존)
        if (vx != 0 or vy != 0): # 속도가 0이 아닐 때만
            heading = math.atan2(vy, vx) # 로켓의 비행각 업데이트
            
        # -------------------------------------------------------------
        # UI 및 뷰포트 그리기
        # -------------------------------------------------------------
        screen.fill(BG_COLOR) # 화면 배경 지우기
        
        r_current = math.sqrt(x**2 + y**2) # 중심점과의 거리 재계산
        h_current = r_current - R_E # 고도 재계산
        v_current = math.sqrt(vx**2 + vy**2) # 속도 크기 재계산
        v_orbit_req = math.sqrt(GM / r_current) # 현재 고도의 목표 원궤도 속도 재계산
        q_current = 0.5 * (RHO_0 * math.exp(-h_current / H_SCALE) if h_current < 100000.0 else 0) * (v_current**2) # 대기 동압 재계산
        
        cx, cy = 384, 384 # 768x768 메인 화면의 중심점 좌표 (픽셀 단위)
        
        if camera_mode == "earth": # 지구 중심 카메라 모드인 경우
            max_r = max(r_current, R_E) * 1.15 # 뷰포트에 지구가 다 들어오도록 반경 최대치 설정
            scale = (360.0 / max_r) * zoom_slider.val # 픽셀 변환 스케일 계산 (슬라이더 줌 반영)
            rx_scr = cx + x * scale # 로켓의 화면 상 x 좌표
            ry_scr = cy - y * scale # 로켓의 화면 상 y 좌표 (y축 반전)
            ex_scr = cx # 지구 중심 x 좌표 (화면 중심)
            ey_scr = cy # 지구 중심 y 좌표 (화면 중심)
        else: # 로켓 추적 카메라 모드인 경우
            scale = 0.002 * zoom_slider.val # 로켓 추적 시 정밀 스케일 계산
            rx_scr = cx # 로켓을 화면 중심 x에 고정
            ry_scr = cy # 로켓을 화면 중심 y에 고정
            ex_scr = cx - x * scale # 상대적인 지구 중심 x 좌표
            ey_scr = cy + y * scale # 상대적인 지구 중심 y 좌표
            
        # 별자리 렌더링
        for s in stars:
            sx = s["x"] # 별의 기본 x 위치
            sy = s["y"] # 별의 기본 y 위치
            if camera_mode == "rocket": # 로켓 카메라 모드일 경우 패닝 효과 추가
                sx = (s["x"] - (x * 0.00004) * 360) % 768 # 비행에 맞춰 무한 스크롤 x
                sy = (s["y"] + (y * 0.00004) * 360) % 768 # 비행에 맞춰 무한 스크롤 y
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), 1) # 하얀색 점으로 별 그리기
            
        # 지구 대기권 발광 광륜 렌더링 (메모리 과다 방지 가드 추가)
        earth_r_px = int(R_E * scale) # 화면에 그려질 지구 반경 (픽셀 단위)
        if 0 < earth_r_px < 3000: # 지구가 너무 크지 않은 적당한 줌 수준일 때
            for j in range(8): # 8중 레이어로 번지는 대기 광륜 연출
                alpha = int(12 * (1.0 - j / 8)) # 멀어질수록 옅어지도록 투명도 조절
                draw_transparent_circle(screen, ATMOSPHERE_COLOR, (ex_scr, ey_scr), earth_r_px + j * 5, alpha) # 대기 효과 그리기
            pygame.draw.circle(screen, EARTH_BLUE, (int(ex_scr), int(ey_scr)), earth_r_px) # 지구 구체 그리기
            pygame.draw.circle(screen, CYAN, (int(ex_scr), int(ey_scr)), earth_r_px, width=1) # 지구 표면 실선 테두리
        elif earth_r_px >= 3000: # 줌이 과도하게 확대된 경우 (로켓 주변 등)
            dist_to_center = math.sqrt((ex_scr - cx)**2 + (ey_scr - cy)**2) # 화면 중심과 지구 중심 거리
            if dist_to_center - earth_r_px < 1000: # 화면 영역 내에 지구 경계선이 걸치는 경우에만 제한적 렌더링
                try:
                    pygame.draw.circle(screen, EARTH_BLUE, (int(ex_scr), int(ey_scr)), earth_r_px) # 지구 일부 렌더링
                    pygame.draw.circle(screen, CYAN, (int(ex_scr), int(ey_scr)), earth_r_px, width=1) # 테두리 렌더링
                except pygame.error: # 너무 큰 구체 렌더링 오류 예외 처리
                    pass
            
        # 우주 경계선(카르만 라인 100km)
        karman_r_px = int((R_E + 100000.0) * scale) # 화면 상 카르만 라인 반경 계산
        if 0 < karman_r_px < 3000: # 화면에 표시 가능한 크기일 때
            draw_transparent_circle(screen, (249, 115, 22), (ex_scr, ey_scr), karman_r_px, 15) # 주황색 반투명 원으로 표현
        
        # 발사대 위치 마커
        pad_x_scr = ex_scr # 지구 최상단이 북극이자 발사대 위치 x
        pad_y_scr = ey_scr - earth_r_px # 발사대 y 좌표 (지구 반경만큼 뺀 지표면)
        if -1000 < pad_x_scr < 2000 and -1000 < pad_y_scr < 2000: # 화면 유효 범위 내에 발사대가 보이면
            pygame.draw.circle(screen, YELLOW, (int(pad_x_scr), int(pad_y_scr)), 3) # 노란색 작은 점으로 마킹
        
        # 비행 궤적 경로 렌더링
        if len(history_pts) > 1: # 저장된 경로 점이 2개 이상일 때
            draw_pts = [] # 화면 좌표로 변환한 점 리스트
            for px, py in history_pts: # 저장된 모든 텔레메트리 점 순회
                tx = ex_scr + px * scale # 화면 x로 변환
                ty = ey_scr - py * scale # 화면 y로 변환
                if -2000 < tx < 3000 and -2000 < ty < 3000: # 그리기 가능한 화면 좌표 가드
                    draw_pts.append((int(tx), int(ty))) # 리스트 추가
            if len(draw_pts) >= 2: # 변환된 점들이 충분히 있으면
                pygame.draw.lines(screen, PATH_COLOR, False, draw_pts, width=2) # 실선으로 궤적 그리기
                
        # 1단 분리 부스터 낙하물
        if booster_active: # 분리된 부스터가 떨어지고 있는 중이면
            bx_scr = ex_scr + booster_x * scale # 부스터 화면 x 좌표
            by_scr = ey_scr - booster_y * scale # 부스터 화면 y 좌표
            if -100 < bx_scr < 868 and -100 < by_scr < 868: # 화면 유효 영역 근처에 있는 경우에만
                booster_stage_sz = (1.5 if camera_mode == "rocket" else 0.6) * zoom_slider.val # 부스터 크기 계산
                draw_booster_drop(screen, bx_scr, by_scr, booster_heading, booster_rot, booster_stage_sz) # 회전하며 떨어지는 이미지 그리기
                if camera_mode == "rocket": # 로켓 추적 모드에서는 텍스트 표시
                    txt_b = font_hud_title.render("Booster", True, GRAY) # 부스터 텍스트 서피스
                    screen.blit(txt_b, (int(bx_scr) + 10, int(by_scr) - 10)) # 부스터 옆에 레이블 블릿
                    
        # 파티클 드로잉
        for p in particles: # 모든 활성 파티클 순회
            px_scr = ex_scr + p.x * scale # 파티클 화면 x 좌표
            py_scr = ey_scr - p.y * scale # 파티클 화면 y 좌표
            if 0 < px_scr < 768 and 0 < py_scr < 768: # 768px 시뮬 영역 내부일 때만
                p.draw(screen) # 개별 파티클 그리기
                
        # Draw Rocket (줌 스케일 줌 팩터 반영 완료, 충돌 각도 보존 완료)
        rocket_sz = (2.0 if camera_mode == "rocket" else 1.0) * zoom_slider.val # 카메라 모드 및 줌 설정에 맞춘 로켓 픽셀 크기 배율 계산
        draw_sleek_rocket(screen, rx_scr, ry_scr, heading, rocket_sz, stage, orbit_achieved, thrust > 0) # 세련된 로켓 아이콘 그리기
        
        # Rocket ring halo glow
        draw_transparent_circle(screen, CYAN, (rx_scr, ry_scr), int(5 * rocket_sz), 30) # 로켓 주변의 푸른색 야광 링 효과 그리기
        
        # -------------------------------------------------------------
        # HUD 계기판 패널 그리기 (우측 256px 영역)
        # -------------------------------------------------------------
        hud_rect = pygame.Rect(768, 0, 256, HEIGHT) # 계기판 영역 정의
        pygame.draw.rect(screen, HUD_BG, hud_rect) # 계기판 어두운 배경 채우기
        pygame.draw.line(screen, (55, 65, 81), (768, 0), (768, HEIGHT), width=2) # 시뮬영역과 경계선 구분선 그리기
        
        title_surf = font_large.render("미션 컨트롤 패널", True, CYAN) # 패널 제목 서피스
        screen.blit(title_surf, (785, 20)) # 제목 배치
        
        def draw_hud_card(y, label, val_str, unit, alert=False): # HUD 카드 개별 컴포넌트 렌더링 헬퍼 함수
            card_rect = pygame.Rect(785, y, 220, 50) # 카드의 사각형 박스 영역
            bg = (75, 30, 30) if alert else HUD_CARD_BG # 경고 상태일 땐 붉은 배경, 평소엔 기본 배경
            pygame.draw.rect(screen, bg, card_rect, border_radius=6) # 둥근 사각형 카드 배경 그리기
            pygame.draw.rect(screen, RED if alert else (55, 65, 81), card_rect, width=1, border_radius=6) # 테두리선 그리기
            
            lbl_surf = font_hud_title.render(label, True, TEXT_COLOR) # 항목 이름 라벨 서피스
            screen.blit(lbl_surf, (795, y + 4)) # 항목명 렌더링
            
            val_surf = font_hud_val.render(val_str, True, RED if alert else CYAN) # 정보 수치값 텍스트 서피스
            screen.blit(val_surf, (795, y + 20)) # 수치값 렌더링
            
            uni_surf = font_hud_title.render(unit, True, GRAY) # 단위명 서피스
            screen.blit(uni_surf, (795 + val_surf.get_width() + 5, y + 26)) # 수치 텍스트 바로 오른쪽에 단위 정렬 배치
            
        g_force_now = res["g_force"] if is_playing and 'res' in locals() else 0.0 # 실행 중일 때 최신 중력 가속도 추출
        
        draw_hud_card(70, "비행 시간 (Time)", f"{current_time:.1f}", "s") # 시간 HUD 카드 출력
        draw_hud_card(130, "비행 고도 (Altitude)", f"{h_current/1000:.2f}", "km") # 고도 HUD 카드 출력
        draw_hud_card(190, "비행 속도 (Velocity)", f"{v_current:.0f}", f"m/s (원궤도:{v_orbit_req:.0f})") # 속도 HUD 카드 출력
        draw_hud_card(250, "중력 가속도 (G-Force)", f"{g_force_now:.2f}", "G", alert=(g_force_now > 6.0)) # 중력가속도 HUD 카드 (6G 초과 시 붉은색 경고)
        draw_hud_card(310, "대기 동압 (Q)", f"{q_current:.0f}", "Pa", alert=(q_current > 18000.0)) # 대기 동압 HUD 카드 (맥스 Q 부하 18kPa 이상 경고)
        
        # 연료 잔량 인디케이터
        lbl_f1 = font_hud_title.render("1단 연료 잔량", True, TEXT_COLOR) # 1단 연료 라벨 서피스
        screen.blit(lbl_f1, (785, 375)) # 1단 연료 라벨 그리기
        pygame.draw.rect(screen, (31, 41, 55), (785, 390, 220, 12), border_radius=4) # 1단 게이지 배경 바
        pct_1 = fuel_1 / s1["fuel_mass"] # 1단 연료 비율 계산 (0 ~ 1)
        if pct_1 > 0: # 잔여 연료가 있을 때만 채우기
            pygame.draw.rect(screen, RED if pct_1 < 0.2 else AMBER, (785, 390, int(220 * pct_1), 12), border_radius=4) # 20% 미만일 땐 빨간색, 평소엔 황색
            
        lbl_f2 = font_hud_title.render("2단 연료 잔량", True, TEXT_COLOR) # 2단 연료 라벨 서피스
        screen.blit(lbl_f2, (785, 410)) # 2단 연료 라벨 그리기
        pygame.draw.rect(screen, (31, 41, 55), (785, 425, 220, 12), border_radius=4) # 2단 게이지 배경 바
        pct_2 = fuel_2 / s2["fuel_mass"] # 2단 연료 비율 계산
        if pct_2 > 0: # 잔여 연료가 있을 때만 채우기
            pygame.draw.rect(screen, CYAN, (785, 425, int(220 * pct_2), 12), border_radius=4) # 2단은 하늘색 게이지바로 채우기
            
        # 줌 슬라이더 그리기
        zoom_slider.draw(screen, font_hud_title) # 슬라이더 그리기 호출
        
        # 버튼 그리기
        for btn in buttons:
            btn.draw(screen) # 리셋, 카메라, 플레이 및 스피드 버튼 일괄 그리기
            
        lbl_spd = font_hud_title.render(f"배속 조절 (현재: {speed_multiplier}x 배속)", True, TEXT_COLOR) # 배속 안내 라벨 서피스
        screen.blit(lbl_spd, (785, 605)) # 배속 정보 표시
        
        # 하단 메시지/이벤트 로그 창
        event_bg = pygame.Rect(785, 680, 220, 65) # 하단 이벤트 로그 영역 설정
        pygame.draw.rect(screen, (30, 27, 75), event_bg, border_radius=8) # 짙은 남색 배경
        pygame.draw.rect(screen, (67, 56, 202), event_bg, width=1, border_radius=8) # 파란색 보더 테두리
        
        words = current_event.split(" ") # 텍스트 자동 줄바꿈용 단어 분할
        lines = [] # 나뉜 줄 저장소
        curr_line = "" # 현재 구성 중인 줄
        for w in words: # 모든 단어를 순회하며
            if font_main.size(curr_line + w)[0] < 200: # 한 줄 제한폭(200px)보다 작으면 추가
                curr_line += w + " "
            else: # 초과하면 이전 줄을 줄 리스트에 넣고 새 줄 시작
                lines.append(curr_line)
                curr_line = w + " "
        lines.append(curr_line) # 미처리 남은 마지막 줄 추가
        
        for idx, ln in enumerate(lines[:3]): # 최대 3줄까지만 제한하여 표시
            ln_surf = font_main.render(ln, True, (165, 180, 252)) # 연보라색 텍스트 렌더링
            screen.blit(ln_surf, (795, 686 + idx * 16)) # 세로 간격 16px로 출력
            
        # 💥 미션 실패(추락) 오버레이 연출 드로잉
        if mission_failed: # 미션이 실패한 상태라면
            # 1. 768px 메인 화면 영역에 반투명 붉은 핏빛 필터 적용
            overlay = pygame.Surface((768, 768), pygame.SRCALPHA) # 투명 채널 포함된 오버레이 서피스 생성
            overlay.fill((30, 8, 8, 90)) # 어두운 빨간색 투명 필터
            screen.blit(overlay, (0, 0)) # 시뮬 영역 위에 블릿
            
            # 2. 멋진 네온 레드 경고 플레이트 상자
            box_w, box_h = 440, 140 # 안내 상자 크기
            box_x = (768 - box_w) // 2 # 가로 중앙 정렬 x
            box_y = (768 - box_h) // 2 # 세로 중앙 정렬 y
            pygame.draw.rect(screen, (24, 15, 15), (box_x, box_y, box_w, box_h), border_radius=12) # 아주 어두운 적색 상자 배경
            pygame.draw.rect(screen, RED, (box_x, box_y, box_w, box_h), width=2, border_radius=12) # 네온 RED 테두리선
            
            # 3. 미션 실패 경고 타이틀 렌더링
            fail_title = font_large.render("💥 MISSION FAILED (실패!)", True, RED) # 빨간색 실패 타이틀
            screen.blit(fail_title, (box_x + (box_w - fail_title.get_width()) // 2, box_y + 20)) # 상자 내부 중앙 정렬 출력
            
            fail_desc1 = font_main.render("로켓이 제어 능력을 상실하고 지표면에 추락하였습니다.", True, TEXT_COLOR) # 사유 설명 서피스
            screen.blit(fail_desc1, (box_x + (box_w - fail_desc1.get_width()) // 2, box_y + 60)) # 본문 배치
            
            # 4. 부드럽게 깜빡이는 조작 키 안내
            if (pygame.time.get_ticks() // 500) % 2 == 0: # 500ms 주기로 깜빡이는 플래그 계산
                fail_desc2 = font_hud_title.render("창(X)을 닫거나 ESC 키를 누르면 비행 분석 대시보드로 이동합니다.", True, YELLOW) # 조작 설명 서피스
                screen.blit(fail_desc2, (box_x + (box_w - fail_desc2.get_width()) // 2, box_y + 95)) # 안내 메시지 배치
            
        pygame.display.flip() # 더블 버퍼링 화면 전환 (화면 갱신)
        clock.tick(FPS) # 설정된 FPS(60)에 맞게 대기 및 프레임 제한
        
    pygame.quit() # 시뮬 루프 종료 시 pygame 리소스 자원 해제
    return history # 수집된 비행 데이터가 포함된 history 딕셔너리 반환


def get_user_input():
    """터미널에서 로켓 제원을 입력받는 함수"""
    print("=" * 50)
    print("🚀 2단 로켓 시뮬레이터 제원 입력 🚀")
    print("Enter 키를 그냥 누르면 기본값이 자동으로 적용됩니다.")
    print("=" * 50)

    def prompt_float(prompt_text, default_val, max_val=None):
        user_val = input(f"▶ {prompt_text} [기본값: {default_val}]: ")
        if user_val.strip() == "":
            if max_val is not None and default_val > max_val:
                print(f"  ⚠️ 기본값({default_val})이 현재 단면적 기준 최대 제한값({max_val:.1f})을 초과합니다. 직접 값을 입력하세요.")
                return prompt_float(prompt_text, default_val, max_val)
            return default_val
        try:
            val = float(user_val)
            if val <= 0:
                print("  ⚠️ 입력값은 0보다 커야 합니다. 다시 입력해 주세요.")
                return prompt_float(prompt_text, default_val, max_val)
            if max_val is not None and val > max_val:
                print(f"  ⚠️ 입력값이 단면적 기준 최대 제한값({max_val:.1f} kg)을 초과했습니다. 다시 입력해 주세요.")
                return prompt_float(prompt_text, default_val, max_val)
            return val
        except ValueError:
            print("  ⚠️ 잘못된 입력입니다. 숫자로 다시 입력하거나 Enter를 누르세요.")
            return prompt_float(prompt_text, default_val, max_val)  # 재귀로 다시 물어봄

    print("\n[1단 로켓 설정]")
    s1_area = prompt_float("1단 단면적 (m^2)", DEFAULT_STAGE_1["area"])
    s1_max_dry = 2500.0 * s1_area
    s1_dry_mass = prompt_float(f"1단 구조체 질량 (kg) (최대 {s1_max_dry:.1f}kg)", DEFAULT_STAGE_1["dry_mass"], max_val=s1_max_dry)
    s1_max_fuel = 10000.0 * s1_area
    s1_fuel_mass = prompt_float(f"1단 초기 연료 질량 (kg) (최대 {s1_max_fuel:.1f}kg)", DEFAULT_STAGE_1["fuel_mass"], max_val=s1_max_fuel)

    print("\n[2단 로켓 설정]")
    s2_area = prompt_float("2단 단면적 (m^2)", DEFAULT_STAGE_2["area"])
    s2_max_dry = 2500.0 * s2_area
    s2_dry_mass = prompt_float(f"2단 구조체 질량 (kg) (최대 {s2_max_dry:.1f}kg)", DEFAULT_STAGE_2["dry_mass"], max_val=s2_max_dry)
    s2_max_fuel = 10000.0 * s2_area
    s2_fuel_mass = prompt_float(f"2단 초기 연료 질량 (kg) (최대 {s2_max_fuel:.1f}kg)", DEFAULT_STAGE_2["fuel_mass"], max_val=s2_max_fuel)

    print("\n[페이로드(위성) 설정]")
    payload_mass = prompt_float("페이로드 질량 (kg)", DEFAULT_PAYLOAD_MASS)

    print("\n✅ 입력 완료! 시뮬레이션을 시작합니다...\n")

    # 기존 기본 제원 딕셔너리를 복사한 뒤, 사용자가 입력한 값으로 덮어씌움
    custom_stage_1 = DEFAULT_STAGE_1.copy()
    custom_stage_1.update({"dry_mass": s1_dry_mass, "fuel_mass": s1_fuel_mass, "area": s1_area})

    custom_stage_2 = DEFAULT_STAGE_2.copy()
    custom_stage_2.update({"dry_mass": s2_dry_mass, "fuel_mass": s2_fuel_mass, "area": s2_area})

    return custom_stage_1, custom_stage_2, payload_mass



if __name__ == "__main__":
    # 1. 시뮬레이션 시작 전 사용자 입력 받기
    custom_s1, custom_s2, p_mass = get_user_input() # 입력함수 호출

    # 2. 입력받은 커스텀 제원을 pygame 시뮬레이션 함수로 전달
    history = run_pygame_simulation(stage_1=custom_s1, stage_2=custom_s2, payload_mass=p_mass) # pygame 시뮬레이션 시작

    # 3. 시뮬레이션 종료 후 데이터 분석 창 띄우기
    if history and len(history.get("time", [])) > 0:
        plot_rocket_analysis(history)