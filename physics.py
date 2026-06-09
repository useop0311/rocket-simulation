import math

# -------------------------------------------------------------
# 1. 지구 환경 물리 상수 정의
# -------------------------------------------------------------
G0 = 9.80665            # 지표면 중력가속도 (m/s^2)
R_E = 6371000.0         # 지구 반지름 (m)
RHO_0 = 1.225           # 지표면 대기 밀도 (kg/m^3)
H_SCALE = 8500.0        # 대기 스케일 하이트 (m)
GM = G0 * (R_E**2)      # 표준 중력 매개변수 (mu = GM)

# -------------------------------------------------------------
# 2. 2차원 구형 지구 중력 벡터계 기반 물리 계산 함수
# -------------------------------------------------------------
def calculate_next_step(
    x: float, y: float, vx: float, vy: float,
    total_mass: float, thrust: float, thrust_angle_rad: float, 
    dt: float, c_d: float, area: float
) -> dict:
    """
    구형 지구 중심력 2D 벡터계로 변환하여 물리 연산을 수행합니다.
    """
    # 1. 지구 중심으로부터의 거리 및 고도 계산
    r = math.sqrt(x**2 + y**2)
    h = r - R_E
    
    if h < 0:
        h = 0.0
        r = R_E
        
    # 2. 중력 계산 (고도 비례 공식 적용)
    g_acc = G0 * (R_E / (R_E + h))**2
    if r > 0:
        gravity_x = -g_acc * (x / r)
        gravity_y = -g_acc * (y / r)
    else:
        gravity_x, gravity_y = 0.0, 0.0
        
    # 3. 대기 밀도 및 공기 저항 계산 (밀도 지수 감소 공식 적용)
    if h < 100000.0:
        rho = RHO_0 * math.exp(-h / H_SCALE)
    else:
        rho = 0.0
        
    v_speed = math.sqrt(vx**2 + vy**2)
    if v_speed > 0:
        drag_force = 0.5 * rho * (v_speed**2) * c_d * area
        drag_x = -drag_force * (vx / v_speed)
        drag_y = -drag_force * (vy / v_speed)
    else:
        drag_force = 0.0
        drag_x, drag_y = 0.0, 0.0
        
    # 동압 (Dynamic Pressure, Q) 계산
    q = 0.5 * rho * (v_speed**2)
    
    # 4. 추력 벡터 계산
    thrust_x = thrust * math.cos(thrust_angle_rad)
    thrust_y = thrust * math.sin(thrust_angle_rad)
    
    # 5. G-force (Proper Acceleration: 중력을 제외한 가속도만 감지)
    ax_proper = (thrust_x + drag_x) / total_mass
    ay_proper = (thrust_y + drag_y) / total_mass
    g_force = math.sqrt(ax_proper**2 + ay_proper**2) / G0
    
    # 6. 알짜 가속도 계산 (F = ma -> a = F/m 공식 적용)
    ax = (thrust_x + drag_x + total_mass * gravity_x) / total_mass
    ay = (thrust_y + drag_y + total_mass * gravity_y) / total_mass
    
    # 7. 상태 업데이트 (오일러 전방 차분 적용)
    next_vx = vx + ax * dt
    next_vy = vy + ay * dt
    next_x = x + next_vx * dt
    next_y = y + next_vy * dt
    
    # 지표면 충돌 시 강제 구동 정지 보정
    next_r = math.sqrt(next_x**2 + next_y**2)
    if next_r < R_E:
        next_x = x * (R_E / r)
        next_y = y * (R_E / r)
        next_vx = 0.0
        next_vy = 0.0
        
    return {
        "x": next_x, "y": next_y,
        "vx": next_vx, "vy": next_vy,
        "ax": ax, "ay": ay,
        "drag": drag_force,
        "q": q,
        "g_force": g_force,
        "altitude": next_r - R_E,
        "gravity_acc": g_acc
    }
