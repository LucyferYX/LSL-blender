import bpy

ARMATURE_NAME = "Armature"  # Laura

print("Starting script.")

arm = bpy.data.objects.get(ARMATURE_NAME)
if not arm:
    print("ERROR: Armature not found"); raise

def pb(name):
    return arm.pose.bones.get(name)

def em(name):
    return bpy.data.objects.get(name)

def clear(bone_name):
    b = pb(bone_name)
    if b:
        for c in b.constraints[:]:
            b.constraints.remove(c)

def ik(bone_name, target_name, chain_count):
    b, t = pb(bone_name), em(target_name)
    if not b or not t: print(f"  SKIP IK {bone_name} → {target_name}"); return
    c = b.constraints.new('IK')
    c.target = t
    c.chain_count = chain_count

def dtrack(bone_name, target_name):
    b, t = pb(bone_name), em(target_name)
    if not b or not t: print(f"  SKIP DT {bone_name} → {target_name}"); return
    c = b.constraints.new('DAMPED_TRACK')
    c.target = t
    c.track_axis = 'TRACK_Y'

def copy_rot(bone_name, target_name):
    b, t = pb(bone_name), em(target_name)
    if not b or not t: print(f"  SKIP CR {bone_name} → {target_name}"); return
    c = b.constraints.new('COPY_ROTATION')
    c.target = t

# ── RIGHT ARM ────────────────────────────────────────────────────────────────
r_arm_bones = [
    "J_Bip_R_Shoulder", "J_Bip_R_UpperArm", "J_Bip_R_LowerArm", "J_Bip_R_Hand",
    "J_Bip_R_Index1", "J_Bip_R_Index2", "J_Bip_R_Index3",
    "J_Bip_R_Middle1","J_Bip_R_Middle2","J_Bip_R_Middle3",
    "J_Bip_R_Ring1",  "J_Bip_R_Ring2",  "J_Bip_R_Ring3",
    "J_Bip_R_Little1","J_Bip_R_Little2","J_Bip_R_Little3",
    "J_Bip_R_Thumb1", "J_Bip_R_Thumb2", "J_Bip_R_Thumb3",
]
for b in r_arm_bones: clear(b)

ik("J_Bip_R_Shoulder", "Empty_RightShoulder", 1)
ik("J_Bip_R_UpperArm", "Empty_RightArm",      1)
ik("J_Bip_R_LowerArm", "Empty_RightHand",     2)
copy_rot("J_Bip_R_LowerArm", "Empty_RightArm")   # forearm twist from arm empty
copy_rot("J_Bip_R_Hand", "Empty_RightHand")

# VRoid uses "Little" for pinky — mapped to existing Pinky empties
r_fingers = {
    "J_Bip_R_Index1": "Empty_RightHandIndex1",
    "J_Bip_R_Index2": "Empty_RightHandIndex2",
    "J_Bip_R_Index3": "Empty_RightHandIndex3",
    "J_Bip_R_Middle1":"Empty_RightHandMiddle1",
    "J_Bip_R_Middle2":"Empty_RightHandMiddle2",
    "J_Bip_R_Middle3":"Empty_RightHandMiddle3",
    "J_Bip_R_Ring1":  "Empty_RightHandRing1",
    "J_Bip_R_Ring2":  "Empty_RightHandRing2",
    "J_Bip_R_Ring3":  "Empty_RightHandRing3",
    "J_Bip_R_Little1":"Empty_RightHandPinky1",
    "J_Bip_R_Little2":"Empty_RightHandPinky2",
    "J_Bip_R_Little3":"Empty_RightHandPinky3",
    "J_Bip_R_Thumb1": "Empty_RightHandThumb1",
    "J_Bip_R_Thumb2": "Empty_RightHandThumb2",
    "J_Bip_R_Thumb3": "Empty_RightHandThumb3",
}
for bone, empty in r_fingers.items(): dtrack(bone, empty)

# ── LEFT ARM ─────────────────────────────────────────────────────────────────
l_arm_bones = [
    "J_Bip_L_Shoulder", "J_Bip_L_UpperArm", "J_Bip_L_LowerArm", "J_Bip_L_Hand",
    "J_Bip_L_Index1", "J_Bip_L_Index2", "J_Bip_L_Index3",
    "J_Bip_L_Middle1","J_Bip_L_Middle2","J_Bip_L_Middle3",
    "J_Bip_L_Ring1",  "J_Bip_L_Ring2",  "J_Bip_L_Ring3",
    "J_Bip_L_Little1","J_Bip_L_Little2","J_Bip_L_Little3",
    "J_Bip_L_Thumb1", "J_Bip_L_Thumb2", "J_Bip_L_Thumb3",
]
for b in l_arm_bones: clear(b)

