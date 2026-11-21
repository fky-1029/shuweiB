import math
import json
import path_planning as path_plan
import geometry_interface as geo
import constants as const

# 1. 加载地图和点位（这是你每次跑都得有的前置）
print("正在加载地图和点位...")
with open("observable_points.json", "r", encoding="utf-8") as f:
    data = json.load(f)
WORLD_GRID = path_plan.build_grid(step=0.5)
candidates = [data["T1"], data["T2"], data["T3"]]


# ==========================================
# 2. 最近分配启发式算法 (NAH)
# ==========================================
def build_nearest_heuristic_plan():
    """
    核心逻辑：谁离目标直线距离最近，就派谁去。
    不考虑 A* 绕路，也不考虑全局统筹。
    """
    cars = [0, 1, 2, 3, 4]

    # 计算所有车到所有目标的直线距离矩阵
    dist_matrix = {c: {} for c in cars}
    for c in cars:
        pos_c = (const.INITIAL_VEHICLE_POSITIONS[c]['x'], const.INITIAL_VEHICLE_POSITIONS[c]['y'])
        for tid in range(3):
            target_pos = (const.TARGETS[tid]['x'], const.TARGETS[tid]['y'])
            dist_matrix[c][tid] = math.hypot(pos_c[0] - target_pos[0], pos_c[1] - target_pos[1])

    # 贪心派车：按照 T1 -> T2 -> T3 的顺序依次挑近的
    plan = {c: [] for c in cars}

    # 1. 给 T1 派距离最近的 2 辆车
    sorted_cars_t1 = sorted(cars, key=lambda c: dist_matrix[c][0])
    plan[sorted_cars_t1[0]].append(0)
    plan[sorted_cars_t1[1]].append(0)

    # 2. 剩下的车里，给 T2 派距离最近的 2 辆车
    available_cars_t2 = sorted_cars_t1[2:]
    sorted_cars_t2 = sorted(available_cars_t2, key=lambda c: dist_matrix[c][1])
    plan[sorted_cars_t2[0]].append(1)
    plan[sorted_cars_t2[1]].append(1)

    # 3. 给 T3 派车：派最后剩下的 1 辆车，再从忙碌的车里挑一个离 T3 最近的复用
    last_car = sorted_cars_t2[2]
    plan[last_car].append(2)

    # 挑选复用车
    busy_cars = sorted_cars_t1[:2] + sorted_cars_t2[:2]
    reuse_car = min(busy_cars, key=lambda c: dist_matrix[c][2])
    plan[reuse_car].append(2)

    return plan


# ==========================================
# 3. 物理时间推演引擎（和主程序完全一样，用于给贪心方案算时间）
# ==========================================
def evaluate_plan(plan):
    car_free_time = {c: 0.0 for c in range(5)}
    car_pos = {c: (const.INITIAL_VEHICLE_POSITIONS[c]['x'], const.INITIAL_VEHICLE_POSITIONS[c]['y']) for c in range(5)}
    target_records = {0: [], 1: [], 2: []}

    for car_id, task_list in plan.items():
        for target in task_list:
            best_pt, drive_t, ready_t = path_plan.find_best_station_for_vehicle(
                car_idx=car_id, target_idx=target, candidate_stations=candidates[target],
                grid=WORLD_GRID, start_pos=car_pos[car_id], start_time=car_free_time[car_id]
            )

            if best_pt is None:
                return float('inf')

            target_records[target].append({'car': car_id, 'ready': ready_t, 'pt': best_pt})

            t_rot, _, _ = geo.compute_gimbal_rotate_time(
                best_pt, (const.TARGETS[target]['x'], const.TARGETS[target]['y'], const.TARGETS[target]['z'])
            )
            car_free_time[car_id] = ready_t + const.JOINT_OBSERVATION_TIME + t_rot
            car_pos[car_id] = best_pt

    for tid in range(3):
        if len(target_records[tid]) != 2:
            return float('inf')

    target_start_times = {tid: max(r['ready'] for r in target_records[tid]) for tid in range(3)}
    return max(target_start_times.values())


# ==========================================
# 4. 执行并对比
# ==========================================
if __name__ == "__main__":
    # 生成就近分配方案
    greedy_plan = build_nearest_heuristic_plan()
    print("\n【基准方案】最近分配启发式算法 (NAH) 派车结果：")
    for car, targets in greedy_plan.items():
        if targets:
            t_names = [f"T{t + 1}" for t in targets]
            print(f"  车辆 V{car + 1}: 跑 {t_names}")

    # 算时间
    greedy_time = evaluate_plan(greedy_plan)
    print(f"👉 该基准方案的 Makespan（最大观测开始时间）: {greedy_time:.2f} 秒")

    print("\n" + "=" * 50)
    print("【论文对比分析参考】")
    print(f"全局优化算法 Makespan: 10.60 秒")
    print(f"最近分配启发式 Makespan: {greedy_time:.2f} 秒")
    print(f"优化提升幅度: {((greedy_time - 10.60) / greedy_time) * 100:.2f}%")
    print("差异来源：全局优化算法能避开 A* 绕路陷阱，并合理选择 V3 作为复用车辆，大幅减少了等待耗时。")
    print("=" * 50)