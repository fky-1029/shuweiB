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
            "status": "completed",      # 或 locked / failed / superseded / pending
            "reason": "",               # 非 completed 时标明原因
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

            # 已下发且继续占车的锁定任务仍有完整时间线；是否形成双车观测
            # 应以告警汇总为准，不把锁定状态误报为任务作废或自动算成功。
            if status in {"failed", "superseded", "pending"}:
                print(
                    f"【任务{seq} {target_label} | 站点 {station_str}】"
                    f" [状态: {status}]"
                )
                print(f"  状态原因:             {task.get('reason', '未执行')}")
                continue

            print(f"【任务{seq} {target_label} | 站点 {station_str}】"
                  f" [状态: 锁定原命令]" if status == "locked" else
                  f"【任务{seq} {target_label} | 站点 {station_str}】")
            if status == "locked":
                print(f"  状态说明:             {task.get('reason', '原命令继续执行')}")
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
    """绘制真实执行区间；锁定原命令与失败/取消任务分别标示。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        from matplotlib.patches import Patch
        chinese_fonts = ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC")
        available_fonts = {font.name for font in font_manager.fontManager.ttflist}
        chinese_font = next((name for name in chinese_fonts if name in available_fonts), None)
        plt.rcParams["font.sans-serif"] = [chinese_font or "DejaVu Sans"]
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
    }

    vehicle_ids = sorted(timeline.keys())
    fig, ax = plt.subplots(
        figsize=(14, max(6, 0.9 * len(vehicle_ids) + 2)),
        dpi=120,
    )
    legend_done = set()
    names = {
        "failed": ("故障/失败", "Failed"),
        "superseded": ("已替代/作废", "Replaced"),
        "pending": ("待执行", "Pending"),
        "drive": ("行驶", "Drive"),
        "rotate": ("云台调转", "Pointing"),
        "wait": ("同步等待", "Wait"),
        "observe": ("联合观测（5s）", "Observe (5s)"),
        "reset": ("云台复位", "Reset"),
    }

    def _name(key):
        return names[key][0 if chinese_font else 1]

    def _label(key, text):
        if key in legend_done:
            return ""
        legend_done.add(key)
        return text

    for row, vehicle_id in enumerate(vehicle_ids):
        for task in timeline[vehicle_id]:
            target_label = task.get("target", "?")
            status = task.get("status", "completed")

            # Explicit status rendering: locked work remains physically active;
            # failed/superseded work is cancelled; pending work has no execution interval.
            if status in {"failed", "superseded", "pending"}:
                marker = {"failed": "x", "superseded": "x", "pending": "o"}[status]
                color = {"failed": "#d03b3b", "superseded": "#ec835a",
                         "pending": "#fab219"}[status]
                timestamp = task.get("fail_time")
                if timestamp is None:
                    timestamp = task.get("depart", 0.0)
                ax.plot(
                    timestamp, row, marker=marker, color=color,
                    markerfacecolor="none" if status == "pending" else color,
                    linestyle="None", markersize=9, markeredgewidth=2,
                    label=_label(status, _name(status)),
                )
                reason = task.get("reason")
                if reason and chinese_font:
                    ax.annotate(reason, (timestamp, row), xytext=(4, 5),
                                textcoords="offset points", fontsize=6,
                                color="#52514e")
                continue

            depart = task["depart"]
            arrival = task["travel_end"]
            pointing = task["gimbal_ready"]
            obs_start = task["observe_start"]
            obs_end = task["observe_end"]
            reset_end = task["reset_end"]

            if status not in {"completed", "locked"}:
                raise ValueError(f"未知车辆任务状态: {status!r}")
            locked = status == "locked"
            for start, end, color_key, hatch in (
                (depart, arrival, "drive", None),
                (arrival, pointing, "rotate", None),
                (pointing, obs_start, "wait", "//"),
                (obs_start, obs_end, "observe", None),
                (obs_end, reset_end, "reset", None),
            ):
                if end > start:
                    ax.barh(
                        row, end - start, left=start, height=0.4,
                        color=color_map[color_key], edgecolor="black",
                        hatch="xx" if locked else hatch,
                        label=_label(color_key, _name(color_key)),
                    )

            ax.text(
                (obs_start + obs_end) / 2, row,
                f"{target_label} [{'锁定' if chinese_font else 'L'}]" if locked else target_label,
                ha="center", va="center", fontsize=8,
            )

    ax.set_yticks(range(len(vehicle_ids)))
    ax.set_yticklabels(vehicle_ids)
    ax.set_xlabel("时间（秒）" if chinese_font else "Time (s)")
    ax.set_ylabel("车辆编号" if chinese_font else "Vehicle")
    if not chinese_font:
        title = title.replace("原计划", "Original").replace("重调度", "Rescheduled")
        title = title.split(" - ")[0] + (" - Rescheduled" if "Rescheduled" in title else " - Original")
    ax.set_title(title, fontsize=12)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    if any(t.get("status") == "locked" for tasks in timeline.values() for t in tasks):
        ax.legend(handles=[*ax.get_legend_handles_labels()[0],
                           Patch(facecolor="white", edgecolor="black", hatch="xx",
                                 label="锁定原命令（仍占车）" if chinese_font else
                                       "Locked order (vehicle occupied)")],
                  loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    else:
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)

    plt.tight_layout()
    save_path = os.path.join(save_dir, filename)
    plt.savefig(save_path, bbox_inches="tight", dpi=200)
    print(f"\n甘特图已保存至：{save_path}")

    if show_plot:
        plt.show()
    plt.close(fig)