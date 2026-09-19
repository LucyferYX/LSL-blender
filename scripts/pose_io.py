# --- LOAD AND SAVE ---

def load_library_from_file(filepath):
    global SIGN_LIBRARY
    full_path = bpy.path.abspath(f"//{filepath}")
    with open(full_path, 'r', encoding='utf-8-sig') as f:
        SIGN_LIBRARY = json.load(f)


def load_pose(pose_name, side="right", apply_arm=True, apply_fingers=True, keyframe_on_frame=None, apply_location=True, filter_fingers=None, apply_arm_location=True, apply_arm_rotation=True):
    global _RIGHT_HAND_WORLD_REF, _LEFT_HAND_WORLD_REF

    filename = f"LSL_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    if not os.path.exists(path):
        print(f"Error: File {path} not found.")
        return
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    if side == "left":
        hand_name, arm_name = LEFTHAND_EMPTY, LEFTARM_EMPTY
    else:
        hand_name, arm_name = RIGHTHAND_EMPTY, RIGHTARM_EMPTY

    # --- 1. ARM LOADING ---
    if apply_arm and "hand" in data:
        # World reference needs both location and rotation for correct left-hand mirroring.
        # When the file has no location (orientation-only), read the current empty position
        # so the world reference stays correct for finger mirroring.
        if apply_arm_location and "location" in data["hand"]:
            rh_loc = Vector(data["hand"]["location"])
        else:
            hand_obj = bpy.data.objects.get(RIGHTHAND_EMPTY)
            rh_loc = hand_obj.location.copy() if hand_obj else Vector([0.0, 0.0, 0.0])

        rh_rot = Euler([math.radians(v) for v in data["hand"].get("rotation", [0.0, 0.0, 0.0])], 'XYZ')
        _RIGHT_HAND_WORLD_REF = Matrix.LocRotScale(rh_loc, rh_rot, None)

        lh_loc = Vector((-rh_loc.x, rh_loc.y, rh_loc.z))
        lh_rot = Euler((rh_rot.x, -rh_rot.y, -rh_rot.z), 'XYZ')
        _LEFT_HAND_WORLD_REF = Matrix.LocRotScale(lh_loc, lh_rot, None)

        mapping = {"hand": hand_name, "arm": arm_name}
        for json_key, target_name in mapping.items():
            if json_key in data:
                obj = bpy.data.objects.get(target_name)
                if obj:
                    has_location = "location" in data[json_key]
                    has_rotation = "rotation" in data[json_key]
                    w_loc = Vector(data[json_key].get("location", [0.0, 0.0, 0.0]))
                    w_rot = [math.radians(v) for v in data[json_key].get("rotation", [math.degrees(v) for v in obj.rotation_euler])]
                    if json_key == "arm":
                        w_rot[2] += math.radians(ARM_ROT_Z_CORRECTION)
                    if side == "left":
                        w_loc.x  = -w_loc.x
                        w_rot[1] = -w_rot[1]
                        w_rot[2] = -w_rot[2]
                    loc_flag = apply_arm_location and has_location and (apply_location if json_key == "hand" else True)
                    rot_flag = apply_arm_rotation and has_rotation
                    apply_world_transform(obj, w_loc, Euler(w_rot, 'XYZ'), keyframe_on_frame,
                                          apply_location=loc_flag, apply_rotation=rot_flag)

    # --- 2. FINGER LOADING ---
    if apply_fingers and "fingers" in data:

        if side == "right":
            for src_name, info in data["fingers"].items():
                if filter_fingers and not any(f in src_name for f in filter_fingers):
                    continue
                obj = bpy.data.objects.get(src_name)
                if obj:
                    obj.location = Vector(info["location"])
                    if keyframe_on_frame is not None:
                        obj.keyframe_insert(data_path="location", frame=keyframe_on_frame)

        else:  # left
            if _RIGHT_HAND_WORLD_REF is None or _LEFT_HAND_WORLD_REF is None:
                # Shape-only file: no prior orientation load set the world refs.
                # Build a virtual right-hand ref that is the X-mirror of the left
                # hand's current world matrix.  This makes the finger mirroring
                # math place fingers correctly relative to the left hand's actual
                # position, not the right hand's (which may be somewhere else).
                lh_obj = bpy.data.objects.get(LEFTHAND_EMPTY)
                if not lh_obj:
                    print("Error: could not find left hand empty.")
                    return
                bpy.context.view_layer.update()
                _MX = Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
                _LEFT_HAND_WORLD_REF  = lh_obj.matrix_world.copy()
                _RIGHT_HAND_WORLD_REF = _MX @ lh_obj.matrix_world @ _MX

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

                finger_world = _RIGHT_HAND_WORLD_REF @ r_mpi @ Matrix.Translation(l_loc)
                mirrored     = MIRROR @ finger_world @ MIRROR
                local_mat    = l_mpi.inverted() @ lh_world_inv @ mirrored

                left_obj.location = local_mat.to_translation()

                if keyframe_on_frame is not None:
                    left_obj.keyframe_insert(data_path="location", frame=keyframe_on_frame)


