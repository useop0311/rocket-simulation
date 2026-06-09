import math         # 수학 함수 라이브러리
import numpy as np        # 과학 계산 라이브러리
import pandas as pd        # 표(DataFrame)를 만드는 라이브러리
import matplotlib.pyplot as plt        # 그래프를 그리는 라이브러리
from matplotlib.gridspec import GridSpec        # 그래프를 여러 개 배치할 때 사용하는 라이브러리
import platform     # 시스템 운영체제(OS) 확인을 위한 라이브러리
import matplotlib.font_manager as fm  # 폰트 파일 속성 추출 및 캐시 관리를 위한 모듈

# =====================================================================
# [공학 상수 정의]
# =====================================================================
R_E = 6371000         # 지구 반지름 (m) -> 6,371km (고도 측정의 기준면)
GM = 3.986e14        # 지구의 표준 중력 변수 (μ = G * M, m^3/s^2)
                     # 만유인력 상수(G)와 지구 질량(M)의 곱으로, 우주 궤도 및 원궤도 속도 계산의 핵심 상수

# =====================================================================
# [시각화 및 데이터 분석 함수]
# =====================================================================
def plot_rocket_analysis(history):        # 로켓 비행 데이터를 시각화하고 통계를 출력하는 함수
    """
    history: 로켓 비행 로그가 저장된 딕셔너리 데이터 구조
    -----------------------------------------------------------------
    [참조 Key 리스트]
    - time: 비행 시간 (s)
    - altitude: 중심 기준이 아닌 지표면 기준 고도 (m)
    - speed: 절대 속도 (m/s)
    - g_force: 로켓이 받는 동적 가속도 (G 단위, 1G = 9.8m/s^2)
    - q: 동압 (Dynamic Pressure, Pa)
    - fuel_1 / fuel_2: 1단 부스터 및 2단 상단 로켓의 잔여 연료량 (kg)
    - x / y: 지구 중심(0,0)을 원점으로 하는 로켓의 2차원 평면 좌표 (m)
    - events: 비행 중 발생한 주요 이벤트 딕셔너리 리스트 (Launch, Separation 등)
    """
    
    # 1. 텔레메트리 딕셔너리 데이터 추출 및 단위 변환
    times = history["time"]        

    altitudes = np.array(history["altitude"]) / 1000        # 고도 데이터 단위 변환 (m -> km)
    speeds = history["speed"]
    g_forces = history["g_force"]
    qs = history["q"]        # 동압 계산식: q = 0.5 * rho * v^2 (rho: 대기밀도, v: 속도)
                             # 대기 밀도와 속도의 제곱에 비례하므로 구조물이 받는 최대 공기역학적 하중(Max-Q) 분석에 필수적임

    fuel_1s = history["fuel_1"]        # 1단(부스터) 잔여 연료 무게 (kg)
    fuel_2s = history["fuel_2"]        # 2단(상단 로켓) 잔여 연료 무게 (kg)

    xs = np.array(history["x"]) / 1000        # 지구 중심 기준 X 위치 변환 (m -> km)
    ys = np.array(history["y"]) / 1000        # 지구 중심 기준 Y 위치 변환 (m -> km)

    events = history["events"]        # 비행 시퀀스별 이벤트 로그 데이터

    
    # 2. 판다스(Pandas) 표 생성 및 콘솔 출력
    df = pd.DataFrame({
        "Time(s)": times,
        "Altitude(km)": np.round(altitudes, 2),        # 가독성을 위해 소수점 둘째 자리까지 반올림
        "Speed(m/s)": np.round(speeds, 2),
        "G-Force": np.round(g_forces, 2),
        "Q(Pa)": np.round(qs, 0),                      # 동압은 정수형태로 표현
        "Fuel1(kg)": np.round(fuel_1s, 0),
        "Fuel2(kg)": np.round(fuel_2s, 0)
    })

    print("\n===== 비행 데이터 (초기 20개 행) =====")
    print(df.head(20))        

    print("\n===== 주요 비행 통계 요약 =====")
    print(f"최고 고도 : {np.max(altitudes):.2f} km")        # 로켓이 도달한 정점 고도(Apogee)
    print(f"최고 속도 : {np.max(speeds):.2f} m/s")       # 최대 도달 속도 (위성 궤도 진입 여부 판단 근거)
    print(f"최대 G : {np.max(g_forces):.2f} G")          # 승우원 또는 탑재체가 견뎌야 하는 최대 탑재 하중
    print(f"최대 동압(Max-Q) : {np.max(qs):,.0f} Pa")        # 발사 중 공기 저항 하중이 가장 강력했던 시점의 압력


    # -------------------------------------------------------------
    # [Matplotlib 스타일 및 한글 폰트 우회 설정]
    # -------------------------------------------------------------
    # ※ 주의: plt.style.use()는 모든 rcParams 설정을 기본값으로 초기화하므로 가장 먼저 선언해야 함
    plt.style.use("dark_background")        # 가독성이 높은 미션 컨트롤 대시보드 스타일의 흑색 배경 적용

    # 크로스 플랫폼(Windows/Mac/Linux) 호환을 위한 폰트 풀(Fallback Pool) 제어 기법
    if platform.system() == 'Windows':
        font_path = "C:/Windows/Fonts/malgun.ttf"
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif'] # 맑은 고딕을 1순위 후보로 삽입
        
    elif platform.system() == 'Darwin':  # macOS 환경
        font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
        font_name = fm.FontProperties(fname=font_path).get_name()
        plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif'] # 애플고딕을 1순위 후보로 삽입
        
    else:  # 리눅스 환경
        plt.rcParams['font.sans-serif'] = ['NanumGothic'] + plt.rcParams['font.sans-serif']

    # 시스템 전역 설정을 건드리지 않고, 특정 요소(예: 범례)에 강제 매핑하기 위한 독립 폰트 객체 생성
    my_font = fm.FontProperties(fname=font_path if platform.system() == 'Windows' else None)

    plt.rcParams['axes.unicode_minus'] = False  # 폰트 변경 시 데이터 음수 기호(-)가 깨지는 전형적인 사이드 이펙트 방지
    

    # 3. 데이터 시각화 대시보드 레이아웃 생성
    fig = plt.figure(figsize=(16,9))        # 대형 디스플레이 규격인 16:9 비율 창 생성
    gs = GridSpec(2,3,figure=fig)        # 공간 효율을 높이기 위해 서브플롯 공간을 2행 3열 바둑판 형태로 분할

    # [서브플롯 1] 고도 프로파일 (좌측 상단)
    ax1 = fig.add_subplot(gs[0,0])        
    ax1.plot(times, altitudes, color='#1f77b4')        # 시계열 고도 곡선 렌더링
    ax1.set_title("Time vs Altitude (시간별 고도)")        
    ax1.set_ylabel("Altitude (km)")        
    ax1.grid(True, alpha=0.3)        

    # [서브플롯 2] 절대 속도 프로파일 (중앙 상단)
    ax2 = fig.add_subplot(gs[0,1])
    ax2.plot(times, speeds, color='#17becf')
    ax2.set_title("Time vs Speed (시간별 속도)")
    ax2.set_ylabel("Speed (m/s)")
    ax2.grid(True, alpha=0.3)

    # [서브플롯 3] 가속도 및 중력가속도 하중 (우측 상단)
    ax3 = fig.add_subplot(gs[0,2])
    ax3.plot(times, g_forces, color='#d62728')
    ax3.set_title("Time vs G-Force (시간별 중력가속도)")
    ax3.set_ylabel("Acceleration (G)")
    ax3.grid(True, alpha=0.3)

    # [서브플롯 4] 공기역학적 동압 변동 (좌측 하단)
    ax4 = fig.add_subplot(gs[1,0])
    ax4.plot(times, qs, color='#9467bd')
    ax4.set_title("Time vs Pressure(시간별 동압)")
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Pressure (Pa)")
    ax4.grid(True, alpha=0.3)

    # [서브플롯 5] 스테이지별 잔여 연료 추이 (중앙 하단)
    ax5 = fig.add_subplot(gs[1,1])
    ax5.plot(times, fuel_1s, label="Stage 1 (Booster)", color='#ff7f0e')        # 1단 로켓 연소 및 소모 그래프
    ax5.plot(times, fuel_2s, label="Stage 2 (Sustainer)", color='#2ca02c')      # 2단 로켓 연소 및 소모 그래프
    ax5.legend(prop=my_font)        # 한글 폰트 객체를 명시적으로 전달하여 깨짐 방지 우회법 완성
    ax5.set_title("Time vs Fuel Mass (시간별 연료)")
    ax5.set_xlabel("Time (s)")
    ax5.set_ylabel("Mass (kg)")
    ax5.grid(True, alpha=0.3)

    # [서브플롯 6] 2차원 지구 탈출/위성 비행 궤적 (우측 하단)
    ax6 = fig.add_subplot(gs[1,2])
    ax6.plot(xs, ys, color='#e377c2', linewidth=2)        # 공간적 이동 경로(Trajectory) 플로팅
    ax6.set_title("2D Orbital Trajectory (구형 지구 궤도)")
    ax6.set_xlabel("X Distance (km)")
    ax6.set_ylabel("Y Distance (km)")
    ax6.set_aspect("equal")        # 우주 공간의 기하학적 형태가 왜곡(찌그러짐)되지 않도록 가로세로 축 비율을 1:1로 고정
    ax6.grid(True, alpha=0.3)

    # 4. 최종 레이아웃 마감 및 드로잉
    plt.tight_layout()        # subplot 간 축 라벨이나 타이틀이 서로 지저분하게 겹치지 않게 여백 최적화
    plt.show()        # 통합 미션 대시보드 윈도우 팝업
