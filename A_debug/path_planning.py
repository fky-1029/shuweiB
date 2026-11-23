import math

class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.g = 0
        self.h = 0
        self.f = 0
        self.parent = None


def octile(node, goal):
    dx = abs(node.x - goal[0])
    dy = abs(node.y - goal[1])
    return 10 * max(dx, dy) + 4 * min(dx, dy)


def a_star_classic(grid, start_pos, end_pos):
    rows = len(grid)
    cols = len(grid[0])
    start = Node(*start_pos)
    goal = end_pos

    open_list = [start]
    close_list = []

    dirs = [
        (0, 1, 10),
        (0, -1, 10),
        (1, 0, 10),
        (-1, 0, 10),
        (-1, 1, 14),
        (1, 1, 14),
        (-1, -1, 14),
        (1, -1, 14)
    ]
    step = 0

    while open_list:
        step += 1
        current = min(open_list, key=lambda n: (n.f, -n.y))

        if current.x == goal[0] and current.y == goal[1]:
            path = []
            p = current
            while p is not None:
                path.append((p.x, p.y))
                p = p.parent
            path.reverse()
            return path

        open_list.remove(current)
        close_list.append(current)
        cx, cy = current.x, current.y

        for dx, dy, cost in dirs:
            nx = cx + dx
            ny = cy + dy
            if not (0 <= nx < rows and 0 <= ny < cols):
                continue
            if grid[nx][ny] == 1:
                continue

            is_diag = abs(dx) == 1 and abs(dy) == 1
            if is_diag:
                s1x, s1y = cx + dx, cy
                s2x, s2y = cx, cy + dy
                w1 = (0 <= s1x < rows and 0 <= s1y < cols) and grid[s1x][s1y] == 1
                w2 = (0 <= s2x < rows and 0 <= s2y < cols) and grid[s2x][s2y] == 1
                if w1 or w2:
                    continue

            if any(n.x == nx and n.y == ny for n in close_list):
                continue

            new_g = current.g + cost
            found = None
            for n in open_list:
                if n.x == nx and n.y == ny:
                    found = n
                    break

            if found is None:
                new_node = Node(nx, ny)
                new_node.g = new_g
                new_node.h = octile(new_node, goal)
                new_node.f = new_node.g + new_node.h
                new_node.parent = current
                open_list.append(new_node)
            else:
                if new_g < found.g:
                    found.g = new_g
                    found.f = new_g + found.h
                    found.parent = current
    return None


def print_grid(grid, path=None):
    for i, row in enumerate(grid):
        line = []
        for j, val in enumerate(row):
            if path and (i, j) in path:
                line.append("*")
            elif val == 1:
                line.append("#")
            else:
                line.append(".")
        print(" ".join(line))

'''以上是最经典的 A* 寻路算法。它会在地图上寻找从 A 点到 B 点最短的路线，如果遇到墙角，它能识别并禁止“斜穿墙角”，保证路线绝对安全。'''


# ==================== 以下是新增的接口代码 ====================

def build_grid(step=0.5):  # 默认改成 0.5
    """
    生成全局栅格地图，并将建筑物和边界（考虑车辆半径）设为障碍物
    step: 每个网格代表的实际距离（米），默认 0.5
    """
    from constants import BUILDINGS, VEHICLE_RADIUS
    import math

    size = int(100 / step)  # 如果是 0.5，这里 size = 200
    grid = [[0 for _ in range(size)] for _ in range(size)]

    # 1. 处理建筑物（向外膨胀 1.5 米，即车辆半径）
    for b in BUILDINGS:
        real_x_min = b['x_min'] - VEHICLE_RADIUS
        real_x_max = b['x_max'] + VEHICLE_RADIUS
        real_y_min = b['y_min'] - VEHICLE_RADIUS
        real_y_max = b['y_max'] + VEHICLE_RADIUS

        # 用 math.floor 和 math.ceil 确保膨胀的边界哪怕差了 0.1m 也能被包进去
        x_min = max(0, math.floor(real_x_min / step))
        x_max = min(size - 1, math.ceil(real_x_max / step))
        y_min = max(0, math.floor(real_y_min / step))
        y_max = min(size - 1, math.ceil(real_y_max / step))

        for i in range(x_min, x_max + 1):
            for j in range(y_min, y_max + 1):
                grid[i][j] = 1

    # 2. 处理场地边界（车心不能离边界小于 1.5m）
    for i in range(size):
        for j in range(size):
            real_x = i * step
            real_y = j * step
            if (real_x < VEHICLE_RADIUS or real_x > 100 - VEHICLE_RADIUS or
                    real_y < VEHICLE_RADIUS or real_y > 100 - VEHICLE_RADIUS):
                grid[i][j] = 1

    return grid
'''以上是自动读取 constants.py 里的建筑坐标，给所有建筑向外“长胖” 1.5 米（即车辆半径），
把所有障碍物和场地边界都涂成“墙”。生成一张 200x200（0.5米精度）的全局地图。'''


