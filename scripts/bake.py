# ══════════════════════════════════════════════════════════════════════════════
#  BAKE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def _animate_sign_for_baking(word, data, start_frame=1):
    """
    Clip structure:
      frame 1               : Start_Position arm + Start_Position fingers  (neutral)
      frame 1+ARM_TRANS     : Sign orientation arm + Sign shape fingers     (full sign)
      frame ... move_end    : Sign held + movement
      frame settle_frame    : Settled sign pose (locked)
      frame settle+ARM_RET  : Start_Position arm + Start_Position fingers  (neutral)

    Every clip starts and ends at Start_Position so the viewer crossfade always
    blends between two near-identical neutral poses, letting Blender's IK solver
    bake the natural elbow path into the clip rather than relying on Three.js
    quaternion interpolation (which ignores IK constraints and can push the
    elbow through the body).
    """
    ARM_TRANS    = 8
    ARM_RET      = 6
    DEFAULT_HOLD = 10
    SETTLE_BUF   = 3

    hold_time   = data.get("duration", DEFAULT_HOLD)
    head_action = data.get("head")
    is_mirror   = data.get("left") == "mirror_right"

    sides_config = {}
    for side in ["right", "left"]:
        hd = _resolve_hand_data(data, side)
        if hd is not None:
            sides_config[side] = hd

    # ── Frame 1: Start_Position for both sides ────────────────────────────────
    load_pose("Start_Position", side="right",
              apply_arm=True, apply_fingers=True, keyframe_on_frame=start_frame)
    load_pose("Start_Position", side="left",
              apply_arm=True, apply_fingers=True, keyframe_on_frame=start_frame)

    sign_frame   = start_frame + ARM_TRANS
    move_end     = sign_frame  + hold_time
    settle_frame = move_end    + SETTLE_BUF
    return_frame = settle_frame + ARM_RET
    mid_trans    = start_frame + (ARM_TRANS // 2)
    mid_ret      = settle_frame + (ARM_RET // 2)

    signing_sides = {side for side, hd in sides_config.items() if hd.get("shape") != "Start_Position"}

    # ── mid_trans: Hand_Relaxed as finger waypoint into the sign ─────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    for side in signing_sides:
        load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=mid_trans)

    # ── sign_frame: full sign pose ────────────────────────────────────────────
    # Right before left so _RIGHT_HAND_WORLD_REF is set before mirror computation.
    # Locations (IK targets) first, then rotations (wrist orientation).
    for side in ["right", "left"]:
        if side not in sides_config:
            continue
        hd = sides_config[side]
        loc_pose = hd["orientation"] if hd.get("shape") == "Start_Position" else hd["location"]
        load_pose(loc_pose, side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=True, apply_arm_rotation=False,
                  keyframe_on_frame=sign_frame)
    for side in ["right", "left"]:
        if side not in sides_config:
            continue
        hd = sides_config[side]
        load_pose(hd["orientation"], side=side, apply_arm=True, apply_fingers=False,
                  apply_arm_location=False, apply_arm_rotation=True,
                  keyframe_on_frame=sign_frame)
    for side, hd in sides_config.items():
        load_pose(hd["shape"], side=side,
                  apply_arm=False, apply_fingers=True,
                  keyframe_on_frame=sign_frame)

    # ── Head ──────────────────────────────────────────────────────────────────
    if head_action:
        animate_head(head_action, start_frame, sign_frame, move_end, settle_frame)

    # ── Movement ──────────────────────────────────────────────────────────────
    is_movement      = False
    protect_rotation = False

    for side, hd in sides_config.items():
        move = hd.get("move")
        if not move:
            continue
        move_type = move if isinstance(move, str) else move.get("type")
        is_dict   = isinstance(move, dict)

        if move_type == "slide":
            raw_dir   = move.get("direction", "left") if is_dict else "left"
            direction = _get_mirror_direction(raw_dir) if (is_mirror and side == "left") else raw_dir
            animate_slide(sign_frame, hold_time, side=side, direction=direction)
            is_movement = True
        elif move_type == "small_slide":
            raw_dir     = move.get("direction", "left") if is_dict else "left"
            moves_count = move.get("moves", 2)           if is_dict else 2
            direction   = _get_mirror_direction(raw_dir) if (is_mirror and side == "left") else raw_dir
            animate_small_slide(sign_frame, hold_time, side=side,
                                direction=direction, moves=moves_count)
            is_movement = True
        elif move_type == "checkmark":
            animate_checkmark(sign_frame, hold_time, side=side)
            is_movement = True; protect_rotation = True
        elif move_type == "halfcircle":
            animate_halfcircle(sign_frame, hold_time, side=side)
            is_movement = True; protect_rotation = True
        elif move_type == "s_shape":
            animate_s(sign_frame, hold_time, side=side)
            is_movement = True; protect_rotation = True
        elif move_type == "point_down":
            animate_pointing_down(sign_frame, hold_time, side=side)
            is_movement = True; protect_rotation = True
        elif move_type == "side_flip":
            animate_side_flip(sign_frame, hold_time, side=side)
            is_movement = True; protect_rotation = True

    # ── Lock at move_end and settle ───────────────────────────────────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for frame in [move_end, settle_frame]:
        for side, hd in sides_config.items():
            loc_pose = hd["orientation"] if hd.get("shape") == "Start_Position" else hd["location"]
            lock_pose_at_frame(
                loc_pose, hd["orientation"], hd["shape"], frame,
                side=side,
                use_location=not is_movement,
                apply_orientation=not protect_rotation
            )

    # ── mid_ret: Hand_Relaxed as finger waypoint out of the sign ─────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    for side in signing_sides:
        load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=mid_ret)

    # ── Return to Start_Position at clip end ──────────────────────────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    load_pose("Start_Position", side="right",
              apply_arm=True, apply_fingers=True, keyframe_on_frame=return_frame)
    load_pose("Start_Position", side="left",
              apply_arm=True, apply_fingers=True, keyframe_on_frame=return_frame)

    fix_finger_interpolation()
    return return_frame


