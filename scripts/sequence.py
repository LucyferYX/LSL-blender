# --- SEQUENCE ---

def _apply_start_position(side, frame):
    """Apply the Start_Position sign from SIGN_LIBRARY so it stays in sync with signs.json."""
    sp = SIGN_LIBRARY.get("Start_Position", {})
    hd = sp.get(side, {})
    if not hd:
        return
    loc   = hd.get("location")
    ori   = hd.get("orientation")
    shape = hd.get("shape")
    if loc:
        load_pose(loc, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=True, apply_arm_rotation=False, keyframe_on_frame=frame)
    if ori:
        load_pose(ori, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=False, apply_arm_rotation=True, keyframe_on_frame=frame)
    if shape:
        load_pose(shape, side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=frame)


def _apply_pose_offsets(hd, side, frame):
    """Apply arm_rot_offset and hand_rot_offset deltas (degrees) from signs.json, then re-keyframe."""
    arm_name  = LEFTARM_EMPTY  if side == "left" else RIGHTARM_EMPTY
    hand_name = LEFTHAND_EMPTY if side == "left" else RIGHTHAND_EMPTY

    arm_rot  = hd.get("arm_rot_offset")
    hand_rot = hd.get("hand_rot_offset")

    if arm_rot:
        obj = bpy.data.objects.get(arm_name)
        if obj:
            dx = math.radians(arm_rot[0])
            dy = math.radians(arm_rot[1]) * (-1 if side == "left" else 1)
            dz = math.radians(arm_rot[2] if len(arm_rot) > 2 else 0) * (-1 if side == "left" else 1)
            obj.rotation_euler.x += dx
            obj.rotation_euler.y += dy
            obj.rotation_euler.z += dz
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    if hand_rot:
        obj = bpy.data.objects.get(hand_name)
        if obj:
            dx = math.radians(hand_rot[0])
            dy = math.radians(hand_rot[1]) * (-1 if side == "left" else 1)
            dz = math.radians(hand_rot[2] if len(hand_rot) > 2 else 0) * (-1 if side == "left" else 1)
            obj.rotation_euler.x += dx
            obj.rotation_euler.y += dy
            obj.rotation_euler.z += dz
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def lock_pose_at_frame(location, orientation, shape, frame, side="right", use_location=True, apply_orientation=True):
    hand_name, arm_name, finger_list = get_rig_info(side)

    if apply_orientation:
        load_pose(location, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=True, apply_arm_rotation=False,
                  keyframe_on_frame=frame, apply_location=use_location)
        load_pose(orientation, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=False, apply_arm_rotation=True,
                  keyframe_on_frame=frame)
    else:
        for part_name in [arm_name]:
            obj = bpy.data.objects.get(part_name)
            if obj:
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                obj.keyframe_insert(data_path="location", frame=frame)

        hand = bpy.data.objects.get(hand_name)
        if hand:
            hand.keyframe_insert(data_path="rotation_euler", frame=frame)

    load_pose(shape, side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=frame)

    if not use_location:
        obj = bpy.data.objects.get(hand_name)
        if obj:
            obj.keyframe_insert(data_path="location", frame=frame)


