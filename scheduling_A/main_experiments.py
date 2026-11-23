"""
main_experiments.py

P4 全场景实验入口：
对比“保留原计划策略”与“动态重调度策略”在 S0-S7 下的表现。
"""

import os
import math
from copy import deepcopy

# 导入原计划策略
from p4_keep_original_policy import (
    get_baseline_timeline,
    get_baseline_alert_status,
    apply_new_alert,
    apply_failure,
    apply_comm_loss,
    compute_metrics,
    _polar_to_cartesian,
)

# 导入重调度策略
from p4_reschedule_policy import (
    apply_reschedule,
    get_all_observable_points,
)

# 导入你的路径规划和几何接口
import path_planning as path_plan
import geometry_interface as geo
import constants as const

# 导入打印与绘图
from timeline_printer import print_timeline, plot_timeline_gantt

# ============================================================
# 1. 全局初始化与适配器定义
# ============================================================
WORLD_GRID = path_plan.build_grid(step=0.5)


def get_station_options_adapter(vehicle_id, task, vehicle_state, all_points):
    target_id = task["target_id"]
    target_pos = task["target_pos"]
    points = all_points.get(target_id, [])
    if len(points) == 0:
        return []

    car_start = vehicle_state["position"]
    start_time = vehicle_state["available_time"]

    quick_list = []
    for pt in points:
        dist = math.hypot(pt[0] - car_start[0], pt[1] - car_start[1])
        t_rot, _, _ = geo.compute_gimbal_rotate_time(pt, target_pos)
        quick_list.append((dist / 3.0 + t_rot, pt))

    quick_list.sort(key=lambda x: x[0])
    top_30 = [item[1] for item in quick_list[:30]]

    options = []
    for pt in top_30:
        car_idx = int(vehicle_id[1:]) - 1
        best_pt, drive_t, ready_t = path_plan.find_best_station_for_vehicle(
            car_idx=car_idx,
            target_idx=0,
            candidate_stations=[pt],
            grid=WORLD_GRID,
            start_pos=car_start,
            start_time=start_time
        )

        if best_pt is None:
            continue

        t_rot, _, _ = geo.compute_gimbal_rotate_time(best_pt, target_pos)

        options.append({
            "station": best_pt,
            "travel_time": drive_t,
            "gimbal_time": t_rot,
            "reset_time": t_rot,
            "ready_time": ready_t
        })

    return options


# ============================================================
# 2. 场景配置
# ============================================================
DEMO_NEW_ALERT = {
    "alert_id": "NEW_ALERT",
    "azimuth": 120.0,
    "horizontal_distance": 40.0,
    "altitude": 50.0,
    "arrival_time": 5.0,
}

SCENARIOS = {
    "S0": {"desc": "无扰动", "new_alert": None, "failed_vehicle": None, "recovery_time": None},
    "S1": {"desc": "只有新警报", "new_alert": DEMO_NEW_ALERT, "failed_vehicle": None, "recovery_time": None},
    "S2": {"desc": "只有车辆故障", "new_alert": None, "failed_vehicle": "V2", "recovery_time": None},
    "S3": {"desc": "只有通信中断", "new_alert": None, "failed_vehicle": None, "recovery_time": 15.0},
    "S4": {"desc": "新警报+车辆故障", "new_alert": DEMO_NEW_ALERT, "failed_vehicle": "V2", "recovery_time": None},
    "S5": {"desc": "新警报+通信中断", "new_alert": DEMO_NEW_ALERT, "failed_vehicle": None, "recovery_time": 15.0},
    "S6": {"desc": "车辆故障+通信中断", "new_alert": None, "failed_vehicle": "V2", "recovery_time": 15.0},
    "S7": {"desc": "三种扰动同时发生", "new_alert": DEMO_NEW_ALERT, "failed_vehicle": "V2", "recovery_time": 15.0},
}


# ============================================================
# 3. 原计划流水线
# ============================================================
def run_keep_original_pipeline(config):
    timeline = get_baseline_timeline()
    alert_status = get_baseline_alert_status()

    if config.get("failed_vehicle"):
        timeline, alert_status = apply_failure(timeline, alert_status, config["failed_vehicle"])
    if config.get("recovery_time"):
        timeline, alert_status = apply_comm_loss(timeline, alert_status, config["recovery_time"])
    if config.get("new_alert"):
        timeline, alert_status = apply_new_alert(timeline, alert_status, config["new_alert"])

    metrics = compute_metrics(alert_status)
    return {"timeline": timeline, "alert_status": alert_status, "metrics": metrics}


