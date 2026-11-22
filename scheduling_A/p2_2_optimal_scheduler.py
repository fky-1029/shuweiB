import json
import itertools
import os

import path_planning as path_plan
import geometry_interface as geo
import constants as const


# ============================================================
# 1. 加载地图和候选观测站
# ============================================================
print("正在加载地图和点位...")

with open("observable_points.json", "r", encoding="utf-8") as f:
    data = json.load(f)

WORLD_GRID = path_plan.build_grid(step=0.5)
candidates = [data["T1"], data["T2"], data["T3"]]


# ============================================================
# 2. 核心评估函数
# ============================================================
def evaluate_plan(plan, return_schedule=False, max_iter=500, tol=1e-7):
    """
    评估一个固定车辆分配及任务顺序。

    本函数沿用原程序接口：
      find_best_station_for_vehicle(...) -> best_pt, drive_t, ready_t

    按原 print_timeline 的用法解释返回值：
      drive_t：行驶时长
      ready_t：从本次任务出发时刻起算/由路径规划函数返回的
               云台指向完成绝对时刻（应与原代码一致）
      arrival_t = depart_t + drive_t

    对每个目标，两辆车都完成指向后才开始联合观测。
    观测持续 JOINT 秒，之后每辆车复位 t_rot 秒再出发。

    默认返回 makespan（float）；return_schedule=True 返回详细结果字典。
    """

    joint = float(const.JOINT_OBSERVATION_TIME)
    car_ids = list(range(5))
    target_ids = list(range(3))

    # ---------- 检查任务分配 ----------
    if any(car not in plan for car in car_ids):
        return float("inf")

    target_cars = {tid: [] for tid in target_ids}
    for car_id in car_ids:
        for target in plan[car_id]:
            if target not in target_cars:
                return float("inf")
            target_cars[target].append(car_id)

    # 每个目标必须恰好由两辆不同车辆观测
    if any(len(target_cars[tid]) != 2 for tid in target_ids):
        return float("inf")

    # ---------- 迭代求解同步观测开始时间 ----------
    obs_start_guess = {tid: 0.0 for tid in target_ids}
    final_raw_schedule = None
    converged = False

    for iteration in range(max_iter):
        car_pos = {
            c: (
                const.INITIAL_VEHICLE_POSITIONS[c]["x"],
                const.INITIAL_VEHICLE_POSITIONS[c]["y"],
            )
            for c in car_ids
        }

        # 每辆车下一项任务的出发时刻
        car_depart = {c: 0.0 for c in car_ids}

        # 本轮各车辆任务记录
        raw_schedule = {c: [] for c in car_ids}

        # 每个目标两辆车的指向完成时刻
        target_pointing_times = {tid: [] for tid in target_ids}

        # ---------- 按车辆任务顺序推演 ----------
        for car_id in car_ids:
            for target in plan[car_id]:
                depart_t = car_depart[car_id]

                best_pt, drive_t, ready_t = (
                    path_plan.find_best_station_for_vehicle(
                        car_idx=car_id,
                        target_idx=target,
                        candidate_stations=candidates[target],
                        grid=WORLD_GRID,
                        start_pos=car_pos[car_id],
                        start_time=depart_t,
                    )
                )

                if best_pt is None:
                    return float("inf")

                drive_t = float(drive_t)
                ready_t = float(ready_t)
                arrival_t = depart_t + drive_t

                # 计算目标方向相对于正东水平姿态的云台转动时间。
                # 此时间用于观测后的云台复位；ready_t 已包含本次指向过程，
                # 因此不能再用 arrival_t + t_rot 代替 ready_t。
                t_rot, _, _ = geo.compute_gimbal_rotate_time(
                    best_pt,
                    (
                        const.TARGETS[target]["x"],
                        const.TARGETS[target]["y"],
                        const.TARGETS[target]["z"],
                    ),
                )
                t_rot = float(t_rot)

                pointing_done = ready_t

                # ready_t 应不早于车辆到达时间
                if pointing_done < arrival_t - tol:
                    return float("inf")

                target_pointing_times[target].append(pointing_done)

                raw_schedule[car_id].append(
                    {
                        "target": target,
                        "station": best_pt,
                        "depart": depart_t,
                        "drive_t": drive_t,
                        "arrival": arrival_t,
                        "t_rot": t_rot,
                        "pointing_done": pointing_done,
                    }
                )

                # 车辆下一次出发必须等待该目标的联合观测结束，
                # 并完成本车云台复位。
                car_depart[car_id] = (
                    obs_start_guess[target] + joint + t_rot
                )
                car_pos[car_id] = best_pt

        # ---------- 根据两车指向完成时刻更新同步观测开始时间 ----------
        new_obs_start = {}
        for tid in target_ids:
            if len(target_pointing_times[tid]) != 2:
                return float("inf")
            new_obs_start[tid] = max(target_pointing_times[tid])

        error = max(
            abs(new_obs_start[tid] - obs_start_guess[tid])
            for tid in target_ids
        )

        obs_start_guess = new_obs_start
        final_raw_schedule = raw_schedule

        if error < tol:
            converged = True
            break

    if not converged or final_raw_schedule is None:
        return float("inf")

    # ---------- 整理最终时间表 ----------
    result_schedule = {c: [] for c in car_ids}

    for car_id in car_ids:
        for task in final_raw_schedule[car_id]:
            tid = task["target"]
            obs_start = obs_start_guess[tid]
            obs_end = obs_start + joint
            reset_end = obs_end + task["t_rot"]

            # 两车必须都在同步观测开始前完成指向
            if task["pointing_done"] > obs_start + tol:
                return float("inf")

            result_schedule[car_id].append(
                {
                    **task,
                    "rotation_start": task["arrival"],
                    "wait_time": max(
                        0.0, obs_start - task["pointing_done"]
                    ),
                    "obs_start": obs_start,
                    "obs_end": obs_end,
                    "reset_time": task["t_rot"],
                    "reset_end": reset_end,
                }
            )

    # ---------- 检查同一辆车前后任务时序 ----------
    for car_id in car_ids:
        tasks = result_schedule[car_id]
        for i in range(len(tasks) - 1):
            previous_reset_end = tasks[i]["reset_end"]
            next_depart = tasks[i + 1]["depart"]
            if abs(next_depart - previous_reset_end) > 1e-5:
                # 迭代未能使车辆复用时间完全一致，不能把该方案当作可行解
                return float("inf")

    makespan = max(obs_start_guess.values())

    # 明确保证目标值就是三个目标观测开始时间的最大值
    assert abs(
        makespan - max(obs_start_guess.values())
    ) < 1e-10

    if not return_schedule:
        return makespan

    return {
        "makespan": makespan,
        "target_obs_start": dict(obs_start_guess),
        "schedule": result_schedule,
        "iterations": iteration + 1,
    }


