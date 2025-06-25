"""
GPU加速版本的主程序
"""
import numpy as np
import os
import gc
import time
from MeshProcessor import MeshProcessor
from Visualizer import Visualizer
from gpu_accelerated_analyzer_fixed import GPUVisibilityAnalyzer
from config import VisibilityConfig as cfg
from PosGen import PosGen
from VisibilityStats import VisibilityStats
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    cp = np


def main_gpu_accelerated():
    """GPU加速的主执行函数"""
    print("="*60)
    print("GPU加速天体表面可见性分析")
    print("="*60)
    
    file_path = cfg.MODEL_PATH   
    camera_distance = cfg.CAMERA_DISTANCE
    sun_theta = cfg.SUN_theta_ANGLE
    sun_phi = cfg.SUN_phi_ANGLE

    print("正在加载和处理网格...")
    start_time = time.time()
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    load_time = time.time() - start_time
    
    print(f"网格加载完成: {len(patch_positions)} patches ({load_time:.2f}s)")
    print(f"网格边界框范围: {mesh.bounding_box.extents}")

    # 计算太阳方向
    sun_direction = np.array([
        np.cos(np.deg2rad(sun_phi)) * np.cos(np.deg2rad(sun_theta)),
        np.cos(np.deg2rad(sun_phi)) * np.sin(np.deg2rad(sun_theta)),
        np.sin(np.deg2rad(sun_phi))
    ])
    sun_direction = sun_direction / np.linalg.norm(sun_direction)

    # 生成相机位置
    print("正在生成相机位置...")
    camera_positions = PosGen.generate_camera_positions_simple_hemisphere(
        distance=cfg.CAMERA_DISTANCE,
        sun_direction=sun_direction,
        phi_levels=5,
        theta_points_equator=8
    )
    print(f"生成了 {len(camera_positions)} 个相机位置")
    
    # 初始化GPU分析器
    print("正在初始化GPU分析器...")
    init_start = time.time()
    gpu_analyzer = GPUVisibilityAnalyzer(mesh, patch_positions, patch_normals)
    init_time = time.time() - init_start
    print(f"GPU分析器初始化完成 ({init_time:.2f}s)")
    
    if GPU_AVAILABLE:
        # 显示GPU信息
        print(f"GPU设备: {cp.cuda.runtime.getDeviceProperties(0)['name'].decode()}")
        print(f"GPU内存: {cp.cuda.runtime.memGetInfo()[1] / 1024**3:.1f} GB")
    
    # 开始分析
    total_analysis_time = 0
    
    for pos_idx, (camera_phi, camera_theta) in enumerate(camera_positions):
        print(f"\n{'='*60}")
        print(f"处理相机位置 {pos_idx+1}/{len(camera_positions)}")
        print(f"相机 phi: {camera_phi:.1f}°, theta: {camera_theta:.1f}°")
        print(f"{'='*60}")
        
        position_start_time = time.time()
        
        beta = camera_phi - sun_phi
        base_camera_pos = PosGen.spherical_to_cartesian(camera_distance, camera_phi, camera_theta)
        
        position_dir = f"visibility_results/pos_{pos_idx:03d}_phi_{camera_phi:+06.1f}_theta_{camera_theta:06.1f}"
        os.makedirs(position_dir, exist_ok=True)
        
        # GPU加速的可见性分析
        if GPU_AVAILABLE:
            combined_visibility_mask = cp.zeros(len(patch_positions), dtype=bool)
        else:
            combined_visibility_mask = np.zeros(len(patch_positions), dtype=bool)
        
        rotation_angles = range(0, 360, 10)
        
        # 批量处理所有旋转角度
        for rotation_angle in rotation_angles:
            print(f"  处理旋转角度: {rotation_angle}°")
            
            rotation_rad = np.deg2rad(rotation_angle)
            rotation_matrix = np.array([
                [np.cos(rotation_rad), -np.sin(rotation_rad), 0],
                [np.sin(rotation_rad),  np.cos(rotation_rad), 0],
                [0,                    0,                   1]
            ])
            
            rotated_camera_pos = rotation_matrix @ base_camera_pos
            rotated_sun_direction = rotation_matrix @ sun_direction
            
            # GPU几何可见性检查
            geometric_visible = gpu_analyzer.gpu_check_fov_visibility(
                rotated_camera_pos, np.zeros(3),
                cfg.FOV_X_DEG, cfg.FOV_Y_DEG, cfg.MAX_VIEWING_ANGLE_DEG
            )
            
            # 遮挡检查（CPU）
            if GPU_AVAILABLE:
                geometric_visible_cpu = cp.asnumpy(geometric_visible)
            else:
                geometric_visible_cpu = geometric_visible
                
            unoccluded_mask = gpu_analyzer.filter_occluded_patches_cpu(
                rotated_camera_pos, geometric_visible_cpu
            )
            
            if GPU_AVAILABLE:
                unoccluded_mask = cp.asarray(unoccluded_mask)
            
            candidate_indices = cp.where(unoccluded_mask)[0] if GPU_AVAILABLE else np.where(unoccluded_mask)[0]
            if len(candidate_indices) == 0:
                # 创建空的统计对象
                stats = VisibilityStats(
                    geometric_visible=0,
                    light_illuminated=0,
                    reflection_good=0,
                    light_unoccluded=0,
                    final_visible=0,
                    visible_indices=np.array([]),
                    incidence_angles=np.array([]),
                    viewing_angles=np.array([]),
                    total_patches=len(patch_positions),
                    visible_area=0.0,
                    total_area=mesh.area
                )
                # 保存单个角度的结果
                output_file = os.path.join(position_dir, f"visibility_analysis_angle_{rotation_angle:03d}.txt")
                stats.print_summary(output_file)
                continue
            
            # GPU太阳光照检查
            sun_illuminated = gpu_analyzer.gpu_check_sun_illumination(
                rotated_sun_direction, cfg.MAX_SUN_ANGLE_DEG
            )
            
            # GPU反射条件检查
            reflection_good = gpu_analyzer.gpu_check_reflection_conditions(
                rotated_camera_pos, rotated_sun_direction, 
                unoccluded_mask, cfg.MAX_REFLECTION_ANGLE_DEG
            )
            
            # 太阳光遮挡检查（CPU）
            if GPU_AVAILABLE:
                candidate_positions_cpu = cp.asnumpy(gpu_analyzer.gpu_patch_positions[candidate_indices])
                reflection_good_cpu = cp.asnumpy(reflection_good)
            else:
                candidate_positions_cpu = gpu_analyzer.gpu_patch_positions[candidate_indices]
                reflection_good_cpu = reflection_good
                
            light_unoccluded_cpu = gpu_analyzer.filter_sun_occluded_cpu(
                candidate_positions_cpu, reflection_good_cpu, rotated_sun_direction
            )
            
            if GPU_AVAILABLE:
                light_unoccluded = cp.asarray(light_unoccluded_cpu)
            else:
                light_unoccluded = light_unoccluded_cpu
            
            # 计算最终可见性
            if GPU_AVAILABLE:
                final_mask = cp.zeros_like(geometric_visible, dtype=bool)
            else:
                final_mask = np.zeros_like(geometric_visible, dtype=bool)
                
            final_mask[candidate_indices] = (
                sun_illuminated[candidate_indices] & 
                reflection_good & 
                light_unoccluded
            )
            
            
            combined_visibility_mask = combined_visibility_mask | final_mask
            
            # 内存清理
            if GPU_AVAILABLE:
                del geometric_visible, final_mask
                cp.get_default_memory_pool().free_all_blocks()
        
        # 计算统计信息
        stats = gpu_analyzer.compute_statistics(combined_visibility_mask)
        
        # 保存结果
        combined_stats_file = os.path.join(position_dir, "combined_stats.txt")
        with open(combined_stats_file, "w") as f:
            f.write(f"Camera Position: phi={camera_phi:.1f}°, theta={camera_theta:.1f}°\n")
            f.write(f"Sun Direction: phi={sun_phi:.1f}°, theta={sun_theta:.1f}°\n")
            f.write(f"Beta angle (camera_phi - sun_phi): {beta:.1f}°\n")
            f.write(f"Total patches: {stats['total_patches']}\n")
            f.write(f"Visible patches: {stats['visible_patches']}\n")
            f.write(f"Patch coverage: {stats['patch_coverage']:.2f}%\n")
            f.write(f"Total area: {stats['total_area']:.2f}\n")
            f.write(f"Visible area: {stats['visible_area']:.2f}\n")
            f.write(f"Area coverage: {stats['area_coverage']:.2f}%\n")
        
        # 导出PLY文件
        if GPU_AVAILABLE:
            combined_visibility_mask_cpu = cp.asnumpy(combined_visibility_mask)
        else:
            combined_visibility_mask_cpu = combined_visibility_mask
            
        Visualizer.export_ply(
            mesh,
            combined_visibility_mask_cpu, 
            position_dir,
            filename="combined_visibility.ply", 
            isshow=False
        )
        
        position_time = time.time() - position_start_time
        total_analysis_time += position_time
        
        print(f"  位置 {pos_idx+1} 完成. 覆盖率: {stats['patch_coverage']:.1f}% (patches), {stats['area_coverage']:.1f}% (area)")
        print(f"  耗时: {position_time:.2f}s")
        
        # 清理GPU内存
        if GPU_AVAILABLE:
            del combined_visibility_mask
            cp.get_default_memory_pool().free_all_blocks()
        
        gc.collect()

    print(f"\n{'='*60}")
    print("所有分析完成!")
    print(f"结果保存在 visibility_results/ 目录")
    print(f"处理了 {len(camera_positions)} 个相机位置")
    print(f"总耗时: {total_analysis_time:.2f}s")
    print(f"平均每个位置: {total_analysis_time/len(camera_positions):.2f}s")
    print(f"{'='*60}")


