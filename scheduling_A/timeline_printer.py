"""
timeline_printer.py

P4 专用：车辆时间线打印 + 甘特图
从 p2_2_optimal_scheduler.py 提取，仅改 4 处（见文件头注释）。

timeline 格式（与 BASELINE_PLAN 字段一致）：
{
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
            "status": "completed",      # 或 "failed"
            "reason": "",               # status != completed 时填
        },
    ],
    ...
}

alert_status 格式：
{
    "ALERT_001": {"started": True,  "observe_start": 1.7519, "vehicles": ["V3","V5"]},
    "ALERT_002": {"started": True,  "observe_start": 7.2107, "vehicles": ["V1","V4"]},
    "ALERT_003": {"started": False, "observe_start": None,   "reason": "V2故障，缺一车"},
    "NEW_ALERT": {"started": False, "observe_start": None,   "reason": "无车分配"},
}
"""

import os


# ============================================================
# 一、时间线打印（P4 专用）
# ============================================================

def print_timeline(
    timeline,
    alert_status,
    title="车辆完整任务时间线",
    joint=5.0,
):
    """
    打印车辆时间线 + 告警观测汇总。

    参数：
        timeline     : {vehicle_id: [task, ...]}，字段同 BASELINE_PLAN
        alert_status : {alert_id: {"started", "observe_start", "vehicles", "reason"}}
        title        : 标题
        joint        : 联合观测时长，默认 5s
    """
    if not timeline:
        print("时间线为空，无法打印。")
        return

    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)

    for vehicle_id in sorted(timeline.keys()):
        print(f"\n-------- 车辆 {vehicle_id} --------")

        seq = 0
        for task in timeline[vehicle_id]:
            status = task.get("status", "completed")
            target_label = task.get("target", "?")
            station = task.get("station")
            station_str = (
                f"({station[0]:.2f}, {station[1]:.2f})"
                if station else "N/A"
            )

            seq += 1

            # 改动 3：失败任务只打印作废原因，不打印时间
            if status != "completed":
                print(
                    f"【任务{seq} {target_label} | 站点 {station_str}】"
                    f" [状态: {status}]"
                )
                print(
                    f"  作废原因:             "
                    f"{task.get('reason', '扰动导致任务作废')}"
                )
                continue

            print(f"【任务{seq} {target_label} | 站点 {station_str}】")
            print(f"  出发时刻:             {task['depart']:9.4f} s")
            print(
                f"  行驶时间:             "
                f"{task['travel_end'] - task['depart']:9.4f} s"
            )
            print(f"  到达观测站:           {task['travel_end']:9.4f} s")
            print(f"  云台对准就绪:         {task['gimbal_ready']:9.4f} s")
            print(
                f"  等待同步:             "
                f"{max(0.0, task['observe_start'] - task['gimbal_ready']):9.4f} s"
            )
            print(f"  同步观测开始:         {task['observe_start']:9.4f} s")
            print(f"  同步观测结束:         {task['observe_end']:9.4f} s")
            print(f"  云台复位完成/可出发:  {task['reset_end']:9.4f} s")

    # ---------- 告警观测汇总 ----------
    print("\n" + "=" * 78)
    print("告警观测汇总")
    print("=" * 78)

    started_starts = []

    # 改动 1 + 2：按 alert_status 动态遍历，不写死 range(3)
    for alert_id in sorted(alert_status.keys()):
        info = alert_status[alert_id]
        started = info.get("started", False)
        obs_start = info.get("observe_start")
        vehicles = info.get("vehicles", [])

        if started and obs_start is not None:
            started_starts.append(obs_start)
            print(
                f"{alert_id}：观测开始={obs_start:.6f} s，"
                f"观测结束={obs_start + joint:.6f} s，"
                f"车辆={vehicles}"
            )
        else:
            print(
                f"{alert_id}：未成功启动"
                f"（{info.get('reason', '未启动')}）"
            )

    print("-" * 78)
    if started_starts:
        print(
            f"已启动警报的最大观测开始时间："
            f"{max(started_starts):.6f} s"
        )
    else:
        print("无任何警报成功启动。")

    # 改动 4：去掉 makespan 断言，P4 有失败警报，max 语义不同
    print("=" * 78)


