
"""
p4_vehicle_state.py

P4：车辆实时状态基础模块

功能：
1. 保存 P2(2) 基准调度方案
2. 处理通信中断对原计划的影响
3. 判断扰动前已开始观测的锁定任务
4. 计算车辆当前物理状态和任务逻辑状态
5. 判断任务是否可以重新分配
6. 为后续扰动模块和重调度模块提供车辆状态接口

注意：
本文件只负责状态计算，不执行实际任务重新分配。
"""

from copy import deepcopy


# ============================================================
# 一、基础参数
# ============================================================

COMMUNICATION_LOSS_START = 5.0
OBSERVATION_DURATION = 5.0
EVALUATION_END = 60.0

VEHICLE_IDS = ["V1", "V2", "V3", "V4", "V5"]

TIME_KEYS = [
    "depart",
    "travel_end",
    "gimbal_ready",
    "observe_start",
    "observe_end",
    "reset_end",
]

EPS = 1e-8


# ============================================================
# 二、P2(2) 基准调度方案
# ============================================================

BASELINE_PLAN = {
    "V1": [
        {
            "task_id": "ALERT_002",
            "target": "T2",
            "station": (14.5, 13.5),
            "depart": 0.0,
            "travel_end": 0.2357,
            "gimbal_ready": 3.3479,
            "observe_start": 7.2107,
            "observe_end": 12.2107,
            "reset_end": 15.3230,
        }
    ],

    "V2": [
        {
            "task_id": "ALERT_003",
            "target": "T3",
            "station": (87.5, 9.5),
            "depart": 0.0,
            "travel_end": 0.2357,
            "gimbal_ready": 5.9753,
            "observe_start": 11.0234,
            "observe_end": 16.0234,
            "reset_end": 21.7631,
        }
    ],

    "V3": [
        {
            "task_id": "ALERT_001",
            "target": "T1",
            "station": (13.5, 86.5),
            "depart": 0.0,
            "travel_end": 0.2357,
            "gimbal_ready": 1.2520,
            "observe_start": 1.7519,
            "observe_end": 6.7519,
            "reset_end": 7.7683,
        }
    ],

    "V4": [
        {
            "task_id": "ALERT_002",
            "target": "T2",
            "station": (87.5, 71.5),
            "depart": 0.0,
            "travel_end": 1.2357,
            "gimbal_ready": 7.2107,
            "observe_start": 7.2107,
            "observe_end": 12.2107,
            "reset_end": 18.1858,
        }
    ],

    "V5": [
        {
            "task_id": "ALERT_001",
            "target": "T1",
            "station": (49.5, 93.5),
            "depart": 0.0,
            "travel_end": 0.2357,
            "gimbal_ready": 1.7519,
            "observe_start": 1.7519,
            "observe_end": 6.7519,
            "reset_end": 8.2682,
        },
        {
            "task_id": "ALERT_003",
            "target": "T3",
            "station": (49.5, 93.5),
            "depart": 8.2682,
            "travel_end": 8.2682,
            "gimbal_ready": 11.0234,
            "observe_start": 11.0234,
            "observe_end": 16.0234,
            "reset_end": 18.7787,
        }
    ],
}


# ============================================================
# 三、参数校验
# ============================================================

def validate_recovery_time(recovery_time):
    """检查通信恢复时间是否合法。"""
    recovery_time = float(recovery_time)

    if not (5.0 < recovery_time <= 30.0):
        raise ValueError(
            "通信恢复时间必须满足 5 < t_rec <= 30。"
        )

    return recovery_time


def validate_current_time(current_time):
    """检查当前仿真时刻是否合法。"""
    current_time = float(current_time)

    if current_time < 0:
        raise ValueError("当前时刻不能小于 0。")

    return current_time


def validate_vehicle_id(vehicle_id):
    """检查车辆编号是否合法。"""
    if vehicle_id not in VEHICLE_IDS:
        raise ValueError(f"未知车辆编号：{vehicle_id}")


# ============================================================
# 四、通信状态
# ============================================================

def get_communication_status(current_time, recovery_time):
    """
    返回当前通信状态。
    interrupted：通信中断
    recovered：通信恢复
    """
    current_time = validate_current_time(current_time)
    recovery_time = validate_recovery_time(recovery_time)

    if (
        current_time >= COMMUNICATION_LOSS_START
        and current_time < recovery_time
    ):
        return "interrupted"

    return "recovered"


# ============================================================
# 五、锁定任务
# ============================================================

