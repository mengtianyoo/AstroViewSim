import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple


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

        ax.scatter(patch_positions[~visibility_mask, 0],
                  patch_positions[~visibility_mask, 1],
                  patch_positions[~visibility_mask, 2],
                  s=1, alpha=0.2, color='gray', label='Not visible')

        ax.scatter(patch_positions[visibility_mask, 0],
                  patch_positions[visibility_mask, 1],
                  patch_positions[visibility_mask, 2],
                  s=2, alpha=0.8, color='red', label='Visible')

        if camera_pos is not None:
            ax.scatter([camera_pos[0]], [camera_pos[1]], [camera_pos[2]],
                      color='blue', s=50, label='Camera')

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