def get_actual_distance(start_xy, end_xy, grid, step=0.5):  # 默认改成 0.5
    """
    计算两点间的实际行驶距离，自动处理避障绕路
    """
    sx, sy = start_xy
    ex, ey = end_xy

    # 物理坐标转网格索引，使用 round 四舍五入更精确
    start_idx = (int(round((sx + 1e-6) / step)), int(round((sy + 1e-6) / step)))
    end_idx = (int(round((ex + 1e-6) / step)), int(round((ey + 1e-6) / step)))

    size = len(grid)
    if not (0 <= start_idx[0] < size and 0 <= start_idx[1] < size):
        return float('inf')
    if not (0 <= end_idx[0] < size and 0 <= end_idx[1] < size):
        return float('inf')

    if grid[start_idx[0]][start_idx[1]] == 1 or grid[end_idx[0]][end_idx[1]] == 1:
        return float('inf')

    # 调用你的 A* 算法
    path = a_star_classic(grid, start_idx, end_idx)

    if path is None:
        return float('inf')

    dist = 0.0
    for i in range(1, len(path)):
        dx = (path[i][0] - path[i - 1][0]) * step
        dy = (path[i][1] - path[i - 1][1]) * step
        dist += math.hypot(dx, dy)

    return dist
'''物理坐标到网格索引的转换。你扔给它起点和终点坐标，它会自动调用 A* 算法，
计算并返回绕开建筑的真实行驶距离（单位：米）。如果起点或终点被墙堵死，返回 inf。'''


# ==================== 高级功能：两阶段最优站点筛选 ====================
# 注意：这里把 geometry_interface 和 constants 导入进来
import geometry_interface as geo
import constants as const


def find_best_station_for_vehicle(car_idx, target_idx, candidate_stations, grid, step=0.5, start_pos=None, start_time=0.0, target_pos_override=None):
    """
    两阶段搜索：粗筛 25 个直线最快的，再 A* 精算挑 1 个真实的
    Args:
        car_idx: 车辆编号 (0~4)
        target_idx: 目标编号 (0~2)
        candidate_stations: 该目标的所有候选点列表，如 [(20.1, 30.5), ...]
        grid: 你的全局栅格地图
    Returns:
        (最优点位坐标, A*真实行驶时间, 行驶+转动总准备时间)
    """
    # 获取车辆起点和目标坐标
    # 获取车辆起点和目标坐标
    if start_pos is not None:
        car_start = start_pos  # 如果传了新起点，就用新起点（第二趟任务）
    else:
        car_start = (const.INITIAL_VEHICLE_POSITIONS[car_idx]['x'], const.INITIAL_VEHICLE_POSITIONS[car_idx]['y']) # 否则用初始位置
    target_pos = target_pos_override or (
        const.TARGETS[target_idx]['x'],
        const.TARGETS[target_idx]['y'],
        const.TARGETS[target_idx]['z'],
    )

    # ================= 阶段 1：直线距离粗筛 =================
    quick_list = []
    for station in candidate_stations:
        # 1. 算直线距离（无视墙壁，纯几何）
        straight_dist = math.hypot(station[0] - car_start[0], station[1] - car_start[1])

        # 2. 算云台转动时间（调用队友的接口）
        t_rot, _, _ = geo.compute_gimbal_rotate_time(station, target_pos)

        # 3. 粗估时间 = 直线距离 / 车速 + 转动时间
        est_time = (straight_dist / const.VEHICLE_SPEED) + t_rot
        quick_list.append((est_time, station))

    # 按照粗估时间从小到大排序，只保留前 25 个（如果没有25个就全保留）
    quick_list.sort(key=lambda x: x[0])
    top_25_stations = [item[1] for item in quick_list[:25]]

    # ================= 阶段 2：A* 精算 =================
    best_station = None
    min_total_time = float('inf')
    best_drive_time = 0.0

    for station in top_25_stations:
        # 调用你自己写的 A*，算出真实绕路距离
        actual_dist = get_actual_distance(car_start, station, grid, step)

        if actual_dist == float('inf'):
            continue  # 被墙堵死了，淘汰

        # 算真实行驶时间
        t_drive = actual_dist / const.VEHICLE_SPEED
        # 再算一次转动时间（因为需要用它算总时间）
        t_rot, _, _ = geo.compute_gimbal_rotate_time(station, target_pos)
        total_time = t_drive + t_rot

        # 打擂台，找真实时间最短的
        if total_time < min_total_time:
            min_total_time = total_time
            best_station = station
            best_drive_time = t_drive

    if best_station is None:
        return None, float('inf'), float('inf')

    # 绝对准备完成时间 = 车辆当前时刻 + 实际行驶时间 + 云台转动时间
    absolute_ready_time = start_time + min_total_time
    return best_station, best_drive_time, absolute_ready_time
'''输入车辆和目标位置，以及目标可观测点位，（grid前面已有函数生成，不需要管），输出最优点位，最优行驶时间，以及最短的全过程耗时
主函数调用时只需要调用这个函数即可'''