def load_sign(sign_name):
    """Apply the static arm/hand start pose of a sign (no head, expression, or move).
    Loads both right and left arms. Right is always processed first so world refs
    are set before the left fingers are mirrored."""
    global SIGN_LIBRARY
    if not SIGN_LIBRARY:
        load_library_from_file("signs.json")

    data = SIGN_LIBRARY.get(sign_name)
    if data is None:
        print(f"load_sign: no sign '{sign_name}' found in signs.json")
        return

    sides_config = {}
    for side in ("right", "left"):
        hd = _resolve_hand_data(data, side)
        if hd:
            sides_config[side] = hd

    # Location first (right before left — sets _RIGHT_HAND_WORLD_REF for finger mirroring).
    # When shape == "Start_Position" there is no "location" key; sequence.py uses the
    # orientation field as the location source (which is also "Start_Position"), because
    # LSL_Start_Position.json contains the belly position data.
    for side in ("right", "left"):
        hd = sides_config.get(side, {})
        loc = hd.get("orientation") if hd.get("shape") == "Start_Position" else hd.get("location")
        if loc:
            load_pose(loc, side=side, apply_arm=True, apply_fingers=False,
                      apply_arm_location=True, apply_arm_rotation=False)

    # Then orientation (rotation only)
    for side in ("right", "left"):
        ori = sides_config.get(side, {}).get("orientation")
        if ori:
            load_pose(ori, side=side, apply_arm=True, apply_fingers=False,
                      apply_arm_location=False, apply_arm_rotation=True)

    # Then shape (fingers)
    for side in ("right", "left"):
        shape = sides_config.get(side, {}).get("shape")
        if shape:
            load_pose(shape, side=side, apply_arm=False, apply_fingers=True)

    print(f"load_sign: '{sign_name}' loaded.")


def save_pose(pose_name, include_arm=True, include_fingers=True, side="right"):
    data = {}

    if side == "left":
        hand_e, arm_e, fingers = LEFTHAND_EMPTY, LEFTARM_EMPTY, LEFT_FINGERS
    else:
        hand_e, arm_e, fingers = RIGHTHAND_EMPTY, RIGHTARM_EMPTY, RIGHT_FINGERS

    if include_arm:
        for name, key in [(hand_e, "hand"), (arm_e, "arm")]:
            obj = bpy.data.objects.get(name)
            if obj:
                loc = list(obj.location)
                rot = list(obj.rotation_euler)
                if side == "left":
                    loc[0] = -loc[0]
                    rot[1] = -rot[1]
                    rot[2] = -rot[2]
                if key == "arm":
                    rot[2] -= math.radians(ARM_ROT_Z_CORRECTION)
                data[key] = {
                    "name": name,
                    "location": [round(v, 3) for v in loc],
                    "rotation": [round(math.degrees(v), 3) for v in rot]
                }

    if include_fingers:
        finger_data = {}
        if side == "left":
            bpy.context.view_layer.update()
            MIRROR    = Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
            lh_obj    = bpy.data.objects.get(LEFTHAND_EMPTY)
            rh_obj    = bpy.data.objects.get(RIGHTHAND_EMPTY)
            lh_world      = lh_obj.matrix_world if lh_obj else Matrix.Identity(4)
            rh_world_inv  = rh_obj.matrix_world.inverted() if rh_obj else Matrix.Identity(4)
            for name in fingers:
                obj = bpy.data.objects.get(name)
                if not obj:
                    continue
                right_name = name.replace("Left", "Right")
                r_obj      = bpy.data.objects.get(right_name)
                r_mpi      = r_obj.matrix_parent_inverse if r_obj else Matrix.Identity(4)
                finger_world = lh_world @ obj.matrix_parent_inverse @ \
                               Matrix.LocRotScale(obj.location, obj.rotation_euler, None)
                unmirrored   = MIRROR @ finger_world @ MIRROR
                local_mat    = r_mpi.inverted() @ rh_world_inv @ unmirrored
                finger_data[right_name] = {
                    "location": [round(v, 3) for v in local_mat.to_translation()]
                }
        else:
            for name in fingers:
                obj = bpy.data.objects.get(name)
                if obj:
                    finger_data[name] = {
                        "location": [round(v, 3) for v in obj.location]
                    }
        data["fingers"] = finger_data

    filename = f"LSL_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved {pose_name}")


