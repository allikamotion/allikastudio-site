# =====================================================================
#  WATERCOLOR JACK-O'-LANTERN  —  one-click scene builder  (v5)
#  Made for Blender 5.1  (EEVEE + real-time Viewport Compositor)
#
#  HOW TO USE:  Scripting tab → New → paste this → press "Run Script" (▶)
#  You can run it again any time — it wipes the scene and rebuilds it.
#
#  What's new in v3 — a soft, hand-painted WATERCOLOR look:
#   - matte skin with "painted" shading and lavender (not black) shadows
#   - a pink/lavender rim glow, like paint pooling at the edges
#   - blotchy watercolor washes on the skin and a painted-paper sky
#   - soft, smooth candle light inside
#   - a stronger painterly compositor that washes the image out a little
#   - v4: the watercolor stem is built in — one script, one Run
#   - v5: QUALITY switch — light "FAST" mode by default, "FULL" for final renders
# =====================================================================

import bpy
import bmesh
import math
from mathutils import Vector

# ---------------------------------------------------------------------
# QUALITY — the most important switch!
#   "FAST" = light and smooth on any computer (default, for playing around)
#   "FULL" = the richest look, but heavy — use it only for the final render
# ---------------------------------------------------------------------
QUALITY = "FAST"
FAST = (QUALITY != "FULL")

# ---------------------------------------------------------------------
# SETTINGS — the easiest knobs to play with
# ---------------------------------------------------------------------
RIB_COUNT = 10              # number of pumpkin ribs (lobes)
GROOVE_DEPTH = 0.10         # how deep the grooves between ribs are
SQUASH_Z = 0.75             # vertical squash of the pumpkin (1.0 = round)
WALL_THICKNESS = 0.07       # thickness of the pumpkin shell
CANDLE_COLOR = (1.0, 0.72, 0.30)   # warm yellow candle light
CANDLE_POWER = 150.0        # strength of the candle light (Watts)
SHADOW_COLOR = (0.36, 0.24, 0.50)  # lavender used instead of dark shadows
RIM_COLOR = (1.0, 0.72, 0.88)      # pink/lavender edge glow
KUWAHARA_SMALL = 6 if FAST else 8    # painterly brush size, branch A (detail)
KUWAHARA_BIG = 12 if FAST else 20    # painterly brush size, branch B (big strokes)
GLOW_STRENGTH = 1.3         # bloom / glow strength in the compositor
FRAMES = 120                # length of one full turn (frames)


# =====================================================================
# 1. CLEANUP — delete everything so we start from an empty scene
# =====================================================================
# If you happen to be in Edit Mode, go back to Object Mode first.
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# Delete all objects (meshes, lights, cameras, empties...)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# Delete the leftover data blocks that are no longer used by anything
for collection in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                   bpy.data.cameras, bpy.data.actions):
    for block in list(collection):
        if block.users == 0:
            collection.remove(block)

# Delete the compositor node group from a previous run
old_group = bpy.data.node_groups.get("Painterly Compositor")
if old_group:
    bpy.data.node_groups.remove(old_group)

scene = bpy.context.scene


# Small helper: get a node's input/output socket by name, but only the
# visible one (some nodes, like Mix, have hidden sockets with the same name)
def sock(sockets, name):
    for s in sockets:
        if s.name == name and s.enabled:
            return s
    return sockets[name]


# Small helper: make a new material that already has a node tree
def new_material(name):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    mat.node_tree.nodes.clear()
    return mat


# Small helper: set the stops of a Color Ramp in one go.
# stops = [(position, (r, g, b)), ...]   Soft "Ease" blending between them.
def set_ramp(ramp_node, stops):
    cr = ramp_node.color_ramp
    cr.interpolation = 'EASE'
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for el, (pos, col) in zip(cr.elements, stops):
        el.position = pos
        el.color = (*col, 1.0)


# =====================================================================
# 2. MATERIALS  (made first, so the carving step can use them)
# Slot 1 = outside skin, Slot 2 = inside wall, Slot 3 = cut edges.
# Slots 2 and 3 use the same "flesh" material, but keeping them as
# separate slots lets the script find the cut edges and keep them crisp.
# =====================================================================

# ---------- 2a. Pumpkin skin (outside) — the WATERCOLOR material ----------
# The idea:
#   A) build the pumpkin's paint colour (orange washes, darker grooves)
#   B) measure how much light hits each spot (Shader to RGB)
#   C) turn that light into a few soft "paint steps" with a Color Ramp
#   D) where it's dark, paint LAVENDER instead of black
#   E) add a pink glow on the edges + a soft matte surface underneath
skin = new_material("Pumpkin Skin")
nodes, links = skin.node_tree.nodes, skin.node_tree.links

# Texture Coordinate + Mapping: lets you move/scale all textures at once
texco = nodes.new("ShaderNodeTexCoord");         texco.location = (-1600, 0)
mapping = nodes.new("ShaderNodeMapping");        mapping.location = (-1400, 0)
links.new(texco.outputs["Object"], mapping.inputs["Vector"])

# --- A) Paint colour ---
# Noise → Color Ramp with 4 soft stops = stylized orange colours
noise = nodes.new("ShaderNodeTexNoise");         noise.location = (-1150, 350)
noise.inputs["Scale"].default_value = 3.0
noise.inputs["Detail"].default_value = 4.0
links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

color_ramp = nodes.new("ShaderNodeValToRGB");    color_ramp.location = (-900, 350)
color_ramp.label = "Pumpkin Colours"
set_ramp(color_ramp, [
    (0.30, (0.70, 0.13, 0.02)),    # deep orange
    (0.45, (0.92, 0.28, 0.03)),    # orange
    (0.60, (1.00, 0.45, 0.06)),    # yellow-orange
    (0.75, (1.00, 0.62, 0.20)),    # pale apricot
])
links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])

# Wave texture = soft organic streaks (Overlay)
wave = nodes.new("ShaderNodeTexWave");           wave.location = (-1150, 50)
wave.inputs["Scale"].default_value = 2.0
wave.inputs["Distortion"].default_value = 8.0
links.new(mapping.outputs["Vector"], wave.inputs["Vector"])

