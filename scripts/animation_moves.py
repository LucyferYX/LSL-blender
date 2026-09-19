# --- ANIMATION MOVES ---

def fix_finger_interpolation():
    """Sets finger empties to Linear to prevent backward 'Bezier overshoot'."""
    for name in FINGER_EMPTIES:
        obj = bpy.data.objects.get(name)
        if obj and obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            if hasattr(action, "fcurves"):
                for fcurve in action.fcurves:
                    for kp in fcurve.keyframe_points:
                        kp.interpolation = 'LINEAR'
    # print("Finger interpolation set to LINEAR.")


def animate_head(head_action, start_transition, start_hold, end_hold, end_settle):
    head = bpy.data.objects.get(HEAD_EMPTY)
    if not head: return

    base_loc = (0, 0.02, 1.8)

    if head_action == "Head_Nod":
        target_loc = (base_loc[0], base_loc[1] - 0.02, base_loc[2])

        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=start_transition)
        head.location = target_loc
        head.keyframe_insert(data_path="location", frame=start_hold)
        head.location = target_loc
        head.keyframe_insert(data_path="location", frame=end_hold)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=end_settle)

        linear_frames = {start_hold, end_hold}
        bezier_frames  = {start_transition, end_settle}

    elif head_action == "Head_Yes":
        lift_loc = (base_loc[0], base_loc[1] + 0.02, base_loc[2])  # Y 0.04
        nod_loc  = (base_loc[0], base_loc[1] - 0.02, base_loc[2])  # Y 0.00
        lift_start_frame = start_transition + 3   # frame 4: head starts lifting
        lift_frame       = start_hold - 1         # frame 8: peak of lift
        nod_frame        = start_hold + 7         # frame 16: nod complete

        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=start_transition)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=lift_start_frame)
        head.location = lift_loc
        head.keyframe_insert(data_path="location", frame=lift_frame)
        head.location = lift_loc
        head.keyframe_insert(data_path="location", frame=start_hold)  # nod starts here
        head.location = nod_loc
        head.keyframe_insert(data_path="location", frame=nod_frame)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=end_hold)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=end_settle)

        linear_frames = {nod_frame, end_hold, end_settle}
        bezier_frames  = {start_transition, lift_start_frame, lift_frame, start_hold}

    elif head_action == "Head_No":
        base_rot  = (math.radians(90), 0, 0)
        shake_z   = math.radians(-10)
        mid_frame = start_hold + (end_hold - start_hold) // 2  # midpoint of hold

        head.rotation_euler = base_rot
        head.keyframe_insert(data_path="rotation_euler", frame=start_transition)
        head.rotation_euler = (base_rot[0], base_rot[1], base_rot[2] + shake_z)
        head.keyframe_insert(data_path="rotation_euler", frame=start_hold)
        head.rotation_euler = (base_rot[0], base_rot[1], base_rot[2] - shake_z)
        head.keyframe_insert(data_path="rotation_euler", frame=mid_frame)
        head.rotation_euler = base_rot
        head.keyframe_insert(data_path="rotation_euler", frame=end_hold)
        head.rotation_euler = base_rot
        head.keyframe_insert(data_path="rotation_euler", frame=end_settle)

        linear_frames = {start_hold, mid_frame, end_hold, end_settle}
        bezier_frames  = {start_transition}

    elif isinstance(head_action, dict):
        # Static pose: transition in, hold, transition out.
        # Only specify keys that differ from the default (loc_x/y/z, rot_x/y/z in degrees).
        base_rot = (math.radians(90), 0, 0)
        target_loc = (
            head_action.get("loc_x", base_loc[0]),
            head_action.get("loc_y", base_loc[1]),
            head_action.get("loc_z", base_loc[2]),
        )
        target_rot = (
            math.radians(head_action.get("rot_x", 90)),
            math.radians(head_action.get("rot_y", 0)),
            math.radians(head_action.get("rot_z", 0)),
        )

        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=start_transition)
        head.location = target_loc
        head.keyframe_insert(data_path="location", frame=start_hold)
        head.location = target_loc
        head.keyframe_insert(data_path="location", frame=end_hold)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=end_settle)

        head.rotation_euler = base_rot
        head.keyframe_insert(data_path="rotation_euler", frame=start_transition)
        head.rotation_euler = target_rot
        head.keyframe_insert(data_path="rotation_euler", frame=start_hold)
        head.rotation_euler = target_rot
        head.keyframe_insert(data_path="rotation_euler", frame=end_hold)
        head.rotation_euler = base_rot
        head.keyframe_insert(data_path="rotation_euler", frame=end_settle)

        linear_frames = {start_hold, end_hold}
        bezier_frames  = {start_transition, end_settle}

    else:
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=start_transition)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=start_hold)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=end_hold)
        head.location = base_loc
        head.keyframe_insert(data_path="location", frame=end_settle)

        linear_frames = {start_hold, end_hold}
        bezier_frames  = {start_transition, end_settle}

    if head.animation_data and head.animation_data.action:
        action = head.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "location" not in fcurve.data_path and "rotation_euler" not in fcurve.data_path:
                    continue
                for kp in fcurve.keyframe_points:
                    if kp.co[0] in linear_frames:
                        kp.interpolation = 'LINEAR'
                    elif kp.co[0] in bezier_frames:
                        kp.interpolation = 'BEZIER'


