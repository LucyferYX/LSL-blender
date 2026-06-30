# --- SEQUENCE ---

def lock_pose_at_frame(location, orientation, shape, frame, side="right", use_location=True, apply_orientation=True):
    hand_name, forearm_name, arm_name, finger_list = get_rig_info(side)

    if apply_orientation:
        load_pose(location, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=True, apply_arm_rotation=False,
                  keyframe_on_frame=frame, apply_location=use_location)
        load_pose(orientation, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=False, apply_arm_rotation=True,
                  keyframe_on_frame=frame)
    else:
        for part_name in [arm_name, forearm_name]:
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

    load_pose("Start_Position", side="right", keyframe_on_frame=1)
    load_pose("Start_Position", side="left",  keyframe_on_frame=1)

    words = sentence.lower().split()

    for word in words:
        data = SIGN_LIBRARY.get(word)
        if not data:
            continue

        hold_time   = data.get("duration", default_hold_time)
        head_action = data.get("head")
        is_mirror   = data.get("left") == "mirror_right"

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
        for side, hd in sides_config.items():
            load_pose(hd["shape"], side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=target_frame)

        signing_sides = {side for side, hd in sides_config.items() if hd.get("shape") != "Start_Position"}
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        for side in signing_sides:
            load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=current_frame + mid_transition)

        # --- HEAD ---
        animate_head(head_action, current_frame, target_frame, move_end_frame, settle_frame)

        # --- MOVEMENT ---
        is_movement      = False
        protect_rotation = False

        for side, hd in sides_config.items():
            move = hd.get("move")
            if not move:
                continue

            move_type = move if isinstance(move, str) else move.get("type")

            if move_type == "slide":
                raw_dir   = move.get("direction", "left") if isinstance(move, dict) else "left"
                direction = _get_mirror_direction(raw_dir) if (is_mirror and side == "left") else raw_dir
                animate_slide(target_frame, hold_time, side=side, direction=direction)
                is_movement = True

            elif move_type == "small_slide":
                raw_dir     = move.get("direction", "left") if isinstance(move, dict) else "left"
                moves_count = move.get("moves", 2) if isinstance(move, dict) else 2
                direction   = _get_mirror_direction(raw_dir) if (is_mirror and side == "left") else raw_dir
                animate_small_slide(target_frame, hold_time, side=side, direction=direction, moves=moves_count)
                is_movement = True

            elif move_type == "checkmark":
                animate_checkmark(target_frame, hold_time, side=side)
                is_movement = True; protect_rotation = True

            elif move_type == "halfcircle":
                animate_halfcircle(target_frame, hold_time, side=side)
                is_movement = True; protect_rotation = True

            elif move_type == "s_shape":
                animate_s(target_frame, hold_time, side=side)
                is_movement = True; protect_rotation = True

            elif move_type == "point_down":
                animate_pointing_down(target_frame, hold_time, side=side)
                is_movement = True; protect_rotation = True

            elif move_type == "side_flip":
                animate_side_flip(target_frame, hold_time, side=side)
                is_movement = True; protect_rotation = True

        # --- UNIFIED LOCKING ---
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        for frame in [move_end_frame, settle_frame]:
            for side, hd in sides_config.items():
                loc_pose = hd["orientation"] if hd.get("shape") == "Start_Position" else hd["location"]
                lock_pose_at_frame(
                    loc_pose, hd["orientation"], hd["shape"], frame,
                    side=side,
                    use_location=not is_movement,
                    apply_orientation=not protect_rotation
                )

        current_frame = settle_frame + 2

    # --- RETURN TO NEUTRAL ---
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    for side in signing_sides:
        load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=current_frame + mid_transition)

    load_pose("Start_Position", side="right", apply_arm=True, apply_fingers=True, keyframe_on_frame=current_frame + 6)
    load_pose("Start_Position", side="left",  apply_arm=True, apply_fingers=True, keyframe_on_frame=current_frame + 6)

    fix_finger_interpolation()
    bpy.context.scene.frame_set(1)
    print(f"Sequence for '{word}' complete.")
