import trimesh
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def load_and_process_mesh(file_path: str):
    """
    Load an .obj mesh, and extract triangle centroids and normals.

    Parameters:
    - file_path: Path to the .obj file

    Returns:
    - patch_positions: (T, 3) numpy array of triangle centroids
    - patch_normals:   (T, 3) numpy array of unit normals for each triangle
    """
   
    mesh = trimesh.load(file_path, force='mesh')

    if not mesh.is_watertight or mesh.faces.shape[1] != 3:
        mesh = mesh.subdivide()

    vertices = mesh.vertices  
    faces = mesh.faces        

    triangles = vertices[faces]  
    patch_positions = np.mean(triangles, axis=1) 

    v1 = triangles[:, 1] - triangles[:, 0]
    v2 = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(v1, v2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    patch_normals = normals / np.maximum(norms, 1e-8)

    return patch_positions, patch_normals
# 可视化

def plot_patches(centers, normals):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.quiver(centers[:, 0], centers[:, 1], centers[:, 2],
              normals[:, 0], normals[:, 1], normals[:, 2],
              length=0.1, normalize=True)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.show()


file_path = 'bennu.obj'
centers, normals = load_and_process_mesh(file_path)
# 保存为文本文件
# output_file = 'patches.txt'
# with open(output_file, 'w') as f:
#     for pos, norm in zip(centers, normals):
#         f.write(f"{pos[0]} {pos[1]} {pos[2]} {norm[0]} {norm[1]} {norm[2]}\n")
# print(f"Saved {len(centers)} patches to {output_file}")
#plot_patches(centers, normals)