streaks = nodes.new("ShaderNodeMix");            streaks.location = (-650, 300)
streaks.data_type = 'RGBA'
streaks.blend_type = 'OVERLAY'
sock(streaks.inputs, "Factor").default_value = 0.15
links.new(color_ramp.outputs["Color"], sock(streaks.inputs, "A"))
links.new(wave.outputs["Color"], sock(streaks.inputs, "B"))

# Watercolor WASHES: a very big, soft noise that makes the colour uneven,
# like paint that dried a little darker in some places
wash = nodes.new("ShaderNodeTexNoise");          wash.location = (-900, 50)
wash.label = "Watercolor Washes"
wash.inputs["Scale"].default_value = 0.8
wash.inputs["Detail"].default_value = 2.0
wash.inputs["Roughness"].default_value = 0.4
links.new(mapping.outputs["Vector"], wash.inputs["Vector"])

washes = nodes.new("ShaderNodeMix");             washes.location = (-450, 300)
washes.data_type = 'RGBA'
washes.blend_type = 'OVERLAY'
sock(washes.inputs, "Factor").default_value = 0.35   # low contrast
links.new(sock(streaks.outputs, "Result"), sock(washes.inputs, "A"))
links.new(wash.outputs["Fac"], sock(washes.inputs, "B"))

# Grooves: the same "angle around Z" formula used for the model.
# The grooves get a dusty PINK-PURPLE tint instead of going brown.
sep = nodes.new("ShaderNodeSeparateXYZ");        sep.location = (-1400, -300)
links.new(texco.outputs["Object"], sep.inputs["Vector"])
atan = nodes.new("ShaderNodeMath");              atan.location = (-1200, -300)
atan.operation = 'ARCTAN2'                       # angle = atan2(y, x)
links.new(sep.outputs["Y"], atan.inputs[0])
links.new(sep.outputs["X"], atan.inputs[1])
times = nodes.new("ShaderNodeMath");             times.location = (-1020, -300)
times.operation = 'MULTIPLY'
times.inputs[1].default_value = RIB_COUNT / 2
links.new(atan.outputs[0], times.inputs[0])
cos = nodes.new("ShaderNodeMath");               cos.location = (-840, -300)
cos.operation = 'COSINE'
links.new(times.outputs[0], cos.inputs[0])
absn = nodes.new("ShaderNodeMath");              absn.location = (-660, -300)
absn.operation = 'ABSOLUTE'
links.new(cos.outputs[0], absn.inputs[0])

groove_ramp = nodes.new("ShaderNodeValToRGB");   groove_ramp.location = (-480, -300)
groove_ramp.label = "Groove Tint"
set_ramp(groove_ramp, [
    (0.00, (0.62, 0.42, 0.62)),    # groove = dusty pink-purple
    (0.45, (1.00, 1.00, 1.00)),    # rib = full colour
])
links.new(absn.outputs[0], groove_ramp.inputs["Fac"])

albedo = nodes.new("ShaderNodeMix");             albedo.location = (-200, 200)
albedo.label = "Paint Colour"
albedo.data_type = 'RGBA'
albedo.blend_type = 'MULTIPLY'
sock(albedo.inputs, "Factor").default_value = 1.0
links.new(sock(washes.outputs, "Result"), sock(albedo.inputs, "A"))
links.new(groove_ramp.outputs["Color"], sock(albedo.inputs, "B"))
paint_color = sock(albedo.outputs, "Result")

# Bumpy skin: fine noise → Bump → Normal (used by everything below)
bump_noise = nodes.new("ShaderNodeTexNoise");    bump_noise.location = (-450, -650)
bump_noise.inputs["Scale"].default_value = 25.0
bump_noise.inputs["Detail"].default_value = 4.0
links.new(mapping.outputs["Vector"], bump_noise.inputs["Vector"])
bump = nodes.new("ShaderNodeBump");              bump.location = (-200, -650)
bump.inputs["Strength"].default_value = 0.12
links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
bump_normal = bump.outputs["Normal"]

# --- B) How much light hits each spot? ---
# A plain white Diffuse shader → Shader to RGB turns "lighting" into a
# colour we can edit → RGB to BW makes it a simple light amount.
probe = nodes.new("ShaderNodeBsdfDiffuse");      probe.location = (0, -350)
probe.label = "Light Probe"
probe.inputs["Color"].default_value = (1, 1, 1, 1)
links.new(bump_normal, probe.inputs["Normal"])
to_rgb = nodes.new("ShaderNodeShaderToRGB");     to_rgb.location = (200, -350)
links.new(probe.outputs["BSDF"], to_rgb.inputs["Shader"])
to_bw = nodes.new("ShaderNodeRGBToBW");          to_bw.location = (380, -350)
links.new(to_rgb.outputs["Color"], to_bw.inputs["Color"])

# --- C) Soft paint steps ---
steps = nodes.new("ShaderNodeValToRGB");         steps.location = (550, -350)
steps.label = "Paint Steps (light → paint)"
set_ramp(steps, [
    (0.00, (0.00, 0.00, 0.00)),    # in shadow → all lavender
    (0.10, (0.40, 0.40, 0.40)),
    (0.25, (0.80, 0.80, 0.80)),
    (0.50, (1.00, 1.00, 1.00)),    # fully lit → full paint colour
])
links.new(to_bw.outputs["Val"], steps.inputs["Fac"])

# --- D) Lavender shadows ---
painted = nodes.new("ShaderNodeMix");            painted.location = (850, 100)
painted.label = "Lavender Shadows"
painted.data_type = 'RGBA'
painted.blend_type = 'MIX'
sock(painted.inputs, "A").default_value = (*SHADOW_COLOR, 1)
links.new(steps.outputs["Color"], sock(painted.inputs, "Factor"))
links.new(paint_color, sock(painted.inputs, "B"))

paint_emit = nodes.new("ShaderNodeEmission");    paint_emit.location = (1050, 100)
paint_emit.inputs["Strength"].default_value = 0.6         # paint brightness
links.new(sock(painted.outputs, "Result"), paint_emit.inputs["Color"])

