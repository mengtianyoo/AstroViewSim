import trimesh
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class VisibilityStats:
    """Data class to hold visibility analysis statistics."""
    geometric_visible: int
    light_illuminated: int
    reflection_good: int
    light_unoccluded: int
    final_visible: int
    total_patches: int
    
    def print_summary(self):
        """Print a formatted summary of visibility statistics."""
        print("=== Visibility Analysis Summary ===")
        print(f"Total patches: {self.total_patches}")
        print(f"Geometric visible: {self.geometric_visible} "
              f"({self.geometric_visible/self.total_patches*100:.1f}%)")
        
        if self.geometric_visible > 0:
            geo_base = self.geometric_visible
            print(f"Light illuminated: {self.light_illuminated} "
                  f"({self.light_illuminated/geo_base*100:.1f}% of geometric)")
            print(f"Reflection conditions met: {self.reflection_good} "
                  f"({self.reflection_good/geo_base*100:.1f}% of geometric)")
            print(f"Light unoccluded: {self.light_unoccluded} "
                  f"({self.light_unoccluded/geo_base*100:.1f}% of geometric)")
        
        print(f"Final visible: {self.final_visible} "
              f"({self.final_visible/self.total_patches*100:.1f}% of total)")


class MeshProcessor:
    """Handles mesh loading and processing operations."""
    
    @staticmethod
    def load_and_process_mesh(file_path: str, scale_factor: float = 0.1) -> Tuple[trimesh.Trimesh, np.ndarray, np.ndarray]:
        """
        Load .obj mesh and extract patch centroids and normals.
        
        Args:
            file_path: Path to the .obj file
            scale_factor: Scale factor to apply to the mesh
            
        Returns:
            Tuple of (mesh, patch_positions, patch_normals)
        """
        mesh = trimesh.load(file_path, force='mesh')
        mesh.apply_scale(scale_factor)
        
        # Ensure mesh is proper triangular mesh
        if not mesh.is_watertight or mesh.faces.shape[1] != 3:
            mesh = mesh.subdivide()

        vertices = mesh.vertices
        faces = mesh.faces
        triangles = vertices[faces]
        
        # Calculate patch centroids
        patch_positions = np.mean(triangles, axis=1)
        
        # Calculate patch normals
        v1 = triangles[:, 1] - triangles[:, 0]
        v2 = triangles[:, 2] - triangles[:, 0]
        normals = np.cross(v1, v2)
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        patch_normals = normals / np.maximum(norms, 1e-8)

        return mesh, patch_positions, patch_normals


