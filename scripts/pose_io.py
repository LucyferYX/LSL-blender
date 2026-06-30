# --- LOAD AND SAVE ---

def load_library_from_file(filepath):
    global SIGN_LIBRARY
    full_path = bpy.path.abspath(f"//{filepath}")
    with open(full_path, 'r', encoding='utf-8') as f:
        SIGN_LIBRARY = json.load(f)


def load_pose(pose_name, side="right", apply_arm=True, apply_fingers=True, keyframe_on_frame=None, apply_location=True, filter_fingers=None, apply_arm_location=True, apply_arm_rotation=True):
    global _RIGHT_HAND_WORLD_REF, _LEFT_HAND_WORLD_REF

    filename = f"LSL_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    if not os.path.exists(path):
        print(f"Error: File {path} not found.")
        return
    with open(path, 'r') as f:
        data = json.load(f)

    if side == "left":
        hand_name, forearm_name, arm_name = LEFTHAND_EMPTY, LEFTFOREARM_EMPTY, LEFTARM_EMPTY
    else:
        hand_name, forearm_name, arm_name = RIGHTHAND_EMPTY, RIGHTFOREARM_EMPTY, RIGHTARM_EMPTY

    # --- 1. ARM LOADING ---
    if apply_arm and "hand" in data:
        # World reference needs both location and rotation for correct left-hand mirroring.
        # When loading an orientation-only file (apply_arm_location=False), the hand location
        # was already set from a preceding Location file — read it directly from the empty.
        if apply_arm_location:
            rh_loc = Vector(data["hand"].get("location", [0.0, 0.0, 0.0]))
        else:
            hand_obj = bpy.data.objects.get(RIGHTHAND_EMPTY)
            rh_loc = hand_obj.location.copy() if hand_obj else Vector([0.0, 0.0, 0.0])

        rh_rot = Euler(data["hand"].get("rotation", [0.0, 0.0, 0.0]), 'XYZ')
        _RIGHT_HAND_WORLD_REF = Matrix.LocRotScale(rh_loc, rh_rot, None)

        lh_loc = Vector((-rh_loc.x, rh_loc.y, rh_loc.z))
        lh_rot = Euler((rh_rot.x, -rh_rot.y, -rh_rot.z), 'XYZ')
        _LEFT_HAND_WORLD_REF = Matrix.LocRotScale(lh_loc, lh_rot, None)

        mapping = {"hand": hand_name, "forearm": forearm_name, "arm": arm_name}
        for json_key, target_name in mapping.items():
            if json_key in data:
                obj = bpy.data.objects.get(target_name)
                if obj:
                    w_loc = Vector(data[json_key].get("location", [0.0, 0.0, 0.0]))
                    w_rot = list(data[json_key].get("rotation", [0.0, 0.0, 0.0]))
                    if side == "left":
                        w_loc.x  = -w_loc.x
                        w_rot[1] = -w_rot[1]
                        w_rot[2] = -w_rot[2]
                    loc_flag = apply_arm_location and (apply_location if json_key == "hand" else True)
                    apply_world_transform(obj, w_loc, Euler(w_rot, 'XYZ'), keyframe_on_frame,
                                          apply_location=loc_flag, apply_rotation=apply_arm_rotation)

    # --- 2. FINGER LOADING ---
    if apply_fingers and "fingers" in data:

        if side == "right":
            for src_name, info in data["fingers"].items():
                if filter_fingers and not any(f in src_name for f in filter_fingers):
                    continue
                obj = bpy.data.objects.get(src_name)
                if obj:
                    obj.location       = Vector(info["location"])
                    obj.rotation_euler = Euler(info["rotation"], 'XYZ')
                    if keyframe_on_frame is not None:
                        obj.keyframe_insert(data_path="location",       frame=keyframe_on_frame)
                        obj.keyframe_insert(data_path="rotation_euler", frame=keyframe_on_frame)

        else:  # left
            if _RIGHT_HAND_WORLD_REF is None or _LEFT_HAND_WORLD_REF is None:
                print("Error: load orientation before loading a shape for the left side.")
                return

            MIRROR       = Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
            lh_world_inv = _LEFT_HAND_WORLD_REF.inverted()

            for src_name, info in data["fingers"].items():
                if filter_fingers and not any(f in src_name for f in filter_fingers):
                    continue
                left_name = src_name.replace("Right", "Left")
                right_obj = bpy.data.objects.get(src_name)
                left_obj  = bpy.data.objects.get(left_name)
                if not right_obj or not left_obj:
                    continue

                r_mpi = right_obj.matrix_parent_inverse
                l_mpi = left_obj.matrix_parent_inverse
                l_loc = Vector(info["location"])
                l_rot = Euler(info["rotation"], 'XYZ')

                finger_world = _RIGHT_HAND_WORLD_REF @ r_mpi @ Matrix.LocRotScale(l_loc, l_rot, None)
                mirrored     = MIRROR @ finger_world @ MIRROR
                local_mat    = l_mpi.inverted() @ lh_world_inv @ mirrored

                left_obj.location       = local_mat.to_translation()
                left_obj.rotation_euler = local_mat.to_euler('XYZ')

                if keyframe_on_frame is not None:
                    left_obj.keyframe_insert(data_path="location",       frame=keyframe_on_frame)
                    left_obj.keyframe_insert(data_path="rotation_euler", frame=keyframe_on_frame)


