import json
import math
from copy import deepcopy
from itertools import combinations
from pathlib import Path

import numpy as np
import geometry_interface as geo
from constants import TARGETS

OBSERVATION_DURATION = 5.0
EVALUATION_END = 60.0
VEHICLE_IDS = ["V1", "V2", "V3", "V4", "V5"]
EPS = 1e-8

P4_DIRECTORY = Path(__file__).resolve().parent
P4_OBSERVABLE_DIRECTORY = P4_DIRECTORY / "observable_points"
SHARED_OBSERVABLE_DIRECTORY = P4_DIRECTORY.parent / "shared" / "observable_points"

# 网格参数：保持已经验证成功的 1.0m
GRID_SPACING = 0.5
FIELD_SIZE = 100.0
T4_HEIGHT = 50.0

# ============================================================
# 1. 评价函数：成功观测数量优先，其次最后观测开始时间
# ============================================================

def is_valid_assignment(item):
    """判断一项任务是否满足双车协同观测的基本条件。"""
    vehicle_ids = item.get("vehicle_ids", [])
    vehicle_results = item.get("vehicle_results", {})
    observe_start = item.get("observe_start")

    if len(vehicle_ids) != 2 or len(set(vehicle_ids)) != 2:
        return False

    if not isinstance(vehicle_results, dict):
        return False

    if not all(v in vehicle_results for v in vehicle_ids):
        return False

    if observe_start is None or observe_start > EVALUATION_END + EPS:
        return False

    # 两辆车都必须在共同观测开始前完成到达和云台指向
    for vehicle_id in vehicle_ids:
        result = vehicle_results[vehicle_id]
        if result.get("ready_time", float("inf")) > observe_start + EPS:
            return False

    return True


def evaluate_schedule(schedule, tasks):
    """评估任务成功率与最后完成观测时间；未成功任务不计入完成数。"""
    """
    统计成功启动观测的不同警报数量。
    每项警报必须由两辆不同车辆共同完成，才计为成功。
    """
    N = len(tasks)

    valid_items = [
        item for item in schedule
        if is_valid_assignment(item)
    ]

    # 同一个 task_id 只能计数一次
    valid_by_id = {}
    for item in valid_items:
        valid_by_id[item["task_id"]] = item

    successful_items = list(valid_by_id.values())
    k = len(successful_items)

    eta = k / N if N > 0 else 1.0

    if k < N:
        t_last = EVALUATION_END
    elif k == 0:
        t_last = 0.0
    else:
        t_last = max(
            item["observe_start"] for item in successful_items
        )

    total_start_time = sum(
        item["observe_start"] for item in successful_items
    )

    return {
        "k": k,
        "N": N,
        "eta": eta,
        "t_last": t_last,
        "total_start_time": total_start_time
    }


def objective_key(metrics):
    """
    字典序优化：
    1. 最大化成功观测数量；
    2. 最小化最后观测开始时间；
    3. 最小化所有成功任务的观测开始时间之和。
    """
    return (
        -metrics["k"],
        metrics["t_last"],
        metrics["total_start_time"]
    )


# ============================================================
# 2. 获取单辆车执行单个任务的最佳站点方案
# ============================================================

def get_best_station_option(
    vehicle_id, task, vehicle_state, get_station_options
):
    options = get_station_options(
        vehicle_id, task, vehicle_state
    )

    if not options:
        return None

    valid_options = [
        opt for opt in options
        if opt["ready_time"] >= vehicle_state.get("available_time", 0.0) - EPS
        and opt["ready_time"] <= EVALUATION_END + EPS
    ]

    if not valid_options:
        return None

    return min(
        valid_options,
        key=lambda x: x["ready_time"]
    )


# ============================================================
# 3. 计算一个任务的车辆组合
# ============================================================

