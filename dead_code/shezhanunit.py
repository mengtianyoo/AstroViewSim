# This script must be run from within Blender's Python environment
import bpy
import math

# Clear existing scene
#bpy.ops.wm.read_homefile(use_empty=True)

# Import your model (update the filepath to your actual model)
model_path = "model/itokawa_f0049152.obj"
bpy.ops.import_scene.obj(filepath=model_path)
model = bpy.context.selected_objects[0]

# Add a Sun light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 5))
sun = bpy.context.object
sun.rotation_euler = (math.radians(45), 0, math.radians(45))

# Add a Camera
bpy.ops.object.camera_add(location=(0, -5, 2))
cam = bpy.context.object
cam.rotation_euler = (math.radians(75), 0, 0)
bpy.context.scene.camera = cam

# Set up model rotation animation (360 degrees over 120 frames)
model.rotation_mode = 'XYZ'
model.rotation_euler = (0, 0, 0)
model.keyframe_insert(data_path="rotation_euler", frame=1)

model.rotation_euler[2] = math.radians(360)
model.keyframe_insert(data_path="rotation_euler", frame=120)

# Make the animation cyclic
fcurve = model.animation_data.action.fcurves[2]
fcurve.modifiers.new(type='CYCLES')

# Render settings
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.frame_end = 120
scene.render.filepath = "dead_code/shezhanunit_render.mp4"  # Update with your desired output path

# Optional: set resolution
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.film_transparent = True  # Transparent background

print("Blender setup script loaded. Please update file paths and run 'Ctrl+F12' to render animation.")