# --- E1) A soft matte skin underneath (no gloss, no clear coat) ---
bsdf = nodes.new("ShaderNodeBsdfPrincipled");    bsdf.location = (850, 650)
links.new(paint_color, bsdf.inputs["Base Color"])
links.new(bump_normal, bsdf.inputs["Normal"])
bsdf.inputs["Roughness"].default_value = 0.8
bsdf.inputs["Specular IOR Level"].default_value = 0.15   # very weak shine
bsdf.inputs["Coat Weight"].default_value = 0.0
bsdf.inputs["Subsurface Weight"].default_value = 0.0 if FAST else 0.35  # soft light bleed (heavy, FULL only)
bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.15)
bsdf.inputs["Subsurface Scale"].default_value = 0.03

# Mostly "painted" shading (70%), a little real matte skin (30%)
blend = nodes.new("ShaderNodeMixShader");        blend.location = (1300, 300)
blend.inputs["Factor"].default_value = 0.7
links.new(bsdf.outputs["BSDF"], blend.inputs[1])
links.new(paint_emit.outputs["Emission"], blend.inputs[2])

# --- E2) Pink rim glow on the silhouette (paint pooling at the edges) ---
layer = nodes.new("ShaderNodeLayerWeight");      layer.location = (850, -650)
layer.inputs["Blend"].default_value = 0.4
links.new(bump_normal, layer.inputs["Normal"])
rim_ramp = nodes.new("ShaderNodeValToRGB");      rim_ramp.location = (1050, -650)
rim_ramp.label = "Rim Width"
set_ramp(rim_ramp, [
    (0.55, (0, 0, 0)),             # facing the camera → no glow
    (0.95, (1, 1, 1)),             # at the edge → full glow
])
links.new(layer.outputs["Facing"], rim_ramp.inputs["Fac"])
rim_emit = nodes.new("ShaderNodeEmission");      rim_emit.location = (1300, -500)
rim_emit.inputs["Color"].default_value = (*RIM_COLOR, 1)
rim_strength = nodes.new("ShaderNodeMath");      rim_strength.location = (1300, -700)
rim_strength.operation = 'MULTIPLY'
rim_strength.inputs[1].default_value = 0.9                 # rim brightness
links.new(rim_ramp.outputs["Color"], rim_strength.inputs[0])
links.new(rim_strength.outputs[0], rim_emit.inputs["Strength"])

add_rim = nodes.new("ShaderNodeAddShader");      add_rim.location = (1550, 0)
links.new(blend.outputs["Shader"], add_rim.inputs[0])
links.new(rim_emit.outputs["Emission"], add_rim.inputs[1])

out = nodes.new("ShaderNodeOutputMaterial");     out.location = (1800, 0)
links.new(add_rim.outputs["Shader"], out.inputs["Surface"])

# ---------- 2b. Pumpkin flesh (inner walls + cut edges) ----------
# A soft matte surface lit by the candle: bright near the flame,
# darker towards the outside of the cuts. A tiny warm self-glow keeps
# the darkest corners from going muddy.
flesh = new_material("Pumpkin Flesh")
fn, fl = flesh.node_tree.nodes, flesh.node_tree.links
f_out = fn.new("ShaderNodeOutputMaterial");      f_out.location = (600, 0)
f_bsdf = fn.new("ShaderNodeBsdfPrincipled");     f_bsdf.location = (300, 0)
f_noise = fn.new("ShaderNodeTexNoise");          f_noise.location = (-300, 0)
f_noise.inputs["Scale"].default_value = 6.0
f_noise.inputs["Detail"].default_value = 3.0
f_ramp = fn.new("ShaderNodeValToRGB");           f_ramp.location = (0, 0)
set_ramp(f_ramp, [
    (0.35, (0.95, 0.45, 0.10)),    # warm orange
    (0.65, (1.00, 0.75, 0.30)),    # soft yellow
])
fl.new(f_noise.outputs["Fac"], f_ramp.inputs["Fac"])
fl.new(f_ramp.outputs["Color"], f_bsdf.inputs["Base Color"])
fl.new(f_ramp.outputs["Color"], f_bsdf.inputs["Emission Color"])
f_bsdf.inputs["Emission Strength"].default_value = 0.12
f_bsdf.inputs["Roughness"].default_value = 0.85
f_bsdf.inputs["Specular IOR Level"].default_value = 0.1
f_bsdf.inputs["Subsurface Weight"].default_value = 0.0 if FAST else 0.2
f_bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.2)
f_bsdf.inputs["Subsurface Scale"].default_value = 0.01
fl.new(f_bsdf.outputs["BSDF"], f_out.inputs["Surface"])

# ---------- 2c. Stem (matte) ----------
stem_mat = new_material("Stem")
sn, sl = stem_mat.node_tree.nodes, stem_mat.node_tree.links
s_out = sn.new("ShaderNodeOutputMaterial");      s_out.location = (600, 0)
s_bsdf = sn.new("ShaderNodeBsdfPrincipled");     s_bsdf.location = (300, 0)
s_noise = sn.new("ShaderNodeTexNoise");          s_noise.location = (-300, 0)
s_noise.inputs["Scale"].default_value = 12.0
s_ramp = sn.new("ShaderNodeValToRGB");           s_ramp.location = (0, 0)
set_ramp(s_ramp, [
    (0.3, (0.18, 0.20, 0.10)),     # muted olive green
    (0.7, (0.30, 0.20, 0.14)),     # soft brown
])
sl.new(s_noise.outputs["Fac"], s_ramp.inputs["Fac"])
sl.new(s_ramp.outputs["Color"], s_bsdf.inputs["Base Color"])
s_bsdf.inputs["Roughness"].default_value = 0.9
s_bsdf.inputs["Specular IOR Level"].default_value = 0.1
sl.new(s_bsdf.outputs["BSDF"], s_out.inputs["Surface"])

# ---------- 2d. Candle flame (tiny glowing ball) ----------
flame_mat = new_material("Candle Flame")
cn_, cl_ = flame_mat.node_tree.nodes, flame_mat.node_tree.links
c_out = cn_.new("ShaderNodeOutputMaterial");     c_out.location = (300, 0)
c_em = cn_.new("ShaderNodeEmission");            c_em.location = (0, 0)
c_em.inputs["Color"].default_value = (1.0, 0.75, 0.35, 1)
c_em.inputs["Strength"].default_value = 20.0
cl_.new(c_em.outputs["Emission"], c_out.inputs["Surface"])


