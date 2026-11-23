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
from p4_vehicle_state import BASELINE_PLAN

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
        quick_list.append((dist / const.VEHICLE_SPEED + t_rot, pt))

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
            start_time=start_time,
            target_pos_override=target_pos,
        )

        if best_pt is None:
            continue

        t_rot, _, _ = geo.compute_gimbal_rotate_time(best_pt, target_pos)

        options.append({
        "station": best_pt,
        "travel_time": drive_t,
        "gimbal_time": t_rot,
        "reset_time": t_rot,
        "ready_time": ready_t,
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
    # 如果无新警报且无车辆故障，通信中断不会改变既定任务执行，不需要创建重调度解。
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

    failed_vehicle = config.get("failed_vehicle")
    for i in range(1, 6):
        vid = f"V{i}"
        if vid == failed_vehicle:
            vehicle_states[vid] = {"failed": True, "position": (0, 0), "available_time": 999.0}
            continue

        cutoff = start_threshold
        pos = (const.INITIAL_VEHICLE_POSITIONS[i - 1]["x"], const.INITIAL_VEHICLE_POSITIONS[i - 1]["y"])
        avail_time = cutoff
        for task in sorted(BASELINE_PLAN[vid], key=lambda item: item["depart"]):
            # 只承认中断/故障前已下发的基准任务；未来任务不应被假定已执行。
            if task["depart"] >= cutoff - 1e-8:
                continue
            pos = task["station"]
            if task["reset_end"] > cutoff + 1e-8:
                # 已下发任务继续完成，车辆复位结束前不可再次派遣。
                avail_time = max(avail_time, task["reset_end"])

        vehicle_states[vid] = {
            "failed": False,
            "position": pos,
            "available_time": avail_time
        }

    # 需要重调度的告警：故障车导致的未完成任务，以及重调度时刻尚未开始的任务。
    # 通信中断期间原计划已下发的任务照常执行，已开始的任务不重复派发。
    tasks = []
    base_status = get_baseline_alert_status()
    affected_by_failure = set()
    if config.get("failed_vehicle"):
        for alert_id, info in base_status.items():
            if config["failed_vehicle"] in info["vehicles"]:
                vehicle_tasks = BASELINE_PLAN[config["failed_vehicle"]]
                assignment = next((t for t in vehicle_tasks if t["task_id"] == alert_id), None)
                # 故障车承担该告警的任务尚未观测完成时，需要重派整项双车任务。
                if assignment and assignment["observe_end"] > 5.0 + 1e-8:
                    affected_by_failure.add(alert_id)

    for alert_id, info in base_status.items():
        unfinished_at_reschedule = info["observe_start"] >= start_threshold - 1e-8
        if unfinished_at_reschedule or alert_id in affected_by_failure:
            tid = int(alert_id.split("_")[1]) - 1
            tasks.append({
                "task_id": alert_id,
                "target_id": f"T{tid + 1}",
                "target_pos": (const.TARGETS[tid]["x"], const.TARGETS[tid]["y"],
                               const.TARGETS[tid]["z"]),
            })

    if config.get("new_alert"):
        tx, ty = _polar_to_cartesian(config["new_alert"]["azimuth"],
                                     config["new_alert"]["horizontal_distance"])
        tasks.append({"task_id": "NEW_ALERT", "target_id": "T4",
                      "target_pos": (tx, ty, config["new_alert"].get("altitude", 50.0))})

    if not tasks:
        return run_keep_original_pipeline(config)

    # 适配器
    def station_options_func(vid, task, state):
        return get_station_options_adapter(vid, task, state, all_points)

    # 重调度统一在扰动时刻开始；通信中断时只允许恢复后启动调度。
    reschedule_time = start_threshold
    if recovery_time > 5.0:
        # 恢复时对未完成告警重新规划，避免恢复期遗漏已失效任务。
        tasks = []
        for alert_id in base_status:
            tid = int(alert_id.split("_")[1]) - 1
            tasks.append({
                "task_id": alert_id,
                "target_id": f"T{tid + 1}",
                "target_pos": (const.TARGETS[tid]["x"], const.TARGETS[tid]["y"],
                               const.TARGETS[tid]["z"]),
            })
        if config.get("new_alert"):
            tx, ty = _polar_to_cartesian(config["new_alert"]["azimuth"],
                                         config["new_alert"]["horizontal_distance"])
            tasks.append({"task_id": "NEW_ALERT", "target_id": "T4",
                          "target_pos": (tx, ty, config["new_alert"].get("altitude", 50.0))})

    reschedule_res = apply_reschedule(
        tasks,
        vehicle_states,
        station_options_func,
        max_iterations=20,
        reschedule_time=reschedule_time,
        communication_recovery_time=(recovery_time if config.get("recovery_time") else 0.0),
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

    # 终态从基准方案构造：扰动前已开始的任务锁定保留；失败车任务按故障作废；
    # 其他被重调度的原任务作废后由新分配替代。
    timeline = get_baseline_timeline()
    alert_status = get_baseline_alert_status()
    disruption_time = 5.0
    affected_task_ids = affected_by_failure
    rescheduled_task_ids = {t["task_id"] for t in tasks}
    for vid, entries in timeline.items():
        for task in entries:
            if vid == failed_vehicle and task["observe_end"] > 5.0 + 1e-8:
                task["status"] = "failed"
                task["reason"] = f"{vid} 在 {disruption_time}s 故障，观测尚未完成"
                task["fail_time"] = disruption_time
            elif task["task_id"] in affected_task_ids:
                task["status"] = "superseded"
                task["reason"] = "协同车辆故障，原联合任务由重调度处理"
                task["fail_time"] = 5.0
            elif task["observe_start"] < disruption_time - 1e-8:
                if task["reset_end"] > disruption_time + 1e-8:
                    task["status"] = "locked"
                    task["reason"] = "扰动前已开始观测，按题设保留完成"
                continue
            elif task["task_id"] in rescheduled_task_ids:
                task["status"] = "superseded"
                task["reason"] = "原计划任务由重调度结果取代"
                task["fail_time"] = disruption_time

    for task in tasks:
        if task["task_id"] == "NEW_ALERT":
            alert_status[task["task_id"]] = {
                "started": False, "observe_start": None, "vehicles": [],
                "reason": "等待重调度", "target": "T4", "is_new_alert": True,
            }
            continue
        info = alert_status[task["task_id"]]
        if task["task_id"] in affected_task_ids or info["observe_start"] >= disruption_time - 1e-8:
            info.update({"started": False, "observe_start": None,
                         "reason": "等待重调度", "vehicles": []})

    for item in reschedule_res["schedule"]:
        task_id = item["task_id"]
        if task_id == "NEW_ALERT":
            alert_status[task_id] = {
                "started": True, "observe_start": item["observe_start"],
                "vehicles": item["vehicle_ids"], "is_new_alert": True,
            }
        else:
            alert_status[task_id] = {
                "started": True, "observe_start": item["observe_start"],
                "vehicles": item["vehicle_ids"],
            }
        for vid in item["vehicle_ids"]:
            result = item["vehicle_results"][vid]
            observe_start = item["observe_start"]
            ready_time = result["ready_time"]
            gimbal_ready = ready_time
            travel_end = ready_time - result["gimbal_time"]
            travel_start = travel_end - result["travel_time"]
            if gimbal_ready > observe_start + 1e-8:
                raise AssertionError(f"{vid}/{task_id} 云台就绪晚于同步观测时刻")
            timeline[vid].append({
                "task_id": task_id, "target": item["target_id"],
                "depart": travel_start,
                "travel_end": travel_end,
                "gimbal_ready": gimbal_ready,
                "observe_start": observe_start, "observe_end": item["observe_end"],
                "reset_end": result["reset_end"], "status": "completed",
            })

    # 一致性检查：单车任务不得重叠，且警报只能在两车均已分配时计成功。
    for vid, entries in timeline.items():
        active = sorted((t for t in entries if t.get("status") == "completed"),
                        key=lambda t: t["depart"])
        for previous, current in zip(active, active[1:]):
            if current["depart"] < previous["reset_end"] - 1e-8:
                raise AssertionError(f"{vid} 任务重叠: {previous['task_id']} / {current['task_id']}")
    for task_id, info in alert_status.items():
        if info.get("started") and len(info.get("vehicles", [])) != 2:
            info.update({"started": False, "observe_start": None,
                         "vehicles": [], "reason": "未形成双车协同"})
        if info.get("started"):
            for vid in info["vehicles"]:
                matching = [t for t in timeline[vid] if t["task_id"] == task_id
                            and t.get("status") in {"completed", "locked"}]
                if not matching:
                    info.update({"started": False, "observe_start": None,
                                 "vehicles": [], "reason": "对应车辆任务未完成"})
                    break

    metrics = compute_metrics(alert_status)
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