def animate_chest(chest_data, start_transition, start_hold, end_hold, end_settle):
    """Drives Empty_Chest rotation (x/y/z in degrees) for lean-forward/backward movements.
    chest_data: dict with optional rot_x, rot_y, rot_z keys (degrees). Base rotation is (0,0,0).
    Optional move_rot_x/y/z keys apply an additional delta during the move (start_hold → end_hold)."""
    chest = bpy.data.objects.get(CHEST_EMPTY)
    if not chest: return

    base_rot = (0.0, 0.0, 0.0)

    if isinstance(chest_data, dict):
        target_rot = (
            math.radians(chest_data.get("rot_x", 0)),
            math.radians(chest_data.get("rot_y", 0)),
            math.radians(chest_data.get("rot_z", 0)),
        )
        move_delta = (
            math.radians(chest_data.get("move_rot_x", 0)),
            math.radians(chest_data.get("move_rot_y", 0)),
            math.radians(chest_data.get("move_rot_z", 0)),
        )
        end_hold_rot = (
            target_rot[0] + move_delta[0],
            target_rot[1] + move_delta[1],
            target_rot[2] + move_delta[2],
        )
    else:
        target_rot = base_rot
        end_hold_rot = base_rot

    chest.rotation_euler = base_rot
    chest.keyframe_insert(data_path="rotation_euler", frame=start_transition)
    chest.rotation_euler = target_rot
    chest.keyframe_insert(data_path="rotation_euler", frame=start_hold)
    chest.rotation_euler = end_hold_rot
    chest.keyframe_insert(data_path="rotation_euler", frame=end_hold)
    chest.rotation_euler = base_rot
    chest.keyframe_insert(data_path="rotation_euler", frame=end_settle)

    if chest.animation_data and chest.animation_data.action:
        action = chest.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" not in fcurve.data_path:
                    continue
                for kp in fcurve.keyframe_points:
                    if kp.co[0] in {start_hold, end_hold}:
                        kp.interpolation = 'LINEAR'
                    elif kp.co[0] in {start_transition, end_settle}:
                        kp.interpolation = 'BEZIER'


def animate_eyes(eyes_data, start_transition, start_hold, end_hold, end_settle):
    """Drives Empty_LeftEye and Empty_RightEye rotation (x/y/z in degrees) for gaze direction.
    eyes_data: dict with optional rot_x, rot_y, rot_z keys (degrees). Base rotation is (0,0,0)."""
    left_eye  = bpy.data.objects.get(LEFTEYE_EMPTY)
    right_eye = bpy.data.objects.get(RIGHTEYE_EMPTY)
    if not left_eye and not right_eye: return

    base_rot = (0.0, 0.0, 0.0)

    if isinstance(eyes_data, dict):
        target_rot = (
            math.radians(eyes_data.get("rot_x", 0)),
            math.radians(eyes_data.get("rot_y", 0)),
            math.radians(eyes_data.get("rot_z", 0)),
        )
    else:
        target_rot = base_rot

    for eye in (left_eye, right_eye):
        if not eye: continue
        eye.rotation_euler = base_rot
        eye.keyframe_insert(data_path="rotation_euler", frame=start_transition)
        eye.rotation_euler = target_rot
        eye.keyframe_insert(data_path="rotation_euler", frame=start_hold)
        eye.rotation_euler = target_rot
        eye.keyframe_insert(data_path="rotation_euler", frame=end_hold)
        eye.rotation_euler = base_rot
        eye.keyframe_insert(data_path="rotation_euler", frame=end_settle)

        if eye.animation_data and eye.animation_data.action:
            action = eye.animation_data.action
            if hasattr(action, "fcurves"):
                for fcurve in action.fcurves:
                    if "rotation_euler" not in fcurve.data_path:
                        continue
                    for kp in fcurve.keyframe_points:
                        if kp.co[0] in {start_hold, end_hold}:
                            kp.interpolation = 'LINEAR'
                        elif kp.co[0] in {start_transition, end_settle}:
                            kp.interpolation = 'BEZIER'


def animate_shoulders(right_data, left_data, start_transition, start_hold, end_hold, end_settle):
    """Drives Empty_RightShoulder / Empty_LeftShoulder location for shoulder raise/lower movements.
    right_data / left_data: dict with optional loc_x, loc_y, loc_z keys (metres), or None.
    Deltas are relative to each empty's current rest position in the scene."""
    for data, empty_name in ((right_data, RIGHTSHOULDER_EMPTY), (left_data, LEFTSHOULDER_EMPTY)):
        if not data:
            continue
        shoulder = bpy.data.objects.get(empty_name)
        if not shoulder:
            continue

        base_loc = tuple(shoulder.location)
        target_loc = (
            base_loc[0] + data.get("loc_x", 0),
            base_loc[1] + data.get("loc_y", 0),
            base_loc[2] + data.get("loc_z", 0),
        )

        shoulder.location = base_loc
        shoulder.keyframe_insert(data_path="location", frame=start_transition)
        shoulder.location = target_loc
        shoulder.keyframe_insert(data_path="location", frame=start_hold)
        shoulder.location = target_loc
        shoulder.keyframe_insert(data_path="location", frame=end_hold)
        shoulder.location = base_loc
        shoulder.keyframe_insert(data_path="location", frame=end_settle)

        if shoulder.animation_data and shoulder.animation_data.action:
            action = shoulder.animation_data.action
            if hasattr(action, "fcurves"):
                for fcurve in action.fcurves:
                    if "location" not in fcurve.data_path:
                        continue
                    for kp in fcurve.keyframe_points:
                        if kp.co[0] in {start_hold, end_hold}:
                            kp.interpolation = 'LINEAR'
                        elif kp.co[0] in {start_transition, end_settle}:
                            kp.interpolation = 'BEZIER'


