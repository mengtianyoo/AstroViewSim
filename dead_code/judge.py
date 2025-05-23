import trimesh
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 加载和处理网格模型
def load_and_process_mesh(file_path: str):
    """加载3D模型并处理成面片数据"""
    mesh = trimesh.load(file_path, force='mesh')
    if not mesh.is_watertight or mesh.faces.shape[1] != 3:
        mesh = mesh.subdivide()  # 如果不是三角面或不封闭，进行细分
    vertices = mesh.vertices
    faces = mesh.faces
    triangles = vertices[faces]
    patch_positions = np.mean(triangles, axis=1)  # 每个三角面片的中心位置
    v1 = triangles[:, 1] - triangles[:, 0]
    v2 = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(v1, v2)  # 计算法向量
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    patch_normals = normals / np.maximum(norms, 1e-8)  # 归一化法向量
    return patch_positions, patch_normals

# 计算镜面反射方向
def compute_reflection(light_dir, normal):
    """计算光线在面片上的镜面反射方向"""
    light_dir = light_dir / np.linalg.norm(light_dir)
    normal = normal / np.linalg.norm(normal)
    return 2 * np.dot(light_dir, normal) * normal - light_dir

# 判断面片是否可见
def is_patch_visible(patch_pos, patch_normal, cam_pos, light_dir, 
                     illum_threshold=90, view_threshold=90, reflect_threshold=5):
    """根据光照、相机视线和反射角度判断面片是否可见"""
    # 相机视线方向
    to_cam = cam_pos - patch_pos
    cam_dir = to_cam / np.linalg.norm(to_cam)
    
    # 光照角度（入射光与法向量的夹角）
    # cos_illum = np.dot(light_dir, patch_normal)
    # if cos_illum <= 0:  # 未被照亮
    #     return False
    # illum_angle = np.rad2deg(np.arccos(cos_illum))
    # if illum_angle > illum_threshold:
    #     return False
    
    # # 相机拍摄角度（视线与法向量的夹角）
    # cos_view = np.dot(cam_dir, patch_normal)
    # if cos_view <= 0:  # 未面向相机
    #     return False
    # view_angle = np.rad2deg(np.arccos(cos_view))
    # if view_angle > view_threshold:
    #     return False
    
    # # 反射光线与相机视线的夹角
    # reflect_dir = compute_reflection(light_dir, patch_normal)
    # cos_reflect = np.dot(reflect_dir, cam_dir)
    # reflect_angle = np.rad2deg(np.arccos(max(min(cos_reflect, 1.0), -1.0)))
    # if reflect_angle > reflect_threshold:
    #     return False
    
    return True

# 可视化所有可见面片
def visualize_all_visible_patches(patch_positions, all_visible_indices, title):
    """在3D中可视化所有曾经可见的面片"""
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    # 绘制所有面片（灰色，半透明）
    ax.scatter(patch_positions[:, 0], patch_positions[:, 1], patch_positions[:, 2], 
               c='gray', alpha=0.1, s=1)
    
    # 绘制所有可见面片（红色）
    visible_positions = patch_positions[all_visible_indices]
    ax.scatter(visible_positions[:, 0], visible_positions[:, 1], visible_positions[:, 2], 
               c='red', s=5)
    
    # 设置坐标轴标签和标题
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title(title)
    plt.show()

# 主程序
def main():
    # 加载模型
    file_path = 'bennu.obj'  # 替换为你的模型文件路径
    patch_positions, patch_normals = load_and_process_mesh(file_path)

    # 参数设置
    distance = 600  # 相机距离原点的距离（单位：米）
    light_dir = np.array([1, 0, 0])  # 光源方向（沿X轴）
    illum_threshold = 90  # 光照角度阈值（度）
    view_threshold = 90  # 相机拍摄角度阈值（度）
    reflect_threshold = 5  # 反射角度阈值（度）

    # 每10度拍摄一次，绕模型旋转360度
    all_visible_indices_set = set()  # 使用集合去重
    for theta_deg in range(0, 360, 10):
        theta_rad = np.deg2rad(theta_deg)
        cam_pos = distance * np.array([np.cos(theta_rad), np.sin(theta_rad), 0])
        
        # 检查每个面片的可见性
        for i in range(len(patch_positions)):
            if is_patch_visible(patch_positions[i], patch_normals[i], cam_pos, light_dir,
                               illum_threshold, view_threshold, reflect_threshold):
                all_visible_indices_set.add(i)
    
    # 转换为列表
    all_visible_indices = list(all_visible_indices_set)
    
    # 可视化所有可见面片
    visualize_all_visible_patches(patch_positions, all_visible_indices, 
                                  '所有可见面片（360°旋转）')

if __name__ == "__main__":
    main()