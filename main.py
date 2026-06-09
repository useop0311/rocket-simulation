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
    "fuel_mass": 80000.0,   # kg (1단 초기 연료 질량)
    "m_dot": 492.28,        # kg/s (초당 연료 소모율 M_DOT)
    "v_e": 2843.93,         # m/s (연료 분사 속도 V_E)
    "c_d": 0.5,             # 공기저항 계수 C_D
    "area": 8.0,            # 단면적 AREA (m^2)
}

DEFAULT_STAGE_2 = {
    "dry_mass": 20000.0,    # kg
    "fuel_mass": 20000.0,   # kg-연료
    "m_dot": 89.97,         # kg/s
    "v_e": 3334.26,         # m/s
    "c_d": 0.5,             # 공기저항
    "area": 4.0,            # 단면적
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
    
    # 전달받은 제원 또는 디폴트 제원 적용
    s1 = stage_1 if stage_1 is not None else DEFAULT_STAGE_1
    s2 = stage_2 if stage_2 is not None else DEFAULT_STAGE_2
    p_mass = payload_mass if payload_mass is not None else DEFAULT_PAYLOAD_MASS
    
    # 시뮬레이션 상태
    x = 0.0
    y = R_E
    vx = 0.0
    vy = 0.0
    thrust = 0.0
    heading = math.pi / 2 # 로켓의 방위각 초기화 (수직)

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
    pitchover_alt = 1500.0
    pitchover_window = 1000.0
    target_pitchover_deg = 80.0
    
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
                # r - 중심으로부터 고도, h - 지표면으로부터 고도, v - 속도
                r_current = math.sqrt(x**2 + y**2)
                h_current = r_current - R_E
                v_current = math.sqrt(vx**2 + vy**2)
                
                # 지표면 충돌 시 즉시 일시정지 및 실패 연출 돌입 (창 바로 꺼지지 않고 각도 유지)
                if h_current <= 0.0 and current_time > 5.0: # 5초 이상 지났는데 아직 지상이면
                    is_playing = False
                    mission_failed = True
                    current_event = "💥 MISSION FAILED: 로켓이 추락하여 지표면에 충돌했습니다! (창을 닫거나 ESC 키를 누르면 분석 대시보드로 이동합니다.)"
                    break
                    
                v_orbit_req = math.sqrt(GM / r_current)
                
                # 궤도 삽입 판정
                if h_current > 100000.0 and stage >= 2 and not orbit_achieved: # 고도가 일정이상이고 2단 분리한 상태고 궤도 안착 안해놨으면
                    # 위치 단위 백터 계산
                    pos_unit_x = x / r_current
                    pos_unit_y = y / r_current
                    v_radial = vx * pos_unit_x + vy * pos_unit_y # 수직 방향 속도 계산 - 양수면 상승 음수면 하강
                    
                    if v_current >= v_orbit_req - 5.0 and abs(v_radial) < 50.0: # 속도가 충분하고 수직비행 속도 ㄱㅊ으면
                        # 궤도 안착으로 판단
                        orbit_achieved = True
                        current_event = "🛰️ Orbit Achieved: 궤도 안착 성공!"
                        history["events"].append({"time": current_time, "x": x, "y": y, "name": "Orbit Achieved"})
                
                # 비행 방위 계산
                phi = math.atan2(y, x)
                horizon_angle = phi - math.pi / 2
                
                if v_current > 0:
                    phi_v = math.atan2(vy, vx)
                    vel_pitch = phi_v - horizon_angle
                    vel_pitch = (vel_pitch + math.pi) % (2 * math.pi) - math.pi
                else:
                    vel_pitch = math.pi / 2
                    
                thrust = 0.0
                active_c_d = 0.0
                active_area = 0.0
                
                if not orbit_achieved:
                    if stage == 1:
                        active_c_d = s1["c_d"]
                        active_area = s1["area"]
                        m_dot = s1["m_dot"]
                        v_e = s1["v_e"]
                        thrust = m_dot * v_e
                        
                        if h_current < pitchover_alt:
                            pitch_deg = 90.0
                        elif h_current >= pitchover_alt and h_current < pitchover_alt + pitchover_window:
                            if not pitchover_triggered:
                                current_event = "🔄 Pitchover: 서서히 동쪽으로 기동 시작"
                                history["events"].append({"time": current_time, "x": x, "y": y, "name": "Pitchover"})
                                pitchover_triggered = True
                            frac = (h_current - pitchover_alt) / pitchover_window
                            pitch_deg = 90.0 - (90.0 - target_pitchover_deg) * frac
                        else:
                            pitch_deg = math.degrees(vel_pitch)
                            pitch_deg = max(20.0, min(85.0, pitch_deg))
                            
                        dm = m_dot * dt
                        if fuel_1 >= dm:
                            fuel_1 -= dm
                        else:
                            fuel_1 = 0.0
                            stage = 1.5
                            sep_timer = 1.5
                            current_event = "💥 Stage 1 Separation: 1단 부스터 탈거"
                            history["events"].append({"time": current_time, "x": x, "y": y, "name": "Stage 1 Separation"})
                            
                            # 부스터 연출 이식
                            booster_active = True
                            booster_x, booster_y = x, y
                            booster_vx = vx - 15.0 * (x/r_current)
                            booster_vy = vy - 15.0 * (y/r_current)
                            booster_rot = 0.0
                            booster_heading = math.atan2(vy, vx) if (vx != 0 or vy != 0) else math.pi/2
                            
                            # 단 분리 충격파 화염 & 가스 파티클 대량 방출
                            for _ in range(40):
                                p_ang = random.uniform(0, 2*math.pi)
                                p_spd = random.uniform(8, 24)
                                p_vx = vx + p_spd * math.cos(p_ang)
                                p_vy = vy + p_spd * math.sin(p_ang)
                                particles.append(Particle(
                                    x, y, p_vx, p_vy,
                                    color=random.choice([(255, 120, 10), (255, 230, 20), (243, 244, 246), (100, 110, 120)]),
                                    size=random.randint(3, 8),
                                    lifetime=random.randint(15, 45)
                                ))
                            
                    elif stage == 1.5:
                        thrust = 0.0
                        active_c_d = s2["c_d"]
                        active_area = s2["area"]
                        sep_timer -= dt
                        if sep_timer <= 0:
                            stage = 2
                            sep_alt = h_current
                            sep_pitch = math.degrees(vel_pitch)
                            current_event = "🔥 Stage 2 Ignition: 2단 엔진 시동 완료!"
                            history["events"].append({"time": current_time, "x": x, "y": y, "name": "Stage 2 Ignition"})
                            
                    elif stage == 2:
                        active_c_d = s2["c_d"]
                        active_area = s2["area"]
                        m_dot = s2["m_dot"]
                        v_e = s2["v_e"]
                        thrust = m_dot * v_e
                        
                        h_target = 160000.0
                        frac = (h_current - sep_alt) / (h_target - sep_alt)
                        frac = max(0.0, min(1.0, frac))
                        target_pitch_deg = sep_pitch * (1.0 - frac)
                        pitch_deg = target_pitch_deg
                        
                        dm = m_dot * dt
                        if fuel_2 >= dm:
                            fuel_2 -= dm
                        else:
                            fuel_2 = 0.0
                            stage = 3
                            current_event = "⚠️ Stage 2 Burnout: 연료 전소!"
                            is_playing = False
                            break
                            
                    thrust_angle_rad = horizon_angle + math.radians(pitch_deg)
                else:
                    thrust = 0.0
                    stage = 3
                    pitch_deg = 0.0
                    thrust_angle_rad = horizon_angle
                    active_c_d = s2["c_d"]
                    active_area = s2["area"]
                    
                if stage == 1:
                    total_mass = s1["dry_mass"] + fuel_1 + s2["dry_mass"] + fuel_2 + p_mass
                else:
                    total_mass = s2["dry_mass"] + fuel_2 + p_mass
                    
                # 물리 스텝 수행
                res = calculate_next_step(x, y, vx, vy, total_mass, thrust, thrust_angle_rad, dt, active_c_d, active_area)
                
                # 상태 갱신
                x, y, vx, vy = res["x"], res["y"], res["vx"], res["vy"]
                current_time += dt
                
                # Falling Booster Gravity
                if booster_active:
                    br = math.sqrt(booster_x**2 + booster_y**2)
                    bh = br - R_E
                    if bh <= 0:
                        booster_active = False
                    else:
                        bg_acc = G0 * (R_E / br)**2
                        bgx = -bg_acc * (booster_x / br)
                        bgy = -bg_acc * (booster_y / br)
                        
                        if bh < 100000.0:
                            brho = RHO_0 * math.exp(-bh / H_SCALE)
                        else:
                            brho = 0.0
                            
                        b_speed = math.sqrt(booster_vx**2 + booster_vy**2)
                        bdrag_x, bdrag_y = 0.0, 0.0
                        if b_speed > 0:
                            bdrag = 0.5 * brho * (b_speed**2) * s1["c_d"] * s1["area"]
                            bdrag_x = -bdrag * (booster_vx / b_speed)
                            bdrag_y = -bdrag * (booster_vy / b_speed)
                            
                        b_ax = (bdrag_x / s1["dry_mass"]) + bgx
                        b_ay = (bdrag_y / s1["dry_mass"]) + bgy
                        
                        booster_vx += b_ax * dt
                        booster_vy += b_ay * dt
                        booster_x += booster_vx * dt
                        booster_y += booster_vy * dt
                        # 부스터 낙하 시 서서히 자이로 텀블링 회전 적용
                        booster_rot += 0.015
                        
                # 0.1초 마다 텔레메트리 누적 기록
                if abs(current_time - last_logged_time) >= 0.1:
                    last_logged_time = current_time
                    history["time"].append(current_time)
                    history["x"].append(x)
                    history["y"].append(y)
                    history["vx"].append(vx)
                    history["vy"].append(vy)
                    history["altitude"].append(h_current)
                    history["speed"].append(v_current)
                    history["g_force"].append(res["g_force"])
                    history["q"].append(res["q"])
                    history["fuel_1"].append(fuel_1)
                    history["fuel_2"].append(fuel_2)
                    history["stage"].append(stage)
                    
                    history_pts.append((x, y))
                    
                # 실시간 배기 파티클 생성
                if thrust > 0:
                    particle_vx = -30.0 * math.cos(thrust_angle_rad) + random.uniform(-5, 5)
                    particle_vy = 30.0 * math.sin(thrust_angle_rad) + random.uniform(-5, 5)
                    
                    particles.append(Particle(
                        x, y, particle_vx, particle_vy,
                        color=random.choice([(255, 230, 20), (255, 120, 10), (239, 68, 68)]),
                        size=random.randint(2, 6),
                        lifetime=random.randint(15, 30)
                    ))
                    
        # 파티클 업데이트
        for p in particles:
            p.update()
        particles = [p for p in particles if p.lifetime > 0]
        
        # heading 갱신 (속도가 있을 때만 업데이트하여 충돌 순간 각도 보존)
        if (vx != 0 or vy != 0):
            heading = math.atan2(vy, vx)
            
        # -------------------------------------------------------------
        # UI 및 뷰포트 그리기
        # -------------------------------------------------------------
        screen.fill(BG_COLOR)
        
        r_current = math.sqrt(x**2 + y**2)
        h_current = r_current - R_E
        v_current = math.sqrt(vx**2 + vy**2)
        v_orbit_req = math.sqrt(GM / r_current)
        q_current = 0.5 * (RHO_0 * math.exp(-h_current / H_SCALE) if h_current < 100000.0 else 0) * (v_current**2)
        
        cx, cy = 384, 384
        
        if camera_mode == "earth":
            max_r = max(r_current, R_E) * 1.15
            scale = (360.0 / max_r) * zoom_slider.val
            rx_scr = cx + x * scale
            ry_scr = cy - y * scale
            ex_scr = cx
            ey_scr = cy
        else:
            scale = 0.002 * zoom_slider.val
            rx_scr = cx
            ry_scr = cy
            ex_scr = cx - x * scale
            ey_scr = cy + y * scale
            
        # 별자리 렌더링
        for s in stars:
            sx = s["x"]
            sy = s["y"]
            if camera_mode == "rocket":
                sx = (s["x"] - (x * 0.00004) * 360) % 768
                sy = (s["y"] + (y * 0.00004) * 360) % 768
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), 1)
            
        # 지구 대기권 발광 광륜 렌더링 (메모리 과다 방지 가드 추가)
        earth_r_px = int(R_E * scale)
        if 0 < earth_r_px < 3000:
            for j in range(8):
                alpha = int(12 * (1.0 - j / 8))
                draw_transparent_circle(screen, ATMOSPHERE_COLOR, (ex_scr, ey_scr), earth_r_px + j * 5, alpha)
            pygame.draw.circle(screen, EARTH_BLUE, (int(ex_scr), int(ey_scr)), earth_r_px)
            pygame.draw.circle(screen, CYAN, (int(ex_scr), int(ey_scr)), earth_r_px, width=1)
        elif earth_r_px >= 3000:
            dist_to_center = math.sqrt((ex_scr - cx)**2 + (ey_scr - cy)**2)
            if dist_to_center - earth_r_px < 1000:
                try:
                    pygame.draw.circle(screen, EARTH_BLUE, (int(ex_scr), int(ey_scr)), earth_r_px)
                    pygame.draw.circle(screen, CYAN, (int(ex_scr), int(ey_scr)), earth_r_px, width=1)
                except pygame.error:
                    pass
            
        # 우주 경계선(카르만 라인 100km)
        karman_r_px = int((R_E + 100000.0) * scale)
        if 0 < karman_r_px < 3000:
            draw_transparent_circle(screen, (249, 115, 22), (ex_scr, ey_scr), karman_r_px, 15)
        
        # 발사대 위치 마커
        pad_x_scr = ex_scr
        pad_y_scr = ey_scr - earth_r_px
        if -1000 < pad_x_scr < 2000 and -1000 < pad_y_scr < 2000:
            pygame.draw.circle(screen, YELLOW, (int(pad_x_scr), int(pad_y_scr)), 3)
        
        # 비행 궤적 경로 렌더링
        if len(history_pts) > 1:
            draw_pts = []
            for px, py in history_pts:
                tx = ex_scr + px * scale
                ty = ey_scr - py * scale
                if -2000 < tx < 3000 and -2000 < ty < 3000:
                    draw_pts.append((int(tx), int(ty)))
            if len(draw_pts) >= 2:
                pygame.draw.lines(screen, PATH_COLOR, False, draw_pts, width=2)
                
        # 1단 분리 부스터 낙하물
        if booster_active:
            bx_scr = ex_scr + booster_x * scale
            by_scr = ey_scr - booster_y * scale
            if -100 < bx_scr < 868 and -100 < by_scr < 868:
                booster_stage_sz = (1.5 if camera_mode == "rocket" else 0.6) * zoom_slider.val
                draw_booster_drop(screen, bx_scr, by_scr, booster_heading, booster_rot, booster_stage_sz)
                if camera_mode == "rocket":
                    txt_b = font_hud_title.render("Booster", True, GRAY)
                    screen.blit(txt_b, (int(bx_scr) + 10, int(by_scr) - 10))
                    
        # 파티클 드로잉
        for p in particles:
            px_scr = ex_scr + p.x * scale
            py_scr = ey_scr - p.y * scale
            if 0 < px_scr < 768 and 0 < py_scr < 768:
                p.draw(screen)
                
        # Draw Rocket (줌 스케일 줌 팩터 반영 완료, 충돌 각도 보존 완료)
        rocket_sz = (2.0 if camera_mode == "rocket" else 1.0) * zoom_slider.val
        draw_sleek_rocket(screen, rx_scr, ry_scr, heading, rocket_sz, stage, orbit_achieved, thrust > 0)
        
        # Rocket ring halo glow
        draw_transparent_circle(screen, CYAN, (rx_scr, ry_scr), int(5 * rocket_sz), 30)
        
        # -------------------------------------------------------------
        # HUD 계기판 패널 그리기 (우측 256px 영역)
        # -------------------------------------------------------------
        hud_rect = pygame.Rect(768, 0, 256, HEIGHT)
        pygame.draw.rect(screen, HUD_BG, hud_rect)
        pygame.draw.line(screen, (55, 65, 81), (768, 0), (768, HEIGHT), width=2)
        
        title_surf = font_large.render("미션 컨트롤 패널", True, CYAN)
        screen.blit(title_surf, (785, 20))
        
        def draw_hud_card(y, label, val_str, unit, alert=False):
            card_rect = pygame.Rect(785, y, 220, 50)
            bg = (75, 30, 30) if alert else HUD_CARD_BG
            pygame.draw.rect(screen, bg, card_rect, border_radius=6)
            pygame.draw.rect(screen, RED if alert else (55, 65, 81), card_rect, width=1, border_radius=6)
            
            lbl_surf = font_hud_title.render(label, True, TEXT_COLOR)
            screen.blit(lbl_surf, (795, y + 4))
            
            val_surf = font_hud_val.render(val_str, True, RED if alert else CYAN)
            screen.blit(val_surf, (795, y + 20))
            
            uni_surf = font_hud_title.render(unit, True, GRAY)
            screen.blit(uni_surf, (795 + val_surf.get_width() + 5, y + 26))
            
        g_force_now = res["g_force"] if is_playing and 'res' in locals() else 0.0
        
        draw_hud_card(70, "비행 시간 (Time)", f"{current_time:.1f}", "s")
        draw_hud_card(130, "비행 고도 (Altitude)", f"{h_current/1000:.2f}", "km")
        draw_hud_card(190, "비행 속도 (Velocity)", f"{v_current:.0f}", f"m/s (원궤도:{v_orbit_req:.0f})")
        draw_hud_card(250, "중력 가속도 (G-Force)", f"{g_force_now:.2f}", "G", alert=(g_force_now > 6.0))
        draw_hud_card(310, "대기 동압 (Q)", f"{q_current:.0f}", "Pa", alert=(q_current > 18000.0))
        
        # 연료 잔량 인디케이터
        lbl_f1 = font_hud_title.render("1단 연료 잔량", True, TEXT_COLOR)
        screen.blit(lbl_f1, (785, 375))
        pygame.draw.rect(screen, (31, 41, 55), (785, 390, 220, 12), border_radius=4)
        pct_1 = fuel_1 / s1["fuel_mass"]
        if pct_1 > 0:
            pygame.draw.rect(screen, RED if pct_1 < 0.2 else AMBER, (785, 390, int(220 * pct_1), 12), border_radius=4)
            
        lbl_f2 = font_hud_title.render("2단 연료 잔량", True, TEXT_COLOR)
        screen.blit(lbl_f2, (785, 410))
        pygame.draw.rect(screen, (31, 41, 55), (785, 425, 220, 12), border_radius=4)
        pct_2 = fuel_2 / s2["fuel_mass"]
        if pct_2 > 0:
            pygame.draw.rect(screen, CYAN, (785, 425, int(220 * pct_2), 12), border_radius=4)
            
        # 줌 슬라이더 그리기
        zoom_slider.draw(screen, font_hud_title)
        
        # 버튼 그리기
        for btn in buttons:
            btn.draw(screen)
            
        lbl_spd = font_hud_title.render(f"배속 조절 (현재: {speed_multiplier}x 배속)", True, TEXT_COLOR)
        screen.blit(lbl_spd, (785, 605))
        
        # 하단 메시지/이벤트 로그 창
        event_bg = pygame.Rect(785, 680, 220, 65)
        pygame.draw.rect(screen, (30, 27, 75), event_bg, border_radius=8)
        pygame.draw.rect(screen, (67, 56, 202), event_bg, width=1, border_radius=8)
        
        words = current_event.split(" ")
        lines = []
        curr_line = ""
        for w in words:
            if font_main.size(curr_line + w)[0] < 200:
                curr_line += w + " "
            else:
                lines.append(curr_line)
                curr_line = w + " "
        lines.append(curr_line)
        
        for idx, ln in enumerate(lines[:3]):
            ln_surf = font_main.render(ln, True, (165, 180, 252))
            screen.blit(ln_surf, (795, 686 + idx * 16))
            
        # 💥 미션 실패(추락) 오버레이 연출 드로잉
        if mission_failed:
            # 1. 768px 메인 화면 영역에 반투명 붉은 핏빛 필터 적용
            overlay = pygame.Surface((768, 768), pygame.SRCALPHA)
            overlay.fill((30, 8, 8, 90))
            screen.blit(overlay, (0, 0))
            
            # 2. 멋진 네온 레드 경고 플레이트 상자
            box_w, box_h = 440, 140
            box_x = (768 - box_w) // 2
            box_y = (768 - box_h) // 2
            pygame.draw.rect(screen, (24, 15, 15), (box_x, box_y, box_w, box_h), border_radius=12)
            pygame.draw.rect(screen, RED, (box_x, box_y, box_w, box_h), width=2, border_radius=12)
            
            # 3. 미션 실패 경고 타이틀 렌더링
            fail_title = font_large.render("💥 MISSION FAILED (실패!)", True, RED)
            screen.blit(fail_title, (box_x + (box_w - fail_title.get_width()) // 2, box_y + 20))
            
            fail_desc1 = font_main.render("로켓이 제어 능력을 상실하고 지표면에 추락하였습니다.", True, TEXT_COLOR)
            screen.blit(fail_desc1, (box_x + (box_w - fail_desc1.get_width()) // 2, box_y + 60))
            
            # 4. 부드럽게 깜빡이는 조작 키 안내
            if (pygame.time.get_ticks() // 500) % 2 == 0:
                fail_desc2 = font_hud_title.render("창(X)을 닫거나 ESC 키를 누르면 비행 분석 대시보드로 이동합니다.", True, YELLOW)
                screen.blit(fail_desc2, (box_x + (box_w - fail_desc2.get_width()) // 2, box_y + 95))
            
        pygame.display.flip()
        clock.tick(FPS)
        
    pygame.quit()
    return history

if __name__ == "__main__":
    history = run_pygame_simulation()
    if history and len(history.get("time", [])) > 0:
        plot_rocket_analysis(history)