def animate_slide(start_frame, duration, side="right", direction="left", distance=0.15, moves=1):
    """Slides the hand empty along the X axis (left/right) or Z axis (up/down).
    moves=1 (default): single one-way translation.
    moves>1: oscillating nudge — wiggles in direction and back, repeated `moves` times."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    origin = wrist.location.copy()
    if direction == "left":
        dx, dz = distance, 0
    elif direction == "right":
        dx, dz = -distance, 0
    elif direction == "up":
        dx, dz = 0, distance
    else:  # "down"
        dx, dz = 0, -distance

    if moves == 1:
        wrist.keyframe_insert(data_path="location", frame=start_frame)
        wrist.location = (origin.x + dx, origin.y, origin.z + dz)
        wrist.keyframe_insert(data_path="location", frame=start_frame + duration)
    else:
        frames_per_move = duration / moves
        frames_per_half = frames_per_move / 2

        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        wrist.location = origin
        wrist.keyframe_insert(data_path="location", frame=start_frame)

        for i in range(moves):
            move_start   = start_frame + i * frames_per_move
            peak_frame   = move_start + frames_per_half
            return_frame = move_start + frames_per_move

            wrist.location = (origin.x + dx, origin.y, origin.z + dz)
            wrist.keyframe_insert(data_path="location", frame=int(peak_frame))

            wrist.location = origin
            wrist.keyframe_insert(data_path="location", frame=int(return_frame))

        if wrist.animation_data and wrist.animation_data.action:
            action = wrist.animation_data.action
            if hasattr(action, "fcurves"):
                for fcurve in action.fcurves:
                    if "location" in fcurve.data_path:
                        for kp in fcurve.keyframe_points:
                            if start_frame <= kp.co[0] <= start_frame + duration:
                                kp.interpolation     = 'BEZIER'
                                kp.handle_left_type  = 'AUTO'
                                kp.handle_right_type = 'AUTO'

        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'


def animate_wave(start_frame, duration, side="right", rot_x=0, rot_y=0, rot_z=0, loc_x=0, loc_y=0, loc_z=0, cycles=2,
                 arm_rot_x=0, arm_rot_y=0, arm_rot_z=0):
    """Oscillating hand wave: alternates ±rot and ±loc for `cycles` full swings.
    arm_rot_x/y/z: optional rotation delta (degrees) applied to the arm empty, oscillating in sync."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    origin_loc = wrist.location.copy()
    origin_rot = wrist.rotation_euler.copy()

    dx, dy, dz = _mirror_rot(math.radians(rot_x), math.radians(rot_y), math.radians(rot_z), side)
    dlx = -loc_x if side == "left" else loc_x
    dly = loc_y
    dlz = loc_z

    arm_obj = bpy.data.objects.get(_forearm_empty(side))
    dax, day, daz = _mirror_rot(math.radians(arm_rot_x), math.radians(arm_rot_y), math.radians(arm_rot_z), side)
    has_arm_rot   = (dax != 0 or day != 0 or daz != 0) and arm_obj
    arm_origin_rot = arm_obj.rotation_euler.copy() if has_arm_rot else None

    total_peaks  = int(cycles * 2)              # e.g. cycles=2 → 4 peaks; cycles=1.5 → 3 peaks
    half_cycle   = (total_peaks % 2 == 1)       # odd peaks → ends displaced, no return to origin
    step         = duration / (total_peaks if half_cycle else total_peaks + 1)
    end_frame    = start_frame + duration

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

    wrist.location = origin_loc
    wrist.rotation_euler = origin_rot
    wrist.keyframe_insert(data_path="location",       frame=start_frame)
    wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    if has_arm_rot:
        arm_obj.rotation_euler = arm_origin_rot
        arm_obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    for i in range(total_peaks):
        sign = 1 if i % 2 == 0 else -1
        f = end_frame if (half_cycle and i == total_peaks - 1) else start_frame + int((i + 1) * step)
        wrist.location       = (origin_loc.x + sign * dlx, origin_loc.y + sign * dly, origin_loc.z + sign * dlz)
        wrist.rotation_euler = (origin_rot.x + sign * dx, origin_rot.y + sign * dy, origin_rot.z + sign * dz)
        wrist.keyframe_insert(data_path="location",       frame=f)
        wrist.keyframe_insert(data_path="rotation_euler", frame=f)
        if has_arm_rot:
            arm_obj.rotation_euler = (arm_origin_rot.x + sign * dax, arm_origin_rot.y + sign * day, arm_origin_rot.z + sign * daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f)

    if not half_cycle:
        wrist.location = origin_loc
        wrist.rotation_euler = origin_rot
        wrist.keyframe_insert(data_path="location",       frame=end_frame)
        wrist.keyframe_insert(data_path="rotation_euler", frame=end_frame)
        if has_arm_rot:
            arm_obj.rotation_euler = arm_origin_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "location" not in fcurve.data_path and "rotation_euler" not in fcurve.data_path:
                    continue
                for kp in fcurve.keyframe_points:
                    if start_frame <= kp.co[0] <= end_frame:
                        kp.interpolation     = 'BEZIER'
                        kp.handle_left_type  = 'AUTO'
                        kp.handle_right_type = 'AUTO'
                fcurve.update()
    if has_arm_rot and arm_obj.animation_data and arm_obj.animation_data.action:
        action = arm_obj.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" not in fcurve.data_path:
                    continue
                for kp in fcurve.keyframe_points:
                    if start_frame <= kp.co[0] <= end_frame:
                        kp.interpolation     = 'BEZIER'
                        kp.handle_left_type  = 'AUTO'
                        kp.handle_right_type = 'AUTO'
                fcurve.update()


