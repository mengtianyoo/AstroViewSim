import numpy as np
import os

from MeshProcessor import MeshProcessor
from Visualizer import Visualizer
from VisibilityAnalyzer import VisibilityAnalyzer

# def main():
#     """Main execution function demonstrating usage."""

#     file_path = 'model/itokawa_f0049152.obj'
#     theta = 0   # Camera angle
#     beta  = 0   # Sun angle


#     camera_distance = 600
 
#     print("Loading and processing mesh...")
#     mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
#     print(f"Loaded mesh with {len(patch_positions)} patches")
#     print(f"Mesh bounding box extent: {mesh.bounding_box.extents}")

#     camera_pos = np.array([
#         camera_distance * np.cos(np.deg2rad(theta)), 
#         camera_distance * np.sin(np.deg2rad(theta)), 
#         0.0
#     ])
#     sun_direction = np.array([
#         np.cos(np.deg2rad(beta)), 
#         np.sin(np.deg2rad(beta)), 
#         0.0
#     ])
#     sun_direction = sun_direction / np.linalg.norm(sun_direction)
    
#     print("\nPerforming visibility analysis...")
#     analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
    
#     visibility_mask, stats = analyzer.analyze_visibility(
#         camera_pos=camera_pos,
#         sun_direction=sun_direction,
#         fov_x_deg=2.0,
#         fov_y_deg=2.0,
#         max_viewing_angle_deg=60.0,
#         max_sun_angle_deg=90.0,
#         max_reflection_angle_deg=100.0
#     )
    
#     output_dir = "visibility_results"
#     os.makedirs(output_dir, exist_ok=True)
#     output_file = os.path.join(output_dir, f"visibility_analysis_{theta}_{beta}.txt")
    
#     stats.print_summary(output_file)
#     print(f"\nResults have been saved to: {output_file}")

#     print("\nGenerating visualization...")
#     Visualizer.plot_visibility_results(
#         patch_positions, visibility_mask, camera_pos
#     )

def main():
    """Main execution function demonstrating usage."""
    file_path = 'model/itokawa_f0049152.obj'
    beta = 0  # Sun angle fixed
    camera_distance = 600
    
    print("Loading and processing mesh...")
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    print(f"Loaded mesh with {len(patch_positions)} patches")
    print(f"Mesh bounding box extent: {mesh.bounding_box.extents}")

    sun_direction = np.array([
        np.cos(np.deg2rad(beta)), 
        np.sin(np.deg2rad(beta)), 
        0.0
    ])
    sun_direction = sun_direction / np.linalg.norm(sun_direction)
    
    analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
    
    combined_visibility_mask = np.zeros_like(patch_positions[:,0], dtype=bool)
    
    for i in range(37):  # 0° to 360° in 10°
        theta = i * 10
        print(f"\nProcessing camera angle: {theta}°")
        
        camera_pos = np.array([
            camera_distance * np.cos(np.deg2rad(theta)), 
            camera_distance * np.sin(np.deg2rad(theta)), 
            0.0
        ])
        
        visibility_mask, stats = analyzer.analyze_visibility(
            camera_pos=camera_pos,
            sun_direction=sun_direction,
            fov_x_deg=2.0,
            fov_y_deg=2.0,
            max_viewing_angle_deg=60.0,
            max_sun_angle_deg=90.0,
            max_reflection_angle_deg=100.0
        )

        combined_visibility_mask = combined_visibility_mask | visibility_mask
  
        output_dir = f"visibility_results/sun_angle_{beta:03d}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"visibility_analysis_angle_{theta:03d}.txt")
        
        stats.print_summary(output_file)
        
        Visualizer.plot_visibility_results(
            patch_positions, visibility_mask, camera_pos, isshow=False,
            save_path=os.path.join(output_dir, f"visibility_plot_angle_{theta:03d}.png")
        )

    print("\nGenerating combined results...")
    #--------- base on the number of the visible patches
    visible_patches = np.sum(combined_visibility_mask)
    total_patches = len(patch_positions)
    num_coverage_percentage = (visible_patches / total_patches) * 100
    #--------- base on the area of the visible patches
    visible_area = np.sum(mesh.area_faces[combined_visibility_mask])
    total_area = mesh.area
    area_coverage_percentage = (visible_area / total_area) * 100




    
    # combined_output_dir = f"visibility_results/sun_angle_{beta:03d}"
    # os.makedirs(combined_output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "combined_stats.txt"), "w") as f:
        f.write(f"Total patches: {total_patches}\n")
        f.write(f"Visible patches from all angles: {visible_patches}\n")
        f.write(f"Coverage percentage: {num_coverage_percentage:.2f}%\n")
        f.write(f"Total area: {total_area:.2f}\n")
        f.write(f"Visible area: {visible_area:.2f}\n")
        f.write(f"Area coverage percentage: {area_coverage_percentage:.2f}%\n")

    
    print("\nGenerating combined visualization...")
    Visualizer.export_ply(mesh, combined_visibility_mask, output_dir)
    # Visualizer.plot_visibility_results(
    #     patch_positions, combined_visibility_mask, camera_pos, isshow=False,
    #     save_path=os.path.join(output_dir, "combined_visibility_plot.png")
    # )
    
    print(f"\nAll results have been saved to the visibility_results directory")


if __name__ == "__main__":
    main()