def evaluate_vehicle_pair(
    vehicle_pair, task, vehicle_states, get_station_options
):
    if len(vehicle_pair) != 2 or len(set(vehicle_pair)) != 2:
        return None

    options = []

    for vehicle_id in vehicle_pair:
        if vehicle_id not in vehicle_states:
            return None

        state = vehicle_states[vehicle_id]

        if state.get("failed", False):
            return None

        option = get_best_station_option(
            vehicle_id, task, state, get_station_options
        )

        if option is None:
            return None

        options.append(option)

    observe_start = max(
        options[0]["ready_time"],
        options[1]["ready_time"]
    )

    if observe_start > EVALUATION_END + EPS:
        return None

    observe_end = observe_start + OBSERVATION_DURATION

    vehicle_results = {}

    for i, vehicle_id in enumerate(vehicle_pair):
        option = options[i]
        reset_end = observe_end + option["reset_time"]

        vehicle_results[vehicle_id] = {
            "station": tuple(option["station"]),
            "travel_time": option["travel_time"],
            "gimbal_time": option["gimbal_time"],
            "ready_time": option["ready_time"],
            "observe_start": observe_start,
            "observe_end": observe_end,
            "reset_time": option["reset_time"],
            "reset_end": reset_end
        }

    return {
        "task_id": task["task_id"],
        "target_id": task["target_id"],
        "vehicle_ids": list(vehicle_pair),
        "observe_start": observe_start,
        "observe_end": observe_end,
        "vehicle_results": vehicle_results
    }


# ============================================================
# 4. 更新车辆状态
# ============================================================

def update_vehicle_states(vehicle_states, assignment):
    new_states = deepcopy(vehicle_states)

    for vehicle_id, result in assignment["vehicle_results"].items():
        if new_states[vehicle_id].get("failed", False):
            continue

        new_states[vehicle_id]["position"] = result["station"]
        new_states[vehicle_id]["available_time"] = max(
            new_states[vehicle_id].get("available_time", 0.0),
            result["reset_end"],
        )

    return new_states


# ============================================================
# 5. 贪心算法：生成初始可行调度方案
# ============================================================

def greedy_initial_solution(
    tasks, vehicle_states, get_station_options
):
    remaining_tasks = deepcopy(tasks)
    current_states = deepcopy(vehicle_states)
    schedule = []

    while remaining_tasks:
        best_candidate = None
        best_key = None

        available_vehicles = [
            v for v in VEHICLE_IDS
            if v in current_states
            and not current_states[v].get("failed", False)
        ]

        for task in remaining_tasks:
            for vehicle_pair in combinations(available_vehicles, 2):
                candidate = evaluate_vehicle_pair(
                    vehicle_pair,
                    task,
                    current_states,
                    get_station_options
                )

                if candidate is None:
                    continue

                # 优先选择最早能够开始观测的任务
                candidate_key = (
                    candidate["observe_start"],
                    candidate["task_id"]
                )

                if best_key is None or candidate_key < best_key:
                    best_key = candidate_key
                    best_candidate = (task, candidate)

        if best_candidate is None:
            break

        selected_task, assignment = best_candidate

        schedule.append(assignment)

        current_states = update_vehicle_states(
            current_states, assignment
        )

        remaining_tasks = [
            task for task in remaining_tasks
            if task["task_id"] != selected_task["task_id"]
        ]

    return schedule, current_states


# ============================================================
# 6. 按任务顺序和车辆组合重建调度
# ============================================================

def rebuild_schedule(
    tasks,
    task_order,
    vehicle_pairs,
    initial_vehicle_states,
    get_station_options
):
    task_dict = {
        task["task_id"]: task
        for task in tasks
    }

    states = deepcopy(initial_vehicle_states)
    schedule = []

    for task_id in task_order:
        if task_id not in task_dict:
            continue

        pair = vehicle_pairs.get(task_id)

        if pair is None:
            continue

        candidate = evaluate_vehicle_pair(
            pair,
            task_dict[task_id],
            states,
            get_station_options
        )

        if candidate is None:
            continue

        schedule.append(candidate)

        states = update_vehicle_states(
            states, candidate
        )

    return schedule, states


# ============================================================
# 7. 局部搜索：任务重分配、车辆组合调整、任务插入和顺序交换
# ============================================================

