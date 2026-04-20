import bpy
import math

# -----------------------
# Reset scene
# -----------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 96
scene.render.fps = 24

# -----------------------
# Use Cycles for CPU headless rendering
# -----------------------
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.use_motion_blur = False

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100

scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.filepath = "/home/user/Geremoah/viewport_park_run.mp4"

# -----------------------
# World
# -----------------------
world = bpy.data.worlds["World"]
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.80, 0.90, 1.00, 1.0)
bg.inputs[1].default_value = 0.7

# -----------------------
# Materials
# -----------------------
def make_mat(name, color, rough=0.5, spec=0.5, subsurf=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = spec
    bsdf.inputs["Subsurface Weight"].default_value = subsurf
    return mat

grass_mat = make_mat("Grass", (0.22, 0.72, 0.28, 1), rough=0.95, spec=0.2)
path_mat = make_mat("Path", (0.76, 0.64, 0.45, 1), rough=1.0, spec=0.15)
skin_mat = make_mat("Skin", (0.73, 0.54, 0.40, 1), rough=0.42, spec=0.35, subsurf=0.05)
shirt_mat = make_mat("Shirt", (0.15, 0.48, 0.95, 1), rough=0.45, spec=0.35)
shorts_mat = make_mat("Shorts", (0.10, 0.16, 0.30, 1), rough=0.55, spec=0.25)
shoe_mat = make_mat("Shoes", (0.96, 0.96, 0.96, 1), rough=0.30, spec=0.45)
leaf_mat = make_mat("Leaves", (0.20, 0.62, 0.23, 1), rough=0.82, spec=0.2)
trunk_mat = make_mat("Trunk", (0.36, 0.23, 0.11, 1), rough=0.9, spec=0.1)
hair_mat = make_mat("Hair", (0.16, 0.09, 0.04, 1), rough=0.7, spec=0.2)
eye_white_mat = make_mat("EyeWhite", (1, 1, 1, 1), rough=0.15, spec=0.6)
pupil_mat = make_mat("Pupil", (0.07, 0.05, 0.03, 1), rough=0.2, spec=0.4)

# -----------------------
# Helpers
# -----------------------
def smooth(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

def add_subsurf(obj, level=1):
    mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    mod.levels = level
    mod.render_levels = level

def add_uv_sphere(name, radius, loc, scale=(1,1,1), mat=None, subsurf_level=1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if mat:
        obj.data.materials.append(mat)
    smooth(obj)
    add_subsurf(obj, subsurf_level)
    return obj

def add_cube(name, loc, scale=(1,1,1), mat=None, subsurf_level=1):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if mat:
        obj.data.materials.append(mat)
    smooth(obj)
    add_subsurf(obj, subsurf_level)
    return obj

# -----------------------
# Ground
# -----------------------
bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 0))
ground = bpy.context.active_object
ground.data.materials.append(grass_mat)

bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0.02))
path = bpy.context.active_object
path.scale[1] = 7
path.data.materials.append(path_mat)

# -----------------------
# Trees
# -----------------------
def make_tree(x, y, trunk_h=2.2, crown=1.2):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=trunk_h, location=(x, y, trunk_h / 2))
    trunk = bpy.context.active_object
    trunk.data.materials.append(trunk_mat)
    smooth(trunk)
    add_subsurf(trunk, 1)

    crown_obj = add_uv_sphere(
        "Leaves", crown, (x, y, trunk_h + crown * 0.7),
        scale=(1.0, 1.0, 1.15), mat=leaf_mat, subsurf_level=1
    )
    return trunk, crown_obj

for pos in [(-5,-9), (5,-8), (-6,-4), (6,-3), (-5,2), (5,3), (-6,8), (6,9)]:
    make_tree(*pos)

# -----------------------
# Stylized boy
# -----------------------
torso = add_uv_sphere("Torso", 0.6, (0, -6, 1.35), scale=(0.75, 0.5, 1.0), mat=shirt_mat)
head = add_uv_sphere("Head", 0.52, (0, -6, 2.35), scale=(1.0, 0.95, 1.08), mat=skin_mat)
hips = add_uv_sphere("Hips", 0.35, (0, -6, 0.72), scale=(0.95, 0.75, 0.7), mat=shorts_mat)

armL = add_cube("ArmL", (-0.72, -6, 1.35), scale=(0.12, 0.12, 0.45), mat=skin_mat)
armR = add_cube("ArmR", (0.72, -6, 1.35), scale=(0.12, 0.12, 0.45), mat=skin_mat)
legL = add_cube("LegL", (-0.22, -6, 0.02), scale=(0.14, 0.14, 0.58), mat=skin_mat)
legR = add_cube("LegR", (0.22, -6, 0.02), scale=(0.14, 0.14, 0.58), mat=skin_mat)

