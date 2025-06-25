"""
GPU vs CPU 性能基准测试
"""
import numpy as np
import time
import gc
from MeshProcessor import MeshProcessor
from VisibilityAnalyzer import VisibilityAnalyzer
from config import VisibilityConfig as cfg
from PosGen import PosGen
import os
try:
    from gpu_accelerated_analyzer_fixed import GPUVisibilityAnalyzer
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
sun_theta = cfg.SUN_theta_ANGLE
sun_phi = cfg.SUN_phi_ANGLE
def benchmark_basic_operations():
    """测试基础数学运算的性能"""
    print("="*60)
    print("基础运算性能测试")
    print("="*60)
    
    # 测试数据大小
    sizes = [10000, 100000, 500000]
    
    for size in sizes:
        print(f"\n测试数据大小: {size:,} 个点")
        
        # 生成测试数据
        positions = np.random.random((size, 3)).astype(np.float32)
        normals = np.random.random((size, 3)).astype(np.float32)
        camera_pos = np.array([100, 0, 0], dtype=np.float32)
        sun_direction = np.array([1, 0, 0], dtype=np.float32)
        
        # CPU测试
        print("  CPU测试:")
        start_time = time.time()
        
        # 向量运算
        view_vectors = positions - camera_pos[None, :]
        view_distances = np.linalg.norm(view_vectors, axis=1)
        view_directions = view_vectors / view_distances[:, None]
        
        # 点积运算
        dot_products = np.sum(normals * view_directions, axis=1)
        
        # 角度计算
        angles = np.arccos(np.clip(dot_products, -1.0, 1.0))
        
        # 布尔运算
        mask1 = dot_products > 0
        mask2 = angles < np.pi/3
        combined_mask = mask1 & mask2
        
        cpu_time = time.time() - start_time
        print(f"    时间: {cpu_time:.4f}s")
        
        # GPU测试（如果可用）
        if GPU_AVAILABLE:
            try:
                import cupy as cp
                print("  GPU测试:")
                start_time = time.time()
                
                # 转移到GPU
                gpu_positions = cp.asarray(positions)
                gpu_normals = cp.asarray(normals)
                gpu_camera_pos = cp.asarray(camera_pos)
                
                # 向量运算
                gpu_view_vectors = gpu_positions - gpu_camera_pos[None, :]
                gpu_view_distances = cp.linalg.norm(gpu_view_vectors, axis=1)
                gpu_view_directions = gpu_view_vectors / gpu_view_distances[:, None]
                
                # 点积运算
                gpu_dot_products = cp.sum(gpu_normals * gpu_view_directions, axis=1)
                
                # 角度计算
                gpu_angles = cp.arccos(cp.clip(gpu_dot_products, -1.0, 1.0))
                
                # 布尔运算
                gpu_mask1 = gpu_dot_products > 0
                gpu_mask2 = gpu_angles < cp.pi/3
                gpu_combined_mask = gpu_mask1 & gpu_mask2
                
                # 同步GPU
                cp.cuda.Stream.null.synchronize()
                
                gpu_time = time.time() - start_time
                print(f"    时间: {gpu_time:.4f}s")
                print(f"    加速比: {cpu_time/gpu_time:.2f}x")
                
                # 内存清理
                cp.get_default_memory_pool().free_all_blocks()
                
            except Exception as e:
                print(f"  GPU测试失败: {e}")
        else:
            print("  GPU不可用")