# ============================================================
# 3. 生成所有合法派车方案
# ============================================================
def generate_all_plans():
    plans = []
    cars = [0, 1, 2, 3, 4]
    task_pool = [0, 0, 1, 1, 2, 2]
    seen = set()

    # 枚举一辆车执行两项不同目标任务，其余四辆车各执行一项
    for double_car in cars:
        single_cars = [c for c in cars if c != double_car]

        for double_tasks in itertools.permutations([0, 1, 2], 2):
            remaining = task_pool.copy()
            remaining.remove(double_tasks[0])
            remaining.remove(double_tasks[1])

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


# ============================================================
# 4. 打印时间线：只读取 evaluate_plan 的结果
# ============================================================
def print_timeline(plan, result):
    if not isinstance(result, dict):
        print("该方案不可行，无法输出时间线。")
        return

    schedule = result["schedule"]
    target_obs = result["target_obs_start"]
    makespan = result["makespan"]
    joint = float(const.JOINT_OBSERVATION_TIME)

    print("\n" + "=" * 76)
    print("车辆完整任务时间线（单位：秒）")
    print("=" * 76)

    for car_id in range(5):
        print(f"\n-------- 车辆 V{car_id + 1} --------")

        for seq, task in enumerate(schedule[car_id], start=1):
            target = task["target"]
            station = tuple(round(float(v), 2) for v in task["station"])

            print(f"【任务{seq} T{target + 1} | 站点 {station}】")
            print(f"  出发时刻:             {task['depart']:9.4f} s")
            print(f"  行驶时间:             {task['drive_t']:9.4f} s")
            print(f"  到达观测站:           {task['arrival']:9.4f} s")
            print(f"  云台对准就绪:         {task['pointing_done']:9.4f} s")
            print(f"  等待同步:             {task['wait_time']:9.4f} s")
            print(f"  同步观测开始:         {task['obs_start']:9.4f} s")
            print(f"  同步观测结束:         {task['obs_end']:9.4f} s")
            print(f"  云台复位完成时刻:     {task['reset_end']:9.4f} s")
            print(f"  云台复位完成/可出发:  {task['reset_end']:9.4f} s")

    print("\n" + "=" * 76)
    print("告警观测汇总")
    starts = []
    for tid in range(3):
        start_t = target_obs[tid]
        end_t = start_t + joint
        starts.append(start_t)
        print(
            f"T{tid + 1}：观测开始={start_t:.6f} s，"
            f"观测结束={end_t:.6f} s"
        )

    calculated_max = max(starts)
    print("-" * 76)
    print(f"三个目标观测开始时间最大值：{calculated_max:.6f} s")
    print(f"优化目标 Makespan：         {makespan:.6f} s")
    print(f"两者差值：                  {abs(calculated_max - makespan):.3e} s")

    if abs(calculated_max - makespan) >= 1e-7:
        raise AssertionError(
            "错误：Makespan 不等于三个目标观测开始时间的最大值！"
        )

    print("=" * 76)


