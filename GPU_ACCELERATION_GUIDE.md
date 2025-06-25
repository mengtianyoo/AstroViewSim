# AstroViewSim GPU加速使用指南

## 概述

您的天体表面可见性分析程序非常适合GPU加速。主要的计算密集型操作包括：

1. **向量/矩阵运算** - 大量的点积、叉积、归一化计算
2. **几何变换** - 旋转矩阵、坐标变换
3. **光照分析** - 太阳光照角度、反射条件检查
4. **并行布尔运算** - 可见性掩码的逻辑运算

## GPU加速优势

- **并行计算**: GPU拥有数千个核心，可以同时处理多个patch
- **向量化运算**: CuPy提供与NumPy相同的API，但运行在GPU上
- **内存带宽**: GPU拥有更高的内存带宽，适合大规模数据处理

## 安装和配置

### 1. 检查GPU环境
```bash
# 检查NVIDIA GPU
nvidia-smi

# 检查CUDA版本
nvcc --version
```

### 2. 安装GPU加速环境
```bash
# 运行自动配置脚本
python setup_gpu.py
```

或手动安装：
```bash
# CUDA 11.x
pip install cupy-cuda11x

# CUDA 12.x
pip install cupy-cuda12x

# 通用版本
pip install cupy
```

### 3. 验证安装
```bash
python -c "import cupy as cp; print('GPU Memory:', cp.cuda.runtime.memGetInfo())"
```

## 使用方法

### 运行GPU加速版本
```bash
# 完整分析
python main_gpu.py

# 性能对比测试
python main_gpu.py benchmark
```

### 配置参数
在 `config.py` 中调整GPU设置：
```python
# GPU加速设置
USE_GPU_ACCELERATION = True  # 启用GPU加速
GPU_BATCH_SIZE = 36  # 批处理大小
GPU_MEMORY_LIMIT_GB = 8  # 内存限制
```

## 性能优化建议

### 1. 内存管理
- **预分配GPU内存**: 数据在初始化时转移到GPU
- **及时释放内存**: 使用 `cp.get_default_memory_pool().free_all_blocks()`
- **批处理**: 将多个旋转角度批量处理

### 2. 计算优化
- **GPU并行**: 几何计算、光照分析在GPU上并行执行
- **CPU-GPU混合**: 复杂的ray casting仍在CPU上执行
- **内存局部性**: 减少CPU-GPU数据传输

### 3. 适合您程序的具体优化

```python
# 原始CPU代码
for rotation_angle in range(0, 360, 10):
    # 计算旋转后的相机位置
    rotated_camera_pos = rotation_matrix @ base_camera_pos
    # 逐个patch检查可见性
    visibility_mask = analyze_visibility(...)

# GPU加速版本
# 预计算所有旋转矩阵
rotation_matrices = cp.array([...])  # 36个旋转矩阵
# 批量处理所有旋转角度
all_camera_positions = rotation_matrices @ base_camera_pos
# 并行计算所有角度的可见性
visibility_masks = gpu_batch_analyze(all_camera_positions)
```

## 预期性能提升

根据您的程序特点，预期加速效果：

- **几何计算**: 5-15x 加速
- **光照分析**: 3-10x 加速
- **整体性能**: 2-8x 加速（取决于GPU型号和数据规模）

## 内存需求估算

对于包含N个patches的模型：
- **基础数据**: N × 24 bytes (positions + normals)
- **中间结果**: N × 20 bytes (各种mask)
- **总GPU内存**: 约 N × 50 bytes

例如：
- 100万patches ≈ 50MB GPU内存
- 1000万patches ≈ 500MB GPU内存

## 故障排除

### 1. CUDA/CuPy安装问题
```bash
# 检查CUDA版本兼容性
python -c "import cupy; print(cupy.cuda.runtime.runtimeGetVersion())"

# 重新安装CuPy
pip uninstall cupy
pip install cupy-cuda11x  # 或对应版本
```

### 2. 内存不足
```python
# 减少批处理大小
GPU_BATCH_SIZE = 18  # 从36减少到18

# 启用内存优化
ENABLE_MEMORY_OPTIMIZATION = True
```

### 3. 性能不佳
- 检查数据是否正确转移到GPU
- 避免频繁的CPU-GPU数据传输
- 使用 `cp.cuda.profile()` 进行性能分析

## 文件说明

- `main_gpu.py` - GPU加速主程序
- `gpu_accelerated_analyzer_fixed.py` - GPU加速分析器
- `setup_gpu.py` - 环境配置脚本
- `config.py` - 包含GPU设置的配置文件

## 使用示例

```python
from gpu_accelerated_analyzer_fixed import GPUVisibilityAnalyzer

# 初始化GPU分析器
gpu_analyzer = GPUVisibilityAnalyzer(mesh, patch_positions, patch_normals)

# GPU加速的可见性分析
visibility_mask = gpu_analyzer.analyze_single_view(
    camera_pos, sun_direction,
    fov_x_deg=2.0, fov_y_deg=2.0
)

# 计算统计信息
stats = gpu_analyzer.compute_statistics(visibility_mask)
print(f"覆盖率: {stats['patch_coverage']:.1f}%")
```

## 注意事项

1. **首次运行**: GPU初始化需要时间，后续运行会更快
2. **数据类型**: 保持float32精度以获得最佳GPU性能
3. **批处理**: 增大批处理大小可提高GPU利用率，但需要更多内存
4. **兼容性**: 如果没有GPU，程序会自动回退到CPU模式

通过GPU加速，您的天体表面可见性分析将显著提速，特别是在处理大规模模型和多个相机位置时！