def save_pose(pose_name, include_arm=True, include_fingers=True):
    data = {}

    if include_arm:
        for name, key in [(RIGHTHAND_EMPTY, "hand"), (RIGHTFOREARM_EMPTY, "forearm"), (RIGHTARM_EMPTY, "arm")]:
            obj = bpy.data.objects.get(name)
            if obj:
                data[key] = {
                    "name": name,
                    "location": list(obj.location),
                    "rotation": list(obj.rotation_euler)
                }

    if include_fingers:
        finger_data = {}
        for name in RIGHT_FINGERS:
            obj = bpy.data.objects.get(name)
            if obj:
                finger_data[name] = {
                    "location": list(obj.location),
                    "rotation": list(obj.rotation_euler)
                }
        data["fingers"] = finger_data

    filename = f"LSL_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved {pose_name}")


def save_location_pose(pose_name):
    """Saves arm location + hand location to poses/LSL_Location_<pose_name>.json."""
    data = {}
    for name, key in [(RIGHTARM_EMPTY, "arm"), (RIGHTHAND_EMPTY, "hand")]:
        obj = bpy.data.objects.get(name)
        if obj:
            data[key] = {"location": [round(v, 3) for v in obj.location]}
    filename = f"LSL_Location_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved Location_{pose_name}")


def save_orientation_pose(pose_name):
    """Saves forearm rotation + hand rotation to poses/LSL_Orientation_<pose_name>.json."""
    data = {}
    for name, key in [(RIGHTFOREARM_EMPTY, "forearm"), (RIGHTHAND_EMPTY, "hand")]:
        obj = bpy.data.objects.get(name)
        if obj:
            data[key] = {"rotation": [round(v, 3) for v in obj.rotation_euler]}
    filename = f"LSL_Orientation_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved Orientation_{pose_name}")


# --- HELPERS ---

def apply_world_transform(obj, world_loc, world_rot_euler, frame=None, apply_location=True, apply_rotation=True):
    target_mat = Matrix.LocRotScale(Vector(world_loc), Euler(world_rot_euler, 'XYZ'), None)

    if obj.parent:
        bpy.context.view_layer.update()
        local_mat = obj.parent.matrix_world.inverted() @ target_mat
        final_loc = local_mat.to_translation()
        final_rot = local_mat.to_euler('XYZ')
    else:
        final_loc = world_loc
        final_rot = world_rot_euler

    if apply_location:
        obj.location = final_loc
    if apply_rotation:
        obj.rotation_euler = final_rot

    if frame is not None:
        if apply_location:
            obj.keyframe_insert(data_path="location", frame=frame)
        if apply_rotation:
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def _hand_empty(side):
    return LEFTHAND_EMPTY if side == "left" else RIGHTHAND_EMPTY

def _mirror_rot(delta_x, delta_y, delta_z, side):
    if side == "left":
        return (delta_x, -delta_y, -delta_z)
    return (delta_x, delta_y, delta_z)

def _mirror_loc_x(delta_x, side):
    return -delta_x if side == "left" else delta_x

def _resolve_hand_data(data, side):
    """Returns the hand config dict for a given side, resolving mirror_right."""
    hand_data = data.get(side)
    if hand_data == "mirror_right" or (side == "left" and hand_data == "mirror_right"):
        hand_data = data.get("right")
    return hand_data  # None means this side is inactive for this sign

def _get_mirror_direction(direction):
    if direction == "left":  return "right"
    if direction == "right": return "left"
    return direction

def get_rig_info(side):
    if side == "left":
        return LEFTHAND_EMPTY, LEFTFOREARM_EMPTY, LEFTARM_EMPTY, LEFT_FINGERS
    return RIGHTHAND_EMPTY, RIGHTFOREARM_EMPTY, RIGHTARM_EMPTY, RIGHT_FINGERS

def get_mirrored_transform(location, rotation):
    m_loc = (-location[0], location[1], location[2])
    m_rot = (rotation[0], -rotation[1], -rotation[2])
    return m_loc, m_rot

def reset_animation():
    all_empties = [HEAD_EMPTY, RIGHTHAND_EMPTY, RIGHTFOREARM_EMPTY, RIGHTARM_EMPTY,
                   LEFTHAND_EMPTY, LEFTFOREARM_EMPTY, LEFTARM_EMPTY] + RIGHT_FINGERS + LEFT_FINGERS
    for name in all_empties:
        obj = bpy.data.objects.get(name)
        if obj and obj.animation_data:
            obj.animation_data_clear()
    bpy.context.scene.frame_set(1)
