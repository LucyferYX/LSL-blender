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
RIGHTHAND_EMPTY    = "Empty_RightHand"
RIGHTFOREARM_EMPTY = "Empty_RightForearm"
RIGHTARM_EMPTY     = "Empty_RightArm"
RIGHT_FINGERS = [
    "Empty_RightHandThumb1", "Empty_RightHandThumb2", "Empty_RightHandThumb3",
    "Empty_RightHandIndex1", "Empty_RightHandIndex2", "Empty_RightHandIndex3",
    "Empty_RightHandMiddle1", "Empty_RightHandMiddle2", "Empty_RightHandMiddle3",
    "Empty_RightHandRing1", "Empty_RightHandRing2", "Empty_RightHandRing3",
    "Empty_RightHandPinky1", "Empty_RightHandPinky2", "Empty_RightHandPinky3"
]

# LEFT SIDE
LEFTHAND_EMPTY    = "Empty_LeftHand"
LEFTFOREARM_EMPTY = "Empty_LeftForearm"
LEFTARM_EMPTY     = "Empty_LeftArm"
LEFT_FINGERS = [
    "Empty_LeftHandThumb1", "Empty_LeftHandThumb2", "Empty_LeftHandThumb3",
    "Empty_LeftHandIndex1", "Empty_LeftHandIndex2", "Empty_LeftHandIndex3",
    "Empty_LeftHandMiddle1", "Empty_LeftHandMiddle2", "Empty_LeftHandMiddle3",
    "Empty_LeftHandRing1", "Empty_LeftHandRing2", "Empty_LeftHandRing3",
    "Empty_LeftHandPinky1", "Empty_LeftHandPinky2", "Empty_LeftHandPinky3"
]

FINGER_EMPTIES = RIGHT_FINGERS + LEFT_FINGERS
