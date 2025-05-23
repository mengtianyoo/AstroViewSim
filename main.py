import numpy as np
import os

from MeshProcessor import MeshProcessor
from Visualizer import Visualizer
from VisibilityAnalyzer import VisibilityAnalyzer

def main():
    """Main execution function demonstrating usage."""

    file_path = 'model/itokawa_f0049152.obj'
    theta = 0   # Camera angle
    beta  = 0   # Sun angle


    camera_distance = 600
 
    print("Loading and processing mesh...")
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    print(f"Loaded mesh with {len(patch_positions)} patches")
    print(f"Mesh bounding box extent: {mesh.bounding_box.extents}")

    camera_pos = np.array([
        camera_distance * np.cos(np.deg2rad(theta)), 
        camera_distance * np.sin(np.deg2rad(theta)), 
        0.0
    ])
    sun_direction = np.array([
        np.cos(np.deg2rad(beta)), 
        np.sin(np.deg2rad(beta)), 
        0.0
    ])
    sun_direction = sun_direction / np.linalg.norm(sun_direction)
    
    print("\nPerforming visibility analysis...")
    analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
    
    visibility_mask, stats = analyzer.analyze_visibility(
        camera_pos=camera_pos,
        sun_direction=sun_direction,
        fov_x_deg=2.0,
        fov_y_deg=2.0,
        max_viewing_angle_deg=60.0,
        max_sun_angle_deg=90.0,
        min_reflection_angle_deg=100.0
    )
    
    output_dir = "visibility_results"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"visibility_analysis_{theta}_{beta}.txt")
    
    stats.print_summary(output_file)
    print(f"\nResults have been saved to: {output_file}")

    print("\nGenerating visualization...")
    Visualizer.plot_visibility_results(
        patch_positions, visibility_mask, camera_pos
    )

if __name__ == "__main__":
    main()