# =====================================================================
# 3. PUMPKIN MODEL
# =====================================================================
# We start from a low-resolution UV sphere and move every vertex:
#   - push vertices in where the grooves are (based on the angle around Z)
#   - press the top and bottom inward (the dent where the stem sits)
#   - squash the whole thing vertically
# 40 segments = exactly 4 vertices per rib, so grooves land on vertices.
mesh = bpy.data.meshes.new("Pumpkin")
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)

for v in bm.verts:
    x, y, z = v.co
    angle = math.atan2(y, x)                 # angle around the Z axis
    ring = math.sqrt(x * x + y * y)          # distance from the Z axis

    # Ribs: |cos| is 1 in the middle of a rib and 0 in a groove
    rib = abs(math.cos(angle * RIB_COUNT / 2))
    groove = (1.0 - rib) ** 2                # 1 in the groove, 0 on the rib
    scale_xy = 1.0 - GROOVE_DEPTH * groove

    # Dents at the top and bottom poles
    dent = 0.28 * math.exp(-(ring / 0.32) ** 2)
    z = z * (1.0 - dent)

    v.co = Vector((x * scale_xy, y * scale_xy, z * SQUASH_Z))

bm.to_mesh(mesh)
bm.free()

pumpkin = bpy.data.objects.new("Pumpkin", mesh)
scene.collection.objects.link(pumpkin)
for poly in mesh.polygons:                   # smooth shading
    poly.use_smooth = True
mesh.materials.append(skin)    # slot 1: outside
mesh.materials.append(flesh)   # slot 2: inside wall
mesh.materials.append(flesh)   # slot 3: cut edges


# ---------------------------------------------------------------------
# Temporary face cutter: 2 angry eyes, a nose and a jagged toothy grin.
# It is pushed through the FRONT of the pumpkin (the side facing -Y,
# towards the camera). We use it once, then delete it.
# ---------------------------------------------------------------------
def grin_outline():
    """Points (x, z) going around the mouth, with teeth."""
    w = 0.62                                       # half width of the mouth
    top = lambda x: -0.17 + 0.20 * (x / w) ** 2    # upper lip (smiles up)
    bot = lambda x: -0.40 + 0.30 * (x / w) ** 2    # lower lip
    pts = [(-w, top(-w) + 0.02)]                   # left corner
    # lower lip, left → right, with one tooth sticking UP in the middle
    for x in (-0.45, -0.25, -0.10):
        pts.append((x, bot(x)))
    pts += [(-0.10, bot(-0.10) + 0.11), (0.10, bot(0.10) + 0.11)]
    for x in (0.10, 0.25, 0.45):
        pts.append((x, bot(x)))
    pts.append((w, top(w) + 0.02))                 # right corner
    # upper lip, right → left, with two teeth hanging DOWN
    for x in (0.45, 0.33):
        pts.append((x, top(x)))
    pts += [(0.33, top(0.33) - 0.12), (0.17, top(0.17) - 0.12)]
    for x in (0.17, 0.0, -0.17):
        pts.append((x, top(x)))
    pts += [(-0.17, top(-0.17) - 0.12), (-0.33, top(-0.33) - 0.12)]
    for x in (-0.33, -0.45):
        pts.append((x, top(x)))
    return pts


face_shapes = [
    [(-0.62, 0.36), (-0.42, 0.02), (-0.16, 0.20)],   # left eye (angry slant)
    [(0.62, 0.36), (0.16, 0.20), (0.42, 0.02)],      # right eye
    [(-0.10, -0.10), (0.10, -0.10), (0.0, 0.08)],    # nose
    grin_outline(),                                  # mouth
]

cut_mesh = bpy.data.meshes.new("FaceCutter")
bm = bmesh.new()
for shape in face_shapes:
    # Each 2D shape becomes a prism from in front of the pumpkin (y = -1.6)
    # to just past the front wall (y = -0.35) — it never touches the back.
    front = [bm.verts.new((x, -1.6, z)) for x, z in shape]
    back = [bm.verts.new((x, -0.35, z)) for x, z in shape]
    n = len(shape)
    cap_a = bm.faces.new(front)
    cap_b = bm.faces.new(list(reversed(back)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bmesh.ops.triangulate(bm, faces=[cap_a, cap_b])   # mouth is not convex
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.material_index = 2          # cut faces → slot 3 ("cut edges")
bm.to_mesh(cut_mesh)
bm.free()
cutter = bpy.data.objects.new("FaceCutter", cut_mesh)
scene.collection.objects.link(cutter)
for m in (skin, flesh, flesh):
    cut_mesh.materials.append(m)


# ---------------------------------------------------------------------
# Carve and BAKE (this is what keeps the scene light!)
#   1. Subdivision (level 1) — a bit smoother before cutting
#   2. Solidify — real wall thickness; the pumpkin becomes HOLLOW
#   3. Boolean — punches the face through the hollow shell
# Then we turn the result into a normal mesh and delete the cutter,
# so Blender never has to re-calculate the Boolean again.
# ---------------------------------------------------------------------
pre_sub = pumpkin.modifiers.new("Pre-Subdivision", 'SUBSURF')
pre_sub.levels = 1

solid = pumpkin.modifiers.new("Solidify", 'SOLIDIFY')
solid.thickness = WALL_THICKNESS
solid.offset = -1.0                # grow the wall inward
solid.use_even_offset = True
solid.material_offset = 1          # inner wall uses slot 2

boolean = pumpkin.modifiers.new("Carve Face", 'BOOLEAN')
boolean.operation = 'DIFFERENCE'
boolean.object = cutter
boolean.solver = 'MANIFOLD'
boolean.material_mode = 'INDEX'    # cut faces keep slot 3

# Bake: evaluated result → brand-new mesh
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
baked = bpy.data.meshes.new_from_object(pumpkin.evaluated_get(depsgraph),
                                       preserve_all_data_layers=True,
                                       depsgraph=depsgraph)
baked.name = "Pumpkin Carved"
old_mesh = pumpkin.data
pumpkin.modifiers.clear()
pumpkin.data = baked
bpy.data.meshes.remove(old_mesh)
# Make sure the new mesh has our 3 material slots (without resetting
# which face uses which slot)
while len(baked.materials) < 3:
    baked.materials.append(None)
for i, m in enumerate((skin, flesh, flesh)):
    baked.materials[i] = m

# Delete the cutter for good
bpy.data.objects.remove(cutter, do_unlink=True)
bpy.data.meshes.remove(cut_mesh)

# Keep the carved outlines crisp: every edge where the cut faces meet the
# skin or the inner wall gets a full crease (so smoothing won't round it)
# and is marked sharp (so the cut walls get clean shading).
bm = bmesh.new()
bm.from_mesh(baked)
crease = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
for e in bm.edges:
    if len(e.link_faces) == 2:
        a, b = e.link_faces
        if a.material_index != b.material_index:
            e[crease] = 1.0
            e.smooth = False
for f in bm.faces:
    f.smooth = True
bm.to_mesh(baked)
bm.free()

# Final smoothing that stays light: level 1 in the viewport, 2 in renders
subsurf = pumpkin.modifiers.new("Subdivision", 'SUBSURF')
subsurf.levels = 1
subsurf.render_levels = 2


# =====================================================================
# 4. STEM — tapered, ridged cylinder, then twisted and bent
# =====================================================================
stem_mesh = bpy.data.meshes.new("Stem")
bm = bmesh.new()
SIDES, LEVELS, HEIGHT = 12, 8, 0.45
rings = []
for i in range(LEVELS + 1):
    t = i / LEVELS
    radius = 0.13 * (1 - t) + 0.075 * t + 0.05 * (1 - t) ** 4   # wider base
    ring = []
    for k in range(SIDES):
        a = 2 * math.pi * k / SIDES
        r = radius * (1 + 0.10 * math.cos(6 * a))               # ridges
        ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), t * HEIGHT)))
    rings.append(ring)
