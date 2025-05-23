import numpy as np
from dataclasses import dataclass


@dataclass
class VisibilityStats:
    """Data class to hold visibility analysis statistics."""
    geometric_visible: int
    light_illuminated: int
    reflection_good: int
    light_unoccluded: int
    final_visible: int
    total_patches: int
    visible_indices: np.ndarray
    incidence_angles: np.ndarray
    viewing_angles: np.ndarray
    
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
            
            # 新增：打印详细信息
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