def save_location_pose(pose_name, side="right"):
    """Saves arm location + hand location to poses/LSL_Location_<pose_name>.json.
    side='left': reads left empties and negates X so the file is in right-hand space."""
    if side == "left":
        empties = [(LEFTARM_EMPTY, "arm"), (LEFTHAND_EMPTY, "hand")]
    else:
        empties = [(RIGHTARM_EMPTY, "arm"), (RIGHTHAND_EMPTY, "hand")]
    data = {}
    for name, key in empties:
        obj = bpy.data.objects.get(name)
        if obj:
            loc = list(obj.location)
            if side == "left":
                loc[0] = -loc[0]
            data[key] = {"location": [round(v, 3) for v in loc]}
    filename = f"LSL_Location_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved Location_{pose_name}")


def save_orientation_pose(pose_name, side="right"):
    """Saves arm rotation + hand rotation to poses/LSL_Orientation_<pose_name>.json.
    side='left': reads left empties and negates Y/Z so the file is in right-hand space."""
    if side == "left":
        empties = [(LEFTARM_EMPTY, "arm"), (LEFTHAND_EMPTY, "hand")]
    else:
        empties = [(RIGHTARM_EMPTY, "arm"), (RIGHTHAND_EMPTY, "hand")]
    data = {}
    for name, key in empties:
        obj = bpy.data.objects.get(name)
        if obj:
            rot = list(obj.rotation_euler)
            if side == "left":
                rot[1] = -rot[1]
                rot[2] = -rot[2]
            if key == "arm":
                rot[2] -= math.radians(ARM_ROT_Z_CORRECTION)
            data[key] = {"rotation": [round(math.degrees(v), 3) for v in rot]}
    filename = f"LSL_Orientation_{pose_name}.json"
    path = bpy.path.abspath(f"//{POSES_DIR}/{filename}")
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Saved Orientation_{pose_name}")


def save_hand_pose(pose_name, side="right"):
    """Saves finger empty locations to poses/LSL_Hand_<pose_name>.json.
    side='left': reads left finger empties and un-mirrors to right-hand space via MIRROR matrix."""
    finger_data = {}
    if side == "left":
        bpy.context.view_layer.update()
        MIRROR   = Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
        lh_obj   = bpy.data.objects.get(LEFTHAND_EMPTY)
        lh_world = lh_obj.matrix_world.copy() if lh_obj else Matrix.Identity(4)
        # Virtual right-hand world = mirror of current left-hand world.
        # Using virtual (not actual) right-hand position keeps the saved local
        # coords independent of wherever the right hand currently happens to be.
        rh_world_inv = (MIRROR @ lh_world @ MIRROR).inverted()
        for name in LEFT_FINGERS:
            obj = bpy.data.objects.get(name)
            if not obj:
                continue
            right_name = name.replace("Left", "Right")
            r_obj = bpy.data.objects.get(right_name)
            r_mpi = r_obj.matrix_parent_inverse if r_obj else Matrix.Identity(4)
            finger_world = lh_world @ obj.matrix_parent_inverse @ \
                           Matrix.LocRotScale(obj.location, obj.rotation_euler, None)
            unmirrored = MIRROR @ finger_world @ MIRROR
            local_mat  = r_mpi.inverted() @ rh_world_inv @ unmirrored
            finger_data[right_name] = {
                "location": [round(v, 3) for v in local_mat.to_translation()]
            }
    else:
        for name in RIGHT_FINGERS:
            obj = bpy.data.objects.get(name)
            if obj:
                finger_data[name] = {
                    "location": [round(v, 3) for v in obj.location]
                }
    path = bpy.path.abspath(f"//{POSES_DIR}/LSL_Hand_{pose_name}.json")
    with open(path, 'w') as f:
        json.dump({"fingers": finger_data}, f, indent=4)
    print(f"Saved Hand_{pose_name}")


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
    if hand_data == "mirror_right":
        hand_data = data.get("right")
    elif isinstance(hand_data, dict) and hand_data.get("mirror_right"):
        overrides = {k: v for k, v in hand_data.items() if k != "mirror_right"}
        hand_data = {**data.get("right", {}), **overrides}
    return hand_data  # None means this side is inactive for this sign