def create_sequence(sentence):
    reset_animation()

    current_frame = 1
    transition_time, mid_transition = 8, 4
    default_hold_time, pause_buffer = 10, 7

    _apply_start_position("right", 1)
    _apply_start_position("left",  1)
    keyframe_expression(None, 1)

    words = sentence.lower().split()
    prev_expression = None

    for word in words:
        data = SIGN_LIBRARY.get(word)
        if not data:
            continue

        hold_time   = data.get("duration", default_hold_time)
        head_action = data.get("head")
        chest_data  = data.get("chest")
        expression  = data.get("expression")
        _left_val   = data.get("left")
        is_mirror   = _left_val == "mirror_right" or (isinstance(_left_val, dict) and bool(_left_val.get("mirror_right")))

        target_frame   = current_frame + transition_time
        move_end_frame = target_frame + hold_time
        settle_frame   = move_end_frame + pause_buffer

        # Build per-side configs
        sides_config = {}
        for side in ["right", "left"]:
            hd = _resolve_hand_data(data, side)
            if hd is not None:
                sides_config[side] = hd

        # --- TRANSITION: location, then orientation, then shape ---
        # Right before left so _RIGHT_HAND_WORLD_REF is set for mirror computation.
        for side in ["right", "left"]:
            if side not in sides_config:
                continue
            hd = sides_config[side]
            loc_pose = hd["orientation"] if hd.get("shape") == "Start_Position" else hd["location"]
            load_pose(loc_pose, side=side, apply_arm=True, apply_fingers=False,
                      apply_arm_location=True, apply_arm_rotation=False, keyframe_on_frame=target_frame)
        for side in ["right", "left"]:
            if side not in sides_config:
                continue
            hd = sides_config[side]
            load_pose(hd["orientation"], side=side, apply_arm=True, apply_fingers=False,
                      apply_arm_location=False, apply_arm_rotation=True, keyframe_on_frame=target_frame)
            _apply_pose_offsets(hd, side, target_frame)
        for side, hd in sides_config.items():
            load_pose(hd["shape"], side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=target_frame)
        if expression != prev_expression:
            keyframe_expression(prev_expression, current_frame)
        keyframe_expression(expression, target_frame)

        signing_sides = {side for side, hd in sides_config.items() if hd.get("shape") != "Start_Position"}
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        for side in signing_sides:
            load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=current_frame + mid_transition)

        # --- HEAD ---
        animate_head(head_action, current_frame, target_frame, move_end_frame, settle_frame)

        # --- CHEST ---
        if chest_data:
            animate_chest(chest_data, current_frame, target_frame, move_end_frame, settle_frame)

        # --- EYES ---
        eyes_data = data.get("eyes")
        if eyes_data:
            animate_eyes(eyes_data, current_frame, target_frame, move_end_frame, settle_frame)

        # --- SHOULDERS ---
        right_shoulder = data.get("right_shoulder")
        left_shoulder  = data.get("left_shoulder")
        if right_shoulder or left_shoulder:
            animate_shoulders(right_shoulder, left_shoulder, current_frame, target_frame, move_end_frame, settle_frame)

        # --- MOVEMENT ---
        protect_rotation  = False
        per_side_end_shape = {}

        for side, hd in sides_config.items():
            move = hd.get("move")
            if not move:
                continue
            pr, es = dispatch_move_or_list(move, side, hd, target_frame, hold_time, is_mirror)
            protect_rotation |= pr
            if es:
                per_side_end_shape[side] = es

        # --- UNIFIED LOCKING ---
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        for frame in [move_end_frame, settle_frame]:
            for side, hd in sides_config.items():
                loc_pose  = hd["orientation"] if hd.get("shape") == "Start_Position" else hd["location"]
                lock_shape = per_side_end_shape.get(side, hd["shape"])
                lock_pose_at_frame(
                    loc_pose, hd["orientation"], lock_shape, frame,
                    side=side,
                    use_location=False,
                    apply_orientation=not protect_rotation
                )
                if not protect_rotation:
                    _apply_pose_offsets(hd, side, frame)

        # Hold expression through the sign — prevents BEZIER from fading early
        keyframe_expression(expression, settle_frame)

        current_frame = settle_frame + 2
        prev_expression = expression

    # --- RETURN TO NEUTRAL ---
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    for side in signing_sides:
        load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=current_frame + mid_transition)

    _apply_start_position("right", current_frame + 6)
    _apply_start_position("left",  current_frame + 6)
    keyframe_expression(None, current_frame + 6)

    fix_finger_interpolation()
    bpy.context.scene.frame_set(1)
    print(f"Sequence for '{word}' complete.")