def local_search(
    tasks,
    initial_schedule,
    initial_vehicle_states,
    get_station_options,
    max_iterations=30
):
    if not tasks:
        return []

    task_dict = {
        task["task_id"]: task
        for task in tasks
    }

    current_schedule = deepcopy(initial_schedule)

    current_order = [
        item["task_id"] for item in current_schedule
    ]

    current_pairs = {
        item["task_id"]: tuple(item["vehicle_ids"])
        for item in current_schedule
    }

    current_metrics = evaluate_schedule(
        current_schedule, tasks
    )

    healthy_vehicles = [
        v for v in VEHICLE_IDS
        if v in initial_vehicle_states
        and not initial_vehicle_states[v].get("failed", False)
    ]

    all_pairs = list(combinations(healthy_vehicles, 2))

    for _ in range(max_iterations):
        improved = False

        # ----------------------------------------------------
        # 操作1：重新分配任务的车辆组合
        # ----------------------------------------------------
        for task_id in current_order:
            old_pair = current_pairs[task_id]

            for new_pair in all_pairs:
                if tuple(new_pair) == tuple(old_pair):
                    continue

                trial_pairs = deepcopy(current_pairs)
                trial_pairs[task_id] = tuple(new_pair)

                trial_schedule, _ = rebuild_schedule(
                    tasks,
                    current_order,
                    trial_pairs,
                    initial_vehicle_states,
                    get_station_options
                )

                trial_metrics = evaluate_schedule(
                    trial_schedule, tasks
                )

                if objective_key(trial_metrics) < objective_key(current_metrics):
                    current_pairs = trial_pairs
                    current_schedule = trial_schedule
                    current_metrics = trial_metrics
                    improved = True
                    break

            if improved:
                break

        if improved:
            continue

        # ----------------------------------------------------
        # 操作2：任务顺序交换
        # ----------------------------------------------------
        for i, j in combinations(range(len(current_order)), 2):
            trial_order = current_order.copy()
            trial_order[i], trial_order[j] = (
                trial_order[j], trial_order[i]
            )

            trial_schedule, _ = rebuild_schedule(
                tasks,
                trial_order,
                current_pairs,
                initial_vehicle_states,
                get_station_options
            )

            trial_metrics = evaluate_schedule(
                trial_schedule, tasks
            )

            if objective_key(trial_metrics) < objective_key(current_metrics):
                current_order = trial_order
                current_schedule = trial_schedule
                current_metrics = trial_metrics
                improved = True
                break

        if improved:
            continue

        # ----------------------------------------------------
        # 操作3：未安排任务插入现有任务序列
        # ----------------------------------------------------
        scheduled_ids = set(current_order)

        unscheduled_tasks = [
            task for task in tasks
            if task["task_id"] not in scheduled_ids
        ]

        for task in unscheduled_tasks:
            task_id = task["task_id"]

            for pair in all_pairs:
                trial_pairs = deepcopy(current_pairs)
                trial_pairs[task_id] = tuple(pair)

                for insert_position in range(len(current_order) + 1):
                    trial_order = current_order.copy()
                    trial_order.insert(insert_position, task_id)

                    trial_schedule, _ = rebuild_schedule(
                        tasks,
                        trial_order,
                        trial_pairs,
                        initial_vehicle_states,
                        get_station_options
                    )

                    trial_metrics = evaluate_schedule(
                        trial_schedule, tasks
                    )

                    if objective_key(trial_metrics) < objective_key(current_metrics):
                        current_order = trial_order
                        current_pairs = trial_pairs
                        current_schedule = trial_schedule
                        current_metrics = trial_metrics
                        improved = True
                        break

                if improved:
                    break

            if improved:
                break

        if improved:
            continue

        # 没有找到更优邻居，停止搜索
        break

    return current_schedule


# ============================================================
# 8. 重调度统一入口
# ============================================================

def apply_reschedule(
    tasks,
    vehicle_states,
    get_station_options,
    max_iterations=30,
    reschedule_time=0.0,
    communication_recovery_time=0.0
):
    """
    执行贪心 + 局部搜索重调度。

    注意：
    1. vehicle_states 必须是重调度时刻的实时车辆状态；
    2. 已开始观测的任务应在调用本函数前锁定，不放入待重调度 tasks；
    3. 已锁定任务占用的车辆，其可用时间必须已反映在 vehicle_states 中；
    4. 通信中断期间不能调用本函数执行远程重调度；
    5. 通信恢复后，以恢复时刻的车辆状态调用本函数。
    """

    tasks = [deepcopy(task) for task in tasks]
    vehicle_states = deepcopy(vehicle_states)

    # 通信中断期间不能执行远程重调度
    if reschedule_time + EPS < communication_recovery_time:
        raise ValueError(
            "通信尚未恢复，不能执行远程重调度。"
        )

    # 故障车辆从可用状态中剔除
    available_states = deepcopy(vehicle_states)

    for vehicle_id in list(available_states):
        if available_states[vehicle_id].get("failed", False):
            continue

    # 第一阶段：贪心生成初始解
    initial_schedule, _ = greedy_initial_solution(
        tasks,
        available_states,
        get_station_options
    )

    # 第二阶段：局部搜索优化
    final_schedule = local_search(
        tasks,
        initial_schedule,
        available_states,
        get_station_options,
        max_iterations=max_iterations
    )

    metrics = evaluate_schedule(
        final_schedule, tasks
    )

    return {
        "schedule": final_schedule,
        "metrics": metrics,
        "algorithm": "Greedy + Local Search",
        "reschedule_time": reschedule_time
    }


