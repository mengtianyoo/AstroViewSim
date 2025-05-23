import trimesh
import numpy as np
from typing import Tuple


class MeshProcessor:
    """Handles mesh loading and processing operations."""
    
    @staticmethod
    def load_and_process_mesh(file_path: str, scale_factor: float = 0.1) -> Tuple[trimesh.Trimesh, np.ndarray, np.ndarray]:
        """
        Load .obj mesh and extract patch centroids and normals.
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