def get_locked_completed_tasks(
    current_time,
    plan=None
):
    """
    获取扰动发生前已经开始观测的车辆任务。

    按题目规定：
    在 t=5s 扰动发生前已经开始观测的车辆任务，
    视为已完成且不可重新调度。

    返回：
        set：由 (vehicle_id, task_id) 组成的锁定集合。
    """
    current_time = validate_current_time(current_time)

    if plan is None:
        plan = BASELINE_PLAN

    locked_task_ids = set()

    if current_time < COMMUNICATION_LOSS_START:
        return locked_task_ids

    for vehicle_id, vehicle_tasks in plan.items():
        for task in vehicle_tasks:
            if (
                task["observe_start"]
                < COMMUNICATION_LOSS_START - EPS
            ):
                locked_task_ids.add(
                    (vehicle_id, task["task_id"])
                )

    return locked_task_ids


# ============================================================
# 六、不重调度策略下的通信中断计划
# ============================================================

def get_no_reschedule_baseline_plan(recovery_time, plan=None):
    """
    计算不重调度策略下的有效计划。

    该计划仅用于与重调度策略进行对比，
    不是重调度后的实际执行计划。

    通信中断期间：
    1. 车辆继续执行正在进行的任务；
    2. 不接收新的调度指令；
    3. 尚未开始的后续任务不能在中断期间启动；
    4. 通信恢复后，才允许执行后续任务。

    返回：
        不重调度策略下调整后的计划副本。
    """
    recovery_time = validate_recovery_time(recovery_time)

    if plan is None:
        plan = BASELINE_PLAN

    effective_plan = deepcopy(plan)

    for vehicle_id, tasks in effective_plan.items():

        for index, task in enumerate(tasks):

            if index == 0:
                continue

            # 后续任务原本计划在通信中断期间启动
            if (
                task["depart"] < recovery_time
                and task["depart"] >= COMMUNICATION_LOSS_START
            ):
                delay = recovery_time - task["depart"]

                for key in TIME_KEYS:
                    task[key] += delay

    # 同一警报的联合观测必须同步
    task_records = {}

    for vehicle_id, tasks in effective_plan.items():
        for task in tasks:
            task_records.setdefault(
                task["task_id"], []
            ).append(task)

    for task_id, records in task_records.items():

        if len(records) < 2:
            continue

        synchronized_start = max(
            task["observe_start"] for task in records
        )

        for task in records:
            delay = synchronized_start - task["observe_start"]

            if delay > EPS:
                for key in TIME_KEYS:
                    if key in task:
                        task[key] += delay

    return effective_plan


# ============================================================
# 七、任务逻辑状态
# ============================================================

def get_task_status(
    vehicle_id,
    task,
    current_time,
    locked_task_ids=None
):
    """
    获取单辆车对应任务的逻辑状态。

    返回状态：
        assigned_not_started：已分配但未开始
        waiting_to_start：等待开始
        observing：正在观测
        resetting：正在复位
        completed：任务完成
        completed_locked：扰动前已开始、逻辑上锁定

    注意：
    锁定以 (vehicle_id, task_id) 为单位。
    completed_locked 表示重调度意义上的锁定，
    不代表车辆的物理观测和复位动作已经结束。
    """
    current_time = validate_current_time(current_time)

    if locked_task_ids is None:
        locked_task_ids = set()

    task_id = task["task_id"]

    # 只有扰动发生后，才将扰动前已开始的车辆任务标记为锁定
    if (
        current_time >= COMMUNICATION_LOSS_START
        and (vehicle_id, task_id) in locked_task_ids
    ):
        return "completed_locked"

    if current_time < task["observe_start"] - EPS:
        if current_time < task["depart"] - EPS:
            return "assigned_not_started"

        return "waiting_to_start"

    if current_time < task["observe_end"] - EPS:
        return "observing"

    if current_time < task["reset_end"] - EPS:
        return "resetting"

    return "completed"


# ============================================================
# 八、车辆物理状态
# ============================================================

