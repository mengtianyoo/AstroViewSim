"""
GPU加速的可见性分析器 - 修复版本
使用CuPy进行GPU加速计算
"""

import numpy as np
import trimesh
import time
from typing import Tuple, Optional, Union
import gc

try:
    import cupy as cp
    GPU_AVAILABLE = True
    print("GPU加速可用 (CuPy)")
    ArrayType = Union[np.ndarray, cp.ndarray]
except ImportError:
    GPU_AVAILABLE = False
    print("警告: CuPy未安装，将使用CPU计算")
    # 如果没有cupy，定义cp为numpy的别名
    cp = np
    ArrayType = np.ndarray

from VisibilityStats import VisibilityStats


class GPUVisibilityAnalyzer:
    """GPU加速的可见性分析器"""
    
    def __init__(self, mesh: trimesh.Trimesh, patch_positions: np.ndarray, patch_normals: np.ndarray):
        self.mesh = mesh
        self.patch_positions = patch_positions
        self.patch_normals = patch_normals
        self.gpu_available = GPU_AVAILABLE
        
        # 将数据预先转移到GPU
        if self.gpu_available:
            self.gpu_patch_positions = cp.asarray(patch_positions)
            self.gpu_patch_normals = cp.asarray(patch_normals)
            self.gpu_area_faces = cp.asarray(mesh.area_faces)
            print(f"数据已转移到GPU: {len(patch_positions)} patches")
        else:
            self.gpu_patch_positions = patch_positions
            self.gpu_patch_normals = patch_normals
            self.gpu_area_faces = mesh.area_faces
    
    def gpu_check_fov_visibility(self, camera_pos: np.ndarray, target: np.ndarray = None,
                                fov_x_deg: float = 2.0, fov_y_deg: float = 2.0,
                                max_angle_deg: float = 45.0):
        """GPU加速的FOV可见性检查"""
        if target is None:
            target = np.zeros(3)
            
        # 转换为GPU数组
        if self.gpu_available:
            gpu_camera_pos = cp.asarray(camera_pos)
            gpu_target = cp.asarray(target)
        else:
            gpu_camera_pos = camera_pos
            gpu_target = target
        
        # 计算相机坐标系
        z_cam = gpu_target - gpu_camera_pos
        z_cam = z_cam / cp.linalg.norm(z_cam)
        
        world_up = cp.array([0, 0, 1], dtype=cp.float32)
        x_cam = cp.cross(z_cam, world_up)
        x_cam = x_cam / cp.linalg.norm(x_cam)
        y_cam = cp.cross(x_cam, z_cam)
        
        # 计算视线向量
        view_vectors = self.gpu_patch_positions - gpu_camera_pos[None, :]
        z_coords = cp.dot(view_vectors, z_cam)
        
        # 检查是否在相机前方
        in_front = z_coords > 0
        
        # 计算视线方向和角度
        view_distances = cp.linalg.norm(view_vectors, axis=1, keepdims=True)
        view_directions = view_vectors / view_distances
        dot_products = cp.sum(self.gpu_patch_normals * view_directions, axis=1)
        
        # 面朝相机
        facing_camera = dot_products < 0
        
        # 良好的观测角度
        cos_max_angle = cp.cos(cp.deg2rad(max_angle_deg))
        good_viewing_angle = dot_products <= -cos_max_angle
        
        # FOV检查
        x_coords = cp.dot(view_vectors, x_cam)
        y_coords = cp.dot(view_vectors, y_cam)
        
        tan_x = cp.abs(x_coords / z_coords)
        tan_y = cp.abs(y_coords / z_coords)
        
        tan_fov_x_half = cp.tan(cp.deg2rad(fov_x_deg / 2))
        tan_fov_y_half = cp.tan(cp.deg2rad(fov_y_deg / 2))
        
        within_fov_x = tan_x <= tan_fov_x_half
        within_fov_y = tan_y <= tan_fov_y_half
        
        visible_mask = (in_front & facing_camera & good_viewing_angle & 
                       within_fov_x & within_fov_y)
        
        return visible_mask
    
    def gpu_check_sun_illumination(self, sun_direction: np.ndarray, 
                                  max_sun_angle_deg: float = 60.0):
        """GPU加速的太阳光照检查"""
        if self.gpu_available:
            gpu_sun_direction = cp.asarray(sun_direction)
        else:
            gpu_sun_direction = sun_direction
            
        dot_products = cp.dot(self.gpu_patch_normals, gpu_sun_direction)
        facing_sun = dot_products > 0
        
        cos_max_angle = cp.cos(cp.deg2rad(max_sun_angle_deg))
        good_sun_angle = dot_products >= cos_max_angle
        
        return facing_sun & good_sun_angle
    
    def gpu_check_reflection_conditions(self, camera_pos: np.ndarray, 
                                      sun_direction: np.ndarray,
                                      candidate_mask,
                                      max_angle_deg: float = 30.0):
        """GPU加速的反射条件检查"""
        if self.gpu_available:
            gpu_camera_pos = cp.asarray(camera_pos)
            gpu_sun_direction = cp.asarray(sun_direction)
        else:
            gpu_camera_pos = camera_pos
            gpu_sun_direction = sun_direction
        
        # 获取候选patch位置
        candidate_positions = self.gpu_patch_positions[candidate_mask]
        
        # 计算视线方向
        view_directions = gpu_camera_pos[None, :] - candidate_positions
        view_directions = view_directions / cp.linalg.norm(view_directions, axis=1, keepdims=True)
        
        # 计算太阳方向与视线方向的角度
        sun_direction_broadcast = gpu_sun_direction[None, :].repeat(len(view_directions), axis=0)
        dot_product = cp.sum(view_directions * sun_direction_broadcast, axis=1)
        angles = cp.arccos(cp.clip(dot_product, -1.0, 1.0))
        angles_deg = cp.rad2deg(angles)
        good_angles = angles_deg <= max_angle_deg
        
        return good_angles
    
    def filter_occluded_patches_cpu(self, camera_pos: np.ndarray, 
                                   candidate_mask: np.ndarray) -> np.ndarray:
        """CPU版本的遮挡检查（使用trimesh的ray casting）"""
        visible_mask = candidate_mask.copy()
        
        if not np.any(candidate_mask):
            return visible_mask
        
        candidate_positions = self.patch_positions[candidate_mask]
        n_candidates = len(candidate_positions)
        
        ray_origins = np.repeat(camera_pos[None, :], n_candidates, axis=0)
        ray_directions = candidate_positions - camera_pos[None, :]
        ray_distances = np.linalg.norm(ray_directions, axis=1)
        ray_directions = ray_directions / ray_distances[:, None]
        
        locations, index_ray, index_tri = self.mesh.ray.intersects_location(
            ray_origins=ray_origins,
            ray_directions=ray_directions
        )
        
        if len(locations) == 0:
            return visible_mask
        
        intersect_distances = np.linalg.norm(locations - camera_pos[None, :], axis=1)
        is_occluded = np.zeros(n_candidates, dtype=bool)
        
        for i in range(n_candidates):
            ray_mask = index_ray == i
            if not np.any(ray_mask):
                continue
            
            ray_intersect_distances = intersect_distances[ray_mask]
            target_distance = ray_distances[i]
            
            tolerance = target_distance * 1e-6 + 1e-8
            closer_intersections = ray_intersect_distances < (target_distance - tolerance)
            
            if np.any(closer_intersections):
                is_occluded[i] = True
        
        visible_mask[candidate_mask] = ~is_occluded
        return visible_mask
    
    def filter_sun_occluded_cpu(self, candidate_positions: np.ndarray,
                               candidate_mask: np.ndarray, 
                               sun_direction: np.ndarray) -> np.ndarray:
        """CPU版本的太阳光遮挡检查"""
        illuminated_mask = candidate_mask.copy()
        if not np.any(candidate_mask):
            return illuminated_mask
        
        sun_direction = sun_direction / np.linalg.norm(sun_direction)
        filtered_positions = candidate_positions[candidate_mask]
        n_candidates = len(filtered_positions)
        
        ray_origins = filtered_positions - sun_direction * 1e-2
        ray_directions = np.tile(sun_direction, (n_candidates, 1))
        
        locations, index_ray, index_tri = self.mesh.ray.intersects_location(
            ray_origins=ray_origins,
            ray_directions=ray_directions
        )
        
        is_shadowed = np.zeros(n_candidates, dtype=bool)
        
        for i in range(n_candidates):
            ray_mask = index_ray == i
            if not np.any(ray_mask):
                continue
            
            ray_locs = locations[ray_mask]
            patch_pos = filtered_positions[i]
            dists = np.linalg.norm(ray_locs - ray_origins[i], axis=1)
            
            actual_dist = np.linalg.norm(patch_pos - ray_origins[i])
            tolerance = actual_dist * 1e-6 + 1e-8
            if np.any(dists < (actual_dist - tolerance)):
                is_shadowed[i] = True
        
        illuminated_mask[candidate_mask] = ~is_shadowed
        return illuminated_mask
    
    def compute_statistics(self, visibility_mask) -> dict:
        """计算可见性统计信息"""
        if self.gpu_available:
            visible_patches = int(cp.sum(visibility_mask))
            visible_area = float(cp.sum(self.gpu_area_faces[visibility_mask]))
            total_area = float(cp.sum(self.gpu_area_faces))
        else:
            visible_patches = int(np.sum(visibility_mask))
            visible_area = float(np.sum(self.gpu_area_faces[visibility_mask]))
            total_area = float(np.sum(self.gpu_area_faces))
        
        total_patches = len(self.patch_positions)
        
        return {
            'visible_patches': visible_patches,
            'total_patches': total_patches,
            'patch_coverage': (visible_patches / total_patches) * 100,
            'visible_area': visible_area,
            'total_area': total_area,
            'area_coverage': (visible_area / total_area) * 100
        }
    
    def analyze_single_view(self, camera_pos: np.ndarray, sun_direction: np.ndarray,
                           fov_x_deg: float = 2.0, fov_y_deg: float = 2.0,
                           max_viewing_angle_deg: float = 60.0,
                           max_sun_angle_deg: float = 60.0,
                           max_reflection_angle_deg: float = 30.0):
        """分析单个视角的可见性"""
        
        # GPU几何可见性检查
        geometric_visible = self.gpu_check_fov_visibility(
            camera_pos, np.zeros(3), fov_x_deg, fov_y_deg, max_viewing_angle_deg
        )
        
        # 遮挡检查（CPU）
        if self.gpu_available:
            geometric_visible_cpu = cp.asnumpy(geometric_visible)
        else:
            geometric_visible_cpu = geometric_visible
            
        unoccluded_mask = self.filter_occluded_patches_cpu(camera_pos, geometric_visible_cpu)
        
        if self.gpu_available:
            unoccluded_mask = cp.asarray(unoccluded_mask)
        
        candidate_indices = cp.where(unoccluded_mask)[0] if self.gpu_available else np.where(unoccluded_mask)[0]
        if len(candidate_indices) == 0:
            return cp.zeros_like(geometric_visible, dtype=bool) if self.gpu_available else np.zeros_like(geometric_visible, dtype=bool)
        
        # GPU太阳光照检查
        sun_illuminated = self.gpu_check_sun_illumination(sun_direction, max_sun_angle_deg)
        
        # GPU反射条件检查
        reflection_good = self.gpu_check_reflection_conditions(
            camera_pos, sun_direction, unoccluded_mask, max_reflection_angle_deg
        )
        
        # 太阳光遮挡检查（CPU）
        if self.gpu_available:
            candidate_positions_cpu = cp.asnumpy(self.gpu_patch_positions[candidate_indices])
            reflection_good_cpu = cp.asnumpy(reflection_good)
        else:
            candidate_positions_cpu = self.gpu_patch_positions[candidate_indices]
            reflection_good_cpu = reflection_good
            
        light_unoccluded_cpu = self.filter_sun_occluded_cpu(
            candidate_positions_cpu, reflection_good_cpu, sun_direction
        )
        
        if self.gpu_available:
            light_unoccluded = cp.asarray(light_unoccluded_cpu)
        else:
            light_unoccluded = light_unoccluded_cpu
        
        # 计算最终可见性
        if self.gpu_available:
            final_mask = cp.zeros_like(geometric_visible, dtype=bool)
        else:
            final_mask = np.zeros_like(geometric_visible, dtype=bool)
            
        final_mask[candidate_indices] = (
            sun_illuminated[candidate_indices] & 
            reflection_good & 
            light_unoccluded
        )
        
        return final_mask