def _remove_bone_constraints(armature):
    """
    Removes all pose bone constraints and returns enough data to restore them.
    More reliable than muting for the GLB exporter, which detects constraint
    presence regardless of mute state in Blender 5.0.
    """
    saved = []
    for pbone in armature.pose.bones:
        for i, con in enumerate(list(pbone.constraints)):
            props = {}
            for prop in con.bl_rna.properties:
                if prop.identifier in ('rna_type', 'type', 'name'):
                    continue
                if prop.is_readonly:
                    continue
                try:
                    props[prop.identifier] = getattr(con, prop.identifier)
                except Exception:
                    pass
            saved.append((pbone.name, con.type, con.name, props))
            pbone.constraints.remove(con)
    return saved


def _restore_bone_constraints(armature, saved):
    for bone_name, con_type, con_name, props in saved:
        pbone = armature.pose.bones.get(bone_name)
        if not pbone:
            continue
        con = pbone.constraints.new(type=con_type)
        con.name = con_name
        for key, val in props.items():
            try:
                setattr(con, key, val)
            except Exception:
                pass


def _animate_static_clip(pose_name, start_frame=1, hold_frames=6):
    for side in ["right", "left"]:
        load_pose(pose_name, side=side, keyframe_on_frame=start_frame)
        load_pose(pose_name, side=side, keyframe_on_frame=start_frame + hold_frames)
    fix_finger_interpolation()
    return start_frame + hold_frames


def _resolve_armature(armature_name):
    obj = bpy.data.objects.get(armature_name)
    if obj and obj.type == 'ARMATURE':
        return obj
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            print(f"[Bake] Warning: '{armature_name}' not found; using '{obj.name}' instead.")
            return obj
    raise RuntimeError(
        f"No ARMATURE object found in the scene!\n"
        f"Set ARMATURE_NAME at the top of scripts/config.py to your rig's name."
    )


def _iter_action_fcurves(action, slot=None):
    """
    Yields all F-curves from an action.
    Works on both Blender 4.x (action.fcurves) and Blender 5.0+
    (layered action system: action.layers -> strips -> channelbag).
    """
    if hasattr(action, 'fcurves'):
        yield from action.fcurves
        return

    slots_to_check = [slot] if slot is not None else list(action.slots)
    for layer in action.layers:
        for strip in layer.strips:
            for s in slots_to_check:
                try:
                    cb = strip.channelbag(s)
                    if cb:
                        yield from cb.fcurves
                except Exception:
                    pass