def animate_checkmark(start_frame, duration, side="right",
                      rot1_x=0, rot1_y=30, rot1_z=-30,
                      rot2_x=0, rot2_y=0,  rot2_z=-75):
    r"""Wrist sweeps: natural pose → rot1 (\) → rot2 (/) forming a \/ checkmark arc.
    All rot values in degrees, mirrored automatically for the left hand.
    Override any value per sign: {"type": "checkmark", "rot1_x": 20, "rot1_z": 15, "rot2_z": -15}"""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    mid_frame = start_frame + (duration // 2)
    end_frame  = start_frame + duration
    base_rot   = wrist.rotation_euler.copy()
    d1x, d1y, d1z = _mirror_rot(math.radians(rot1_x), math.radians(rot1_y), math.radians(rot1_z), side)
    d2x, d2y, d2z = _mirror_rot(math.radians(rot2_x), math.radians(rot2_y), math.radians(rot2_z), side)

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    wrist.rotation_euler = base_rot
    wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    wrist.rotation_euler = (base_rot.x + d1x, base_rot.y + d1y, base_rot.z + d1z)
    wrist.keyframe_insert(data_path="rotation_euler", frame=mid_frame)
    wrist.rotation_euler = (base_rot.x + d2x, base_rot.y + d2y, base_rot.z + d2z)
    wrist.keyframe_insert(data_path="rotation_euler", frame=end_frame)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if start_frame <= kp.co[0] <= end_frame:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'AUTO'


def animate_halfcircle(start_frame, duration, side="right", direction="inner"):
    """C-curve arc: finger traces from pointing-up to pointing-forwards.

    direction="inner" is the default D-sign arc; "outer" flips the rotation direction
    so the arc curves the opposite way (independent of which hand performs it).
    End: hand left in pointing-forwards position; follow with {"type": "flip", "y": -90, "settle": false} for the upstroke.
    """
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    start_rot = wrist.rotation_euler.copy()

    f1 = start_frame
    f2 = start_frame + int(duration * 0.25)
    f3 = start_frame + int(duration * 0.50)
    f4 = start_frame + int(duration * 0.75)
    f5 = start_frame + duration

    def r(dx, dy, dz):
        ddx, ddy, ddz = _mirror_rot(math.radians(dx), math.radians(dy), math.radians(dz), side)
        if direction == "outer":
            ddx = -ddx  # mirror the wrist tilt (X) and curve direction (Z); Y (forward) stays the same
            ddz = -ddz
        return (start_rot.x + ddx, start_rot.y + ddy, start_rot.z + ddz)

    for frame, rot in [
        (f1, r(  0,  0,  0)),   # 0%
        (f2, r(  0, 40, 35)),   # 25%  — user-confirmed abs (270, 220, -55)
        (f3, r(-20, 60, 60)),   # 50%  — user-confirmed abs (250, 240, -30)
        (f4, r(-50, 70, 75)),   # 75%  — user-confirmed abs (220, 250, -15)
        (f5, r(  0, 90,  0)),   # 100%
    ]:
        wrist.rotation_euler = rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=frame)

    action = wrist.animation_data.action if wrist.animation_data else None
    if action:
        def _apply_to_fcurves(fcurves):
            for fc in fcurves:
                if "rotation_euler" not in fc.data_path:
                    continue
                for kp in fc.keyframe_points:
                    if kp.co[0] in (f2, f3, f4):
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = 'AUTO'
                        kp.handle_right_type = 'AUTO'
                    elif kp.co[0] in (f1, f5):
                        kp.interpolation = 'LINEAR'
                fc.update()

        if hasattr(action, 'fcurves'):
            _apply_to_fcurves(action.fcurves)
        else:
            for layer in getattr(action, 'layers', []):
                for strip in layer.strips:
                    for slot in getattr(action, 'slots', []):
                        cb = strip.channelbag(slot, ensure=False)
                        if cb:
                            _apply_to_fcurves(cb.fcurves)



def animate_s(start_frame, duration, side="right"):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    start_rot = wrist.rotation_euler.copy()

    t_top = int(duration * 0.3); t_spine = int(duration * 0.3)
    f1=start_frame; f2=f1+int(t_top*0.5); f3=f1+t_top
    f4=f3+int(t_spine*0.5); f5=f3+t_spine
    f6=f5+int((duration-t_top-t_spine)*0.6); f7=start_frame+duration

    def r(dx, dy, dz):
        ddx, ddy, ddz = _mirror_rot(math.radians(dx), math.radians(dy), math.radians(dz), side)
        return (start_rot.x + ddx, start_rot.y + ddy, start_rot.z + ddz)

    keyframes = [
        (f1, r(-25, -25, 0)), (f2, r(  0, -40, 0)), (f3, r( 25, -25, 0)),
        (f4, r(  0,   0, 0)), (f5, r(-25,  25, 0)), (f6, r(  0,  40, 0)),
        (f7, r( 25,  25, 0)),
    ]
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    for frame, rot in keyframes:
        wrist.rotation_euler = rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=frame)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if start_frame <= kp.co[0] <= f7:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'AUTO'


def _forearm_empty(side):
    return LEFTARM_EMPTY if side == "left" else RIGHTARM_EMPTY


def _set_bezier_on_object(obj, f_start, f_end):
    if obj and obj.animation_data and obj.animation_data.action:
        fcurves = getattr(obj.animation_data.action, "fcurves", None)
        if fcurves:
            for fcurve in fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if f_start <= kp.co[0] <= f_end:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'AUTO'