# ============================================================
# 5. 绘制甘特图：使用同一份调度结果
# ============================================================
def plot_timeline_gantt(
    result,
    save_dir="./output_fig",
    show_plot=False,
):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
    except ImportError:
        print("未安装 matplotlib，跳过甘特图绘制。")
        return

    if not isinstance(result, dict):
        print("该方案不可行，无法绘制甘特图。")
        return

    os.makedirs(save_dir, exist_ok=True)

    schedule = result["schedule"]
    color_map = {
        "drive": "#87CEFA",  # 蓝色：行驶
        "rotate": "#FFD700",  # 黄色：云台调转
        "wait": "#D3D3D3",  # 灰色：同步等待
        "observe": "#32CD32",  # 绿色：联合观测
        "reset": "#FFA07A",  # 橙色：云台复位
    }

    fig, ax = plt.subplots(figsize=(14, 6), dpi=120)
    legend_used = set()

    for car_id in range(5):
        y = car_id

        for task in schedule[car_id]:
            target = task["target"]

            depart = task["depart"]
            arrival = task["arrival"]
            pointing_done = task["pointing_done"]
            obs_start = task["obs_start"]
            obs_end = task["obs_end"]
            reset_end = task["reset_end"]

            label = f"T{target + 1}" if target not in legend_used else None
            legend_used.add(target)

            # 行驶：蓝色
            if arrival > depart:
                ax.barh(
                    y, arrival - depart, left=depart,
                    height=0.4, color=color_map["drive"],
                    edgecolor="black",
                    label="行驶" if (car_id == 0 and task == schedule[car_id][0]) else ""
                )

            # 云台调转：黄色
            if pointing_done > arrival:
                ax.barh(
                    y, pointing_done - arrival, left=arrival,
                    height=0.4, color=color_map["rotate"],
                    edgecolor="black",
                    label="云台调转" if (car_id == 0 and task == schedule[car_id][0]) else ""
                )

            # 同步等待：灰色斜线填充
            if obs_start > pointing_done:
                ax.barh(
                    y, obs_start - pointing_done, left=pointing_done,
                    height=0.4, color=color_map["wait"],
                    edgecolor="black", hatch="//",
                    label="同步等待" if (car_id == 0 and task == schedule[car_id][0]) else ""
                )

            # 联合观测：绿色
            ax.barh(
                y, obs_end - obs_start, left=obs_start,
                height=0.4, color=color_map["observe"],
                edgecolor="black",
                label="联合观测（5s）" if (car_id == 0 and task == schedule[car_id][0]) else ""
            )

            # 云台复位：橙色
            if reset_end > obs_end:
                ax.barh(
                    y, reset_end - obs_end, left=obs_end,
                    height=0.4, color=color_map["reset"],
                    edgecolor="black",
                    label="云台复位" if (car_id == 0 and task == schedule[car_id][0]) else ""
                )

    ax.set_yticks(range(5))
    ax.set_yticklabels(["V1", "V2", "V3", "V4", "V5"])
    ax.set_xlabel("时间（秒）")
    ax.set_ylabel("车辆编号")
    ax.set_title(
        f"P2(2) 全局最优调度车辆时间线(Gantt Chart) "
        f"(Makespan={result['makespan']:.4f}s)",
        fontsize=12
    )
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right")

    plt.tight_layout()
    save_path = os.path.join(save_dir, "schedule_gantt.png")
    plt.savefig(save_path, bbox_inches="tight")
    print(f"\n甘特图已保存至：{save_path}")

    if show_plot:
        # 创建图片保存目录
        os.makedirs(save_dir, exist_ok=True)

        # 保存甘特图
        save_path = os.path.join(save_dir, "optimal_schedule_gantt.png")

        plt.savefig(
            save_path,
            dpi=300,
            bbox_inches='tight'
        )

        # 关闭图像，释放资源
        plt.close()

        print(f"甘特图已保存至: {os.path.abspath(save_path)}")

    plt.close(fig)


