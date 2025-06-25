"""
GPU加速环境安装和配置脚本
"""

import subprocess
import sys
import os


def check_cuda_availability():
    """检查CUDA是否可用"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ NVIDIA GPU 检测成功")
            print(result.stdout.split('\n')[0])  # 显示第一行GPU信息
            return True
        else:
            print("✗ 未检测到NVIDIA GPU")
            return False
    except FileNotFoundError:
        print("✗ nvidia-smi 命令未找到，请安装NVIDIA驱动")
        return False


def install_cupy():
    """安装CuPy"""
    print("正在安装CuPy...")
    try:
        # 检查CUDA版本
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ CUDA工具包已安装")
            
            # 根据CUDA版本安装相应的CuPy
            if "11." in result.stdout:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cupy-cuda11x'])
            elif "12." in result.stdout:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cupy-cuda12x'])
            else:
                print("使用通用版本的CuPy")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cupy'])
                
            print("✓ CuPy 安装成功")
            return True
            
        else:
            print("✗ CUDA工具包未安装，尝试安装通用版本")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cupy'])
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"✗ CuPy 安装失败: {e}")
        return False
    except FileNotFoundError:
        print("✗ nvcc 命令未找到，请安装CUDA工具包")
        return False


def install_opencl_alternative():
    """安装OpenCL替代方案"""
    print("正在安装OpenCL替代方案...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyopencl'])
        print("✓ PyOpenCL 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ PyOpenCL 安装失败: {e}")
        return False


def test_gpu_acceleration():
    """测试GPU加速功能"""
    print("\n测试GPU加速功能...")
    
    try:
        import cupy as cp
        import numpy as np
        
        # 简单的GPU测试
        print("✓ CuPy 导入成功")
        
        # 测试GPU内存分配
        gpu_array = cp.random.random((1000, 1000))
        cpu_array = np.random.random((1000, 1000))
        
        # 测试GPU计算
        import time
        start_time = time.time()
        gpu_result = cp.dot(gpu_array, gpu_array)
        gpu_time = time.time() - start_time
        
        start_time = time.time()
        cpu_result = np.dot(cpu_array, cpu_array)
        cpu_time = time.time() - start_time
        
        print(f"GPU计算时间: {gpu_time:.4f}s")
        print(f"CPU计算时间: {cpu_time:.4f}s")
        print(f"加速比: {cpu_time/gpu_time:.2f}x")
        
        return True
        
    except ImportError:
        print("✗ CuPy 未正确安装")
        return False
    except Exception as e:
        print(f"✗ GPU测试失败: {e}")
        return False


def create_gpu_requirements():
    """创建GPU加速的requirements文件"""
    gpu_requirements = """# GPU加速版本的依赖包
# 基础依赖
numpy>=1.21.0
trimesh>=3.9.0
matplotlib>=3.5.0

# GPU加速依赖 (根据您的CUDA版本选择一个)
# CUDA 11.x
cupy-cuda11x>=11.0.0

# CUDA 12.x (如果您使用CUDA 12)
# cupy-cuda12x>=12.0.0

# 或者使用通用版本 (如果上述版本不兼容)
# cupy>=11.0.0

# OpenCL替代方案 (如果没有NVIDIA GPU)
# pyopencl>=2022.1

# 可选的额外加速库
# numba>=0.56.0  # JIT编译加速
# scipy>=1.7.0   # 科学计算库
"""
    
    with open('requirements_gpu.txt', 'w') as f:
        f.write(gpu_requirements)
    
    print("✓ 已创建 requirements_gpu.txt")


def main():
    """主安装流程"""
    print("="*60)
    print("AstroViewSim GPU加速环境配置")
    print("="*60)
    
    # 检查GPU
    has_nvidia_gpu = check_cuda_availability()
    
    if has_nvidia_gpu:
        print("\n正在配置NVIDIA GPU加速...")
        if install_cupy():
            if test_gpu_acceleration():
                print("\n✓ GPU加速配置成功!")
                print("您可以运行以下命令测试:")
                print("python main_gpu.py")
                print("python main_gpu.py benchmark  # 性能对比测试")
            else:
                print("\n⚠ GPU加速配置可能存在问题")
        else:
            print("\n尝试OpenCL替代方案...")
            install_opencl_alternative()
    else:
        print("\n未检测到NVIDIA GPU，尝试OpenCL替代方案...")
        install_opencl_alternative()
    
    # 创建requirements文件
    create_gpu_requirements()
    
    print("\n" + "="*60)
    print("配置完成!")
    print("="*60)
    
    print("\n使用说明:")
    print("1. 运行GPU加速版本: python main_gpu.py")
    print("2. 性能对比测试: python main_gpu.py benchmark")
    print("3. 原始CPU版本: python main.py")
    
    print("\n优化建议:")
    print("- 确保GPU有足够内存 (建议8GB+)")
    print("- 对于大型模型，可以调整批处理大小")
    print("- 监控GPU使用率: nvidia-smi")


if __name__ == "__main__":
    main()