for i in range(LEVELS):
    for k in range(SIDES):
        k2 = (k + 1) % SIDES
        bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
bm.faces.new(list(reversed(rings[0])))     # bottom cap
bm.faces.new(rings[-1])                    # top cap
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(stem_mesh)
bm.free()

stem = bpy.data.objects.new("Stem", stem_mesh)
scene.collection.objects.link(stem)
stem.parent = pumpkin                       # turns with the pumpkin
stem.location = (0, 0, SQUASH_Z * 0.72 - 0.06)   # sits in the top dent
for poly in stem_mesh.polygons:
    poly.use_smooth = True
stem_mesh.materials.append(stem_mat)

twist = stem.modifiers.new("Twist", 'SIMPLE_DEFORM')
twist.deform_method = 'TWIST'
twist.deform_axis = 'Z'            # twist around its own length
twist.angle = math.radians(60)

bend = stem.modifiers.new("Bend", 'SIMPLE_DEFORM')
bend.deform_method = 'BEND'
bend.deform_axis = 'Y'             # bend sideways (around the Y axis)
bend.angle = math.radians(55)

stem_sub = stem.modifiers.new("Subdivision", 'SUBSURF')
stem_sub.levels = 1
stem_sub.render_levels = 2


# =====================================================================
# 5. LIGHTING — big, soft area lights, low contrast
# =====================================================================
def add_light(name, kind, location, color, energy, parent=None, **extra):
    data = bpy.data.lights.new(name, kind)
    data.color = color
    data.energy = energy
    for key, value in extra.items():
        setattr(data, key, value)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.parent = parent
    return obj

def aim(obj, target=(0, 0, 0)):
    """Point a light/camera at a target point."""
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Candle: warm yellow point light INSIDE the pumpkin, near the bottom.
# A bigger soft radius + extra shadow filtering = smooth, grain-free glow.
# Shadows stay ON so the closed shell still blocks the light.
CANDLE_POS = (0, 0, -0.30)
add_light("Candle", 'POINT', CANDLE_POS, CANDLE_COLOR, CANDLE_POWER,
          parent=pumpkin, use_shadow=True, shadow_soft_size=0.22,
          shadow_filter_radius=3.0)

# Candle flame: a tiny glowing ball at the light, for a visible "hot core".
# It does not cast shadows, so it doesn't block the candle light.
fbm = bmesh.new()
bmesh.ops.create_uvsphere(fbm, u_segments=12, v_segments=8, radius=0.04)
flame_mesh = bpy.data.meshes.new("Candle Flame")
fbm.to_mesh(flame_mesh)
fbm.free()
flame_mesh.materials.append(flame_mat)
flame = bpy.data.objects.new("Candle Flame", flame_mesh)
scene.collection.objects.link(flame)
flame.parent = pumpkin
flame.location = CANDLE_POS
flame.scale = (1, 1, 1.6)                   # a little taller, like a flame
flame.visible_shadow = False

# Warm key light: big and soft, from the front-left
key = add_light("Key Light (warm)", 'AREA', (-3.5, -3.0, 2.5),
                (1.0, 0.82, 0.65), 160, size=5.0)
aim(key)

# Cool fill light: lavender-blue, big and soft, from the right
fill = add_light("Fill Light (lavender)", 'AREA', (4.0, -1.5, 1.0),
                 (0.62, 0.55, 1.0), 90, size=6.0)
aim(fill)

# Rim light: soft lavender-pink from behind, outlines the silhouette
rim = add_light("Rim Light", 'AREA', (1.5, 3.5, 2.5), (0.80, 0.60, 1.0), 300,
                size=5.0)
aim(rim)


# =====================================================================
# 6. BACKGROUND — painted-paper purple sky
# Two muted purples mixed by big soft noise (blotchy washes) plus a
# fine noise (paper grain). It's on the World, so it also gives the
# whole scene a gentle lavender ambient light.
# =====================================================================
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
if world.node_tree is None:
    world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
wn.clear()

w_coord = wn.new("ShaderNodeTexCoord");          w_coord.location = (-1000, 0)
w_blotch = wn.new("ShaderNodeTexNoise");         w_blotch.location = (-750, 150)
w_blotch.label = "Blotchy Washes"
w_blotch.inputs["Scale"].default_value = 2.5
w_blotch.inputs["Detail"].default_value = 3.0
w_blotch.inputs["Roughness"].default_value = 0.5
wl.new(w_coord.outputs["Generated"], w_blotch.inputs["Vector"])

w_ramp = wn.new("ShaderNodeValToRGB");           w_ramp.location = (-500, 150)
w_ramp.label = "Two Purples"
set_ramp(w_ramp, [
    (0.35, (0.035, 0.022, 0.060)),  # deeper muted purple
    (0.65, (0.080, 0.050, 0.110)),  # lighter dusty purple
])
wl.new(w_blotch.outputs["Fac"], w_ramp.inputs["Fac"])

