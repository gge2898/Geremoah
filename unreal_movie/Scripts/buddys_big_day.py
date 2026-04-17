"""
Buddy's Big Day - A 30-second animated kids movie
Rendered with Blender 4.x in headless CPU mode (Cycles)

Story:
  0-5s   Establishing shot - colorful meadow, camera pans in
  5-15s  Buddy the orange ball rolls in and bounces around
  15-22s Colorful balloons float down from the sky
  22-30s Buddy jumps up, everyone celebrates!

Run with:
  blender --background --python buddys_big_day.py
"""

import bpy
import math
import os

# ============================================================
# SETTINGS
# ============================================================
OUTPUT_DIR  = "/tmp/buddy_frames"
FPS         = 24
DURATION    = 30          # seconds
TOTAL       = FPS * DURATION   # 720 frames
RES_X, RES_Y = 640, 360
SAMPLES     = 16          # low = fast CPU render; bump to 32 for better quality

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# SCENE RESET
# ============================================================
scene = bpy.context.scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)

# ============================================================
# MATERIALS
# ============================================================
def mat(name, rgb, roughness=0.7, metallic=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    links = m.node_tree.links
    nodes.clear()
    out  = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value   = (*rgb, 1.0)
    bsdf.inputs['Roughness'].default_value    = roughness
    bsdf.inputs['Metallic'].default_value     = metallic
    if emit > 0:
        bsdf.inputs['Emission Color'].default_value   = (*rgb, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emit
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m

M_GROUND   = mat("Ground",  (0.18, 0.65, 0.25), roughness=0.95)
M_BUDDY    = mat("Buddy",   (1.00, 0.45, 0.05), roughness=0.25)
M_TRUNK    = mat("Trunk",   (0.38, 0.20, 0.07), roughness=0.95)
M_LEAVES   = mat("Leaves",  (0.08, 0.52, 0.15), roughness=0.85)
M_CLOUD    = mat("Cloud",   (0.96, 0.97, 1.00), roughness=0.90)
M_WHITE    = mat("White",   (1.00, 1.00, 1.00), roughness=0.10)
M_BLACK    = mat("Black",   (0.02, 0.02, 0.02), roughness=0.05)
M_BALLOON  = [
    mat("BRed",    (0.95, 0.12, 0.12), roughness=0.15),
    mat("BBlue",   (0.12, 0.35, 0.98), roughness=0.15),
    mat("BYellow", (1.00, 0.85, 0.05), roughness=0.15),
    mat("BGreen",  (0.08, 0.80, 0.28), roughness=0.15),
    mat("BPurple", (0.62, 0.12, 0.92), roughness=0.15),
]

# ============================================================
# PRIMITIVE HELPERS
# ============================================================
def sphere(name, loc, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0, location=loc, segments=24, ring_count=16)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

def cylinder(name, loc, scale, material):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=1.0, depth=2.0, location=loc, vertices=16)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

def plane(name, loc, scale, material):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    return o

# ============================================================
# KEYFRAME HELPER  (loc/rot in Blender units / radians)
# ============================================================
def kf(obj, frame, loc=None, rot=None, scl=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert("rotation_euler", frame=frame)
    if scl is not None:
        obj.scale = scl
        obj.keyframe_insert("scale", frame=frame)

def smooth_interp(obj):
    if obj.animation_data and obj.animation_data.action:
        for fc in obj.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'

def r(deg): return math.radians(deg)

# ============================================================
# WORLD / SKY
# ============================================================
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
sky = wn.new('ShaderNodeTexSky')
sky.sky_type = 'NISHITA'
sky.sun_elevation = r(40)
sky.sun_rotation   = r(120)
bg  = wn.new('ShaderNodeBackground')
bg.inputs['Strength'].default_value = 1.8
wo  = wn.new('ShaderNodeOutputWorld')
wl.new(sky.outputs['Color'], bg.inputs['Color'])
wl.new(bg.outputs['Background'], wo.inputs['Surface'])

# Sun
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
sun = bpy.context.active_object
sun.name = "Sun"
sun.data.energy = 4.0
sun.rotation_euler = (r(50), r(0), r(130))

# ============================================================
# GROUND
# ============================================================
ground = plane("Ground", (0, 0, 0), (40, 40, 1), M_GROUND)

# ============================================================
# TREES  (cylinder trunk + two spheres for canopy)
# ============================================================
TREE_POS = [
    (-10, -6), (-14, 4), (-11, 9), (-8, -11),
    ( 11, -7), ( 13, 5), ( 12, 10), ( 9, -11),
]
for i, (tx, ty) in enumerate(TREE_POS):
    cylinder(f"Trunk{i}",  (tx, ty,  1.2), (0.22, 0.22, 1.2), M_TRUNK)
    sphere  (f"Leaves{i}", (tx, ty,  3.6), (2.0,  2.0,  1.8), M_LEAVES)
    sphere  (f"LeafB{i}",  (tx+0.8, ty, 3.0), (1.3, 1.3, 1.2), M_LEAVES)

# ============================================================
# CLOUDS
# ============================================================
CLOUD_GROUPS = [
    [(-7, -4, 8.5, 1.6), (-5.5, -4, 8.9, 1.2), (-8.2, -4, 8.7, 1.0)],
    [( 3,  7, 9.5, 1.9), ( 4.5,  7, 9.9, 1.4), ( 2.0,  7, 9.6, 1.1)],
    [( 9, -3, 8.0, 1.4), (10.2, -3, 8.3, 1.0), ( 8.1, -3, 8.1, 0.9)],
]
cloud_objs = []
for ci, grp in enumerate(CLOUD_GROUPS):
    parts = []
    for pi, (cx, cy, cz, cs) in enumerate(grp):
        p = sphere(f"Cloud{ci}_{pi}", (cx, cy, cz), (cs, cs, cs*0.55), M_CLOUD)
        parts.append(p)
    cloud_objs.append(parts)

# ============================================================
# BUDDY  (orange ball with eyes)
# ============================================================
buddy = sphere("Buddy", (-16, 0, 1.0), (1.0, 1.0, 1.0), M_BUDDY)

eye_l  = sphere("EyeL",    (-0.38, -0.88, 0.50), (0.22, 0.18, 0.18), M_WHITE)
eye_r  = sphere("EyeR",    ( 0.38, -0.88, 0.50), (0.22, 0.18, 0.18), M_WHITE)
pupil_l = sphere("PupilL", (-0.38, -1.06, 0.50), (0.09, 0.06, 0.09), M_BLACK)
pupil_r = sphere("PupilR", ( 0.38, -1.06, 0.50), (0.09, 0.06, 0.09), M_BLACK)
for e in [eye_l, eye_r, pupil_l, pupil_r]:
    e.parent = buddy

# ============================================================
# BALLOONS  (start far above, float down)
# ============================================================
BALLOON_DATA = [
    ((2.0,  1.0),  M_BALLOON[0]),
    ((3.2, -0.8),  M_BALLOON[1]),
    ((1.0,  2.2),  M_BALLOON[2]),
    ((4.0,  0.0),  M_BALLOON[3]),
    ((2.6, -2.0),  M_BALLOON[4]),
]
balloons = []
for i, ((bx, by), bmat) in enumerate(BALLOON_DATA):
    b = sphere(f"Balloon{i}", (bx, by, 18 + i*2), (0.55, 0.55, 0.75), bmat)
    balloons.append(b)

# ============================================================
# CAMERA
# ============================================================
bpy.ops.object.camera_add(location=(-6, -20, 7))
cam = bpy.context.active_object
cam.name = "Cam"
cam.rotation_euler = (r(73), r(0), r(-17))
cam.data.lens = 35
scene.camera = cam

# ============================================================
# ANIMATE BUDDY
# ============================================================
# --- Scene 1 (f1-120): Roll in from left ---
kf(buddy,   1, loc=(-16, 0, 1.0), rot=(0, 0, 0))
kf(buddy, 120, loc=(  0, 0, 1.0), rot=(r(0), r(-16*r(1)*180/math.pi*180/math.pi), r(0)))

# Simpler: just keyframe rotation as cumulative spin
# Buddy rolls: distance 16 units, radius 1 → 16 radians of rotation around world X
kf(buddy,   1, rot=(0, 0, 0))
kf(buddy, 120, rot=(r(0), r(0), r(0)), loc=(-16, 0, 1.0))  # override above

# Use simpler direct keyframes
buddy.location = (-16, 0, 1.0)
buddy.rotation_euler = (0, 0, 0)
buddy.keyframe_insert("location", frame=1)
buddy.keyframe_insert("rotation_euler", frame=1)

buddy.location = (0, 0, 1.0)
buddy.rotation_euler = (0, 0, -16.0)   # ~916 deg spin while rolling in
buddy.keyframe_insert("location", frame=120)
buddy.keyframe_insert("rotation_euler", frame=120)

# --- Scene 2 (f120-360): Bouncing ---
BOUNCES = [
    #  frame  x      y     z    spin_z
    (  120,   0.0,   0.0,  1.0, -16.0),
    (  136,   1.2,   0.0,  3.8, -17.2),
    (  152,   2.8,   0.0,  1.0, -18.8),
    (  168,   4.0,   0.0,  3.8, -20.0),
    (  184,   5.5,   0.0,  1.0, -21.5),
    (  200,   6.5,   0.5,  3.8, -22.5),
    (  216,   7.0,   1.2,  1.0, -23.0),
    (  232,   5.5,   2.0,  3.8, -24.5),
    (  248,   3.5,   3.0,  1.0, -26.5),
    (  264,   1.5,   3.8,  3.8, -28.5),
    (  280,  -0.5,   4.0,  1.0, -30.5),
    (  296,  -1.5,   3.0,  3.8, -31.5),
    (  312,  -2.0,   1.5,  1.0, -32.0),
    (  328,  -0.5,   0.5,  3.8, -33.5),
    (  344,   1.5,   0.0,  1.0, -35.5),
    (  360,   2.0,   0.5,  1.0, -36.0),
]
for frame, x, y, z, spin in BOUNCES:
    buddy.location       = (x, y, z)
    buddy.rotation_euler = (0, 0, spin)
    buddy.keyframe_insert("location",       frame=frame)
    buddy.keyframe_insert("rotation_euler", frame=frame)

# --- Scene 3 (f360-528): Move toward balloons ---
buddy.location = (2.5, 0.5, 1.0)
buddy.rotation_euler = (0, 0, -38.5)
buddy.keyframe_insert("location",       frame=528)
buddy.keyframe_insert("rotation_euler", frame=528)

# --- Scene 4 (f528-720): Jump up & celebrate ---
CELEBRATE = [
    (528, (2.5, 0.5, 1.0), (0, 0, -38.5), (1.0, 1.0, 1.0)),
    (552, (2.5, 0.5, 5.5), (0, 0, -41.5), (1.2, 1.2, 1.2)),
    (576, (2.5, 0.5, 4.0), (0, 0, -44.5), (1.0, 1.0, 1.0)),
    (600, (2.5, 0.5, 6.0), (0, 0, -47.5), (1.3, 1.3, 1.3)),
    (624, (2.5, 0.5, 4.5), (0, 0, -50.5), (1.0, 1.0, 1.0)),
    (648, (2.5, 0.5, 6.5), (0, 0, -53.5), (1.4, 1.4, 1.4)),
    (672, (2.5, 0.5, 5.0), (0, 0, -56.5), (1.1, 1.1, 1.1)),
    (696, (2.5, 0.5, 6.0), (0, 0, -59.5), (1.3, 1.3, 1.3)),
    (720, (2.5, 0.5, 5.5), (0, 0, -62.5), (1.2, 1.2, 1.2)),
]
for frame, loc, rot, scl in CELEBRATE:
    buddy.location       = loc
    buddy.rotation_euler = rot
    buddy.scale          = scl
    buddy.keyframe_insert("location",       frame=frame)
    buddy.keyframe_insert("rotation_euler", frame=frame)
    buddy.keyframe_insert("scale",          frame=frame)

smooth_interp(buddy)

# ============================================================
# ANIMATE BALLOONS
# ============================================================
for i, balloon in enumerate(balloons):
    bx, by = BALLOON_DATA[i][0]
    start_z = 20 + i * 2
    end_z   = 7.5 + i * 0.6

    # Hold high until frame 300, then float down to frame 450
    balloon.location = (bx, by, start_z)
    balloon.keyframe_insert("location", frame=1)
    balloon.keyframe_insert("location", frame=300)

    balloon.location = (bx, by, end_z)
    balloon.keyframe_insert("location", frame=450)

    # Bobbing + slight orbit during celebration
    for f in range(450, 721, 36):
        angle = r((f - 450) * 5 + i * 72)
        ox = bx + math.cos(angle) * 0.35
        oy = by + math.sin(angle) * 0.35
        bz = end_z + math.sin(r((f - 450) * 8)) * 0.5
        balloon.location = (ox, oy, bz)
        balloon.keyframe_insert("location", frame=f)

    smooth_interp(balloon)

# ============================================================
# ANIMATE CLOUDS  (slow drift)
# ============================================================
for ci, parts in enumerate(cloud_objs):
    drift = 0.025 + ci * 0.008
    for p in parts:
        bx2 = p.location.x
        by2 = p.location.y
        bz2 = p.location.z
        p.location = (bx2, by2, bz2)
        p.keyframe_insert("location", frame=1)
        p.location = (bx2 + drift * TOTAL, by2, bz2)
        p.keyframe_insert("location", frame=TOTAL)
        smooth_interp(p)

# ============================================================
# ANIMATE CAMERA
# ============================================================
CAM_KEYS = [
    # frame  location              rotation (deg x, y, z)
    (    1, (-8,  -20, 7.0),    (73,  0, -17)),
    (  120, (-4,  -18, 6.0),    (71,  0, -12)),   # scene 1 end
    (  240, ( 3,  -18, 5.5),    (70,  0,   4)),   # follow buddy right
    (  360, ( 2,  -16, 5.0),    (68,  0,   2)),   # scene 2 end
    (  480, ( 0,  -13, 6.5),    (64,  0,   0)),   # tilt up for balloons
    (  600, (-2,  -16, 8.5),    (67,  0,  -5)),   # pull back
    (  720, (-5,  -19, 11.0),   (70,  0,  -9)),   # wide final shot
]
for frame, loc, rot_deg in CAM_KEYS:
    cam.location       = loc
    cam.rotation_euler = (r(rot_deg[0]), r(rot_deg[1]), r(rot_deg[2]))
    cam.keyframe_insert("location",       frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)
smooth_interp(cam)

# ============================================================
# RENDER SETTINGS
# ============================================================
scene.render.engine       = 'CYCLES'
scene.cycles.samples      = SAMPLES
scene.cycles.device       = 'CPU'
scene.cycles.use_denoising = False
scene.render.threads_mode = 'FIXED'
scene.render.threads      = os.cpu_count() or 8

scene.render.resolution_x          = RES_X
scene.render.resolution_y          = RES_Y
scene.render.resolution_percentage = 100
scene.render.fps                   = FPS
scene.frame_start                  = 1
scene.frame_end                    = TOTAL

# Render PNG sequence (ffmpeg assembles into MP4 after)
scene.render.image_settings.file_format       = 'PNG'
scene.render.image_settings.color_mode        = 'RGB'
scene.render.image_settings.compression       = 15
scene.render.filepath = os.path.join(OUTPUT_DIR, "frame_####")

# ============================================================
# SAVE .BLEND  then  RENDER
# ============================================================
blend_path = "/tmp/buddys_big_day.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"\nSaved scene to {blend_path}")

print(f"\n{'='*55}")
print("  BUDDY'S BIG DAY  —  starting render")
print(f"  {RES_X}x{RES_Y}  |  {FPS}fps  |  {TOTAL} frames ({DURATION}s)")
print(f"  {SAMPLES} samples  |  {scene.render.threads} CPU threads")
print(f"  Output: {OUTPUT_DIR}/frame_####.png")
print(f"{'='*55}\n")

bpy.ops.render.render(animation=True)
print("\nRender complete! Frames written to", OUTPUT_DIR)