class GeometricVisibility:
    """Handles geometric visibility calculations."""
    
    @staticmethod
    def check_fov_visibility(patch_positions: np.ndarray,
                           patch_normals: np.ndarray,
                           camera_pos: np.ndarray,
                           target: np.ndarray = None,
                           fov_x_deg: float = 2.0,
                           fov_y_deg: float = 2.0,
                           max_angle_deg: float = 45.0) -> np.ndarray:
        """
        Check visibility within field of view with angle constraints.
        
        Returns:
            Boolean mask indicating visible patches
        """
        if target is None:
            target = np.zeros(3)
            
        # Build camera coordinate system
        z_cam = (target - camera_pos)
        z_cam = z_cam / np.linalg.norm(z_cam)
        world_up = np.array([0, 0, 1], dtype=float)
        x_cam = np.cross(z_cam, world_up)
        x_cam /= np.linalg.norm(x_cam)
        y_cam = np.cross(x_cam, z_cam)

        view_vectors = patch_positions - camera_pos[None, :]
        z_coords = view_vectors.dot(z_cam)
        
        # Check if patches are in front of camera
        in_front = z_coords > 0

        # Check if patches face the camera
        view_distances = np.linalg.norm(view_vectors, axis=1, keepdims=True)
        view_directions = view_vectors / view_distances
        dot_products = np.einsum('ij,ij->i', patch_normals, view_directions)
        facing_camera = dot_products < 0
        
        # Check angle constraint
        cos_max_angle = np.cos(np.deg2rad(max_angle_deg))
        good_viewing_angle = dot_products <= -cos_max_angle

        # Check field of view constraints
        x_coords = view_vectors.dot(x_cam)
        y_coords = view_vectors.dot(y_cam)
        
        tan_x = np.abs(x_coords / z_coords)
        tan_y = np.abs(y_coords / z_coords)
        
        tan_fov_x_half = np.tan(np.deg2rad(fov_x_deg / 2))
        tan_fov_y_half = np.tan(np.deg2rad(fov_y_deg / 2))
        
        within_fov_x = tan_x <= tan_fov_x_half
        within_fov_y = tan_y <= tan_fov_y_half

        visible_mask = (in_front & 
                       facing_camera & 
                       good_viewing_angle & 
                       within_fov_x & 
                       within_fov_y)
        
        return visible_mask

    @staticmethod
    def filter_occluded_patches(mesh: trimesh.Trimesh,
                              patch_positions: np.ndarray,
                              camera_pos: np.ndarray,
                              candidate_mask: np.ndarray) -> np.ndarray:
        """
        Filter out occluded patches using ray casting.
        
        Returns:
            Updated visibility mask with occlusion filtering
        """
        visible_mask = candidate_mask.copy()
        
        if not np.any(candidate_mask):
            return visible_mask
        
        candidate_positions = patch_positions[candidate_mask]
        n_candidates = len(candidate_positions)

        ray_origins = np.repeat(camera_pos[None, :], n_candidates, axis=0)
        ray_directions = candidate_positions - camera_pos[None, :]
        ray_distances = np.linalg.norm(ray_directions, axis=1)
        ray_directions = ray_directions / ray_distances[:, None]
        
        # Get all ray-mesh intersections
        locations, index_ray, index_tri = mesh.ray.intersects_location(
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
            
            # Check for closer intersections (with tolerance)
            tolerance = target_distance * 1e-6 + 1e-8
            closer_intersections = ray_intersect_distances < (target_distance - tolerance)
            
            if np.any(closer_intersections):
                is_occluded[i] = True
        
        visible_mask[candidate_mask] = ~is_occluded
        return visible_mask


class LightingAnalysis:
    """Handles lighting and reflection analysis."""
    
    @staticmethod
    def check_sun_illumination(patch_normals: np.ndarray,
                             sun_direction: np.ndarray,
                             max_sun_angle_deg: float = 60.0) -> np.ndarray:
        """Check if patches are properly illuminated by sun."""
        dot_products = np.dot(patch_normals, sun_direction)
        facing_sun = dot_products > 0
        
        cos_max_angle = np.cos(np.deg2rad(max_sun_angle_deg))
        good_sun_angle = dot_products >= cos_max_angle
        
        return facing_sun & good_sun_angle

    @staticmethod
    def check_reflection_conditions(patch_positions: np.ndarray,
                                  patch_normals: np.ndarray,
                                  camera_pos: np.ndarray,
                                  sun_direction: np.ndarray,
                                  max_reflection_angle_deg: float = 30.0) -> np.ndarray:
        """Check if reflection conditions are met for specular reflection."""
        view_directions = camera_pos[None, :] - patch_positions
        view_directions = view_directions / np.linalg.norm(view_directions, axis=1, keepdims=True)
        
        # Calculate reflection direction: R = 2 * (N · L) * N - L
        dot_nl = np.dot(patch_normals, sun_direction)
        reflection_directions = (2 * dot_nl[:, None] * patch_normals - 
                               sun_direction[None, :])
        reflection_directions = (reflection_directions / 
                               np.linalg.norm(reflection_directions, axis=1, keepdims=True))

        dot_rv = np.einsum('ij,ij->i', reflection_directions, view_directions)
        
        cos_max_angle = np.cos(np.deg2rad(max_reflection_angle_deg))
        good_reflection = dot_rv >= cos_max_angle
        
        return good_reflection

    @staticmethod
    def filter_sun_occluded(mesh: trimesh.Trimesh,
                          patch_positions: np.ndarray,
                          candidate_mask: np.ndarray,
                          sun_direction: np.ndarray) -> np.ndarray:
        """Filter patches that are occluded from sunlight."""
        illuminated_mask = candidate_mask.copy()
        if not np.any(candidate_mask):
            return illuminated_mask

        sun_direction = sun_direction / np.linalg.norm(sun_direction)
        candidate_positions = patch_positions[candidate_mask]
        n_candidates = len(candidate_positions)

        # Cast rays from sun direction to patches
        ray_origins = candidate_positions - sun_direction * 1e-2  # Avoid self-intersection
        ray_directions = np.tile(sun_direction, (n_candidates, 1))

        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=ray_origins,
            ray_directions=ray_directions
        )

        is_shadowed = np.zeros(n_candidates, dtype=bool)

        for i in range(n_candidates):
            ray_mask = index_ray == i
            if not np.any(ray_mask):
                continue

            ray_locs = locations[ray_mask]
            patch_pos = candidate_positions[i]
            dists = np.linalg.norm(ray_locs - ray_origins[i], axis=1)

            actual_dist = np.linalg.norm(patch_pos - ray_origins[i])
            tolerance = actual_dist * 1e-6 + 1e-8
            if np.any(dists < (actual_dist - tolerance)):
                is_shadowed[i] = True

        illuminated_mask[candidate_mask] = ~is_shadowed
        return illuminated_mask


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
        
        Returns:
            Tuple of (final_visibility_mask, visibility_stats)
        """
        if target is None:
            target = np.zeros(3)
            
        # Step 1: Geometric visibility
        geometric_visible = GeometricVisibility.check_fov_visibility(
            self.patch_positions, self.patch_normals, camera_pos, target,
            fov_x_deg, fov_y_deg, max_viewing_angle_deg
        )
        
        # Step 2: Occlusion filtering
        unoccluded_mask = GeometricVisibility.filter_occluded_patches(
            self.mesh, self.patch_positions, camera_pos, geometric_visible
        )
        
        # Step 3: Lighting analysis on geometrically visible patches
        candidate_indices = np.where(unoccluded_mask)[0]
        if len(candidate_indices) == 0:
            empty_stats = VisibilityStats(0, 0, 0, 0, 0, len(self.patch_positions))
            return np.zeros_like(geometric_visible), empty_stats
            
        candidate_positions = self.patch_positions[candidate_indices]
        candidate_normals = self.patch_normals[candidate_indices]
        
        # Check lighting conditions
        light_illuminated = LightingAnalysis.check_sun_illumination(
            candidate_normals, sun_direction, max_sun_angle_deg
        )
        
        reflection_good = LightingAnalysis.check_reflection_conditions(
            candidate_positions, candidate_normals, camera_pos, 
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
        
        # Create statistics
        stats = VisibilityStats(
            geometric_visible=np.sum(geometric_visible),
            light_illuminated=np.sum(light_illuminated),
            reflection_good=np.sum(reflection_good),
            light_unoccluded=np.sum(light_unoccluded),
            final_visible=np.sum(final_visible_mask),
            total_patches=len(self.patch_positions)
        )
        
        return final_visible_mask, stats


class Visualizer:
    """Handles visualization of results."""
    
    @staticmethod
    def plot_visibility_results(patch_positions: np.ndarray,
                              visibility_mask: np.ndarray,
                              camera_pos: np.ndarray = None,
                              figsize: Tuple[int, int] = (16, 8)):
        """Plot visibility analysis results in 3D."""
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        # Plot invisible patches in gray
        ax.scatter(patch_positions[~visibility_mask, 0],
                  patch_positions[~visibility_mask, 1],
                  patch_positions[~visibility_mask, 2],
                  s=1, alpha=0.2, color='gray', label='Not visible')
        
        # Plot visible patches in red
        ax.scatter(patch_positions[visibility_mask, 0],
                  patch_positions[visibility_mask, 1],
                  patch_positions[visibility_mask, 2],
                  s=2, alpha=0.8, color='red', label='Visible')
        
        # Plot camera position if provided
        if camera_pos is not None:
            ax.scatter([camera_pos[0]], [camera_pos[1]], [camera_pos[2]],
                      color='blue', s=50, label='Camera')

        # Set equal aspect ratio
        Visualizer._set_axes_equal(ax, patch_positions)
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.legend()
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def _set_axes_equal(ax, positions: np.ndarray):
        """Set equal aspect ratio for 3D plot."""
        x_min, x_max = positions[:, 0].min(), positions[:, 0].max()
        y_min, y_max = positions[:, 1].min(), positions[:, 1].max()
        z_min, z_max = positions[:, 2].min(), positions[:, 2].max()
        
        x_range = x_max - x_min
        y_range = y_max - y_min
        z_range = z_max - z_min
        max_range = max(x_range, y_range, z_range)

        x_middle = (x_max + x_min) / 2
        y_middle = (y_max + y_min) / 2
        z_middle = (z_max + z_min) / 2

        ax.set_xlim(x_middle - max_range/2, x_middle + max_range/2)
        ax.set_ylim(y_middle - max_range/2, y_middle + max_range/2)
        ax.set_zlim(z_middle - max_range/2, z_middle + max_range/2)


def main():
    """Main execution function demonstrating usage."""
    # Configuration
    file_path = 'itokawa_f0049152.obj'  # Update path as needed
    theta = -np.pi / 4 * 0  # Camera angle
    camera_distance = 600
    
    # Load and process mesh
    print("Loading and processing mesh...")
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    print(f"Loaded mesh with {len(patch_positions)} patches")
    print(f"Mesh bounding box extent: {mesh.bounding_box.extents}")
    
    # Set up camera and sun positions
    camera_pos = np.array([
        camera_distance * np.cos(theta), 
        camera_distance * np.sin(theta), 
        0.0
    ])
    sun_direction = np.array([np.cos(theta), np.sin(theta), 0.0])
    sun_direction = sun_direction / np.linalg.norm(sun_direction)
    
    # Create analyzer and run analysis
    print("\nPerforming visibility analysis...")
    analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
    
    visibility_mask, stats = analyzer.analyze_visibility(
        camera_pos=camera_pos,
        sun_direction=sun_direction,
        fov_x_deg=2.0,
        fov_y_deg=2.0,
        max_viewing_angle_deg=60.0,
        max_sun_angle_deg=90.0,
        max_reflection_angle_deg=150.0
    )
    
    # Print results
    stats.print_summary()
    
    # Visualize results
    print("\nGenerating visualization...")
    Visualizer.plot_visibility_results(
        patch_positions, visibility_mask, camera_pos
    )

if __name__ == "__main__":
    main()