w_grain = wn.new("ShaderNodeTexNoise");          w_grain.location = (-750, -150)
w_grain.label = "Paper Grain"
w_grain.inputs["Scale"].default_value = 60.0
w_grain.inputs["Detail"].default_value = 2.0
wl.new(w_coord.outputs["Generated"], w_grain.inputs["Vector"])

w_paper = wn.new("ShaderNodeMix");               w_paper.location = (-250, 50)
w_paper.data_type = 'RGBA'
w_paper.blend_type = 'OVERLAY'
sock(w_paper.inputs, "Factor").default_value = 0.15
wl.new(w_ramp.outputs["Color"], sock(w_paper.inputs, "A"))
wl.new(w_grain.outputs["Fac"], sock(w_paper.inputs, "B"))

w_bg = wn.new("ShaderNodeBackground");           w_bg.location = (0, 0)
w_bg.inputs["Strength"].default_value = 1.0
wl.new(sock(w_paper.outputs, "Result"), w_bg.inputs["Color"])
w_out = wn.new("ShaderNodeOutputWorld");         w_out.location = (250, 0)
wl.new(w_bg.outputs["Background"], w_out.inputs["Surface"])


# =====================================================================
# 7. CAMERA — front, slightly from above, vertical 9:16 for Shorts
# =====================================================================
cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 42
camera = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(camera)
camera.location = (0, -5.0, 1.6)
aim(camera, (0, 0, 0.1))
scene.camera = camera

scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.resolution_percentage = 100


# =====================================================================
# 8. RENDER SETTINGS — light EEVEE, smooth shadows, soft AgX colour
# =====================================================================
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 64
scene.eevee.taa_samples = 8 if FAST else 16   # viewport samples (fewer = smoother orbiting)
# FAST: the viewport draws at half resolution (4x fewer pixels) — the biggest
# speed-up on Retina / 4K screens. Final renders are NOT affected.
scene.render.preview_pixel_size = '2' if FAST else 'AUTO'
scene.eevee.use_raytracing = False       # off = much faster viewport
scene.eevee.use_shadows = True
scene.eevee.shadow_ray_count = 1 if FAST else 3   # soft-shadow quality (3 = less grain, but heavy)
scene.eevee.shadow_step_count = 6 if FAST else 12
scene.eevee.shadow_pool_size = '512'
# (EEVEE has no "Bloom" checkbox any more — the glow comes from the
#  Glare node in the compositor below.)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Base Contrast'   # softer than before


# =====================================================================
# 9. COMPOSITOR — the painterly / watercolor finish
# In Blender 5.x the compositor is a node group plugged into the scene,
# and the final image goes into a "Group Output" (it replaces the old
# Composite node).
# =====================================================================
comp = bpy.data.node_groups.new("Painterly Compositor", "CompositorNodeTree")
comp.interface.new_socket(name="Image", in_out='OUTPUT',
                          socket_type='NodeSocketColor')
scene.compositing_node_group = comp
cn, cl = comp.nodes, comp.links

X = 300   # horizontal spacing between nodes (keeps things tidy on screen)

render = cn.new("CompositorNodeRLayers");        render.location = (0, 0)

# Lens Distortion: a soft coloured halo on the edges
lens = cn.new("CompositorNodeLensdist");         lens.location = (X, 0)
lens.inputs["Dispersion"].default_value = 0.04

# Glare: Bloom — soft, wide glow (lower threshold = more things glow)
glare = cn.new("CompositorNodeGlare");           glare.location = (2 * X, 0)
glare.inputs["Type"].default_value = 'Bloom'
glare.inputs["Quality"].default_value = 'Low' if FAST else 'Medium'
glare.inputs["Threshold"].default_value = 0.9
glare.inputs["Smoothness"].default_value = 0.5
glare.inputs["Size"].default_value = 0.7
glare.inputs["Strength"].default_value = GLOW_STRENGTH

# Diamond Sharpen: just a little, so the strokes keep some definition
sharpen = cn.new("CompositorNodeFilter");        sharpen.location = (3 * X, 0)
sharpen.inputs["Type"].default_value = 'Diamond Sharpen'
sharpen.inputs["Factor"].default_value = 0.2

# Branch A — Kuwahara for fine brush strokes
kuw_a = cn.new("CompositorNodeKuwahara");        kuw_a.location = (4 * X, 200)
kuw_a.label = "Kuwahara A (detail)"
kuw_a.inputs["Type"].default_value = 'Classic' if FAST else 'Anisotropic'   # Classic is much lighter
kuw_a.inputs["Size"].default_value = KUWAHARA_SMALL
kuw_a.inputs["Uniformity"].default_value = 4
kuw_a.inputs["Sharpness"].default_value = 0.5
kuw_a.inputs["Eccentricity"].default_value = 1.0

# Branch B — Kuwahara for big, loose brush strokes
kuw_b = cn.new("CompositorNodeKuwahara");        kuw_b.location = (4 * X, -200)
kuw_b.label = "Kuwahara B (big strokes)"
kuw_b.inputs["Type"].default_value = 'Classic' if FAST else 'Anisotropic'
kuw_b.inputs["Size"].default_value = KUWAHARA_BIG

# Mix both branches (a bit more of the big strokes)
mix = cn.new("ShaderNodeMix");                   mix.location = (5 * X + 50, 0)
mix.data_type = 'RGBA'
mix.blend_type = 'MIX'
sock(mix.inputs, "Factor").default_value = 0.55

# Watercolor finish 1: lower the contrast and lift it slightly (airy)
soften = cn.new("CompositorNodeBrightContrast"); soften.location = (6 * X + 50, 0)
soften.label = "Wash Out (less contrast)"
soften.inputs["Brightness"].default_value = 0.0
soften.inputs["Contrast"].default_value = -6.0

# Watercolor finish 2: a small saturation boost so colours stay lively
saturate = cn.new("CompositorNodeHueSat");       saturate.location = (7 * X + 50, 0)
saturate.label = "Saturation Boost"
saturate.inputs["Saturation"].default_value = 1.25

