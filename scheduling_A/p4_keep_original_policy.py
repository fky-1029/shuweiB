"""
p4_keep_original_policy.py

P4 保留原计划策略 - 基础工具与扰动模块
"""

import math
from copy import deepcopy
from p4_vehicle_state import BASELINE_PLAN


# ============================================================
# 1. 基础数据准备
# ============================================================

def get_baseline_timeline():
    """
    将 P2 导出的 BASELINE_PLAN 转换为 P4 标准的 timeline 格式。
    保留原始任务时间字段，只补充任务状态。
    """
    timeline = deepcopy(BASELINE_PLAN)

    for vehicle_id in timeline:
        for task in timeline[vehicle_id]:
            task["status"] = "completed"

    return timeline


def get_baseline_alert_status():
    """从 BASELINE_PLAN 自动提取原 3 个警报的初始成功状态。"""
    alert_status = {}

    for vehicle_id, tasks in BASELINE_PLAN.items():
        for task in tasks:
            alert_id = task["task_id"]

            if alert_id not in alert_status:
                alert_status[alert_id] = {
                    "started": True,
                    "observe_start": task["observe_start"],
                    "vehicles": [],
                }

            alert_status[alert_id]["vehicles"].append(vehicle_id)

            alert_status[alert_id]["observe_start"] = max(
                alert_status[alert_id]["observe_start"],
                task["observe_start"]
            )

    return alert_status


# ============================================================
# 2. 统一指标计算
# ============================================================

def compute_metrics(alert_status):
    """
    根据 alert_status 计算题目要求的评价指标。
    返回：{"N": N, "k": k, "eta": eta, "t_last": t_last}
    """
    N = len(alert_status)
    success_list = []
    has_failure_case = False
    EPS = 1e-8
    EVAL_END = 60.0

    for alert_id, info in alert_status.items():
        if info["started"]:
            obs_t = info["observe_start"]
            if obs_t <= EVAL_END + EPS:
                success_list.append(obs_t)
            else:
                has_failure_case = True
        else:
            has_failure_case = True

    k = len(success_list)
    eta = k / N if N > 0 else 0.0

    if has_failure_case:
        t_last = 60.0
    else:
        t_last = max(success_list)
    return {
        "N": N,
        "k": k,
        "eta": eta,
        "t_last": t_last
    }



# ============================================================
# 3. 坐标转换
# ============================================================

def _polar_to_cartesian(azimuth_deg, horizontal_distance, dispatch_center=(50.0, 50.0)):
    """题目公式：(x, y) = (50 + R cosθ, 50 + R sinθ)"""
    rad = math.radians(azimuth_deg)
    x = dispatch_center[0] + horizontal_distance * math.cos(rad)
    y = dispatch_center[1] + horizontal_distance * math.sin(rad)
    return x, y


# ============================================================
# 4. 扰动算子：新警报（保留原计划策略下不分配车）
# ============================================================

def apply_new_alert(timeline, alert_status, new_alert_params):
    """
    保留原计划策略下处理新警报。
    """
    if not isinstance(timeline, dict):
        raise TypeError("timeline 必须是 dict")
    if not isinstance(alert_status, dict):
        raise TypeError("alert_status 必须是 dict")

    alert_id = new_alert_params.get("alert_id", "NEW_ALERT")
    azimuth = float(new_alert_params["azimuth"])
    distance = float(new_alert_params["horizontal_distance"])
    altitude = float(new_alert_params["altitude"])
    arrival_time = float(new_alert_params.get("arrival_time", 5.0))

    tx, ty = _polar_to_cartesian(azimuth, distance)

    alert_status.pop(alert_id, None)

    alert_status[alert_id] = {
        "started": False,
        "observe_start": None,
        "vehicles": [],
        "reason": "保留原计划策略不重新分配车辆",
        "target": f"T_{alert_id}",
        "target_xyz": (tx, ty, altitude),
        "azimuth": azimuth,
        "horizontal_distance": distance,
        "altitude": altitude,
        "arrival_time": arrival_time,
        "is_new_alert": True,
    }

    return timeline, alert_status


# ============================================================
# 5. 扰动算子：车辆故障（保留原计划策略）
# ============================================================

def apply_failure(timeline, alert_status, failed_vehicle, fail_time=5.0):
    """
    保留原计划策略下处理车辆故障。
    """
    if failed_vehicle not in timeline:
        raise ValueError(f"未知车辆编号：{failed_vehicle}")

    # 1. 截断该车的时间线，把未完成的任务标记为作废
    # 1. 处理故障车辆的任务时间线
    for task in timeline[failed_vehicle]:

        # 扰动前已经开始观测的任务，按题目规定视为已完成
        if task["observe_start"] < fail_time - 1e-8:
            continue

        # 扰动时尚未开始观测的任务，全部作废
        task["status"] = "failed"
        task["reason"] = (
            f"车辆 {failed_vehicle} 在 {fail_time}s 发生故障，退出服务"
        )
        task["fail_time"] = fail_time

    # 2. 重新审查所有警报的状态
    for alert_id, info in alert_status.items():
        if not info["started"]:
            continue

        original_vehicles = info.get("vehicles", [])
        observe_start = info.get("observe_start")

        # 扰动前已经开始观测的警报，按题目规定视为完成
        if observe_start is not None and observe_start < fail_time:
            continue

        # 尚未开始观测的警报，如果依赖故障车辆，则无法完成
        if failed_vehicle in original_vehicles:
            info["started"] = False
            info["observe_start"] = None
            info["reason"] = (
                f"车辆 {failed_vehicle} 在 {fail_time}s 故障，"
                "任务无法完成且不进行车辆替换"
            )
            info["vehicles"] = [
                v for v in original_vehicles if v != failed_vehicle
            ]

    return timeline, alert_status


# ============================================================
# 6. 扰动算子：通信中断（保留原计划策略）
# ============================================================
# ============================================================
# 6. 扰动算子：通信中断（保留原计划策略）
# ============================================================
def apply_comm_loss(timeline, alert_status, recovery_time):
    """
    保留原计划策略下处理通信中断。

    假设：
    原计划已提前下发给车辆，车辆能够自主执行已分配任务。
    因此通信中断不改变原计划的任务时间，只记录受影响任务。
    """

    timeline = deepcopy(timeline)
    alert_status = deepcopy(alert_status)

    COMM_LOSS_START = 5.0

    if recovery_time <= COMM_LOSS_START or recovery_time > 30:
        raise ValueError("recovery_time 必须满足 5 < recovery_time <= 30")

    # 标记与通信中断时间区间重叠的任务
    for vehicle_id, tasks in timeline.items():
        for task in tasks:

            if task.get("status") == "failed":
                continue

            depart = task["depart"]
            reset_end = task["reset_end"]

            if depart < recovery_time and reset_end > COMM_LOSS_START:
                task["comm_status"] = (
                    f"overlaps_comm_loss_{recovery_time}"
                )
            else:
                task["comm_status"] = "unaffected"

    # 不修改原有警报的观测时间
    # 新警报仍保持未启动状态
    return timeline, alert_status
