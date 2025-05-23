import numpy as np
from scipy.spatial.transform import Rotation as R
def ray_intersects_triangle(orig, dir, v0, v1, v2, eps=1e-6):

    edge1 = v1 - v0
    edge2 = v2 - v0
    h = np.cross(dir, edge2)
    a = np.dot(edge1, h)
    if -eps < a < eps:
        return False
    f = 1.0 / a
    s = orig - v0
    u = f * np.dot(s, h)
    if not (0.0 <= u <= 1.0):
        return False
    q = np.cross(s, edge1)
    v = f * np.dot(dir, q)
    if not (0.0 <= v <= 1.0 - u):
        return False
    t = f * np.dot(edge2, q)
    if t > eps:
        return True
    else:
        return False

def compute_visibility_with_occlusion(patch_positions, patch_normals, station_positions, triangles, fov_angle):

    N, M = len(patch_positions), len(station_positions)
    C = np.zeros((N, M), dtype=bool)
    cos_fov = np.cos(fov_angle)

    for j in range(M):
        s = station_positions[j]
        for i in range(N):
            p = patch_positions[i]
            n = patch_normals[i]
            dir_vec = p - s
            dist = np.linalg.norm(dir_vec)
            dir_unit = dir_vec / dist

            cos_angle = np.dot(n, dir_unit)
            if cos_angle <= 0 or cos_angle < cos_fov:
                continue 


            occluded = False
            for tri in triangles:
                if ray_intersects_triangle(s, dir_unit, tri[0], tri[1], tri[2]):
            
                    if np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) > 1e-12:  
                        inter_pt = s + dir_unit * np.dot(tri[0] - s, dir_unit)
                        if np.linalg.norm(inter_pt - s) < dist - 1e-3:
                            occluded = True
                            break
            if not occluded:
                C[i, j] = True
    return C
def simulate_observable_area(patch_positions, patch_normals, triangles,
                             station_positions, rotation_axis, rotation_period,
                             fov_angle_deg, num_steps=36):
    """
    Simulate asteroid rotation and compute observable facets for each station.

    Parameters:
    - patch_positions: (N, 3) array of triangle centroids.
    - patch_normals:   (N, 3) array of triangle normals.
    - triangles:       (T, 3, 3) array of triangle vertices.
    - station_positions: (M, 3) array of station coords (in asteroid body frame).
    - rotation_axis:   (3,) unit vector of asteroid rotation axis.
    - rotation_period: rotation period (same units as time step).
    - fov_angle_deg:   camera half FOV in degrees.
    - num_steps:       number of rotation samples over one period.

    Returns:
    - visibility_fraction: (N,) fraction of rotation period each patch is visible.
    """
    # Precompute rotation angles
    angles = np.linspace(0, 360, num_steps, endpoint=False)
    fov_rad = np.deg2rad(fov_angle_deg)
    visibility_counts = np.zeros(patch_positions.shape[0], dtype=int)
    
    # For each time step
    for angle in angles:
        # Rotate mesh
        rot = R.from_rotvec(np.deg2rad(angle) * rotation_axis)
        pos_rot = rot.apply(patch_positions)
        norm_rot = rot.apply(patch_normals)
        
        # Compute visibility with occlusion for each station
        C = compute_visibility_with_occlusion(
            pos_rot, norm_rot, station_positions, triangles, fov_rad
        )
        # Count facets visible by any station
        visible = np.any(C, axis=1)
        visibility_counts += visible.astype(int)
    
    # Fraction of time visible
    visibility_fraction = visibility_counts / num_steps
    return visibility_fraction

# Example usage:
visibility_frac = simulate_observable_area(
    patch_positions, patch_normals, triangles,
    station_positions, rotation_axis=np.array([0,0,1]),
    rotation_period=1.0, fov_angle_deg=60, num_steps=36
)
# Now visibility_frac[i] gives the fraction of rotation period patch i is visible.