# Outputs: final image + Viewer (for the backdrop / Image Editor)
group_out = cn.new("NodeGroupOutput");           group_out.location = (8 * X + 100, 100)
viewer = cn.new("CompositorNodeViewer");         viewer.location = (8 * X + 100, -150)

cl.new(render.outputs["Image"], lens.inputs["Image"])
cl.new(lens.outputs["Image"], glare.inputs["Image"])
cl.new(glare.outputs["Image"], sharpen.inputs["Image"])
cl.new(sharpen.outputs["Image"], kuw_a.inputs["Image"])
cl.new(sharpen.outputs["Image"], kuw_b.inputs["Image"])
cl.new(kuw_a.outputs["Image"], sock(mix.inputs, "A"))
cl.new(kuw_b.outputs["Image"], sock(mix.inputs, "B"))
cl.new(sock(mix.outputs, "Result"), soften.inputs["Image"])
cl.new(soften.outputs["Image"], saturate.inputs["Image"])
cl.new(saturate.outputs["Image"], group_out.inputs[0])
cl.new(saturate.outputs["Image"], viewer.inputs["Image"])


# =====================================================================
# 10. ANIMATION — one slow, seamless 360° turn
# Frame 1 = 0°, frame 121 = 360° (same as 0°), so frames 1–120 loop
# perfectly with no repeated frame.
# =====================================================================
scene.frame_start = 1
scene.frame_end = FRAMES
scene.render.fps = 30
scene.frame_set(1)

pumpkin.rotation_euler = (0, 0, 0)
pumpkin.keyframe_insert("rotation_euler", index=2, frame=1)
pumpkin.rotation_euler = (0, 0, 2 * math.pi)
pumpkin.keyframe_insert("rotation_euler", index=2, frame=FRAMES + 1)
pumpkin.rotation_euler = (0, 0, 0)

# Make the motion constant speed (Linear) instead of ease-in/ease-out.
# (Blender 5 stores keys in "layered actions", so we look in every channel bag.)
action = pumpkin.animation_data.action
for layer_ in action.layers:
    for strip in layer_.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'


# =====================================================================
# 11. WATERCOLOR STEM — same painted look as the pumpkin
#   (colours from dark brown at the base to yellow-green at the tip,
#    fibre streaks, lavender shadows and the pink rim glow)
# =====================================================================
STEM_BASE = 0.08                   # where the stem comes out of the pumpkin
STEM_TOP = 0.42                    # where the stem ends

# ---------------------------------------------------------------------
# 11a. Build the watercolor stem material
# ---------------------------------------------------------------------
old = bpy.data.materials.get("Stem Watercolor")
if old:
    bpy.data.materials.remove(old)
mat = bpy.data.materials.new("Stem Watercolor")
if mat.node_tree is None:
    mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
nodes.clear()

texco = nodes.new("ShaderNodeTexCoord");         texco.location = (-1600, 0)

# --- A) Colour from bottom to top ---
# Object Z = height along the stem: 0 where it leaves the pumpkin, 1 at the tip
sep = nodes.new("ShaderNodeSeparateXYZ");        sep.location = (-1400, 300)
links.new(texco.outputs["Object"], sep.inputs["Vector"])
height = nodes.new("ShaderNodeMapRange");        height.location = (-1200, 300)
height.label = "Height 0→1"
height.inputs["From Min"].default_value = STEM_BASE
height.inputs["From Max"].default_value = STEM_TOP
links.new(sep.outputs["Z"], height.inputs["Value"])

# Watercolor WASHES: big soft noise that makes the colour bands uneven
wash = nodes.new("ShaderNodeTexNoise");          wash.location = (-1200, 0)
wash.label = "Watercolor Washes"
wash.inputs["Scale"].default_value = 4.0
wash.inputs["Detail"].default_value = 2.0
links.new(texco.outputs["Object"], wash.inputs["Vector"])
wobble = nodes.new("ShaderNodeMix");             wobble.location = (-950, 250)
wobble.label = "Uneven Height"
wobble.data_type = 'FLOAT'
wobble.blend_type = 'MIX'
sock(wobble.inputs, "Factor").default_value = 0.25    # how wobbly the bands are
links.new(height.outputs["Result"], sock(wobble.inputs, "A"))
links.new(wash.outputs["Fac"], sock(wobble.inputs, "B"))

color_ramp = nodes.new("ShaderNodeValToRGB");    color_ramp.location = (-750, 250)
color_ramp.label = "Stem Colours (base → top)"
set_ramp(color_ramp, [
    (0.00, (0.34, 0.14, 0.04)),    # dark brown at the base
    (0.30, (0.55, 0.30, 0.09)),    # warm brown
    (0.60, (0.30, 0.36, 0.08)),    # dark olive green
    (0.95, (0.62, 0.70, 0.20)),    # light yellow-green at the top
])
links.new(sock(wobble.outputs, "Result"), color_ramp.inputs["Fac"])

# Low-contrast wash on top of the colour (like paint drying unevenly)
washes = nodes.new("ShaderNodeMix");             washes.location = (-500, 250)
washes.data_type = 'RGBA'
washes.blend_type = 'OVERLAY'
sock(washes.inputs, "Factor").default_value = 0.3
links.new(color_ramp.outputs["Color"], sock(washes.inputs, "A"))
links.new(wash.outputs["Fac"], sock(washes.inputs, "B"))

# --- B) Vertical fibre streaks ---
# Noise squashed sideways and stretched along Z = long thin streaks
stretch = nodes.new("ShaderNodeMapping");        stretch.location = (-1200, -300)
stretch.label = "Stretch Along Stem"
stretch.inputs["Scale"].default_value = (40.0, 40.0, 2.0)
links.new(texco.outputs["Object"], stretch.inputs["Vector"])
fibres = nodes.new("ShaderNodeTexNoise");        fibres.location = (-950, -300)
fibres.label = "Fibre Streaks"
fibres.inputs["Scale"].default_value = 1.0
fibres.inputs["Detail"].default_value = 3.0
links.new(stretch.outputs["Vector"], fibres.inputs["Vector"])

streaks = nodes.new("ShaderNodeMix");            streaks.location = (-250, 200)
streaks.data_type = 'RGBA'
streaks.blend_type = 'OVERLAY'
sock(streaks.inputs, "Factor").default_value = 0.45   # subtle
links.new(sock(washes.outputs, "Result"), sock(streaks.inputs, "A"))
links.new(fibres.outputs["Fac"], sock(streaks.inputs, "B"))
paint_color = sock(streaks.outputs, "Result")