def _get_mirror_direction(direction):
    if direction == "left":  return "right"
    if direction == "right": return "left"
    return direction

def get_rig_info(side):
    if side == "left":
        return LEFTHAND_EMPTY, LEFTARM_EMPTY, LEFT_FINGERS
    return RIGHTHAND_EMPTY, RIGHTARM_EMPTY, RIGHT_FINGERS

def get_mirrored_transform(location, rotation):
    m_loc = (-location[0], location[1], location[2])
    m_rot = (rotation[0], -rotation[1], -rotation[2])
    return m_loc, m_rot

def _all_expression_key_names():
    """Return the set of all shape key names referenced anywhere in EXPRESSION_MAP."""
    names = set()
    for v in EXPRESSION_MAP.values():
        if isinstance(v, dict):
            names.update(v.keys())
        else:
            names.add(v)
    return names

def keyframe_expression(expression_name, frame):
    """Keyframe facial shape keys. expression_name=None sets all to 0 (neutral)."""
    face_obj = bpy.data.objects.get(FACE_MESH_NAME)
    if not face_obj or not face_obj.data.shape_keys:
        return
    keys = face_obj.data.shape_keys.key_blocks
    for key_name in _all_expression_key_names():
        kb = keys.get(key_name)
        if kb:
            kb.value = 0.0
            kb.keyframe_insert("value", frame=frame)
    if expression_name and expression_name in EXPRESSION_MAP:
        expr_val = EXPRESSION_MAP[expression_name]
        if isinstance(expr_val, dict):
            for key_name, weight in expr_val.items():
                kb = keys.get(key_name)
                if kb:
                    kb.value = weight
                    kb.keyframe_insert("value", frame=frame)
        else:
            kb = keys.get(expr_val)
            if kb:
                kb.value = 1.0
                kb.keyframe_insert("value", frame=frame)


def reset_animation():
    all_empties = [HEAD_EMPTY, CHEST_EMPTY, LEFTEYE_EMPTY, RIGHTEYE_EMPTY,
                   RIGHTSHOULDER_EMPTY, LEFTSHOULDER_EMPTY,
                   RIGHTHAND_EMPTY, RIGHTARM_EMPTY,
                   LEFTHAND_EMPTY, LEFTARM_EMPTY] + RIGHT_FINGERS + LEFT_FINGERS
    for name in all_empties:
        obj = bpy.data.objects.get(name)
        if obj and obj.animation_data:
            old_action = obj.animation_data.action
            obj.animation_data_clear()
            if old_action and old_action.users == 0:
                bpy.data.actions.remove(old_action)
    head = bpy.data.objects.get(HEAD_EMPTY)
    if head:
        head.location = (0, 0.02, 1.8)
        head.rotation_euler = (math.radians(90), 0, 0)
    chest = bpy.data.objects.get(CHEST_EMPTY)
    if chest:
        chest.rotation_euler = (0.0, 0.0, 0.0)
    for _eye_name in (LEFTEYE_EMPTY, RIGHTEYE_EMPTY):
        _eye = bpy.data.objects.get(_eye_name)
        if _eye:
            _eye.rotation_euler = (0.0, 0.0, 0.0)
    r_shoulder = bpy.data.objects.get(RIGHTSHOULDER_EMPTY)
    if r_shoulder:
        r_shoulder.location = (-0.17, -0.025, 1.49)
    l_shoulder = bpy.data.objects.get(LEFTSHOULDER_EMPTY)
    if l_shoulder:
        l_shoulder.location = (0.17, -0.025, 1.49)
    face_obj = bpy.data.objects.get(FACE_MESH_NAME)
    if face_obj and face_obj.data.shape_keys:
        sk = face_obj.data.shape_keys
        if sk.animation_data:
            # Only clear the active action — NLA tracks hold already-baked clips and
            # must NOT be destroyed here (animation_data_clear would wipe them).
            old_sk_action = sk.animation_data.action
            sk.animation_data.action = None
            if old_sk_action and old_sk_action.users == 0:
                bpy.data.actions.remove(old_sk_action)
        # Reset all tracked shape key values to 0 (neutral face).
        for key_name in _all_expression_key_names():
            kb = sk.key_blocks.get(key_name) if sk.key_blocks else None
            if kb:
                kb.value = 0.0
    bpy.context.scene.frame_set(1)
