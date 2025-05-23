import trimesh
import numpy as np


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
                                  min_reflection_angle_deg: float = 30.0) -> np.ndarray:
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
        
        cos_max_angle = np.cos(np.deg2rad(min_reflection_angle_deg))
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