# ============================================================
# 4. 重调度流水线
# ============================================================
def run_reschedule_pipeline(config):
    # 如果没有新警报，且没有车辆故障，直接返回原计划
    if not config.get("new_alert") and not config.get("failed_vehicle"):
        return run_keep_original_pipeline(config)

    # 【核心修复】：如果【没有新警报】，就不要去碰 T4
    if config.get("new_alert"):
        theta = config["new_alert"]["azimuth"]
        R = config["new_alert"]["horizontal_distance"]
        all_points = get_all_observable_points(theta, R)
    else:
        # 没有新警报时，只加载原计划里需要的 T1/T2/T3
        from p4_reschedule_policy import load_official_observable_points
        all_points = load_official_observable_points()

    # 提取 t=5s 时的车辆状态
    vehicle_states = {}
    recovery_time = config.get("recovery_time")
    if recovery_time is None:
        recovery_time = 0.0

    start_threshold = max(5.0, recovery_time)

    for i in range(1, 6):
        vid = f"V{i}"
        if vid == config.get("failed_vehicle"):
            vehicle_states[vid] = {"failed": True, "position": (0, 0), "available_time": 999.0}
            continue

        pos = (const.INITIAL_VEHICLE_POSITIONS[i - 1]["x"], const.INITIAL_VEHICLE_POSITIONS[i - 1]["y"])
        avail_time = start_threshold

        for task in get_baseline_timeline()[vid]:
            if task["reset_end"] < start_threshold:
                pos = task["station"]
            elif task["depart"] < start_threshold:
                pos = task["station"]
                avail_time = max(avail_time, task["reset_end"])

        vehicle_states[vid] = {
            "failed": False,
            "position": pos,
            "available_time": avail_time
        }

    # 构建待调度任务池
    tasks = []
    base_status = get_baseline_alert_status()

    # 如果有故障车，把缺车的旧任务放进池子
    for alert_id, info in base_status.items():
        if info["started"] and alert_id not in ["ALERT_001"]:
            if config.get("failed_vehicle") in info["vehicles"]:
                tid = int(alert_id.split("_")[1]) - 1
                tasks.append({"task_id": alert_id, "target_id": f"T{tid + 1}",
                              "target_pos": (const.TARGETS[tid]["x"], const.TARGETS[tid]["y"],
                                             const.TARGETS[tid]["z"])})

    # 【核心修复】：只有确认有新警报，才把 NEW_ALERT 加进池子
    if config.get("new_alert"):
        tx, ty = _polar_to_cartesian(config["new_alert"]["azimuth"], config["new_alert"]["horizontal_distance"])
        tasks.append({"task_id": "NEW_ALERT", "target_id": "T4", "target_pos": (tx, ty, 50.0)})

    if not tasks:
        return run_keep_original_pipeline(config)

    # 适配器
    def station_options_func(vid, task, state):
        return get_station_options_adapter(vid, task, state, all_points)

    # 调用重调度
    reschedule_res = apply_reschedule(
        tasks,
        vehicle_states,
        station_options_func,
        max_iterations=20
    )

    # 策略详情
    print("\n--- 重调度决策详情 ---")
    strategy_desc = []
    for item in reschedule_res["schedule"]:
        vid1, vid2 = item["vehicle_ids"]
        strategy_desc.append(
            f"派 {vid1} 和 {vid2} 去执行 {item['task_id']} (预计观测开始: {item['observe_start']:.2f}s)")
    if not strategy_desc:
        strategy_desc.append("无可用车辆组合，所有任务均失败。")
    for desc in strategy_desc:
        print(f"  * {desc}")
    print("----------------------\n")

    # 转换成 timeline 格式
    timeline = get_baseline_timeline()
    alert_status = get_baseline_alert_status()

    for item in reschedule_res["schedule"]:
        tid = item["task_id"]
        alert_status[tid] = {"started": True, "observe_start": item["observe_start"], "vehicles": item["vehicle_ids"]}
        for vid in item["vehicle_ids"]:
            timeline[vid].append({
                "task_id": tid, "target": item["target_id"], "station": item["vehicle_results"][vid]["station"],
                "depart": item["observe_start"] - 5, "travel_end": item["observe_start"] - 2,
                "gimbal_ready": item["observe_start"], "observe_start": item["observe_start"],
                "observe_end": item["observe_end"], "reset_end": item["vehicle_results"][vid]["reset_end"],
                "status": "completed"
            })

    metrics = compute_metrics(alert_status)

    # 【加一句提示，方便你确认没有 T4】
    print(">>> 本次重调度时间线打印完成。")

    return {"timeline": timeline, "alert_status": alert_status, "metrics": metrics,
            "strategy_desc": "; ".join(strategy_desc)}


# ============================================================
# 5. 主程序入口
# ============================================================
if __name__ == "__main__":
    print("开始执行 P4 全场景对比实验...\n")
    os.makedirs("./output_fig", exist_ok=True)
    summary = []

    for sc_id, config in SCENARIOS.items():
        print(f"\n{'=' * 70}")
        print(f"场景 {sc_id}: {config['desc']}")
        print(f"{'=' * 70}")

        # 1. 原计划
        orig_res = run_keep_original_pipeline(config)
        m_orig = orig_res["metrics"]

        # 2. 重调度
        resch_res = run_reschedule_pipeline(config)
        m_resch = resch_res["metrics"]

        # 3. 打印对比
        print(f"【原计划策略】 η = {m_orig['eta']:.4f}, t_last = {m_orig['t_last']:.2f} s")
        print(f"【重调度策略】 η = {m_resch['eta']:.4f}, t_last = {m_resch['t_last']:.2f} s")

        # 4. 画甘特图
        plot_timeline_gantt(orig_res["timeline"], filename=f"{sc_id}_orig.png", title=f"{sc_id} - 原计划")
        plot_timeline_gantt(resch_res["timeline"], filename=f"{sc_id}_resch.png", title=f"{sc_id} - 重调度")

        summary.append((sc_id, m_orig, m_resch))

    print("\n\n" + "=" * 80)
    print("最终汇总对比表")
    print("=" * 80)
    print(f"{'场景':<6} | {'原计划(η, t_last)':<20} | {'重调度(η, t_last)':<20}")
    print("-" * 80)
    for sc_id, m1, m2 in summary:
        print(f"{sc_id:<8} | ({m1['eta']:.4f}, {m1['t_last']:5.2f}) | ({m2['eta']:.4f}, {m2['t_last']:5.2f})")
    print("=" * 80)