# ============================================================
# 6. 主程序：优化、打印、绘图使用同一份最终结果
# ============================================================
if __name__ == "__main__":
    all_plans = generate_all_plans()
    print(f"共生成 {len(all_plans)} 种排班方案，开始计算最优解...\n")

    best_makespan = float("inf")
    best_plan = None

    for plan in all_plans:
        score = evaluate_plan(plan)

        if score < best_makespan:
            best_makespan = score
            best_plan = plan
            print(f"新最优！当前 Makespan: {best_makespan:.6f} s")

    if best_plan is None or best_makespan == float("inf"):
        print("未找到合法可行方案！")
    else:
        # 只复算一次，后续所有输出都使用 best_result
        best_result = evaluate_plan(best_plan, return_schedule=True)

        if not isinstance(best_result, dict):
            raise RuntimeError("最优方案最终复算失败，请检查路径规划函数。")

        best_makespan = best_result["makespan"]
        target_starts = best_result["target_obs_start"]
        actual_max = max(target_starts.values())

        print("\n" + "=" * 48)
        print(f"最优 Makespan：{best_makespan:.6f} 秒")
        print(f"三个目标开始时间最大值：{actual_max:.6f} 秒")
        print(f"二者差值：{abs(best_makespan - actual_max):.3e} 秒")

        if abs(best_makespan - actual_max) >= 1e-7:
            raise AssertionError("最终 Makespan 与目标开始时间最大值不一致。")

        print("\n派车方案：")
        for car in range(5):
            names = [f"T{tid + 1}" for tid in best_plan[car]]
            print(f"  车辆 V{car + 1}: 跑 {names}")

        print("=" * 48)

        print_timeline(best_plan, best_result)
        plot_timeline_gantt(
            best_result,
            save_dir="./output_fig",
            show_plot=False
        )