def benchmark_visibility_analysis():
    """测试完整可见性分析的性能"""
    print("\n" + "="*60)
    print("完整可见性分析性能测试")
    print("="*60)
    
    # 加载模型
    print("加载测试模型...")
    file_path = cfg.MODEL_PATH
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    print(f"模型包含 {len(patch_positions):,} patches")
    
    # 生成测试相机位置
    sun_direction = np.array([1, 0, 0])
    test_positions = [(90, 180), (90, 180), (90, 180), (90, 180), (90, 180), (90, 180)]
    
    print(f"测试 {len(test_positions)} 个相机位置")
    
    # # CPU测试
    # print("\nCPU分析测试:")
    # cpu_analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
    
    # cpu_start_time = time.time()
    # cpu_results = []
    
    # for i, (phi, theta) in enumerate(test_positions):
    #     print(f"  处理位置 {i+1}/{len(test_positions)}: phi={phi}°, theta={theta}°")
        
    #     camera_pos = PosGen.spherical_to_cartesian(cfg.CAMERA_DISTANCE, phi, theta)
        
    #     # 测试多个旋转角度
    #     position_masks = []
    #     for rotation_angle in range(0, 360, 30):  # 减少角度数量以加快测试
    #         rotation_rad = np.deg2rad(rotation_angle)
    #         rotation_matrix = np.array([
    #             [np.cos(rotation_rad), -np.sin(rotation_rad), 0],
    #             [np.sin(rotation_rad),  np.cos(rotation_rad), 0],
    #             [0,                    0,                   1]
    #         ])
            
    #         rotated_camera_pos = rotation_matrix @ camera_pos
    #         rotated_sun_direction = rotation_matrix @ sun_direction
            
    #         visibility_mask, stats = cpu_analyzer.analyze_visibility(
    #             rotated_camera_pos, rotated_sun_direction,
    #             fov_x_deg=cfg.FOV_X_DEG, fov_y_deg=cfg.FOV_Y_DEG,
    #             max_viewing_angle_deg=cfg.MAX_VIEWING_ANGLE_DEG,
    #             max_sun_angle_deg=cfg.MAX_SUN_ANGLE_DEG,
    #             max_reflection_angle_deg=cfg.MAX_REFLECTION_ANGLE_DEG
    #         )
    #         position_masks.append(visibility_mask)
        
    #     # 合并结果
    #     combined_mask = np.zeros_like(position_masks[0], dtype=bool)
    #     for mask in position_masks:
    #         combined_mask = combined_mask | mask
        
    #     cpu_results.append(combined_mask)
    
    # cpu_total_time = time.time() - cpu_start_time
    # print(f"CPU总时间: {cpu_total_time:.2f}s")
    # print(f"平均每个位置: {cpu_total_time/len(test_positions):.2f}s")
    
    # GPU测试（如果可用）
    if GPU_AVAILABLE:
        print("\nGPU分析测试:")
        try:
            gpu_analyzer = GPUVisibilityAnalyzer(mesh, patch_positions, patch_normals)
            
            gpu_start_time = time.time()
            gpu_results = []
            
            for i, (phi, theta) in enumerate(test_positions):
                position_dir = f"visibility_results/pos_{i:03d}_phi_{phi:+06.1f}_theta_{theta:06.1f}"
                os.makedirs(position_dir, exist_ok=True)
                beta = phi - sun_phi
                print(f"  处理位置 {i+1}/{len(test_positions)}: phi={phi}°, theta={theta}°")
                
                camera_pos = PosGen.spherical_to_cartesian(cfg.CAMERA_DISTANCE, phi, theta)
                
                # 测试多个旋转角度
                position_masks = []
                for rotation_angle in range(0, 360, 30):
                    rotation_rad = np.deg2rad(rotation_angle)
                    rotation_matrix = np.array([
                        [np.cos(rotation_rad), -np.sin(rotation_rad), 0],
                        [np.sin(rotation_rad),  np.cos(rotation_rad), 0],
                        [0,                    0,                   1]
                    ])
                    
                    rotated_camera_pos = rotation_matrix @ camera_pos
                    rotated_sun_direction = rotation_matrix @ sun_direction
                    
                    visibility_mask = gpu_analyzer.analyze_single_view(
                        rotated_camera_pos, rotated_sun_direction,
                        fov_x_deg=cfg.FOV_X_DEG, fov_y_deg=cfg.FOV_Y_DEG,
                        max_viewing_angle_deg=cfg.MAX_VIEWING_ANGLE_DEG,
                        max_sun_angle_deg=cfg.MAX_SUN_ANGLE_DEG,
                        max_reflection_angle_deg=cfg.MAX_REFLECTION_ANGLE_DEG
                    )
                    position_masks.append(visibility_mask)
                stats = gpu_analyzer.compute_statistics(position_masks)
                        # 保存结果
                combined_stats_file = os.path.join(position_dir, "combined_stats.txt")
                with open(combined_stats_file, "w") as f:
                    f.write(f"Camera Position: phi={phi:.1f}°, theta={theta:.1f}°\n")
                    f.write(f"Sun Direction: phi={sun_phi:.1f}°, theta={sun_theta:.1f}°\n")
                    f.write(f"Beta angle (camera_phi - sun_phi): {beta:.1f}°\n")
                    f.write(f"Total patches: {stats['total_patches']}\n")
                    f.write(f"Visible patches: {stats['visible_patches']}\n")
                    f.write(f"Patch coverage: {stats['patch_coverage']:.2f}%\n")
                    f.write(f"Total area: {stats['total_area']:.2f}\n")
                    f.write(f"Visible area: {stats['visible_area']:.2f}\n")
                    f.write(f"Area coverage: {stats['area_coverage']:.2f}%\n")
                # 合并结果
                if gpu_analyzer.gpu_available:
                    import cupy as cp
                    combined_mask = cp.zeros_like(position_masks[0], dtype=bool)
                    for mask in position_masks:
                        combined_mask = combined_mask | mask
                else:
                    combined_mask = np.zeros_like(position_masks[0], dtype=bool)
                    for mask in position_masks:
                        combined_mask = combined_mask | mask
                
                gpu_results.append(combined_mask)
                
                # 内存清理
                if gpu_analyzer.gpu_available:
                    cp.get_default_memory_pool().free_all_blocks()
            
            gpu_total_time = time.time() - gpu_start_time
            print(f"GPU总时间: {gpu_total_time:.2f}s")
            print(f"平均每个位置: {gpu_total_time/len(test_positions):.2f}s")
            
            # # 计算加速比
            # speedup = cpu_total_time / gpu_total_time
            # print(f"\n整体加速比: {speedup:.2f}x")
            
            # # 验证结果一致性
            # print("\n结果一致性检查:")
            # for i, (cpu_mask, gpu_mask) in enumerate(zip(cpu_results, gpu_results)):
            #     if gpu_analyzer.gpu_available:
            #         import cupy as cp
            #         gpu_mask_cpu = cp.asnumpy(gpu_mask)
            #     else:
            #         gpu_mask_cpu = gpu_mask
                
            #     consistency = np.sum(cpu_mask == gpu_mask_cpu) / len(cpu_mask)
            #     print(f"  位置 {i+1}: {consistency*100:.1f}% 一致")
            
        except Exception as e:
            print(f"GPU测试失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nGPU不可用，跳过GPU测试")


def main():
    """主测试函数"""
    print("AstroViewSim GPU加速性能基准测试")
    print("="*60)
    
    # 检查GPU可用性
    if GPU_AVAILABLE:
        try:
            import cupy as cp
            print(f"GPU设备: {cp.cuda.runtime.getDeviceProperties(0)['name'].decode()}")
            print(f"GPU内存: {cp.cuda.runtime.memGetInfo()[1] / 1024**3:.1f} GB")
        except:
            print("GPU信息获取失败")
    else:
        print("GPU不可用，仅进行CPU测试")
    
    # 运行基础运算测试
    benchmark_basic_operations()
    
    # 运行完整分析测试
    benchmark_visibility_analysis()
    
    print("\n" + "="*60)
    print("基准测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
