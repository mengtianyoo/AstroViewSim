import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib import cm

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
def plot_visibility_map(mesh_file, station_positions, rotation_axis,
                        fov_deg=60, num_steps=36):

    mesh = trimesh.load(mesh_file, force='mesh')
    if mesh.faces.shape[1] != 3:
        mesh = mesh.subdivide()
    vertices = mesh.vertices
    faces = mesh.faces
    triangles = vertices[faces]
    
    patch_positions = triangles.mean(axis=1)
    v1 = triangles[:,1] - triangles[:,0]
    v2 = triangles[:,2] - triangles[:,0]
    normals = np.cross(v1, v2)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    
    # 莫拟
    visibility_counts = np.zeros(len(patch_positions), dtype=int)
    angles = np.linspace(0, 360, num_steps, endpoint=False)
    fov_rad = np.deg2rad(fov_deg)
    for angle in angles:
        rot = R.from_rotvec(np.deg2rad(angle) * rotation_axis)
        pos_rot = rot.apply(patch_positions)
        norm_rot = rot.apply(normals)
        C = compute_visibility_with_occlusion(pos_rot, norm_rot, station_positions, triangles, fov_rad)
        visibility_counts += np.any(C, axis=1)
    vis_frac = visibility_counts / num_steps
    
    # Color
    cmap = cm.viridis
    face_colors = cmap(vis_frac)
    
    # 可视化
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    mesh_collection = Poly3DCollection(triangles, facecolors=face_colors, linewidths=0.1)
    ax.add_collection3d(mesh_collection)
    ax.auto_scale_xyz(vertices[:,0], vertices[:,1], vertices[:,2])
    ax.set_axis_off()
    plt.title('bennu Visibility Fraction')
    plt.show()

plot_visibility_map(
    'bennu.obj',
    np.array([[1000, 0, 0], [0, 1000, 0]]),
    np.array([0, 0, 1]),
    fov_deg=60,
    num_steps=36
)