def _bake_armature(armature, frame_start, frame_end, initial_prev_quat=None):
    from mathutils import Quaternion, Euler

    scene  = bpy.context.scene
    IS_BL5 = bpy.app.version >= (5, 0, 0)

    # ── 1. Mute NLA, detach action ───────────────────────────────────────────
    nla_mute_states = {}
    if armature.animation_data:
        for track in armature.animation_data.nla_tracks:
            nla_mute_states[track.name] = track.mute
            track.mute = True
        armature.animation_data.action = None

    # ── 2. Root-to-leaf bone order ────────────────────────────────────────────
    bone_order = []
    def _add(b):
        bone_order.append(b.name)
        for c in b.children:
            _add(c)
    for rb in armature.data.bones:
        if rb.parent is None:
            _add(rb)

    # ── 3. PHASE 1: step through every frame, read evaluated matrices ─────────
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    bpy.context.view_layer.update()

    original_rot_modes = {}
    for pbone in armature.pose.bones:
        original_rot_modes[pbone.name] = pbone.rotation_mode
        pbone.rotation_mode = 'QUATERNION'

    total = frame_end - frame_start + 1
    # print(f"[Bake]   Phase 1: evaluating {total} frames...")

    frame_data = {}
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj  = armature.evaluated_get(depsgraph)
        frame_data[frame] = {
            bn: eval_obj.pose.bones[bn].matrix.copy()
            for bn in bone_order
            if bn in eval_obj.pose.bones
        }

    bpy.ops.object.mode_set(mode='OBJECT')

    # ── 4. Pre-compute per-frame matrix_basis ─────────────────────────────────
    # print(f"[Bake]   Phase 2: writing F-curves directly...")

    bone_rest = {bn: armature.data.bones[bn].matrix_local.copy()
                 for bn in bone_order if bn in armature.data.bones}
    rot_modes = {bn: 'QUATERNION' for bn in bone_order if bn in armature.pose.bones}

    frames_basis = {}

    if initial_prev_quat:
        prev_quat = {bn: Quaternion(q) for bn, q in initial_prev_quat.items()}
    else:
        prev_quat = {}

    for frame in range(frame_start, frame_end + 1):
        mats    = frame_data[frame]
        f_basis = {}
        for bn in bone_order:
            if bn not in mats or bn not in armature.pose.bones or bn not in bone_rest:
                continue
            rest        = bone_rest[bn]
            pose_mat    = mats[bn]
            pbone       = armature.pose.bones[bn]
            parent_name = pbone.parent.name if pbone.parent else None

            if parent_name and parent_name in mats and parent_name in bone_rest:
                mb = (rest.inverted()
                      @ bone_rest[parent_name]
                      @ mats[parent_name].inverted()
                      @ pose_mat)
            else:
                mb = rest.inverted() @ pose_mat

            loc, rot_q, sc = mb.decompose()

            # Quaternion continuity: if dot product with previous frame is negative,
            # negate so Three.js always SLERPs the short way (<180°).
            if bn in prev_quat:
                if rot_q.dot(prev_quat[bn]) < 0.0:
                    rot_q = -rot_q
            prev_quat[bn] = rot_q.copy()

            rot_out = tuple(rot_q)
            f_basis[bn] = (tuple(loc), rot_out, tuple(sc), 'QUATERNION')
        frames_basis[frame] = f_basis


    # ── 5. Create action + Blender 5.0 slot ───────────────────────────────────
    action = bpy.data.actions.new(name="_BakeTemp")
    if not armature.animation_data:
        armature.animation_data_create()

    bake_slot = None
    if IS_BL5 and hasattr(action, 'slots'):
        for id_type in ('OBJECT', 'ARMATURE'):
            try:
                bake_slot = action.slots.new(id_type=id_type, name=armature.name)
                break
            except Exception:
                continue

    # ── 6. Build F-curve containers ───────────────────────────────────────────
    if IS_BL5 and bake_slot is not None and hasattr(action, 'layers'):
        layer      = action.layers.new(name='Layer')
        strip      = layer.strips.new(type='KEYFRAME')
        channelbag = strip.channelbag(bake_slot, ensure=True)

        def _new_fc(data_path, index, group):
            return channelbag.fcurves.new(data_path, index=index, group_name=group)
    else:
        def _new_fc(data_path, index, group):
            return action.fcurves.new(data_path, index=index, action_group=group)

    fcurve_map = {}
    for bn in bone_order:
        if bn not in armature.pose.bones or bn not in armature.data.bones:
            continue
        prefix = f'pose.bones["{bn}"]'
        rm     = rot_modes.get(bn, 'XYZ')

        for idx in range(3):
            fcurve_map[(bn, 'loc',   idx)] = _new_fc(f"{prefix}.location", idx, bn)
        for idx in range(3):
            fcurve_map[(bn, 'scale', idx)] = _new_fc(f"{prefix}.scale",    idx, bn)

        if rm == 'QUATERNION':
            for idx in range(4):
                fcurve_map[(bn, 'rot', idx)] = _new_fc(f"{prefix}.rotation_quaternion", idx, bn)
        elif rm == 'AXIS_ANGLE':
            for idx in range(4):
                fcurve_map[(bn, 'rot', idx)] = _new_fc(f"{prefix}.rotation_axis_angle", idx, bn)
        else:
            for idx in range(3):
                fcurve_map[(bn, 'rot', idx)] = _new_fc(f"{prefix}.rotation_euler", idx, bn)

    # ── 7. Insert values directly into F-curve keyframe arrays ────────────────
    for frame in range(frame_start, frame_end + 1):
        for bn, (loc, rot_out, sc, rm) in frames_basis.get(frame, {}).items():
            for idx in range(3):
                if (bn, 'loc', idx) in fcurve_map:
                    fcurve_map[(bn, 'loc', idx)].keyframe_points.insert(
                        frame, loc[idx], options={'FAST'})
            for idx in range(3):
                if (bn, 'scale', idx) in fcurve_map:
                    fcurve_map[(bn, 'scale', idx)].keyframe_points.insert(
                        frame, sc[idx], options={'FAST'})
            rot_channels = len(rot_out)
            for idx in range(rot_channels):
                if (bn, 'rot', idx) in fcurve_map:
                    fcurve_map[(bn, 'rot', idx)].keyframe_points.insert(
                        frame, rot_out[idx], options={'FAST'})

    # ── 8. Finalise: set LINEAR + update ──────────────────────────────────────
    for fc in fcurve_map.values():
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
        fc.update()

    # ── 9. Restore armature state ─────────────────────────────────────────────
    armature.animation_data.action = None
    for track in armature.animation_data.nla_tracks:
        if track.name in nla_mute_states:
            track.mute = nla_mute_states[track.name]

    for pbone in armature.pose.bones:
        if pbone.name in original_rot_modes:
            pbone.rotation_mode = original_rot_modes[pbone.name]

    ref_quats = {}
    if frame_start in frames_basis:
        for bn, (loc, rot_out, sc, rm) in frames_basis[frame_start].items():
            ref_quats[bn] = rot_out

    return action, bake_slot, ref_quats