def get_physical_state(
    vehicle_tasks,
    current_time
):
    """
    根据车辆当前计划计算物理状态。

    返回：
        dict：车辆物理状态信息。

    物理状态包括：
        traveling
        gimbal_turning
        waiting_sync
        observing
        resetting
        waiting_command
        idle
    """
    current_time = validate_current_time(current_time)

    active_task = None
    next_task = None
    previous_task = None

    # 判断当前正在执行的任务
    for task in vehicle_tasks:

        if (
            task["depart"] - EPS
            <= current_time
            < task["reset_end"] - EPS
        ):
            active_task = task
            break

        if task["reset_end"] <= current_time + EPS:
            previous_task = task

        if task["depart"] > current_time + EPS:
            if (
                next_task is None
                or task["depart"] < next_task["depart"]
            ):
                next_task = task

    # 没有正在执行的任务
    if active_task is None:

        if next_task is not None:
            return {
                "physical_state": "waiting_command",
                "current_task": None,
                "current_task_id": None,
                "next_task": next_task["target"],
                "next_task_id": next_task["task_id"],
                "phase_start": None,
                "phase_end": next_task["depart"],
                "physical_release_time": current_time,
                "previous_task": (
                    previous_task["target"]
                    if previous_task else None
                ),
            }

        return {
            "physical_state": "idle",
            "current_task": None,
            "current_task_id": None,
            "next_task": None,
            "next_task_id": None,
            "phase_start": None,
            "phase_end": None,
            "physical_release_time": current_time,
            "previous_task": (
                previous_task["target"]
                if previous_task else None
            ),
        }

    # 当前任务的物理执行阶段
    if current_time < active_task["travel_end"] - EPS:

        physical_state = "traveling"
        phase_start = active_task["depart"]
        phase_end = active_task["travel_end"]

    elif current_time < active_task["gimbal_ready"] - EPS:

        physical_state = "gimbal_turning"
        phase_start = active_task["travel_end"]
        phase_end = active_task["gimbal_ready"]

    elif current_time < active_task["observe_start"] - EPS:

        physical_state = "waiting_sync"
        phase_start = active_task["gimbal_ready"]
        phase_end = active_task["observe_start"]

    elif current_time < active_task["observe_end"] - EPS:

        physical_state = "observing"
        phase_start = active_task["observe_start"]
        phase_end = active_task["observe_end"]

    else:

        physical_state = "resetting"
        phase_start = active_task["observe_end"]
        phase_end = active_task["reset_end"]

    return {
        "physical_state": physical_state,
        "current_task": active_task["target"],
        "current_task_id": active_task["task_id"],
        "next_task": (
            next_task["target"] if next_task else None
        ),
        "next_task_id": (
            next_task["task_id"] if next_task else None
        ),
        "phase_start": phase_start,
        "phase_end": phase_end,
        "physical_release_time": active_task["reset_end"],
        "previous_task": (
            previous_task["target"]
            if previous_task else None
        ),
    }


# ============================================================
# 九、车辆完整状态
# ============================================================

def get_vehicle_state(
    vehicle_id,
    current_time,
    recovery_time,
    plan=None,
    failed_vehicles=None
):
    """
    获取单辆车在指定时刻的完整状态。

    参数：
        vehicle_id：车辆编号
        current_time：当前时刻
        recovery_time：通信恢复时刻
        plan：车辆任务计划
        failed_vehicles：故障车辆集合

    返回：
        dict：车辆状态信息

    注意：
        can_accept_new_task 表示可以接收调度指令，
        不代表车辆可以立即开始执行新任务。
    """
    validate_vehicle_id(vehicle_id)

    current_time = validate_current_time(current_time)
    recovery_time = validate_recovery_time(recovery_time)

    if plan is None:
        plan = BASELINE_PLAN

    if failed_vehicles is None:
        failed_vehicles = set()

    # 提前判断车辆是否故障
    is_failed = vehicle_id in failed_vehicles

    # 这里只获取不重调度策略下的对比基线计划
    effective_plan = get_no_reschedule_baseline_plan(
        recovery_time,
        plan
    )

    vehicle_tasks = effective_plan[vehicle_id]

    communication_status = get_communication_status(
        current_time,
        recovery_time
    )

    locked_task_ids = get_locked_completed_tasks(
        current_time,
        plan
    )

    physical_info = get_physical_state(
        vehicle_tasks,
        current_time
    )

    task_states = []

    for task in vehicle_tasks:

        task_status = get_task_status(
            vehicle_id,
            task,
            current_time,
            locked_task_ids
        )

        # 任务是否可以重新分配
        reassignable = (
            not is_failed
            and task_status in [
                "assigned_not_started",
                "waiting_to_start"
            ]
            and current_time >= COMMUNICATION_LOSS_START
            and (vehicle_id, task["task_id"]) not in locked_task_ids
        )

        task_states.append({
            "task_id": task["task_id"],
            "target": task["target"],
            "status": task_status,
            "reassignable": reassignable,
            "observe_start": task["observe_start"],
            "observe_end": task["observe_end"],
        })

    reassignable_task_ids = [
        item["task_id"]
        for item in task_states
        if item["reassignable"]
    ]

    can_accept_new_task = (
        communication_status == "recovered"
        and not is_failed
        and physical_info["physical_state"] in [
            "idle",
            "waiting_command",
        ]
    )

    current_plan_available_time = max(
        (
            task["reset_end"]
            for task in vehicle_tasks
        ),
        default=current_time
    )

    return {
        "vehicle_id": vehicle_id,

        "current_time": current_time,

        "communication_status": communication_status,

        "communication_recovered": (
            communication_status == "recovered"
        ),

        "is_failed": is_failed,

        "physical_state": physical_info["physical_state"],

        "current_task": physical_info["current_task"],

        "current_task_id": physical_info["current_task_id"],

        "next_task": physical_info["next_task"],

        "next_task_id": physical_info["next_task_id"],

        "phase_start": physical_info["phase_start"],

        "phase_end": physical_info["phase_end"],

        "physical_release_time": physical_info[
            "physical_release_time"
        ],

        "previous_task": physical_info["previous_task"],

        "task_states": task_states,

        "can_reassign_task": (
            len(reassignable_task_ids) > 0
            and not is_failed
        ),

        "reassignable_task_ids": (
            reassignable_task_ids
            if not is_failed else []
        ),

        "can_accept_new_task": can_accept_new_task,

        "current_plan_available_time": (
            current_plan_available_time
        ),
    }


