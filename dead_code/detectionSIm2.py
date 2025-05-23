import trimesh
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def load_and_process_mesh(file_path: str):
    """
    Load an OBJ mesh and extract triangle centroids and normals.

    Parameters:
        file_path: str
            Path to the .obj mesh file.

    Returns:
        patch_positions: np.ndarray, shape (T,3)
            Centroids of each triangular patch.
        patch_normals: np.ndarray, shape (T,3)
            Unit normal vectors of each triangular patch.
    """
    mesh = trimesh.load(file_path, force='mesh')

    # 如果不是三角网格或网格不闭合，就细分一次
    if not mesh.is_watertight or mesh.faces.shape[1] != 3:
        mesh = mesh.subdivide()

    vertices = mesh.vertices        # (V,3)
    faces = mesh.faces              # (F,3)

    # 对每个面拿到三个顶点坐标，组合成 (F,3,3)
    triangles = vertices[faces]
    # 质心
    patch_positions = np.mean(triangles, axis=1)

    # 计算面法向量
    v1 = triangles[:, 1] - triangles[:, 0]
    v2 = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(v1, v2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    patch_normals = normals / np.maximum(norms, 1e-8)

    return patch_positions, patch_normals

def count_visible_patches(centers, normals, camera_pos, light_dir, inc_thresh_deg, view_thresh_deg):
    """
    计算在给定相机位置和光照条件下，可见（三角面片）的数量。

    Parameters:
        centers: np.ndarray (T,3)
            面片质心坐标。
        normals: np.ndarray (T,3)
            面片单位法向量。
        camera_pos: np.ndarray (3,)
            相机位置坐标。
        light_dir: np.ndarray (3,)
            太阳光方向向量（从太阳指向原点）。
        inc_thresh_deg: float
            漫反射入射角阈值（度），即 n·s >= cos(inc_thresh)。
        view_thresh_deg: float
            视角阈值（度），即 n·v >= cos(view_thresh)。

    Returns:
        count: int
            满足可见条件的面片数量。
    """
    # 确保单位化
    s = light_dir / np.linalg.norm(light_dir)

    # 入射角 cosα = n · s
    cos_inc = normals.dot(s)

    # 视线向量 v_i
    vs = camera_pos[None, :] - centers  # (T,3)
    vs_norm = vs / np.linalg.norm(vs, axis=1, keepdims=True)

    # 视角 cosβ = n · v
    cos_view = np.einsum('ij,ij->i', normals, vs_norm)

    # 阈值比较
    inc_mask  = cos_inc  >= np.cos(np.deg2rad(inc_thresh_deg))
    view_mask = cos_view >= np.cos(np.deg2rad(view_thresh_deg))

    visible_mask = inc_mask & view_mask
    return np.count_nonzero(visible_mask)

def main():
    # —— 参数设置 —— #
    mesh_file    = 'bennu.obj'            # OBJ 文件路径
    radius       = 600.0                  # 相机轨道半径 (m)
    inc_thresh   = 90.0                   # 光照角阈值 (°)
    view_thresh  = 1.0                    # 相机视角阈值 (°)
    angle_step   = 10                     # 每隔多少度拍一次

    # 太阳光方向：x 轴正方向指向太阳，所以光线方向为 (-1,0,0)
    light_dir = np.array([-1.0, 0.0, 0.0])

    # 加载网格并提取面片质心、法向量
    centers, normals = load_and_process_mesh(mesh_file)
    print(f"Loaded mesh: {len(centers)} patches")

    # 遍历角度，统计可见面片数量
    angles = np.arange(0, 360, angle_step)
    counts = []

    for theta in angles:
        rad = np.deg2rad(theta)
        cam_pos = radius * np.array([np.cos(rad), np.sin(rad), 0.0])
        cnt = count_visible_patches(centers, normals, cam_pos, light_dir,
                                    inc_thresh, view_thresh)
        counts.append(cnt)
        print(f"Angle {theta:3.0f}°: {cnt} visible patches")

    # —— 3D 可视化 —— #
    fig = plt.figure(figsize=(8,6))
    ax = fig.add_subplot(111, projection='3d')
    xs = radius * np.cos(np.deg2rad(angles))
    ys = radius * np.sin(np.deg2rad(angles))
    zs = counts

    sc = ax.scatter(xs, ys, zs, c=zs, cmap='viridis')
    ax.plot(xs, ys, zs, linestyle='--', alpha=0.5)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Visible Patch Count')
    ax.set_title('每10°相机位置的可见面片数量')
    fig.colorbar(sc, label='Visible Count')
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
