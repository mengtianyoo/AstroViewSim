import numpy as np
from dataclasses import dataclass


@dataclass
class VisibilityStats:
    """Data class to hold visibility analysis statistics."""
    def __init__(self,
                    geometric_visible: int,
                    light_illuminated: int,
                    reflection_good: int,
                    light_unoccluded: int,
                    final_visible: int,
                    visible_indices: np.ndarray,
                    incidence_angles: np.ndarray,
                    viewing_angles: np.ndarray,
                    total_patches: int = 0,
                    visible_area: float = 0.0,
                    total_area: float = 0.0):
        self.geometric_visible = geometric_visible
        self.light_illuminated = light_illuminated
        self.reflection_good = reflection_good
        self.light_unoccluded = light_unoccluded
        self.final_visible = final_visible
        self.visible_indices = visible_indices
        self.incidence_angles = incidence_angles
        self.viewing_angles = viewing_angles
        self.total_patches = total_patches
        self.visible_area = visible_area
        self.total_area = total_area



    
    def print_summary(self, output_file: str = "visibility_results.txt"):
        with open(output_file, 'w') as f:
            f.write("=== Visibility Analysis Summary ===\n")
            f.write(f"Total patches: {self.total_patches}\n")
            f.write(f"Geometric visible: {self.geometric_visible} "
                f"({self.geometric_visible/self.total_patches*100:.1f}%)\n")
            
            if self.geometric_visible > 0:
                geo_base = self.geometric_visible
                f.write(f"Light illuminated: {self.light_illuminated} "
                    f"({self.light_illuminated/geo_base*100:.1f}% of geometric)\n")
                f.write(f"Reflection conditions met: {self.reflection_good} "
                    f"({self.reflection_good/geo_base*100:.1f}% of geometric)\n")
                f.write(f"Light unoccluded: {self.light_unoccluded} "
                    f"({self.light_unoccluded/geo_base*100:.1f}% of geometric)\n")
            
            f.write(f"Final visible: {self.final_visible} "
                f"({self.final_visible/self.total_patches*100:.1f}% of total)\n")
            f.write(f"Visible area: {self.visible_area:.2f} "
                f"({self.visible_area/self.total_area*100:.1f}% of total area)\n")
            # 打印详细信息
            if self.final_visible > 0:
                f.write("\n=== Detailed Visibility Information ===\n")
                f.write(f"{'Patch Index':^12} | {'Incidence Angle':^16} | {'Viewing Angle':^16}\n")
                f.write(f"{'-'*12:^12}-+-{'-'*16:^16}-+-{'-'*16:^16}\n")
                
                for idx, inc_ang, view_ang in zip(
                    self.visible_indices,
                    np.rad2deg(self.incidence_angles),
                    np.rad2deg(self.viewing_angles)
                ):
                    f.write(f"{idx:^12d} | {inc_ang:^16.2f} | {view_ang:^16.2f}\n")