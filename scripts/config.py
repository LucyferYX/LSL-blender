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

HEAD_EMPTY = "Empty_Head"

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

# Bone name prefixes to skip during bake (physics/spring bones — no constraints, viewer ignores them)
BAKE_EXCLUDE_PREFIXES = ["J_Sec_"]

# Bake frame constants — must match ARM_TRANS_FRAMES, ARM_RET_FRAMES, CLIP_FPS in viewer.html
ARM_TRANS_FRAMES = 8
ARM_RET_FRAMES   = 6
CLIP_FPS         = 24

EXPRESSION_MAP = {
    "neutral":     "Fcl_ALL_Neutral",
    "happy":       "Fcl_ALL_Joy",
    "angry":       "Fcl_ALL_Angry",
    "sad":         "Fcl_ALL_Sorrow",
    "surprised":   "Fcl_ALL_Surprised",
    "smiling":     "Fcl_ALL_Fun",
    "questioning": {"Fcl_BRW_Joy": 0.8},
    "concerned":   {"Fcl_BRW_Sorrow": 0.8},
}