def animate_finger_wiggle(start_frame, duration, side="right", shape_1="Hand_B", shape_2="Hand_F", cycles=3, use_relaxed=True,
                          relaxed_fingers=None,
                          rot_x=0, rot_y=0, rot_z=0, loc_x=0, loc_y=0, loc_z=0):
    """Alternates between two finger shapes for 'cycles' complete oscillations.
    cycles accepts .5 increments: cycles=1.5 does 3 half-steps, ending on shape_2.
    use_relaxed=True (default): inserts Hand_Relaxed at each midpoint to prevent finger twisting.
    use_relaxed=False: direct linear transition between shapes, no intermediate keyframe.
    rot_x/y/z: optional rotation delta (degrees) applied to the hand empty linearly over the duration.
    loc_x/y/z: optional location delta applied to the hand empty linearly over the duration.
      loc_x is negated for the left hand; loc_y/loc_z are symmetric."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    dlx = -loc_x if side == "left" else loc_x
    dly, dlz = loc_y, loc_z
    dx, dy, dz = _mirror_rot(math.radians(rot_x), math.radians(rot_y), math.radians(rot_z), side)
    has_loc = wrist and (dlx != 0 or dly != 0 or dlz != 0)
    has_rot = wrist and (dx != 0 or dy != 0 or dz != 0)

    if has_loc:
        start_loc = wrist.location.copy()
        wrist.keyframe_insert(data_path="location", frame=start_frame)
    if has_rot:
        start_rot = wrist.rotation_euler.copy()
        wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    total_halves = int(cycles * 2)
    frames_per_half = duration / total_halves
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for i in range(1, total_halves + 1):
        frame = int(start_frame + i * frames_per_half)
        t = (frame - start_frame) / duration
        if use_relaxed:
            mid_frame = int(start_frame + (i - 0.5) * frames_per_half)
            t_mid = (mid_frame - start_frame) / duration
            if has_loc:
                wrist.location = (start_loc.x + dlx * t_mid, start_loc.y + dly * t_mid, start_loc.z + dlz * t_mid)
                wrist.keyframe_insert(data_path="location", frame=mid_frame)
            if has_rot:
                wrist.rotation_euler = (start_rot.x + dx * t_mid, start_rot.y + dy * t_mid, start_rot.z + dz * t_mid)
                wrist.keyframe_insert(data_path="rotation_euler", frame=mid_frame)
            _rf = relaxed_fingers if relaxed_fingers is not None else ["Index", "Middle", "Ring", "Pinky"]
            load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=mid_frame,
                      filter_fingers=_rf)
        if has_loc:
            wrist.location = (start_loc.x + dlx * t, start_loc.y + dly * t, start_loc.z + dlz * t)
            wrist.keyframe_insert(data_path="location", frame=frame)
        if has_rot:
            wrist.rotation_euler = (start_rot.x + dx * t, start_rot.y + dy * t, start_rot.z + dz * t)
            wrist.keyframe_insert(data_path="rotation_euler", frame=frame)
        shape = shape_2 if i % 2 == 1 else shape_1
        load_pose(shape, side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=frame)


def animate_flip(start_frame, duration, side="right",
                 rot_x=0, rot_y=0, rot_z=0,
                 loc_x=0, loc_y=0, loc_z=0,
                 arm_rot_x=0, arm_rot_y=0, arm_rot_z=0,
                 settle=True, use_quaternion=False,
                 rot_end_pct=None, loc_end_pct=None):
    """Wrist flip by the given degrees on each axis, with optional location delta.
    Rotation is mirrored via _mirror_rot; loc_x is negated for left hand, loc_y/loc_z are applied as-is.
    arm_rot_x/y/z: optional rotation delta (degrees) applied to the arm empty (mirrored automatically).
    use_quaternion=True: applies rotation via quaternion SLERP — correct at any orientation including
      gimbal lock (Y≈±90°). Default False preserves existing Euler-addition behaviour for all signs.
    settle=True: 3 keyframes with ease-back at end; settle=False: clean linear 2-keyframe move.
    rot_end_pct: fraction of duration at which rotation finishes (e.g. 0.5 = halfway through the sign).
      Location continues independently to its normal end. Omit to use standard 70%/100% timing.
    loc_end_pct: fraction of duration at which location translation finishes (e.g. 0.6).
      Omit to use standard 70%/100% timing."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    start_rot  = wrist.rotation_euler.copy()
    start_loc  = wrist.location.copy()
    f_start    = start_frame
    f_end      = start_frame + duration
    dx, dy, dz = _mirror_rot(math.radians(rot_x), math.radians(rot_y), math.radians(rot_z), side)
    dlx = -loc_x if side == "left" else loc_x
    dly, dlz = loc_y, loc_z
    has_loc = dlx != 0 or dly != 0 or dlz != 0

    arm_obj = bpy.data.objects.get(_forearm_empty(side))
    dax, day, daz = _mirror_rot(math.radians(arm_rot_x), math.radians(arm_rot_y), math.radians(arm_rot_z), side)
    has_arm_rot   = dax != 0 or day != 0 or daz != 0
    arm_start_rot = arm_obj.rotation_euler.copy() if arm_obj else None

    # Compute independent end frames for rotation and location.
    # rot_end_pct / loc_end_pct override the 70% hit; settle adds 2 frames of ease-back after the hit.
    # When omitted, both default to the standard settle (70% hit, 100% ease-back) or linear (100% hit).
    if rot_end_pct is not None:
        f_rot_hit    = start_frame + int(duration * rot_end_pct)
        f_rot_settle = f_rot_hit + 2 if settle else f_rot_hit
    else:
        f_rot_hit    = start_frame + int(duration * 0.70) if settle else f_end
        f_rot_settle = f_end

    if loc_end_pct is not None:
        f_loc_hit    = start_frame + int(duration * loc_end_pct)
        f_loc_settle = f_loc_hit + 2 if settle else f_loc_hit
    else:
        f_loc_hit    = start_frame + int(duration * 0.70) if settle else f_end
        f_loc_settle = f_end

    if use_quaternion:
        # Stepped SLERP: 8 small linear steps keep each quat-to-Euler conversion numerically
        # close to the previous frame, avoiding the wild spins a single large-angle conversion
        # produces near gimbal lock (Y ≈ ±90°/270°).
        sq         = start_rot.to_quaternion()
        tq         = sq @ Euler((dx, dy, dz), 'XYZ').to_quaternion()
        span       = f_rot_hit - f_start
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        prev_euler = start_rot.copy()
        for i in range(9):  # i = 0..8 → 8 equal steps
            t     = i / 8
            frame = f_start + round(t * span)
            iq    = sq.slerp(tq, t)
            euler = iq.to_euler('XYZ', prev_euler)
            wrist.rotation_euler = euler
            wrist.keyframe_insert(data_path="rotation_euler", frame=frame)
            prev_euler = euler
        if settle:
            wrist.rotation_euler = sq.slerp(tq, 0.93).to_euler('XYZ', prev_euler)
            wrist.keyframe_insert(data_path="rotation_euler", frame=f_rot_settle)
        if has_loc:
            wrist.location = start_loc
            wrist.keyframe_insert(data_path="location", frame=f_start)
            wrist.location = (start_loc.x + dlx, start_loc.y + dly, start_loc.z + dlz)
            wrist.keyframe_insert(data_path="location", frame=f_loc_hit)
            if settle:
                wrist.location = (start_loc.x + dlx * 0.93, start_loc.y + dly * 0.93, start_loc.z + dlz * 0.93)
                wrist.keyframe_insert(data_path="location", frame=f_loc_settle)
        if has_arm_rot and arm_obj:
            arm_obj.rotation_euler = arm_start_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
            arm_obj.rotation_euler = (arm_start_rot.x + dax, arm_start_rot.y + day, arm_start_rot.z + daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_rot_hit)
            if settle:
                arm_obj.rotation_euler = (arm_start_rot.x + dax * 0.93, arm_start_rot.y + day * 0.93, arm_start_rot.z + daz * 0.93)
                arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_rot_settle)
            _set_bezier_on_object(arm_obj, f_start, f_rot_settle)
        return

    target_rot = Euler((start_rot.x + dx,        start_rot.y + dy,        start_rot.z + dz),        'XYZ')
    settle_rot = Euler((start_rot.x + dx * 0.93, start_rot.y + dy * 0.93, start_rot.z + dz * 0.93), 'XYZ')

    if settle:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        wrist.rotation_euler = start_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_start)
        wrist.rotation_euler = target_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_rot_hit)
        wrist.rotation_euler = settle_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_rot_settle)
        if has_loc:
            wrist.location = start_loc
            wrist.keyframe_insert(data_path="location", frame=f_start)
            wrist.location = (start_loc.x + dlx,        start_loc.y + dly,        start_loc.z + dlz)
            wrist.keyframe_insert(data_path="location", frame=f_loc_hit)
            wrist.location = (start_loc.x + dlx * 0.93, start_loc.y + dly * 0.93, start_loc.z + dlz * 0.93)
            wrist.keyframe_insert(data_path="location", frame=f_loc_settle)
        if has_arm_rot and arm_obj:
            arm_obj.rotation_euler = arm_start_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
            arm_obj.rotation_euler = (arm_start_rot.x + dax,        arm_start_rot.y + day,        arm_start_rot.z + daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_rot_hit)
            arm_obj.rotation_euler = (arm_start_rot.x + dax * 0.93, arm_start_rot.y + day * 0.93, arm_start_rot.z + daz * 0.93)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_rot_settle)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        _set_bezier_on_object(wrist, f_start, max(f_rot_settle, f_loc_settle))
        if has_arm_rot and arm_obj:
            _set_bezier_on_object(arm_obj, f_start, f_rot_settle)
    else:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        wrist.rotation_euler = start_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_start)
        wrist.rotation_euler = target_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_rot_hit)
        if has_loc:
            wrist.location = start_loc
            wrist.keyframe_insert(data_path="location", frame=f_start)
            wrist.location = (start_loc.x + dlx, start_loc.y + dly, start_loc.z + dlz)
            wrist.keyframe_insert(data_path="location", frame=f_loc_hit)
        if has_arm_rot and arm_obj:
            arm_obj.rotation_euler = arm_start_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
            arm_obj.rotation_euler = (arm_start_rot.x + dax, arm_start_rot.y + day, arm_start_rot.z + daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_rot_hit)
        action = wrist.animation_data.action if wrist.animation_data else None
        if action:
            def _apply_linear(fcurves):
                for fc in fcurves:
                    if "rotation_euler" not in fc.data_path and "location" not in fc.data_path:
                        continue
                    for kp in fc.keyframe_points:
                        if kp.co[0] in (f_start, f_rot_hit, f_loc_hit):
                            kp.interpolation = 'LINEAR'
                    fc.update()
            if hasattr(action, 'fcurves'):
                _apply_linear(action.fcurves)
            else:
                for layer in getattr(action, 'layers', []):
                    for strip in layer.strips:
                        for slot in getattr(action, 'slots', []):
                            cb = strip.channelbag(slot, ensure=False)
                            if cb:
                                _apply_linear(cb.fcurves)


