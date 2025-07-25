class VisibilityConfig:
    # 模型路径
    MODEL_PATH = "model\\bennu_lp.obj"
    
    START_ANGLE = 0
    END_ANGLE = 360
    ANGLE_STEP = 10

    # 相机参数
    CAMERA_theta_ANGLE = 0.0
    CAMERA_phi_ANGLE = 0.0
   
    CAMERA_DISTANCE = 600.0

    # Fov
    FOV_X_DEG = 2.0
    FOV_Y_DEG = 2.0

    # sun prameters
    SUN_theta_ANGLE = 0.0
    SUN_phi_ANGLE = 0.0
    
    #restrictions
    MAX_VIEWING_ANGLE_DEG = 60.0  # 最大视角
    MAX_SUN_ANGLE_DEG = 90.0  # 最大太阳角
    MAX_REFLECTION_ANGLE_DEG = 100.0  # 最大反射角

    # 输出目录
    OUTPUT_BASE_DIR = "visibility_results"

    # 输出控制
    SAVE_INDIVIDUAL_PLY = False  # 是否保存每个角度的PLY
    SAVE_PLOTS = False  # 是否保存可视化图片

    MAX_VIEWING_ANGLE_DEG = 60.0
    MAX_SUN_ANGLE_DEG = 90.0
    MAX_REFLECTION_ANGLE_DEG = 100.0