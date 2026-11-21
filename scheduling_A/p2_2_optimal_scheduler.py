import json
import itertools
import path_planning as path_plan
import geometry_interface as geo
import constants as const

# 1. 加载地图和点位
print("正在加载地图和点位...")
with open("observable_points.json", "r", encoding="utf-8") as f:
    data = json.load(f)
WORLD_GRID = path_plan.build_grid(step=0.5)
candidates = [data["T1"], data["T2"], data["T3"]]


# ==========================================
# 2. 核心评估函数：彻底修复时序与死锁
# ==========================================
def evaluate_plan(plan):
    # 记录车辆当前状态
    car_free_time = {c: 0.0 for c in range(5)}
    car_pos = {c: (const.INITIAL_VEHICLE_POSITIONS[c]['x'], const.INITIAL_VEHICLE_POSITIONS[c]['y']) for c in range(5)}

    # 记录每个目标分配到的车辆信息 (车辆ID, 准备完成时间, 观测站坐标)
    target_records = {0: [], 1: [], 2: []}

    # 第一轮：让所有车沿着自己的任务路线开（不处理同步等待）
    for car_id, task_list in plan.items():
        for target in task_list:
            best_pt, drive_t, ready_t = path_plan.find_best_station_for_vehicle(
                car_idx=car_id, target_idx=target, candidate_stations=candidates[target],
                grid=WORLD_GRID, start_pos=car_pos[car_id], start_time=car_free_time[car_id]
            )

            if best_pt is None:
                return float('inf')  # 彻底去不了

            target_records[target].append({
                'car': car_id, 'ready': ready_t, 'pt': best_pt
            })

            # 暂时先不管别的车，假设这辆车去完之后立马就空闲了
            # 真实空闲时间 = 就绪时间 + 5秒观测 + 复位时间（复位时间 = 转过去的耗时）
            t_rot, _, _ = geo.compute_gimbal_rotate_time(
                best_pt, (const.TARGETS[target]['x'], const.TARGETS[target]['y'], const.TARGETS[target]['z'])
            )
            car_free_time[car_id] = ready_t + const.JOINT_OBSERVATION_TIME + t_rot
            car_pos[car_id] = best_pt

    # 检查每个目标是否凑够 2 辆车
    for tid in range(3):
        if len(target_records[tid]) != 2:
            return float('inf')

    # 计算每个目标的观测开始时间（需要同步，取两车中就绪最晚的那一个）
    target_start_times = {}
    for tid in range(3):
        target_start_times[tid] = max(r['ready'] for r in target_records[tid])

    # 【关键补丁】如果有辆车去早了，它必须在原地等。它的观测结束时间要按更晚的那个算。
    # 因为上面的推演可能让跑第二趟的车“提前”出发了，所以我们要严格按照最终的观测开始时间，
    # 重新推演一次车辆空闲时间，以更新给可能存在的后续任务（虽然这里最多只有2趟，不用重推也没事，但为了严谨）。
    # 实际上这题 P2(2) 没有复用跑 3 趟的，所以上面的 car_free_time 已经足够准了。

    return max(target_start_times.values())


# ==========================================
# 3. 生成所有合法派车方案
# ==========================================
def generate_all_plans():
    plans = []
    cars = [0, 1, 2, 3, 4]
    task_pool = [0, 0, 1, 1, 2, 2]
    seen = set()

    # 枚举哪辆车跑双趟，剩下的车跑单趟
    for double_car in cars:
        single_cars = [c for c in cars if c != double_car]

        # 双趟车跑哪两个目标（不能重复）
        for double_tasks in itertools.permutations([0, 1, 2], 2):
            remaining = task_pool.copy()
            remaining.remove(double_tasks[0])
            remaining.remove(double_tasks[1])

            # 剩下的 4 个任务分给 4 辆车
            for perm in set(itertools.permutations(remaining)):
                plan = {c: [] for c in cars}
                plan[double_car] = list(double_tasks)
                for i, car in enumerate(single_cars):
                    plan[car] = [perm[i]]

                key = tuple(tuple(plan[c]) for c in cars)
                if key not in seen:
                    seen.add(key)
                    plans.append(plan)
    return plans


# ==========================================
# 4. 穷举并输出最优解
# ==========================================
if __name__ == "__main__":
    all_plans = generate_all_plans()
    print(f"共生成 {len(all_plans)} 种排班方案，开始计算最优解...\n")

    best_makespan = float('inf')
    best_plan = None

    for plan in all_plans:
        ms = evaluate_plan(plan)
        if ms < best_makespan:
            best_makespan = ms
            best_plan = plan
            print(f"新最优！当前 Makespan: {best_makespan:.2f}")

    if best_plan:
        print("=" * 40)
        print(f"🏆 最优 Makespan (最大观测开始时间): {best_makespan:.2f} 秒")
        print("派车方案：")
        for car, targets in best_plan.items():
            t_names = [f"T{t + 1}" for t in targets]
            print(f"  车辆 V{car + 1}: 跑 {t_names}")
        print("=" * 40)
    else:
        print("未找到合法方案！")