# ============================================================
# 十、批量获取车辆状态
# ============================================================

def get_vehicle_states_at_time(
    current_time,
    recovery_time,
    plan=None,
    failed_vehicles=None
):
    """
    获取所有车辆在指定时刻的状态。
    """
    states = {}

    for vehicle_id in VEHICLE_IDS:

        states[vehicle_id] = get_vehicle_state(
            vehicle_id=vehicle_id,
            current_time=current_time,
            recovery_time=recovery_time,
            plan=plan,
            failed_vehicles=failed_vehicles,
        )

    return states


# ============================================================
# 十一、系统状态
# ============================================================

def get_system_snapshot(
    current_time,
    recovery_time,
    plan=None,
    failed_vehicles=None
):
    """
    获取系统在指定时刻的完整状态。

    供扰动模块和重调度模块调用。
    """
    current_time = validate_current_time(current_time)
    recovery_time = validate_recovery_time(recovery_time)

    if plan is None:
        plan = BASELINE_PLAN

    locked_task_ids = get_locked_completed_tasks(
        current_time,
        plan
    )

    vehicle_states = get_vehicle_states_at_time(
        current_time=current_time,
        recovery_time=recovery_time,
        plan=plan,
        failed_vehicles=failed_vehicles,
    )

    return {
        "current_time": current_time,

        "recovery_time": recovery_time,

        "communication_status": get_communication_status(
            current_time,
            recovery_time
        ),

        "locked_task_ids": locked_task_ids,

        "vehicle_states": vehicle_states,
    }


# ============================================================
# 十二、联合观测同步检查
# ============================================================

def check_joint_observation_sync(plan):
    """
    检查同一警报的多辆车是否同步开始观测。

    返回：
        (是否通过, 检查详情)

    注意：
        本函数检查的是计划时间一致性。
        故障场景下，警报所需车辆数量应由重调度模块
        根据实际任务需求另行检查。
    """
    task_records = {}

    for vehicle_id, tasks in plan.items():

        for task in tasks:

            task_records.setdefault(
                task["task_id"], []
            ).append({
                "vehicle_id": vehicle_id,
                "target": task["target"],
                "observe_start": task["observe_start"],
                "observe_end": task["observe_end"],
            })

    details = {}
    is_valid = True

    for task_id, records in task_records.items():

        start_times = [
            record["observe_start"]
            for record in records
        ]

        end_times = [
            record["observe_end"]
            for record in records
        ]

        synchronized = (
            max(start_times) - min(start_times) <= EPS
            and max(end_times) - min(end_times) <= EPS
        )

        details[task_id] = {
            "target": records[0]["target"],
            "vehicles": [
                record["vehicle_id"]
                for record in records
            ],
            "start_times": start_times,
            "end_times": end_times,
            "synchronized": synchronized,
        }

        if not synchronized:
            is_valid = False

    return is_valid, details




