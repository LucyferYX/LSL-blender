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
        shake_z   = math.radians(10)
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


def animate_wave(start_frame, duration, side="right", rot_x=20, rot_y=0, rot_z=0, loc_x=0.02, cycles=2):
    """Oscillating hand wave: alternates ±rot and ±loc_x for `cycles` full swings."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    origin_loc = wrist.location.copy()
    origin_rot = wrist.rotation_euler.copy()

    dx, dy, dz = _mirror_rot(math.radians(rot_x), math.radians(rot_y), math.radians(rot_z), side)
    dlx = -loc_x if side == "left" else loc_x

    total_peaks  = int(cycles * 2)              # e.g. cycles=2 → 4 peaks; cycles=1.5 → 3 peaks
    half_cycle   = (total_peaks % 2 == 1)       # odd peaks → ends displaced, no return to origin
    step         = duration / (total_peaks if half_cycle else total_peaks + 1)
    end_frame    = start_frame + duration

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

    wrist.location = origin_loc
    wrist.rotation_euler = origin_rot
    wrist.keyframe_insert(data_path="location",       frame=start_frame)
    wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)

    for i in range(total_peaks):
        sign = 1 if i % 2 == 0 else -1
        f = end_frame if (half_cycle and i == total_peaks - 1) else start_frame + int((i + 1) * step)
        wrist.location       = (origin_loc.x + sign * dlx, origin_loc.y, origin_loc.z)
        wrist.rotation_euler = (origin_rot.x + sign * dx, origin_rot.y + sign * dy, origin_rot.z + sign * dz)
        wrist.keyframe_insert(data_path="location",       frame=f)
        wrist.keyframe_insert(data_path="rotation_euler", frame=f)

    if not half_cycle:
        wrist.location = origin_loc
        wrist.rotation_euler = origin_rot
        wrist.keyframe_insert(data_path="location",       frame=end_frame)
        wrist.keyframe_insert(data_path="rotation_euler", frame=end_frame)

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


def animate_pointing_down(start_frame, duration, side="right"):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    start_rot = wrist.rotation_euler.copy()
    f_start, f_hit, f_end = start_frame, start_frame + int(duration * 0.6), start_frame + duration
    dx_hit, dy_hit, dz_hit = _mirror_rot(math.radians(60), math.radians(25), math.radians(10), side)
    dx_end, dy_end, dz_end = _mirror_rot(math.radians(55), math.radians(20), math.radians(10), side)

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    wrist.rotation_euler = start_rot
    wrist.keyframe_insert(data_path="rotation_euler", frame=f_start)
    wrist.rotation_euler = (start_rot.x+dx_hit, start_rot.y+dy_hit, start_rot.z+dz_hit)
    wrist.keyframe_insert(data_path="rotation_euler", frame=f_hit)
    wrist.rotation_euler = (start_rot.x+dx_end, start_rot.y+dy_end, start_rot.z+dz_end)
    wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if kp.co[0] == f_start:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_right_type = 'VECTOR'
                        elif kp.co[0] == f_hit:
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



def animate_morph(start_frame, duration, side="right",
                  rot_x=0, rot_y=0, rot_z=0,
                  from_shape=None, settle=True):
    """Simultaneous wrist rotation + hand shape transition.
    from_shape: shape keyframed at start_frame (overrides what the sequence loaded).
    The end shape is the sign's own 'shape' field, applied by the sequence lock.
    settle=True: ease-back at end (3 rotation keyframes, like flip); settle=False: clean 2-keyframe move."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    start_rot = wrist.rotation_euler.copy()
    f_end = start_frame + duration
    dx, dy, dz = _mirror_rot(math.radians(rot_x), math.radians(rot_y), math.radians(rot_z), side)

    if settle:
        f_hit = start_frame + int(duration * 0.70)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        wrist.rotation_euler = start_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        wrist.rotation_euler = (start_rot.x + dx,        start_rot.y + dy,        start_rot.z + dz)
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_hit)
        wrist.rotation_euler = (start_rot.x + dx * 0.93, start_rot.y + dy * 0.93, start_rot.z + dz * 0.93)
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)
        bezier_frames = (start_frame, f_hit, f_end)
    else:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        wrist.rotation_euler = start_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)
        wrist.rotation_euler = (start_rot.x + dx, start_rot.y + dy, start_rot.z + dz)
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)
        bezier_frames = (start_frame, f_end)

    if from_shape:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        load_pose(from_shape, side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=start_frame)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if kp.co[0] in bezier_frames:
                            kp.interpolation = 'BEZIER'
                            kp.handle_left_type = 'AUTO'
                            kp.handle_right_type = 'AUTO'

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'