shoeL = add_cube("ShoeL", (-0.22, -5.92, -0.58), scale=(0.18, 0.28, 0.09), mat=shoe_mat)
shoeR = add_cube("ShoeR", (0.22, -5.92, -0.58), scale=(0.18, 0.28, 0.09), mat=shoe_mat)

earL = add_uv_sphere("EarL", 0.09, (-0.48, -6, 2.34), mat=skin_mat)
earR = add_uv_sphere("EarR", 0.09, (0.48, -6, 2.34), mat=skin_mat)

eyeL = add_uv_sphere("EyeWhiteL", 0.09, (-0.16, -5.56, 2.40), scale=(1,0.6,1), mat=eye_white_mat, subsurf_level=0)
eyeR = add_uv_sphere("EyeWhiteR", 0.09, (0.16, -5.56, 2.40), scale=(1,0.6,1), mat=eye_white_mat, subsurf_level=0)
pupilL = add_uv_sphere("PupilL", 0.04, (-0.16, -5.48, 2.39), scale=(1,0.5,1), mat=pupil_mat, subsurf_level=0)
pupilR = add_uv_sphere("PupilR", 0.04, (0.16, -5.48, 2.39), scale=(1,0.5,1), mat=pupil_mat, subsurf_level=0)

hair = add_uv_sphere("Hair", 0.54, (0, -6.02, 2.48), scale=(1.02, 0.96, 0.82), mat=hair_mat)

# Parent parts to torso
for obj in [head, hips, armL, armR, legL, legR, shoeL, shoeR, earL, earR, eyeL, eyeR, pupilL, pupilR, hair]:
    obj.parent = torso

# -----------------------
# Animation
# -----------------------
def pose(frame, y, arm_swing, leg_swing, bounce):
    torso.location = (0, y, 1.35 + bounce)
    torso.rotation_euler = (math.radians(-4), 0, 0)
    torso.keyframe_insert(data_path="location", frame=frame)
    torso.keyframe_insert(data_path="rotation_euler", frame=frame)

    armL.rotation_euler = (math.radians(arm_swing), 0, math.radians(8))
    armR.rotation_euler = (math.radians(-arm_swing), 0, math.radians(-8))
    legL.rotation_euler = (math.radians(-leg_swing), 0, 0)
    legR.rotation_euler = (math.radians(leg_swing), 0, 0)
    shoeL.rotation_euler = (math.radians(leg_swing * 0.35), 0, 0)
    shoeR.rotation_euler = (math.radians(-leg_swing * 0.35), 0, 0)

    for obj in [armL, armR, legL, legR, shoeL, shoeR]:
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)

keys = [
    (1,  -6.0,  38, 42, -0.05),
    (12, -4.7, -38,-42,  0.06),
    (24, -3.4,  38, 42, -0.05),
    (36, -2.1, -38,-42,  0.06),
    (48, -0.8,  38, 42, -0.05),
    (60,  0.5, -38,-42,  0.06),
    (72,  1.8,  38, 42, -0.05),
    (84,  3.1, -38,-42,  0.06),
    (96,  4.4,  38, 42, -0.05),
]

for k in keys:
    pose(*k)

for obj in [torso, armL, armR, legL, legR, shoeL, shoeR]:
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'

# -----------------------
# Camera
# -----------------------
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, -6, 1.7))
target = bpy.context.active_object
target.name = "Target"

for f, y, *_ in keys:
    target.location = (0, y, 1.7)
    target.keyframe_insert(data_path="location", frame=f)

bpy.ops.object.camera_add(location=(0, -11, 2.7), rotation=(math.radians(78), 0, 0))
cam = bpy.context.active_object
scene.camera = cam

cam.data.lens = 40
cam.data.dof.use_dof = True
cam.data.dof.focus_object = target
cam.data.dof.aperture_fstop = 3.2

track = cam.constraints.new(type='TRACK_TO')
track.target = target
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

for f, y, *_ in keys:
    cam.location = (0, y - 5.2, 2.7)
    cam.keyframe_insert(data_path="location", frame=f)

# -----------------------
# Lights
# -----------------------
bpy.ops.object.light_add(type='SUN', location=(6, -6, 10))
sun = bpy.context.active_object
sun.data.energy = 2.8
sun.rotation_euler = (math.radians(40), 0, math.radians(28))

bpy.ops.object.light_add(type='AREA', location=(0, -7.2, 3.8))
fill = bpy.context.active_object
fill.data.energy = 1200
fill.data.shape = 'RECTANGLE'
fill.data.size = 5
fill.data.size_y = 5
fill.rotation_euler = (math.radians(75), 0, 0)

bpy.ops.object.light_add(type='AREA', location=(0, -3.5, 4.2))
rim = bpy.context.active_object
rim.data.energy = 700
rim.data.size = 4
rim.rotation_euler = (math.radians(-65), 0, math.radians(180))

# -----------------------
# Render animation
# -----------------------
print("Starting render...")
bpy.ops.render.render(animation=True)
print("Render complete: /home/user/Geremoah/viewport_park_run.mp4")
