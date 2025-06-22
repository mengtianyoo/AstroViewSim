import numpy as np
import os

from MeshProcessor import MeshProcessor
from Visualizer import Visualizer
from VisibilityAnalyzer import VisibilityAnalyzer
from config import VisibilityConfig as cfg


def main():
    """Main execution function demonstrating usage."""
    file_path = cfg.MODEL_PATH
    camera_distance = cfg.CAMERA_DISTANCE
    sun_theta = cfg.SUN_theta_ANGLE
    sun_phi = cfg.SUN_phi_ANGLE
    camera_theta = cfg.CAMERA_theta_ANGLE
    camera_phi = cfg.CAMERA_phi_ANGLE
    beta = camera_phi - sun_phi


    print("Loading and processing mesh...")
    mesh, patch_positions, patch_normals = MeshProcessor.load_and_process_mesh(file_path)
    print(f"Loaded mesh with {len(patch_positions)} patches")
    print(f"Mesh bounding box extent: {mesh.bounding_box.extents}")


    base_camera_pos = np.array([
        camera_distance * np.cos(np.deg2rad(camera_phi)) * np.cos(np.deg2rad(camera_theta)),
        camera_distance * np.cos(np.deg2rad(camera_phi)) * np.sin(np.deg2rad(camera_theta)),
        camera_distance * np.sin(np.deg2rad(camera_phi))
    ])

    sun_direction = np.array([
        np.cos(np.deg2rad(sun_phi)) * np.cos(np.deg2rad(sun_theta)),
        np.cos(np.deg2rad(sun_phi)) * np.sin(np.deg2rad(sun_theta)),
        np.sin(np.deg2rad(sun_phi))
    ])
    sun_direction = sun_direction / np.linalg.norm(sun_direction)
    
    analyzer = VisibilityAnalyzer(mesh, patch_positions, patch_normals)
    
    combined_visibility_mask = np.zeros_like(patch_positions[:,0], dtype=bool)
    
    for i in range(37):  # 0° to 360° in 10°
        theta = i * 10
        print(f"\nProcessing camera angle: {theta}°")
        
        rotation_rad = np.deg2rad(theta)
        rotation_matrix = np.array([
            [np.cos(rotation_rad), -np.sin(rotation_rad), 0],
            [np.sin(rotation_rad),  np.cos(rotation_rad), 0],
            [0,                    0,                   1]
        ])
        camera_pos = rotation_matrix @ base_camera_pos
        sun_direction_base = rotation_matrix @ sun_direction
        visibility_mask, stats = analyzer.analyze_visibility(
            camera_pos=camera_pos,
            sun_direction=sun_direction_base,
            fov_x_deg=2.0,
            fov_y_deg=2.0,
            max_viewing_angle_deg=60.0,
            max_sun_angle_deg=90.0,
            max_reflection_angle_deg=100.0
        )

        combined_visibility_mask = combined_visibility_mask | visibility_mask
        
  
        output_dir = f"visibility_results/sun_angle_{beta:03f}"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"visibility_analysis_angle_{theta:03f}.txt")
        
        stats.print_summary(output_file)
        Visualizer.export_ply(mesh, 
                              visibility_mask, 
                              output_dir, 
                              filename=f"visibility_angle_{theta:03f}.ply",
                              isshow=False)

        # Visualizer.plot_visibility_results(
        #     patch_positions, visibility_mask, camera_pos, isshow=False,
        #     save_path=os.path.join(output_dir, f"visibility_plot_angle_{theta:03f}.png")
        # )

    print("\nGenerating combined results...")
    #--------- base on the number of the visible patches
    visible_patches = np.sum(combined_visibility_mask)
    total_patches = len(patch_positions)
    num_coverage_percentage = (visible_patches / total_patches) * 100
    #--------- base on the area of the visible patches
    visible_area = np.sum(mesh.area_faces[combined_visibility_mask])
    total_area = mesh.area
    area_coverage_percentage = (visible_area / total_area) * 100

    with open(os.path.join(output_dir, "combined_stats.txt"), "w") as f:
        f.write(f"Total patches: {total_patches}\n")
        f.write(f"Visible patches from all angles: {visible_patches}\n")
        f.write(f"Coverage percentage: {num_coverage_percentage:.2f}%\n")
        f.write(f"Total area: {total_area:.2f}\n")
        f.write(f"Visible area: {visible_area:.2f}\n")
        f.write(f"Area coverage percentage: {area_coverage_percentage:.2f}%\n")

    
    print("\nGenerating combined visualization...")
    Visualizer.export_ply(mesh,
                            combined_visibility_mask, 
                            output_dir,
                            filename="combined_visibility.ply", 
                            isshow=True)

    
    print(f"\nAll results have been saved to the visibility_results directory")


if __name__ == "__main__":
    main()