# ============================================================
# 二、甘特图（P4 专用）
# ============================================================

def plot_timeline_gantt(
    timeline,
    save_dir="./output_fig",
    filename="schedule_gantt.png",
    title="车辆调度时间线 (Gantt Chart)",
    show_plot=False,
):
    """
    绘制 P4 甘特图。失败任务不画条，在该车行用红色 × 标记。
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError:
        print("未安装 matplotlib，跳过甘特图绘制。")
        return

    if not timeline:
        print("时间线为空，无法绘图。")
        return

    os.makedirs(save_dir, exist_ok=True)

    color_map = {
        "drive": "#87CEFA",
        "rotate": "#FFD700",
        "wait": "#D3D3D3",
        "observe": "#32CD32",
        "reset": "#FFA07A",
        "failed": "#FF0000",
    }

    vehicle_ids = sorted(timeline.keys())
    fig, ax = plt.subplots(
        figsize=(14, max(6, 0.9 * len(vehicle_ids) + 2)),
        dpi=120,
    )
    legend_done = set()

    def _label(key, text):
        if key in legend_done:
            return ""
        legend_done.add(key)
        return text

    for row, vehicle_id in enumerate(vehicle_ids):
        for task in timeline[vehicle_id]:
            target_label = task.get("target", "?")
            status = task.get("status", "completed")

            # 改动 3 的绘图版：失败任务画红色 ×
            if status != "completed":
                # 优先用 fail_time（任务作废的逻辑时刻），
                # 没有才回退到 depart，再没有才回退到 0.0
                fail_time = task.get("fail_time")
                if fail_time is None:
                    fail_time = task.get("depart", 0.0)
                ax.plot(
                    fail_time, row,
                    marker="x", color=color_map["failed"],
                    markersize=10, markeredgewidth=2,
                )
                continue

            depart = task["depart"]
            arrival = task["travel_end"]
            pointing = task["gimbal_ready"]
            obs_start = task["observe_start"]
            obs_end = task["observe_end"]
            reset_end = task["reset_end"]

            if arrival > depart:
                ax.barh(
                    row, arrival - depart, left=depart, height=0.4,
                    color=color_map["drive"], edgecolor="black",
                    label=_label("drive", "行驶"),
                )
            if pointing > arrival:
                ax.barh(
                    row, pointing - arrival, left=arrival, height=0.4,
                    color=color_map["rotate"], edgecolor="black",
                    label=_label("rotate", "云台调转"),
                )
            if obs_start > pointing:
                ax.barh(
                    row, obs_start - pointing, left=pointing, height=0.4,
                    color=color_map["wait"], edgecolor="black", hatch="//",
                    label=_label("wait", "同步等待"),
                )
            ax.barh(
                row, obs_end - obs_start, left=obs_start, height=0.4,
                color=color_map["observe"], edgecolor="black",
                label=_label("observe", "联合观测（5s）"),
            )
            if reset_end > obs_end:
                ax.barh(
                    row, reset_end - obs_end, left=obs_end, height=0.4,
                    color=color_map["reset"], edgecolor="black",
                    label=_label("reset", "云台复位"),
                )

            ax.text(
                (obs_start + obs_end) / 2, row, target_label,
                ha="center", va="center", fontsize=8,
            )

    if any(
        t.get("status", "completed") != "completed"
        for tasks in timeline.values() for t in tasks
    ):
        ax.plot(
            [], [], marker="x", color=color_map["failed"],
            linestyle="None", markersize=10, label="任务作废",
        )

    ax.set_yticks(range(len(vehicle_ids)))
    ax.set_yticklabels(vehicle_ids)
    ax.set_xlabel("时间（秒）")
    ax.set_ylabel("车辆编号")
    ax.set_title(title, fontsize=12)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    save_path = os.path.join(save_dir, filename)
    plt.savefig(save_path, bbox_inches="tight", dpi=200)
    print(f"\n甘特图已保存至：{save_path}")

    if show_plot:
        plt.show()
    plt.close(fig)