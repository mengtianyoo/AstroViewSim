import numpy as np
class PosGen:
    
    def generate_camera_positions_simple_hemisphere(distance=600,
                                              sun_direction=np.array([1, 0, 0]),
                                              phi_levels=9,
                                              theta_points_equator=16):
        """
        简化版本：生成面向太阳方向半球的相机位置
        使用简单的点积检验方法
        """
        positions = []

        phi_angles = np.linspace(-80, 80, phi_levels)
        
        for phi in phi_angles:

            cos_phi = np.cos(np.deg2rad(phi))
            theta_points = max(4, int(theta_points_equator * cos_phi))
            
            if theta_points % 2 != 0:
                theta_points += 1
                
            theta_angles = np.linspace(0, 360-360/theta_points, theta_points)
            
            for theta in theta_angles:
                pos_unit = np.array([
                    np.cos(np.deg2rad(phi)) * np.cos(np.deg2rad(theta)),
                    np.cos(np.deg2rad(phi)) * np.sin(np.deg2rad(theta)),
                    np.sin(np.deg2rad(phi))
                ])

                if np.dot(pos_unit, sun_direction) > 0:
                    positions.append((phi, theta))
        
        return positions


    def spherical_to_cartesian(distance, phi, theta):
        """将球坐标转换为笛卡尔坐标"""
        return np.array([
            distance * np.cos(np.deg2rad(phi)) * np.cos(np.deg2rad(theta)),
            distance * np.cos(np.deg2rad(phi)) * np.sin(np.deg2rad(theta)),
            distance * np.sin(np.deg2rad(phi))
        ])