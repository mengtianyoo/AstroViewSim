import trimesh
import numpy as np
from typing import Tuple

from VisibilityStats import VisibilityStats
from GeometricVisibility import GeometricVisibility
from LightingAnalysis import LightingAnalysis


class VisibilityAnalyzer:
    """Main class for comprehensive visibility analysis."""
    
    def __init__(self, mesh: trimesh.Trimesh, patch_positions: np.ndarray, patch_normals: np.ndarray):
        self.mesh = mesh
        self.patch_positions = patch_positions
        self.patch_normals = patch_normals
        
    def analyze_visibility(self,
                         camera_pos: np.ndarray,
                         sun_direction: np.ndarray,
                         target: np.ndarray = None,
                         fov_x_deg: float = 2.0,
                         fov_y_deg: float = 2.0,
                         max_viewing_angle_deg: float = 60.0,
                         max_sun_angle_deg: float = 60.0,
                         max_reflection_angle_deg: float = 30.0) -> Tuple[np.ndarray, VisibilityStats]:
        """
        Comprehensive visibility analysis considering geometry and lighting.
        """
        if target is None:
            target = np.zeros(3)
            
        # Geometric visibility
        geometric_visible = GeometricVisibility.check_fov_visibility(
            self.patch_positions, self.patch_normals, camera_pos, target,
            fov_x_deg, fov_y_deg, max_viewing_angle_deg
        )
        
        # Occlusion filtering
        unoccluded_mask = GeometricVisibility.filter_occluded_patches(
            self.mesh, self.patch_positions, camera_pos, geometric_visible
        )
        
        # Lighting analysis on geometrically visible patches
        candidate_indices = np.where(unoccluded_mask)[0]
        if len(candidate_indices) == 0:
            empty_stats = VisibilityStats(0, 0, 0, 0, 0, len(self.patch_positions), 0.0, 0.0)
            return np.zeros_like(geometric_visible), empty_stats
            
        candidate_positions = self.patch_positions[candidate_indices]
        candidate_normals = self.patch_normals[candidate_indices]
        
        # Check lighting conditions
        light_illuminated = LightingAnalysis.check_sun_illumination(
            candidate_normals, sun_direction, max_sun_angle_deg
        )
        
        reflection_good = LightingAnalysis.check_reflection_conditions(
            candidate_positions, camera_pos, 
            sun_direction, max_reflection_angle_deg
        )
        
        # Check sun occlusion
        lighting_candidates = light_illuminated & reflection_good
        light_unoccluded = LightingAnalysis.filter_sun_occluded(
            self.mesh, candidate_positions, lighting_candidates, sun_direction
        )
        
        # Combine all conditions
        final_lighting_mask = light_illuminated & reflection_good & light_unoccluded
        
        # Create final visibility mask
        final_visible_mask = np.zeros_like(geometric_visible)
        final_visible_mask[candidate_indices] = final_lighting_mask

        visible_indices = np.where(final_visible_mask)[0]
        if len(visible_indices) > 0:
            visible_positions = self.patch_positions[visible_indices]
            visible_normals = self.patch_normals[visible_indices]

            incidence_angles = np.arccos(np.clip(
                np.dot(visible_normals, sun_direction), -1.0, 1.0))

            view_directions = camera_pos[None, :] - visible_positions
            view_directions = view_directions / np.linalg.norm(view_directions, axis=1, keepdims=True)
            viewing_angles = np.arccos(np.clip(
                np.sum(visible_normals * view_directions, axis=1), -1.0, 1.0))
        else:
            visible_indices = np.array([], dtype=int)
            incidence_angles = np.array([], dtype=float)
            viewing_angles = np.array([], dtype=float)
        # Create statistics
        stats = VisibilityStats(
            geometric_visible=np.sum(geometric_visible),
            light_illuminated=np.sum(light_illuminated),
            reflection_good=np.sum(reflection_good),
            light_unoccluded=np.sum(light_unoccluded),
            final_visible=np.sum(final_visible_mask),
            total_patches=len(self.patch_positions),
            visible_area=np.sum(self.mesh.area_faces[final_visible_mask]),
            total_area=self.mesh.area,
            visible_indices=visible_indices,
            incidence_angles=incidence_angles,
            viewing_angles=viewing_angles
        )
        
        return final_visible_mask, stats