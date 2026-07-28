# --- RIG SETUP (run once per Blender session after opening the .blend file) ---

def setup_arm_pole_targets():
    """
    One-time rig setup: creates pole target empties and assigns them to the IK
    constraints on both forearm bones. Positions and angles are defined in config.py.
    """
    right_deg = POLE_R_ANGLE
    left_deg  = POLE_L_ANGLE

    # --- Create or reposition pole empties ---
    for name, loc in (
        ("Empty_RightArmPole", POLE_R_LOC),
        ("Empty_LeftArmPole",  POLE_L_LOC),
    ):
        obj = bpy.data.objects.get(name)
        if obj is None:
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=loc)
            bpy.context.active_object.name = name
        else:
            obj.location = loc

    armature = bpy.data.objects.get(ARMATURE_NAME)
    if armature is None:
        print(f"[Setup] ERROR: Armature '{ARMATURE_NAME}' not found.")
        return

    # Map each forearm bone to its pole empty and angle.
    # Only the IK constraint that targets Empty_RightHand / Empty_LeftHand
    # (the hand-position IK) gets the pole target — the arm-position IK is
    # left alone because it drives a single bone and pole targets only affect
    # chains of 2+ bones.
    FOREARM_IK_TARGETS = {
        "J_Bip_R_LowerArm": (RIGHTHAND_EMPTY, "Empty_RightArmPole", right_deg),
        "J_Bip_L_LowerArm": (LEFTHAND_EMPTY,  "Empty_LeftArmPole",  left_deg),
    }

    for bone_name, (ik_target_name, pole_name, angle_deg) in FOREARM_IK_TARGETS.items():
        pbone = armature.pose.bones.get(bone_name)
        if pbone is None:
            print(f"[Setup] Bone not found: {bone_name}")
            continue

        ik_target_obj = bpy.data.objects.get(ik_target_name)
        pole_obj      = bpy.data.objects.get(pole_name)

        found = False
        for con in pbone.constraints:
            if con.type != 'IK':
                continue
            if ik_target_obj and con.target != ik_target_obj:
                continue
            con.pole_target = pole_obj
            con.pole_angle  = math.radians(angle_deg)
            found = True

        if not found:
            print(f"[Setup] No matching IK constraint found on {bone_name} "
                  f"(expected target={ik_target_name})")