# The streaks also make a gentle bump, so the stem feels fibrous
bump = nodes.new("ShaderNodeBump");              bump.location = (-500, -500)
bump.inputs["Strength"].default_value = 0.2
links.new(fibres.outputs["Fac"], bump.inputs["Height"])
bump_normal = bump.outputs["Normal"]

# --- C) Painted shading with lavender shadows (same as the pumpkin) ---
probe = nodes.new("ShaderNodeBsdfDiffuse");      probe.location = (0, -350)
probe.label = "Light Probe"
probe.inputs["Color"].default_value = (1, 1, 1, 1)
links.new(bump_normal, probe.inputs["Normal"])
to_rgb = nodes.new("ShaderNodeShaderToRGB");     to_rgb.location = (200, -350)
links.new(probe.outputs["BSDF"], to_rgb.inputs["Shader"])
to_bw = nodes.new("ShaderNodeRGBToBW");          to_bw.location = (380, -350)
links.new(to_rgb.outputs["Color"], to_bw.inputs["Color"])

steps = nodes.new("ShaderNodeValToRGB");         steps.location = (550, -350)
steps.label = "Paint Steps (light → paint)"
set_ramp(steps, [
    (0.00, (0.00, 0.00, 0.00)),    # in shadow → lavender
    (0.05, (0.50, 0.50, 0.50)),    # (a bit gentler than the pumpkin,
    (0.15, (0.85, 0.85, 0.85)),    #  because the stem's base sits in
    (0.35, (1.00, 1.00, 1.00)),    #  the shade of the top dent)
])
links.new(to_bw.outputs["Val"], steps.inputs["Fac"])

painted = nodes.new("ShaderNodeMix");            painted.location = (850, 100)
painted.label = "Lavender Shadows"
painted.data_type = 'RGBA'
painted.blend_type = 'MIX'
sock(painted.inputs, "A").default_value = (*SHADOW_COLOR, 1)
links.new(steps.outputs["Color"], sock(painted.inputs, "Factor"))
links.new(paint_color, sock(painted.inputs, "B"))

paint_emit = nodes.new("ShaderNodeEmission");    paint_emit.location = (1050, 100)
paint_emit.inputs["Strength"].default_value = 0.6
links.new(sock(painted.outputs, "Result"), paint_emit.inputs["Color"])

# Soft matte surface underneath: rough, almost no shine, no clear coat
bsdf = nodes.new("ShaderNodeBsdfPrincipled");    bsdf.location = (850, 650)
links.new(paint_color, bsdf.inputs["Base Color"])
links.new(bump_normal, bsdf.inputs["Normal"])
bsdf.inputs["Roughness"].default_value = 0.8
bsdf.inputs["Specular IOR Level"].default_value = 0.1
bsdf.inputs["Coat Weight"].default_value = 0.0

blend = nodes.new("ShaderNodeMixShader");        blend.location = (1300, 300)
blend.inputs["Factor"].default_value = 0.7       # 70% painted, 30% matte
links.new(bsdf.outputs["BSDF"], blend.inputs[1])
links.new(paint_emit.outputs["Emission"], blend.inputs[2])

# --- D) Lavender rim glow on the edges ---
layer = nodes.new("ShaderNodeLayerWeight");      layer.location = (850, -650)
layer.inputs["Blend"].default_value = 0.4
links.new(bump_normal, layer.inputs["Normal"])
rim_ramp = nodes.new("ShaderNodeValToRGB");      rim_ramp.location = (1050, -650)
rim_ramp.label = "Rim Width"
set_ramp(rim_ramp, [
    (0.55, (0, 0, 0)),
    (0.95, (1, 1, 1)),
])
links.new(layer.outputs["Facing"], rim_ramp.inputs["Fac"])
rim_strength = nodes.new("ShaderNodeMath");      rim_strength.location = (1300, -700)
rim_strength.operation = 'MULTIPLY'
rim_strength.inputs[1].default_value = 0.6
links.new(rim_ramp.outputs["Color"], rim_strength.inputs[0])
rim_emit = nodes.new("ShaderNodeEmission");      rim_emit.location = (1300, -500)
rim_emit.inputs["Color"].default_value = (*RIM_COLOR, 1)
links.new(rim_strength.outputs[0], rim_emit.inputs["Strength"])

add_rim = nodes.new("ShaderNodeAddShader");      add_rim.location = (1550, 0)
links.new(blend.outputs["Shader"], add_rim.inputs[0])
links.new(rim_emit.outputs["Emission"], add_rim.inputs[1])

out = nodes.new("ShaderNodeOutputMaterial");     out.location = (1800, 0)
links.new(add_rim.outputs["Shader"], out.inputs["Surface"])


# ---------------------------------------------------------------------
# 11b. Put it on the stem (replaces the simple stem material)
# ---------------------------------------------------------------------
old_mats = [m for m in stem.data.materials if m]
if len(stem.data.materials) == 0:
    stem.data.materials.append(mat)
else:
    for i in range(len(stem.data.materials)):
        stem.data.materials[i] = mat

# Tidy up: delete the old stem material if nothing else uses it
for m in old_mats:
    if m.users == 0:
        bpy.data.materials.remove(m)


# =====================================================================
# 12. VIEWPORT — Rendered mode + live compositor, look through camera
# =====================================================================
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'
                    space.shading.use_compositor = 'ALWAYS'
                    space.region_3d.view_perspective = 'CAMERA'

# Select the pumpkin so it's active in the Properties panel
bpy.context.view_layer.objects.active = pumpkin
pumpkin.select_set(True)

faces = len(pumpkin.data.polygons) * 4 + len(stem_mesh.polygons) * 4
print("")
print("Watercolor stem applied.")
print("Pumpkin ready!  (about %d faces in the viewport)" % faces)
print("Script version: v5   |   Quality mode: %s" % QUALITY)
print("The painterly compositor is ON (Viewport Shading → Compositor → 'Always').")
print("Still slow? Set Compositor to 'Disabled' while you orbit.")
print("For the final render: set QUALITY = \"FULL\" at the top and run again.")