def animate_circle(start_frame, duration, side="right", plane="xz",
                   radius_a=20, radius_b=None, cycles=2, direction="cw",
                   settle=False, phase=0, arc=1.0):
    """Rotates the hand empty in a circular pattern across two rotation axes simultaneously.
    plane:     which rotation axis pair: "xz" (rot_x + rot_z, default), "xy" (rot_x + rot_y),
               "yz" (rot_y + rot_z).
    radius_a:  amplitude in degrees on the first axis of the plane.
    radius_b:  amplitude in degrees on the second axis; None = same as radius_a (circle).
               Different values produce an oval — e.g. radius_a=30, radius_b=10 for a
               wide-but-shallow rotation arc.
    cycles:    number of complete rotations.
    direction: "cw" or "ccw". Mirrored automatically for left hand.
    settle:    if True, eases the wrist smoothly into the final resting position after the
               last cycle (EASE_IN on the last keyframe only — inter-cycle transitions unchanged).
    phase:     starting offset in degrees around the circle (0 = bottom of the path,
               90 = 1/4 into the circle, etc.). The wrist stays at its current orientation
               at t=0 regardless of phase.
    arc:       fraction of the full circle to trace (1.0 = complete circle, 0.75 = 3/4, etc.).
               Values < 1.0 leave the wrist at a non-zero offset unless settle=True."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    if radius_b is None:
        radius_b = radius_a

    origin_rot = wrist.rotation_euler.copy()
    plane_axes = {"xz": (0, 2), "xy": (0, 1), "yz": (1, 2)}
    idx_a, idx_b = plane_axes.get(plane, (0, 2))

    ra = math.radians(radius_a)
    rb = math.radians(radius_b)
    phase_rad = math.radians(phase)

    sign = -1.0 if direction == "cw" else 1.0
    sign_a = sign * (-1.0 if (side == "left" and idx_a > 0) else 1.0)
    sign_b =  1.0 * (-1.0 if (side == "left" and idx_b > 0) else 1.0)

    n_steps   = cycles * 8
    arc_steps = max(1, round(arc * n_steps))
    end_frame = start_frame + duration

    if settle:
        loop_steps     = max(1, arc_steps - 1)
        loop_end_frame = round(start_frame + duration * 0.80)
    else:
        loop_steps     = arc_steps
        loop_end_frame = end_frame

    # final arc position (= origin only when arc=1.0 and cycles is whole number)
    t_final = phase_rad + arc * cycles * 2 * math.pi
    final_rot = list(origin_rot)
    final_rot[idx_a] += sign_a * ra * (math.sin(t_final) - math.sin(phase_rad))
    final_rot[idx_b] += sign_b * rb * (math.cos(phase_rad) - math.cos(t_final))

    inserted = set()
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

    for i in range(loop_steps + 1):
        t     = phase_rad + (i / arc_steps) * arc * cycles * 2 * math.pi
        frame = round(start_frame + (i / loop_steps) * (loop_end_frame - start_frame)) if loop_steps > 0 else start_frame
        if frame in inserted:
            continue
        inserted.add(frame)
        rot = list(origin_rot)
        rot[idx_a] += sign_a * ra * (math.sin(t) - math.sin(phase_rad))
        rot[idx_b] += sign_b * rb * (math.cos(phase_rad) - math.cos(t))
        wrist.rotation_euler = Euler(rot, 'XYZ')
        wrist.keyframe_insert(data_path="rotation_euler", frame=frame)

    if settle and end_frame not in inserted:
        wrist.rotation_euler = Euler(final_rot, 'XYZ')
        wrist.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if start_frame <= kp.co[0] <= end_frame:
                            kp.interpolation = 'BEZIER'
                            if settle and kp.co[0] == end_frame:
                                kp.handle_left_type = 'EASE_IN'
                            else:
                                kp.handle_left_type = 'AUTO'
                            kp.handle_right_type = 'AUTO'

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    wrist.rotation_euler = Euler(final_rot, 'XYZ')


def animate_orbit(start_frame, duration, side="right", plane="xz",
                  radius_a=0.05, radius_b=None, cycles=2, direction="cw",
                  settle=False, phase=0, arc=1.0,
                  rot_x=0, rot_y=0, rot_z=0):
    """Moves the hand empty in a circular or oval location path.
    plane:     which pair of world axes the circle is drawn in:
               "xz" — frontal (X left/right + Z up/down, circle faces viewer),
               "xy" — horizontal (X left/right + Y forward/backward),
               "yz" — sagittal (Y forward/backward + Z up/down, circle faces sideways).
    radius_a:  radius in metres along the first axis of the plane.
    radius_b:  radius in metres along the second axis; None = same as radius_a (circle).
               Different values give an oval — e.g. radius_a=0.08, radius_b=0.03.
    cycles:    number of complete loops.
    direction: "cw" or "ccw" when viewed straight-on into the chosen plane.
               Mirrored automatically for left hand (flips direction on X-containing planes).
    settle:    if True, eases the hand smoothly back to its sign position after the last
               cycle (same behaviour as circle's settle — last 20% of duration).
    phase:     starting offset in degrees around the circle (0 = bottom of the path,
               90 = 1/4 in, 270 = 3/4 in). The hand stays at its current location at
               t=0 regardless of phase.
    arc:       fraction of the full circle to trace (1.0 = complete loop, 0.75 = 3/4, etc.).
               Values < 1.0 leave the hand at a non-zero offset unless settle=True.
    rot_x/y/z: total rotation delta (degrees) applied to the hand empty's rotation_euler
               over the duration of the orbit. The rotation interpolates linearly from the
               starting orientation to start+delta. rot_x negated for left hand."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    if radius_b is None:
        radius_b = radius_a

    origin = wrist.location.copy()
    rot_origin = wrist.rotation_euler.copy()
    drx = math.radians(-rot_x if side == "left" else rot_x)
    dry = math.radians(rot_y)
    drz = math.radians(rot_z)
    has_rot = (rot_x != 0 or rot_y != 0 or rot_z != 0)
    plane_axes = {"xz": (0, 2), "xy": (0, 1), "yz": (1, 2)}
    idx_a, idx_b = plane_axes.get(plane, (0, 2))
    phase_rad = math.radians(phase)

    sign = -1.0 if direction == "cw" else 1.0
    if side == "left" and idx_a == 0:
        sign = -sign

    n_steps   = cycles * 8
    arc_steps = max(1, round(arc * n_steps))
    end_frame = start_frame + duration

    if settle:
        loop_steps     = max(1, arc_steps - 1)
        loop_end_frame = round(start_frame + duration * 0.80)
    else:
        loop_steps     = arc_steps
        loop_end_frame = end_frame

    # final arc position (= origin only when arc=1.0 and cycles is whole number)
    t_final = phase_rad + arc * cycles * 2 * math.pi
    final_loc = list(origin)
    final_loc[idx_a] += sign * radius_a * (math.sin(t_final) - math.sin(phase_rad))
    final_loc[idx_b] += radius_b * (math.cos(phase_rad) - math.cos(t_final))

    inserted = set()
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

    for i in range(loop_steps + 1):
        t     = phase_rad + (i / arc_steps) * arc * cycles * 2 * math.pi
        frame = round(start_frame + (i / loop_steps) * (loop_end_frame - start_frame)) if loop_steps > 0 else start_frame
        if frame in inserted:
            continue
        inserted.add(frame)
        loc = list(origin)
        loc[idx_a] += sign * radius_a * (math.sin(t) - math.sin(phase_rad))
        loc[idx_b] += radius_b * (math.cos(phase_rad) - math.cos(t))
        wrist.location = Vector(loc)
        wrist.keyframe_insert(data_path="location", frame=frame)
        if has_rot:
            progress = i / loop_steps if loop_steps > 0 else 1.0
            wrist.rotation_euler = Euler((
                rot_origin[0] + drx * progress,
                rot_origin[1] + dry * progress,
                rot_origin[2] + drz * progress,
            ), rot_origin.order)
            wrist.keyframe_insert(data_path="rotation_euler", frame=frame)

    if settle and end_frame not in inserted:
        wrist.location = Vector(final_loc)
        wrist.keyframe_insert(data_path="location", frame=end_frame)
        if has_rot:
            wrist.rotation_euler = Euler((
                rot_origin[0] + drx,
                rot_origin[1] + dry,
                rot_origin[2] + drz,
            ), rot_origin.order)
            wrist.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "location" in fcurve.data_path or (has_rot and "rotation_euler" in fcurve.data_path):
                    for kp in fcurve.keyframe_points:
                        if start_frame <= kp.co[0] <= end_frame:
                            kp.interpolation = 'BEZIER'
                            if settle and kp.co[0] == end_frame:
                                kp.handle_left_type = 'EASE_IN'
                            else:
                                kp.handle_left_type = 'AUTO'
                            kp.handle_right_type = 'AUTO'

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    wrist.location = Vector(final_loc)
    if has_rot:
        wrist.rotation_euler = Euler((
            rot_origin[0] + drx,
            rot_origin[1] + dry,
            rot_origin[2] + drz,
        ), rot_origin.order)


def animate_scallop(start_frame, duration, side="right",
                    loc_x=0, loc_y=0, loc_z=0,
                    arch_height=0.04, cycles=3, settle=False):
    """Traces N upward-arching scallop curves (◠◠◠) while drifting diagonally.

    The hand travels (loc_x, loc_y, loc_z) total over all cycles. Each cycle is
    one upward arch: the midpoint rises arch_height above the travel line in world Z.
    loc_x is negated for left hand; loc_y/loc_z applied as-is.
    settle=True eases the final position in smoothly (EASE_IN on last keyframe)."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    origin = wrist.location.copy()
    dlx = -loc_x if side == "left" else loc_x
    dly, dlz = loc_y, loc_z

    frames_per_cycle = duration / cycles
    end_frame = start_frame + duration

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

    wrist.location = origin
    wrist.keyframe_insert(data_path="location", frame=start_frame)

    for i in range(cycles):
        t_mid = (i + 0.5) / cycles
        t_end = (i + 1.0) / cycles

        wrist.location = (
            origin.x + t_mid * dlx,
            origin.y + t_mid * dly,
            origin.z + t_mid * dlz + arch_height,
        )
        wrist.keyframe_insert(data_path="location", frame=round(start_frame + (i + 0.5) * frames_per_cycle))

        wrist.location = (
            origin.x + t_end * dlx,
            origin.y + t_end * dly,
            origin.z + t_end * dlz,
        )
        wrist.keyframe_insert(data_path="location", frame=round(start_frame + (i + 1) * frames_per_cycle))

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "location" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if start_frame <= kp.co[0] <= end_frame:
                            kp.interpolation = 'BEZIER'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'AUTO'
                            if settle and kp.co[0] == end_frame:
                                kp.handle_left_type = 'EASE_IN'

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    wrist.location = Vector((origin.x + dlx, origin.y + dly, origin.z + dlz))


# ── Move registry ─────────────────────────────────────────────────────────────
# Add new moves here only — no changes needed in sequence.py or bake.py.
# Tuple: (animate_fn, sets_protect_rotation)
MOVE_REGISTRY = {
    "slide":         (animate_slide,         False),
    "wave":          (animate_wave,          True),
    "checkmark":     (animate_checkmark,     True),
    "halfcircle":    (animate_halfcircle,    True),
    "s_shape":       (animate_s,             True),
    "flip":          (animate_flip,          True),
    "finger_wiggle": (animate_finger_wiggle, True),
    "circle":        (animate_circle,        True),
    "orbit":         (animate_orbit,         False),
    "scallop":       (animate_scallop,       False),
}


def dispatch_move(move, side, hd, start_frame, duration, is_mirror=False):
    """Call the animation function for a single move string or dict.
    Returns protect_rotation."""
    move_type = move if isinstance(move, str) else move.get("type")
    is_dict   = isinstance(move, dict)

    entry = MOVE_REGISTRY.get(move_type)
    if not entry:
        return False
    fn, sets_protect = entry

    kwargs = {"side": side}
    if move_type == "slide":
        raw_dir            = move.get("direction", "left") if is_dict else "left"
        kwargs["direction"] = _get_mirror_direction(raw_dir) if (is_mirror and side == "left") else raw_dir
        if is_dict and "distance" in move:
            kwargs["distance"] = move["distance"]
        if is_dict and "moves" in move:
            kwargs["moves"] = move["moves"]
    elif move_type == "checkmark":
        if is_dict:
            for key in ("rot1_x", "rot1_y", "rot1_z", "rot2_x", "rot2_y", "rot2_z"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "halfcircle":
        kwargs["direction"] = move.get("direction", "inner") if is_dict else "inner"
    elif move_type == "flip":
        if is_dict:
            for key in ("rot_x", "rot_y", "rot_z", "loc_x", "loc_y", "loc_z", "arm_rot_x", "arm_rot_y", "arm_rot_z", "settle", "use_quaternion", "rot_end_pct", "loc_end_pct"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "wave":
        if is_dict:
            for key in ("rot_x", "rot_y", "rot_z", "loc_x", "loc_y", "loc_z", "cycles", "arm_rot_x", "arm_rot_y", "arm_rot_z"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type in ("circle", "orbit"):
        if is_dict:
            for key in ("plane", "radius_a", "radius_b", "cycles", "direction", "settle", "phase", "arc"):
                if key in move:
                    kwargs[key] = move[key]
            if move_type == "orbit":
                for key in ("rot_x", "rot_y", "rot_z"):
                    if key in move:
                        kwargs[key] = move[key]
                if any(k in move for k in ("rot_x", "rot_y", "rot_z")):
                    sets_protect = True
    elif move_type == "scallop":
        if is_dict:
            for key in ("loc_x", "loc_y", "loc_z", "arch_height", "cycles", "settle"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "finger_wiggle":
        kwargs["shape_1"] = hd["shape"]
        kwargs["shape_2"] = move.get("shape_2", "Hand_Relaxed") if is_dict else "Hand_Relaxed"
        kwargs["cycles"]  = move.get("cycles", 3) if is_dict else 3
        if is_dict:
            for key in ("use_relaxed", "relaxed_fingers", "rot_x", "rot_y", "rot_z", "loc_x", "loc_y", "loc_z"):
                if key in move:
                    kwargs[key] = move[key]

    # Generic from_shape: overrides finger positions at this segment's start frame.
    # Works on any move type — lets weighted lists start each segment in the right shape.
    if is_dict and "from_shape" in move:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        load_pose(move["from_shape"], side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=start_frame)

    fn(start_frame, duration, **kwargs)

    # Generic use_relaxed: inserts Hand_Relaxed at the move midpoint for smoother hand shape transitions.
    # Works on any move type alongside from_shape.
    if is_dict and move.get("use_relaxed"):
        mid_frame = start_frame + duration // 2
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        relaxed_fingers = move.get("relaxed_fingers", ["Index", "Middle", "Ring", "Pinky"])
        load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True,
                  keyframe_on_frame=mid_frame, filter_fingers=relaxed_fingers)
    end_shape_out = move.get("end_shape") if is_dict else None
    return sets_protect, end_shape_out


def dispatch_move_or_list(move, side, hd, start_frame, duration, is_mirror=False):
    """Dispatch a move that may be a weighted list or a single move.
    Returns (protect_rotation, end_shape) where end_shape overrides the lock shape if set."""
    if not isinstance(move, list):
        return dispatch_move(move, side, hd, start_frame, duration, is_mirror)

    total_weight     = sum((m.get("weight", 1) if isinstance(m, dict) else 1) for m in move)
    protect_rotation = False
    end_shape        = None
    current_offset   = 0
    for m in move:
        weight       = m.get("weight", 1) if isinstance(m, dict) else 1
        seg_duration = int(duration * weight / total_weight)
        pr, es       = dispatch_move(m, side, hd, start_frame + current_offset, seg_duration, is_mirror)
        protect_rotation |= pr
        if es:
            end_shape = es
        current_offset   += seg_duration
    return protect_rotation, end_shape