# ============================================================
# 9. 可观测点生成（统一 0.5m，用 check_observation_feasibility）
# ============================================================
def generate_observable_points(target_pos, spacing=GRID_SPACING):
    """
    按照原始 JSON 的网格规则生成可观测点。

    网格起点：1.5m
    网格终点：98.5m
    默认间距：0.5m

    使用 geometry_interface 判断可观测性。
    """

    if spacing <= 0:
        raise ValueError("网格间距必须大于0")

    if len(target_pos) != 3:
        raise ValueError("target_pos 必须包含 x、y、z 三个坐标")

    # 与原始 JSON 保持相同的网格起点
    start = 1.5
    end = FIELD_SIZE - 1.5

    xs = np.arange(start, end + EPS, spacing)
    ys = np.arange(start, end + EPS, spacing)

    points = []

    for x in xs:
        for y in ys:
            result = geo.check_observation_feasibility(
                (float(x), float(y)),
                target_pos
            )

            if result["feasible"]:
                points.append([float(x), float(y)])

    return np.asarray(points, dtype=float).reshape(-1, 2)


def load_official_observable_points():
    """从共享目录官方 0.5m CSV，或兼容本地 JSON，加载 T1/T2/T3 点集。"""
    file_path = P4_DIRECTORY.parent.parent / "shared" / "observable_points.json"

    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # 工作区交付副本采用共享目录中的官方 0.5m CSV。
        data = {}
        for tid in ("T1", "T2", "T3"):
            csv_path = SHARED_OBSERVABLE_DIRECTORY / f"{tid}_0p5m.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"缺少官方可观测点数据：{csv_path}")
            data[tid] = np.loadtxt(csv_path, delimiter=",", skiprows=1).tolist()

    official = {}

    for tid in ["T1", "T2", "T3"]:
        if tid not in data:
            raise KeyError(f"JSON 文件中缺少 {tid} 数据")

        official[tid] = np.asarray(data[tid], dtype=float)

        print(f"{tid}: {len(official[tid])} 个官方可观测点")

    return official


def generate_t4_observable_points(theta, R, save=True):
    if not 0.0 <= theta < 360.0:
        raise ValueError("theta 必须满足 0 <= theta < 360")
    if not 30.0 <= R <= 50.0:
        raise ValueError("R 必须满足 30 <= R <= 50")

    theta_rad = math.radians(theta)
    target_pos = (50.0 + R * math.cos(theta_rad),
                  50.0 + R * math.sin(theta_rad),
                  T4_HEIGHT)
    print(f"\nT4 目标坐标: x={target_pos[0]:.4f}, y={target_pos[1]:.4f}, z={target_pos[2]:.4f}")

    points = generate_observable_points(target_pos, spacing=GRID_SPACING)
    print(f"T4：筛选到 {len(points)} 个可观测点")

    if save:
        P4_OBSERVABLE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        theta_label = f"{theta:g}".replace(".", "p")
        R_label = f"{R:g}".replace(".", "p")
        output_path = P4_OBSERVABLE_DIRECTORY / f"T4_theta_{theta_label}_R_{R_label}_{GRID_SPACING:g}m.csv"
        np.savetxt(output_path, points, delimiter=",", header="x_east_m,y_north_m",
                   comments="", fmt="%.6f")

    return {"target_pos": target_pos, "points": points, "count": len(points)}


def get_all_observable_points(theta, R):
    """T1/T2/T3 读官方 0.5m；T4 动态生成 0.5m。"""
    all_points = load_official_observable_points()
    t4_result = generate_t4_observable_points(theta=theta, R=R, save=True)
    all_points["T4"] = t4_result["points"]

    print("\n========== 可观测点集合汇总 ==========")
    for tid, pts in all_points.items():
        print(f"{tid}: {len(pts)} 个")
    return all_points