ik("J_Bip_L_Shoulder", "Empty_LeftShoulder", 1)
ik("J_Bip_L_UpperArm", "Empty_LeftArm",      1)
ik("J_Bip_L_LowerArm", "Empty_LeftHand",     2)
copy_rot("J_Bip_L_LowerArm", "Empty_LeftArm")
copy_rot("J_Bip_L_Hand", "Empty_LeftHand")

l_fingers = {
    "J_Bip_L_Index1": "Empty_LeftHandIndex1",
    "J_Bip_L_Index2": "Empty_LeftHandIndex2",
    "J_Bip_L_Index3": "Empty_LeftHandIndex3",
    "J_Bip_L_Middle1":"Empty_LeftHandMiddle1",
    "J_Bip_L_Middle2":"Empty_LeftHandMiddle2",
    "J_Bip_L_Middle3":"Empty_LeftHandMiddle3",
    "J_Bip_L_Ring1":  "Empty_LeftHandRing1",
    "J_Bip_L_Ring2":  "Empty_LeftHandRing2",
    "J_Bip_L_Ring3":  "Empty_LeftHandRing3",
    "J_Bip_L_Little1":"Empty_LeftHandPinky1",
    "J_Bip_L_Little2":"Empty_LeftHandPinky2",
    "J_Bip_L_Little3":"Empty_LeftHandPinky3",
    "J_Bip_L_Thumb1": "Empty_LeftHandThumb1",
    "J_Bip_L_Thumb2": "Empty_LeftHandThumb2",
    "J_Bip_L_Thumb3": "Empty_LeftHandThumb3",
}
for bone, empty in l_fingers.items(): dtrack(bone, empty)

# ── HEAD ─────────────────────────────────────────────────────────────────────
clear("J_Bip_C_Head")
dtrack("J_Bip_C_Head", "Empty_Head")

# ── EYES — rotation drivers ───────────────────────────────────────────────────
# Eyes counter-rotate slightly against head movement so they appear more stable.
# Driven from Empty_Head directly so they react only to *changes* from rest,
# not the absolute rotation (which differs from the eye bone rest orientation).
#
# Tune these two constants if the effect is too strong or too subtle:
REST_LOC_Y  = 0.02   # Empty_Head Y location at neutral (metres)
LOC_Y_SCALE = 6.0    # radians/m  — loc_y delta → eye X counter-rotation (nod)
ROT_Z_SCALE = 0.5    # fraction   — rot_z delta → eye Z counter-rotation (shake)

head_empty = em("Empty_Head")

def _clear_eye_drivers(bone_name):
    if not arm.animation_data:
        return
    for fc in list(arm.animation_data.drivers):
        if f'pose.bones["{bone_name}"]' in fc.data_path:
            arm.animation_data.drivers.remove(fc)

def _transform_var(driver, name, obj, transform_type):
    v = driver.variables.new()
    v.name = name
    v.type = 'TRANSFORMS'
    v.targets[0].id = obj
    v.targets[0].transform_type = transform_type
    v.targets[0].transform_space = 'WORLD_SPACE'

for _eye_bone in ("J_Adj_L_FaceEye", "J_Adj_R_FaceEye"):
    _pbone = arm.pose.bones.get(_eye_bone)
    if not _pbone:
        print(f"  SKIP: {_eye_bone} not found"); continue

    _pbone.rotation_mode = 'XYZ'
    _clear_eye_drivers(_eye_bone)
    for _con in list(_pbone.constraints):          # remove any leftover constraints
        _pbone.constraints.remove(_con)

    # X — counter nod: when head loc_y drops, eyes drift slightly up
    _fc = arm.driver_add(f'pose.bones["{_eye_bone}"].rotation_euler', 0)
    _fc.driver.type = 'SCRIPTED'
    _transform_var(_fc.driver, "loc_y", head_empty, 'LOC_Y')
    _fc.driver.expression = f"-{LOC_Y_SCALE} * (loc_y - {REST_LOC_Y})"

    # Z — counter shake: when head rotates on Z, eyes drift slightly opposite
    _fc = arm.driver_add(f'pose.bones["{_eye_bone}"].rotation_euler', 2)
    _fc.driver.type = 'SCRIPTED'
    _transform_var(_fc.driver, "rot_z", head_empty, 'ROT_Z')
    _fc.driver.expression = f"-{ROT_Z_SCALE} * rot_z"

print("Bone constraints have been set.")

for _script in ("config.py", "setup.py"):
    _path = bpy.path.abspath(f"//scripts/{_script}")
    with open(_path) as _f:
        exec(compile(_f.read(), _path, 'exec'), globals())
setup_arm_pole_targets()

print("Pole targets have been set.")