def benchmark_comparison():
    """性能对比测试"""
    print("="*60)
    print("GPU vs CPU 性能对比测试")
    print("="*60)
    
    # 加载小规模数据进行测试
    file_path = cfg.MODEL_PATH   
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    
    # 减少测试规模
    test_positions = [(0, 0), (45, 90), (90, 180)]
    
    print(f"测试数据: {len(patch_positions)} patches")
    print(f"测试相机位置: {len(test_positions)} 个")
    
    if GPU_AVAILABLE:
        print("\n测试GPU版本...")
        gpu_start = time.time()
        gpu_analyzer = GPUVisibilityAnalyzer(mesh, patch_positions, patch_normals)
        
        for phi, theta in test_positions:
            camera_pos = PosGen.spherical_to_cartesian(600.0, phi, theta)
            sun_direction = np.array([1, 0, 0])
            
            visibility_mask = gpu_analyzer.gpu_check_fov_visibility(camera_pos)
            stats = gpu_analyzer.compute_statistics(visibility_mask)
        
        gpu_time = time.time() - gpu_start
        print(f"GPU总耗时: {gpu_time:.3f}s")
        
        # 测试CPU版本进行对比
        # print("\n测试CPU版本...")
        # cpu_start = time.time()
        
        # from VisibilityAnalyzer import VisibilityAnalyzer
        # cpu_analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
        
        # for phi, theta in test_positions:
        #     camera_pos = PosGen.spherical_to_cartesian(600.0, phi, theta)
        #     sun_direction = np.array([1, 0, 0])
            
        #     visibility_mask, stats = cpu_analyzer.analyze_visibility(
        #         camera_pos, sun_direction
        #     )
        
        # cpu_time = time.time() - cpu_start
        # print(f"CPU总耗时: {cpu_time:.3f}s")
        
        # speedup = cpu_time / gpu_time
        # print(f"\n加速比: {speedup:.2f}x")
        
    else:
        print("CuPy未安装，无法进行GPU测试")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        benchmark_comparison()
    else:
        main_gpu_accelerated()
