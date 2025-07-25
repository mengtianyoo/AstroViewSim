import numpy as np
import os
import trimesh
import copy

class Visualizer:
    """Handles visualization of results."""
    @staticmethod
    def export_ply(mesh: trimesh.Trimesh,
                   visibility_mask: np.ndarray,
                   output_dir: str,
                   filename: str,
                   ishow: bool = False) -> None:
        colored_mesh = copy.deepcopy(mesh)

        colors = np.ones((len(mesh.faces), 4))  # 默认全白色
        colors[visibility_mask] = [1.0, 0.0, 0.0, 1.0]  # 红色
        colors[~visibility_mask] = [0.7, 0.7, 0.7, 1.0]  # 灰色
        colored_mesh.visual.face_colors = colors

        output_mesh_path = os.path.join(output_dir, filename)
        colored_mesh.export(output_mesh_path, file_type='ply')
        if ishow:
            colored_mesh.show()