def _push_to_nla(armature, action, bake_slot=None):
    if not armature.animation_data:
        armature.animation_data_create()
    armature.animation_data.action = None

    for track in list(armature.animation_data.nla_tracks):
        if track.name == action.name:
            armature.animation_data.nla_tracks.remove(track)

    track       = armature.animation_data.nla_tracks.new()
    track.name  = action.name
    strip_start = int(action.frame_range[0])
    strip       = track.strips.new(action.name, strip_start, action)
    strip.name  = action.name

    if hasattr(strip, 'action_slot') and strip.action_slot is None:
        slot = bake_slot
        if slot is None and hasattr(action, 'slots') and action.slots:
            slot = action.slots[0]
        if slot is not None:
            try:
                strip.action_slot = slot
            except Exception as e:
                print(f"[Bake]   Strip slot note: {e}")

    frames = f"{action.frame_range[0]:.0f}–{action.frame_range[1]:.0f}"
    print(f"[Bake]   → NLA  '{action.name}'  ({frames} frames)")
    return strip


def bake_all_signs_to_glb(
    armature_name = ARMATURE_NAME,
    output_glb    = OUTPUT_GLB,
    signs_filter  = None,
):
    global SIGN_LIBRARY

    blend_dir = bpy.path.abspath("//")

    json_path = os.path.join(blend_dir, "signs.json")
    with open(json_path, 'r', encoding='utf-8') as f:
        SIGN_LIBRARY = json.load(f)
        print(f"SIGN_LIBRARY loaded.")

    armature = _resolve_armature(armature_name)

    # Clear all NLA tracks from previous bakes so the GLB only contains fresh clips.
    # Without this, Blender renames new actions to "l.001", "i.001" etc. (because
    # old actions still exist in bpy.data.actions), and the viewer plays the old
    # stale clips instead of the newly baked ones.
    if armature.animation_data:
        stale = list(armature.animation_data.nla_tracks)
        for t in stale:
            armature.animation_data.nla_tracks.remove(t)
        if stale:
            print(f"[Bake] Cleared {len(stale)} stale NLA tracks.")

    original_rot_modes = {}
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for pbone in armature.pose.bones:
        original_rot_modes[pbone.name] = pbone.rotation_mode
        pbone.rotation_mode = 'QUATERNION'
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[Bake] Set {len(original_rot_modes)} bones to QUATERNION rotation mode.")

    STATIC_CLIPS = {
        "Start_Position": "Start_Position",
        "Hand_Relaxed":   "Hand_Relaxed",
    }

    all_signs = [k for k in SIGN_LIBRARY if k not in STATIC_CLIPS]
    if signs_filter:
        signs_to_bake = [s for s in signs_filter
                         if s in SIGN_LIBRARY and s not in STATIC_CLIPS]
    else:
        signs_to_bake = all_signs

    total = len(STATIC_CLIPS) + len(signs_to_bake)
    bar   = "═" * 60
    print(f"\n{bar}")
    print(f"[Bake] {total} clips  ({len(signs_to_bake)} signs  +  {len(STATIC_CLIPS)} static)")
    print(f"[Bake] Armature : '{armature.name}'")
    print(f"[Bake] Output   : {os.path.join(blend_dir, output_glb)}")
    print(f"{bar}\n")

    baked = []
    global_ref_quats = None

    # ── STEP 1: Static clips ──────────────────────────────────────────────────
    for clip_name, pose_name in STATIC_CLIPS.items():
        print(f"[Bake] Static  '{clip_name}'")
        reset_animation()

        end_frame = _animate_static_clip(pose_name, start_frame=1, hold_frames=6)
        action, slot, ref_quats = _bake_armature(armature, 1, end_frame, global_ref_quats)

        if action:
            old = bpy.data.actions.get(clip_name)
            if old:
                bpy.data.actions.remove(old)
            action.name = clip_name
            _push_to_nla(armature, action, slot)
            baked.append(clip_name)
            if global_ref_quats is None:
                global_ref_quats = ref_quats
                print(f"[Bake]   Global quaternion reference set from '{clip_name}'")
        else:
            print(f"[Bake]   ✗  No action for '{clip_name}'")

    # ── STEP 2: Sign clips ────────────────────────────────────────────────────
    n = len(signs_to_bake)
    for i, word in enumerate(signs_to_bake, 1):
        data = SIGN_LIBRARY[word]
        print(f"\n[Bake] [{i:>3}/{n}]  '{word}'")
        reset_animation()

        end_frame = _animate_sign_for_baking(word, data, start_frame=1)
        action, slot, _ = _bake_armature(armature, 1, end_frame, global_ref_quats)

        if action:
            old = bpy.data.actions.get(word)
            if old:
                bpy.data.actions.remove(old)
            action.name = word
            _push_to_nla(armature, action, slot)
            baked.append(word)
        else:
            print(f"[Bake]   ✗  No action for '{word}'")

    # ── STEP 3: Export GLB ────────────────────────────────────────────────────
    glb_path = os.path.join(blend_dir, output_glb)
    print(f"\n{bar}")
    print(f"[Bake] Exporting {len(baked)} clips → {glb_path}")
    print(f"{bar}")

    armature.animation_data.action = None
    saved_constraints = _remove_bone_constraints(armature)
    print(f"[Bake] Removed {len(saved_constraints)} bone constraints for export.")

    try:
        bpy.ops.export_scene.gltf(
            filepath             = glb_path,
            export_format        = 'GLB',
            export_animations    = True,
            export_nla_strips    = True,
            export_current_frame = False,
            export_skins         = True,
            export_morph         = True,
            export_apply         = False,
        )
    finally:
        _restore_bone_constraints(armature, saved_constraints)
        print(f"[Bake] Restored {len(saved_constraints)} bone constraints.")

    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for pbone in armature.pose.bones:
        if pbone.name in original_rot_modes:
            pbone.rotation_mode = original_rot_modes[pbone.name]
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[Bake] Restored original rotation modes.")

    bpy.context.scene.frame_set(1)
    reset_animation()

    print(f"\n[Bake] ✓  Done!  {len(baked)} clips baked.")
    print(f"[Bake]    {baked}\n")
    return baked


def bake_single_sign(word, armature_name=ARMATURE_NAME):
    """
    Convenience wrapper: bakes and re-exports just one sign.
    Note: this re-exports the full GLB, so all previously-baked NLA
    tracks are included automatically.
    """
    return bake_all_signs_to_glb(
        armature_name = armature_name,
        signs_filter  = [word],
    )
