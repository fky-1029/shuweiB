"""
环境测试脚本 - 验证 Python 依赖是否正确安装
"""

def test_imports():
    """测试核心库导入"""
    print("=" * 50)
    print("环境测试开始")
    print("=" * 50)

    # 测试 NumPy
    try:
        import numpy as np
        print(f"✓ NumPy {np.__version__} 导入成功")
        # 简单计算测试
        arr = np.array([1, 2, 3, 4, 5])
        assert arr.mean() == 3.0
        print(f"  - 基础计算测试通过")
    except ImportError as e:
        print(f"✗ NumPy 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ NumPy 测试失败: {e}")
        return False

    # 测试 Matplotlib
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        print(f"✓ Matplotlib {matplotlib.__version__} 导入成功")
        print(f"  - 后端: {matplotlib.get_backend()}")
    except ImportError as e:
        print(f"✗ Matplotlib 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ Matplotlib 测试失败: {e}")
        return False

    # 测试 SciPy
    try:
        import scipy
        print(f"✓ SciPy {scipy.__version__} 导入成功")
    except ImportError as e:
        print(f"✗ SciPy 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ SciPy 测试失败: {e}")
        return False

    print("=" * 50)
    print("所有依赖测试通过 ✓")
    print("=" * 50)
    return True


def test_project_structure():
    """测试项目结构和导入"""
    print("\n" + "=" * 50)
    print("项目结构测试")
    print("=" * 50)

    try:
        from constants import (
            FIELD_SIZE, VEHICLE_RADIUS, CAMERA_HEIGHT,
            GIMBAL_PITCH_MIN, GIMBAL_PITCH_MAX,
            BUILDINGS, INITIAL_VEHICLE_POSITIONS, TARGETS
        )
        print(f"✓ constants.py 导入成功")
        print(f"  - 场地尺寸: {FIELD_SIZE} m")
        print(f"  - 摄像头高度: {CAMERA_HEIGHT} m")
        print(f"  - 建筑物数量: {len(BUILDINGS)}")
        print(f"  - 车辆数量: {len(INITIAL_VEHICLE_POSITIONS)}")
        print(f"  - 目标数量: {len(TARGETS)}")
    except ImportError as e:
        print(f"✗ constants.py 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ constants.py 测试失败: {e}")
        return False

    try:
        from geometry_interface import (
            check_observation_feasibility,
            calculate_elevation_angle,
            is_within_gimbal_range
        )
        print(f"✓ geometry_interface.py 导入成功")
        print(f"  - 接口函数已定义（尚未实现）")
    except ImportError as e:
        print(f"✗ geometry_interface.py 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ geometry_interface.py 测试失败: {e}")
        return False

    print("=" * 50)
    print("项目结构测试通过 ✓")
    print("=" * 50)
    return True


if __name__ == "__main__":
    import sys

    success = True

    # 测试依赖
    if not test_imports():
        success = False
        print("\n⚠️  依赖测试未通过，请检查安装")

    # 测试项目结构
    if not test_project_structure():
        success = False
        print("\n⚠️  项目结构测试未通过")

    if success:
        print("\n🎉 环境准备完成，可以开始开发")
        sys.exit(0)
    else:
        print("\n❌ 存在问题，请检查上述错误信息")
        sys.exit(1)