def animate_finger_wiggle(start_frame, duration, side="right", shape_1="Hand_B", shape_2="Hand_F", cycles=3, use_relaxed=True):
    """Alternates between two finger shapes for 'cycles' complete oscillations.
    cycles accepts .5 increments: cycles=1.5 does 3 half-steps, ending on shape_2.
    use_relaxed=True (default): inserts Hand_Relaxed at each midpoint to prevent finger twisting.
    use_relaxed=False: direct linear transition between shapes, no intermediate keyframe."""
    total_halves = int(cycles * 2)
    frames_per_half = duration / total_halves
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for i in range(1, total_halves + 1):
        frame = int(start_frame + i * frames_per_half)
        if use_relaxed:
            mid_frame = int(start_frame + (i - 0.5) * frames_per_half)
            load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=mid_frame,
                      filter_fingers=["Index", "Middle", "Ring", "Pinky"])
        shape = shape_2 if i % 2 == 1 else shape_1
        load_pose(shape, side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=frame)


def animate_flip(start_frame, duration, side="right",
                 rot_x=0, rot_y=0, rot_z=0,
                 loc_x=0, loc_y=0, loc_z=0,
                 arm_rot_x=0, arm_rot_y=0, arm_rot_z=0,
                 settle=True, use_quaternion=False):
    """Wrist flip by the given degrees on each axis, with optional location delta.
    Rotation is mirrored via _mirror_rot; loc_x is negated for left hand, loc_y/loc_z are applied as-is.
    arm_rot_x/y/z: optional rotation delta (degrees) applied to the arm empty (mirrored automatically).
    use_quaternion=True: applies rotation via quaternion SLERP — correct at any orientation including
      gimbal lock (Y≈±90°). Default False preserves existing Euler-addition behaviour for all signs.
    settle=True: 3 keyframes with ease-back at end; settle=False: clean linear 2-keyframe move."""
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

    if use_quaternion:
        # Stepped SLERP: 8 small linear steps keep each quat-to-Euler conversion numerically
        # close to the previous frame, avoiding the wild spins a single large-angle conversion
        # produces near gimbal lock (Y ≈ ±90°/270°).
        sq         = start_rot.to_quaternion()
        tq         = sq @ Euler((dx, dy, dz), 'XYZ').to_quaternion()
        f_hit      = start_frame + int(duration * 0.70) if settle else f_end
        span       = f_hit - f_start
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
            wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)
        if has_loc:
            wrist.location = start_loc
            wrist.keyframe_insert(data_path="location", frame=f_start)
            wrist.location = (start_loc.x + dlx, start_loc.y + dly, start_loc.z + dlz)
            wrist.keyframe_insert(data_path="location", frame=f_hit)
            if settle:
                wrist.location = (start_loc.x + dlx * 0.93, start_loc.y + dly * 0.93, start_loc.z + dlz * 0.93)
                wrist.keyframe_insert(data_path="location", frame=f_end)
        if has_arm_rot and arm_obj:
            arm_obj.rotation_euler = arm_start_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
            arm_obj.rotation_euler = (arm_start_rot.x + dax, arm_start_rot.y + day, arm_start_rot.z + daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_hit)
            if settle:
                arm_obj.rotation_euler = (arm_start_rot.x + dax * 0.93, arm_start_rot.y + day * 0.93, arm_start_rot.z + daz * 0.93)
                arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_end)
            _set_bezier_on_object(arm_obj, f_start, f_end)
        return

    target_rot = Euler((start_rot.x + dx,        start_rot.y + dy,        start_rot.z + dz),        'XYZ')
    settle_rot = Euler((start_rot.x + dx * 0.93, start_rot.y + dy * 0.93, start_rot.z + dz * 0.93), 'XYZ')

    if settle:
        f_hit = start_frame + int(duration * 0.70)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        wrist.rotation_euler = start_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_start)
        wrist.rotation_euler = target_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_hit)
        wrist.rotation_euler = settle_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)
        if has_loc:
            wrist.location = start_loc
            wrist.keyframe_insert(data_path="location", frame=f_start)
            wrist.location = (start_loc.x + dlx,        start_loc.y + dly,        start_loc.z + dlz)
            wrist.keyframe_insert(data_path="location", frame=f_hit)
            wrist.location = (start_loc.x + dlx * 0.93, start_loc.y + dly * 0.93, start_loc.z + dlz * 0.93)
            wrist.keyframe_insert(data_path="location", frame=f_end)
        if has_arm_rot and arm_obj:
            arm_obj.rotation_euler = arm_start_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
            arm_obj.rotation_euler = (arm_start_rot.x + dax,        arm_start_rot.y + day,        arm_start_rot.z + daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_hit)
            arm_obj.rotation_euler = (arm_start_rot.x + dax * 0.93, arm_start_rot.y + day * 0.93, arm_start_rot.z + daz * 0.93)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_end)
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        _set_bezier_on_object(wrist, f_start, f_end)
        if has_arm_rot and arm_obj:
            _set_bezier_on_object(arm_obj, f_start, f_end)
    else:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        wrist.rotation_euler = start_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_start)
        wrist.rotation_euler = target_rot
        wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)
        if has_loc:
            wrist.location = start_loc
            wrist.keyframe_insert(data_path="location", frame=f_start)
            wrist.location = (start_loc.x + dlx, start_loc.y + dly, start_loc.z + dlz)
            wrist.keyframe_insert(data_path="location", frame=f_end)
        if has_arm_rot and arm_obj:
            arm_obj.rotation_euler = arm_start_rot
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_start)
            arm_obj.rotation_euler = (arm_start_rot.x + dax, arm_start_rot.y + day, arm_start_rot.z + daz)
            arm_obj.keyframe_insert(data_path="rotation_euler", frame=f_end)
        action = wrist.animation_data.action if wrist.animation_data else None
        if action:
            def _apply_linear(fcurves):
                for fc in fcurves:
                    if "rotation_euler" not in fc.data_path and "location" not in fc.data_path:
                        continue
                    for kp in fc.keyframe_points:
                        if kp.co[0] in (f_start, f_end):
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
                  settle=False, phase=0, arc=1.0):
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
               Values < 1.0 leave the hand at a non-zero offset unless settle=True."""
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    if radius_b is None:
        radius_b = radius_a

    origin = wrist.location.copy()
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

    if settle and end_frame not in inserted:
        wrist.location = Vector(final_loc)
        wrist.keyframe_insert(data_path="location", frame=end_frame)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "location" in fcurve.data_path:
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
    "point_down":    (animate_pointing_down, True),
    "flip":          (animate_flip,          True),
    "morph":         (animate_morph,         True),
    "finger_wiggle": (animate_finger_wiggle, False),
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
            for key in ("rot_x", "rot_y", "rot_z", "loc_x", "loc_y", "loc_z", "arm_rot_x", "arm_rot_y", "arm_rot_z", "settle", "use_quaternion"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "wave":
        if is_dict:
            for key in ("rot_x", "rot_y", "rot_z", "loc_x", "cycles"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "morph":
        if is_dict:
            for key in ("rot_x", "rot_y", "rot_z"):
                if key in move:
                    kwargs[key] = move[key]
            if "settle" in move:
                kwargs["settle"] = move["settle"]
    elif move_type in ("circle", "orbit"):
        if is_dict:
            for key in ("plane", "radius_a", "radius_b", "cycles", "direction", "settle", "phase", "arc"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "scallop":
        if is_dict:
            for key in ("loc_x", "loc_y", "loc_z", "arch_height", "cycles", "settle"):
                if key in move:
                    kwargs[key] = move[key]
    elif move_type == "finger_wiggle":
        kwargs["shape_1"] = hd["shape"]
        kwargs["shape_2"] = move.get("shape_2", "Hand_Relaxed") if is_dict else "Hand_Relaxed"
        kwargs["cycles"]  = move.get("cycles", 3) if is_dict else 3
        if is_dict and "use_relaxed" in move:
            kwargs["use_relaxed"] = move["use_relaxed"]

    # Generic from_shape: overrides finger positions at this segment's start frame.
    # Works on any move type — lets weighted lists start each segment in the right shape.
    if is_dict and "from_shape" in move:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
        load_pose(move["from_shape"], side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=start_frame)

    fn(start_frame, duration, **kwargs)
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
