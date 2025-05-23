import trimesh
import numpy as np

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