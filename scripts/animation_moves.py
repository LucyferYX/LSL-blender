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
    print("Finger interpolation set to LINEAR.")


def animate_head(head_action, start_transition, start_hold, end_hold, end_settle):
    head = bpy.data.objects.get(HEAD_EMPTY)
    if not head: return

    base_loc = (0, -0.01, 1.765)

    if head_action == "Head_Nod":
        target_loc = (base_loc[0], base_loc[1] - 0.02, base_loc[2])
    else:
        target_loc = base_loc

    head.location = base_loc
    head.keyframe_insert(data_path="location", frame=start_transition)
    head.location = target_loc
    head.keyframe_insert(data_path="location", frame=start_hold)
    head.location = target_loc
    head.keyframe_insert(data_path="location", frame=end_hold)
    head.location = base_loc
    head.keyframe_insert(data_path="location", frame=end_settle)

    if head.animation_data and head.animation_data.action:
        action = head.animation_data.action
        if hasattr(action, "fcurves"):
            for fcurve in action.fcurves:
                if "location" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if kp.co[0] == start_hold or kp.co[0] == end_hold:
                            kp.interpolation = 'LINEAR'
                        elif kp.co[0] == start_transition or kp.co[0] == end_settle:
                            kp.interpolation = 'BEZIER'


def animate_slide(start_frame, duration, side="right", direction="left", distance=0.15):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return
    end_frame = start_frame + duration

    current_loc = wrist.location.copy()
    wrist.keyframe_insert(data_path="location", frame=start_frame)

    delta_x = distance if direction == "left" else -distance
    wrist.location = (current_loc.x + delta_x, current_loc.y, current_loc.z)
    wrist.keyframe_insert(data_path="location", frame=end_frame)


def animate_small_slide(start_frame, duration, side="right", direction="left", moves=2, distance=0.02):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    origin = wrist.location.copy()
    delta_x = -distance if direction == "left" else distance

    frames_per_move = duration / moves
    frames_per_half = frames_per_move / 2

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'

    wrist.location = origin
    wrist.keyframe_insert(data_path="location", frame=start_frame)

    for i in range(moves):
        move_start  = start_frame + i * frames_per_move
        peak_frame  = move_start + frames_per_half
        return_frame = move_start + frames_per_move

        wrist.location = (origin.x + delta_x, origin.y, origin.z)
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


def animate_checkmark(start_frame, duration, side="right"):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    mid_frame = start_frame + (duration // 2)
    end_frame  = start_frame + duration
    offset     = math.radians(30)
    base_rot   = wrist.rotation_euler.copy()
    dx, dy, dz = _mirror_rot(offset, 0, offset, side)

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    wrist.rotation_euler = (base_rot.x,      base_rot.y, base_rot.z + dz)
    wrist.keyframe_insert(data_path="rotation_euler", frame=start_frame)
    wrist.rotation_euler = (base_rot.x + dx, base_rot.y, base_rot.z)
    wrist.keyframe_insert(data_path="rotation_euler", frame=mid_frame)
    wrist.rotation_euler = (base_rot.x,      base_rot.y, base_rot.z - dz)
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


def animate_halfcircle(start_frame, duration, side="right"):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    curve_dur = int(duration * 0.8)
    f1, f2 = start_frame,                    start_frame + int(curve_dur * 0.25)
    f3, f4 = start_frame + int(curve_dur * 0.5), start_frame + int(curve_dur * 0.75)
    f5, f6 = start_frame + curve_dur,        start_frame + duration

    def r(x, y, z): return tuple(_mirror_rot(math.radians(x), math.radians(y), math.radians(z), side))

    keyframes = [
        (f1, r(90,  0,  45)),
        (f2, r(112.5, 0, 95)),
        (f3, r(135, 0,  90)),
        (f4, r(157.5, 0, 65)),
        (f5, r(180, 0,   0)),
        (f6, r(90,  0,   0)),
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
                        if f1 <= kp.co[0] < f5:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'AUTO'
                        elif kp.co[0] == f5:
                            kp.interpolation     = 'LINEAR'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'VECTOR'
                        elif kp.co[0] == f6:
                            kp.interpolation = 'LINEAR'


def animate_s(start_frame, duration, side="right"):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    t_top = int(duration * 0.3); t_spine = int(duration * 0.3)
    f1=start_frame; f2=f1+int(t_top*0.5); f3=f1+t_top
    f4=f3+int(t_spine*0.5); f5=f3+t_spine
    f6=f5+int((duration-t_top-t_spine)*0.6); f7=start_frame+duration

    def r(x, y, z): return tuple(_mirror_rot(math.radians(x), math.radians(y), math.radians(z), side))

    keyframes = [
        (f1, r(145, 0, -25)), (f2, r(130, 0,   0)), (f3, r(145, 0,  25)),
        (f4, r(170, 0,   0)), (f5, r(195, 0, -25)), (f6, r(210, 0,   0)),
        (f7, r(195, 0,  25)),
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


def animate_side_flip(start_frame, duration, side="right"):
    wrist = bpy.data.objects.get(_hand_empty(side))
    if not wrist: return

    start_rot = wrist.rotation_euler.copy()
    f_start, f_hit, f_end = start_frame, start_frame + int(duration * 0.7), start_frame + duration
    y_dir    = math.radians(75) if side == "left" else -math.radians(75)
    target_y = start_rot[1] + y_dir

    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    wrist.rotation_euler = start_rot
    wrist.keyframe_insert(data_path="rotation_euler", frame=f_start)
    wrist.rotation_euler = (start_rot.x, target_y,                  start_rot.z)
    wrist.keyframe_insert(data_path="rotation_euler", frame=f_hit)
    wrist.rotation_euler = (start_rot.x, target_y - y_dir*0.067,    start_rot.z)
    wrist.keyframe_insert(data_path="rotation_euler", frame=f_end)

    if wrist.animation_data and wrist.animation_data.action:
        action = wrist.animation_data.action
        fcurves = getattr(action, "fcurves", None)
        if fcurves:
            for fcurve in fcurves:
                if "rotation_euler" in fcurve.data_path:
                    for kp in fcurve.keyframe_points:
                        if f_start <= kp.co[0] <= f_end:
                            kp.interpolation     = 'BEZIER'
                            kp.handle_left_type  = 'AUTO'
                            kp.handle_right_type = 'AUTO'
