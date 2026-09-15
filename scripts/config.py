import bpy
import json
import os
import math
from mathutils import Matrix, Vector, Euler

# --- CONFIG ---
ARMATURE_NAME = "Armature"
OUTPUT_GLB    = "lsl_3d_model.glb"
POSES_DIR     = "poses"   # subfolder relative to the .blend file

_RIGHT_HAND_WORLD_REF = None
_LEFT_HAND_WORLD_REF  = None
SIGN_LIBRARY = {}

HEAD_EMPTY          = "Empty_Head"
CHEST_EMPTY         = "Empty_Chest"
LEFTEYE_EMPTY       = "Empty_LeftEye"
RIGHTEYE_EMPTY      = "Empty_RightEye"
RIGHTSHOULDER_EMPTY = "Empty_RightShoulder"
LEFTSHOULDER_EMPTY  = "Empty_LeftShoulder"

# RIGHT SIDE
RIGHTHAND_EMPTY = "Empty_RightHand"
RIGHTARM_EMPTY  = "Empty_RightArm"
RIGHT_FINGERS = [
    "Empty_RightHandThumb1", "Empty_RightHandThumb2", "Empty_RightHandThumb3",
    "Empty_RightHandIndex1", "Empty_RightHandIndex2", "Empty_RightHandIndex3",
    "Empty_RightHandMiddle1", "Empty_RightHandMiddle2", "Empty_RightHandMiddle3",
    "Empty_RightHandRing1", "Empty_RightHandRing2", "Empty_RightHandRing3",
    "Empty_RightHandPinky1", "Empty_RightHandPinky2", "Empty_RightHandPinky3"
]

# LEFT SIDE
LEFTHAND_EMPTY = "Empty_LeftHand"
LEFTARM_EMPTY  = "Empty_LeftArm"
LEFT_FINGERS = [
    "Empty_LeftHandThumb1", "Empty_LeftHandThumb2", "Empty_LeftHandThumb3",
    "Empty_LeftHandIndex1", "Empty_LeftHandIndex2", "Empty_LeftHandIndex3",
    "Empty_LeftHandMiddle1", "Empty_LeftHandMiddle2", "Empty_LeftHandMiddle3",
    "Empty_LeftHandRing1", "Empty_LeftHandRing2", "Empty_LeftHandRing3",
    "Empty_LeftHandPinky1", "Empty_LeftHandPinky2", "Empty_LeftHandPinky3"
]

FINGER_EMPTIES = RIGHT_FINGERS + LEFT_FINGERS

FACE_MESH_NAME = "Face"

# IK pole target positions and angles (used by setup_arm_pole_targets)
POLE_R_LOC   = (0.55, 0.4, 0.8)
POLE_L_LOC   = (-0.55, 0.4, 0.8)
POLE_R_ANGLE = 150   # degrees
POLE_L_ANGLE = 40    # degrees, changed from 45

# Arm empty Z rotation correction (degrees). Compensates for forearm bone rest matrix
# offset introduced by a fresh VRM import. Set to 0 if no correction is needed.
# Empirically: new import needs arm Z = 150 where old import used 270 → correction = -120.
ARM_ROT_Z_CORRECTION = -120

# Bone name prefixes to skip during bake (physics/spring bones — no constraints, viewer ignores them)
BAKE_EXCLUDE_PREFIXES = ["J_Sec_"]

# Bake frame constants — must match ARM_TRANS_FRAMES, ARM_RET_FRAMES, CLIP_FPS in viewer.html
ARM_TRANS_FRAMES = 8
ARM_RET_FRAMES   = 6
CLIP_FPS         = 24

EXPRESSION_MAP = {
    "neutral":     {"Fcl_BRW_Neutral": 1, "Fcl_EYE_Neutral": 1, "Fcl_MTH_Close": 1, "Fcl_MTH_Fun": 0.5},
    "happy":       {"Fcl_ALL_Joy": 1},
    "angry":       {"Fcl_ALL_Angry": 1},
    "sad":         {"Fcl_ALL_Sorrow": 1},
    "surprised":   {"Fcl_ALL_Surprised": 1},
    "smiling":     {"Fcl_ALL_Fun": 1},
    "questioning": {"Fcl_BRW_Surprised": 1, "Fcl_EYE_Spread": 0.3, "Fcl_MTH_Surprised": 0.3, "Fcl_MTH_Close": 1.5},
    "concerned":   {"Fcl_BRW_Sorrow": 0.8, "Fcl_MTH_U": 0.6, "Fcl_EYE_Angry": 0.5},
    "mth_m":       {"Fcl_MTH_Close": 8},
    "mth_f":       {"Fcl_MTH_Angry": 1.0},
    # Mouthing visemes — vowels
    "mth_a":       {"Fcl_MTH_A": 1.0},
    "mth_e":       {"Fcl_MTH_E": 1.0},
    "mth_i":       {"Fcl_MTH_I": 1.0},
    "mth_o":       {"Fcl_MTH_O": 1.0},
    "mth_u":       {"Fcl_MTH_U": 1.0},
    # Mouthing visemes — consonants
    "mth_b":       {"Fcl_MTH_Close": 1.0},
    "mth_c":       {"Fcl_MTH_I": 0.3, "Fcl_MTH_Close": 0.5},
    "mth_d":       {"Fcl_MTH_A": 0.3, "Fcl_MTH_Close": 0.3},
    "mth_g":       {"Fcl_MTH_A": 0.2},
    "mth_h":       {"Fcl_MTH_A": 0.5},
    "mth_j":       {"Fcl_MTH_I": 0.5},
    "mth_k":       {"Fcl_MTH_A": 0.2},
    "mth_l":       {"Fcl_MTH_A": 0.4},
    "mth_n":       {"Fcl_MTH_A": 0.2, "Fcl_MTH_Close": 0.2},
    "mth_p":       {"Fcl_MTH_Close": 1.0},
    "mth_r":       {"Fcl_MTH_A": 0.3},
    "mth_s":       {"Fcl_MTH_I": 0.3, "Fcl_MTH_Close": 0.5},
    "mth_t":       {"Fcl_MTH_A": 0.3, "Fcl_MTH_Close": 0.2},
}
