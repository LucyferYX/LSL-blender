# ══════════════════════════════════════════════════════════════════════════════
#  BAKE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
import time as _time

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

    hold_time    = data.get("duration", DEFAULT_HOLD)
    head_action       = data.get("head")
    chest_data        = data.get("chest")
    eyes_data         = data.get("eyes")
    right_shoulder    = data.get("right_shoulder")
    left_shoulder     = data.get("left_shoulder")
    expression   = data.get("expression")
    _left_val   = data.get("left")
    is_mirror   = _left_val == "mirror_right" or (isinstance(_left_val, dict) and bool(_left_val.get("mirror_right")))

    sides_config = {}
    for side in ["right", "left"]:
        hd = _resolve_hand_data(data, side)
        if hd is not None:
            sides_config[side] = hd

    # ── Frame 1: Start_Position for both sides ────────────────────────────────
    _apply_start_position("right", start_frame)
    _apply_start_position("left",  start_frame)
    keyframe_expression(None, start_frame)

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
        _apply_pose_offsets(hd, side, sign_frame)
    for side, hd in sides_config.items():
        load_pose(hd["shape"], side=side,
                  apply_arm=False, apply_fingers=True,
                  keyframe_on_frame=sign_frame)
    keyframe_expression(expression, sign_frame)

    # ── Head ──────────────────────────────────────────────────────────────────
    if head_action:
        animate_head(head_action, start_frame, sign_frame, move_end, settle_frame)

    # ── Chest ─────────────────────────────────────────────────────────────────
    if chest_data:
        animate_chest(chest_data, start_frame, sign_frame, move_end, settle_frame)

    # ── Eyes ──────────────────────────────────────────────────────────────────
    if eyes_data:
        animate_eyes(eyes_data, start_frame, sign_frame, move_end, settle_frame)

    # ── Shoulders ─────────────────────────────────────────────────────────────
    if right_shoulder or left_shoulder:
        animate_shoulders(right_shoulder, left_shoulder, start_frame, sign_frame, move_end, settle_frame)

    # ── Movement ──────────────────────────────────────────────────────────────
    protect_rotation   = False
    per_side_end_shape = {}

    for side, hd in sides_config.items():
        move = hd.get("move")
        if not move:
            continue
        pr, es = dispatch_move_or_list(move, side, hd, sign_frame, hold_time, is_mirror)
        protect_rotation |= pr
        if es:
            per_side_end_shape[side] = es

    # ── Lock at move_end and settle ───────────────────────────────────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for frame in [move_end, settle_frame]:
        for side, hd in sides_config.items():
            loc_pose   = hd["orientation"] if hd.get("shape") == "Start_Position" else hd["location"]
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

    # ── mid_ret: Hand_Relaxed as finger waypoint out of the sign ─────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    for side in signing_sides:
        load_pose("Hand_Relaxed", side=side, apply_arm=False, apply_fingers=True, keyframe_on_frame=mid_ret)

    # ── Return to Start_Position at clip end ──────────────────────────────────
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
    _apply_start_position("right", return_frame)
    _apply_start_position("left",  return_frame)
    keyframe_expression(None, return_frame)

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
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name, con_type, con_name, props in saved:
        pbone = armature.pose.bones.get(bone_name)
        if not pbone:
            continue
        con = pbone.constraints.new(type=con_type)
        con.name = con_name
        failed = []
        for key, val in props.items():
            try:
                setattr(con, key, val)
                actual = getattr(con, key, '???')
                if actual != val:
                    failed.append(f"{key}: set={val!r} got={actual!r}")
            except Exception as e:
                failed.append(f"{key}: EXCEPTION {e}")

    bpy.ops.object.mode_set(mode='OBJECT')


def _animate_static_clip(pose_name, start_frame=1, hold_frames=6):
    for frame in [start_frame, start_frame + hold_frames]:
        if pose_name == "Start_Position":
            _apply_start_position("right", frame)
            _apply_start_position("left",  frame)
        else:
            for side in ["right", "left"]:
                load_pose(pose_name, side=side, keyframe_on_frame=frame)
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


def _snapshot_frame(action, slot, frame):
    """Return {(data_path, array_index): value} for all F-curve keypoints at the given frame."""
    snap = {}
    for fc in _iter_action_fcurves(action, slot):
        for kp in fc.keyframe_points:
            if abs(kp.co.x - frame) < 0.5:
                snap[(fc.data_path, fc.array_index)] = kp.co.y
                break
    return snap


def _debug_arm_frame1(action, slot, label):
    """Print frame-1 rotation_quaternion for left and right lower arm bones."""
    bones = ['J_Bip_R_LowerArm', 'J_Bip_L_LowerArm']
    for bn in bones:
        vals = {}
        for fc in _iter_action_fcurves(action, slot):
            if f'"{bn}"' not in fc.data_path:
                continue
            if 'rotation_quaternion' not in fc.data_path:
                continue
            for kp in fc.keyframe_points:
                if abs(kp.co.x - 1) < 0.5:
                    vals[fc.array_index] = kp.co.y
                    break
        if vals:
            q = [round(vals.get(i, 0), 5) for i in range(4)]
            print(f"[Debug][ArmF1] {label}  {bn}: {q}")


def _pin_frames(action, slot, snapshot, frames):
    """Overwrite keypoint values at the given frames with values from snapshot."""
    for fc in _iter_action_fcurves(action, slot):
        key = (fc.data_path, fc.array_index)
        if key not in snapshot:
            continue
        val = snapshot[key]
        changed = False
        for kp in fc.keyframe_points:
            if any(abs(kp.co.x - f) < 0.5 for f in frames):
                kp.co.y = val
                changed = True
        if changed:
            fc.update()


def _bake_armature(armature, frame_start, frame_end, initial_prev_quat=None, exclude_prefixes=None, initial_bone_quats=None):
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
    if exclude_prefixes:
        bone_order = [bn for bn in bone_order
                      if not any(bn.startswith(p) for p in exclude_prefixes)]

    # ── 3. PHASE 1: step through every frame, read evaluated matrices ─────────
    # Seed IK to the correct local minimum BEFORE the mode_set(mode='POSE') that
    # starts phase 1.  That mode switch triggers a depsgraph evaluation; if IK's
    # internal state is at the wrong local minimum at that moment (because NLA was
    # just muted and the last evaluation was from rest pose), every frame in the
    # bake loop records the wrong elbow position and the GLB is wrong.
    # Fix: remove all constraints → set bone channels from pre-VTA (blend-file)
    # rotations → restore constraints.  _restore_bone_constraints ends in OBJECT
    # mode and triggers an evaluation with IK active from our seed values, putting
    # IK's internal state at the correct local minimum before phase 1 begins.
    if initial_bone_quats:
        # Remove ONLY IK and COPY_ROTATION — the constraints that have the local-minimum
        # problem.  Removing ALL constraints (via _remove_bone_constraints) risks breaking
        # DAMPED_TRACK on finger bones if any property fails to restore, which causes
        # finger bones to stop tracking their empties → stretched fingers in the baked GLB.
        _saved_ik_seed = []
        for pbone in armature.pose.bones:
            for con in list(pbone.constraints):
                if con.type not in ('IK', 'COPY_ROTATION'):
                    continue
                props = {}
                for prop in con.bl_rna.properties:
                    if prop.identifier in ('rna_type', 'type', 'name') or prop.is_readonly:
                        continue
                    try:
                        props[prop.identifier] = getattr(con, prop.identifier)
                    except Exception:
                        pass
                _saved_ik_seed.append((pbone.name, con.type, con.name, props))
                pbone.constraints.remove(con)
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
        # Only seed IK-chain bones (the ones whose IK/COPY_ROTATION was removed).
        # Finger bones use DAMPED_TRACK: writing a pre-VTA seed to them changes the
        # roll orientation DAMPED_TRACK picks, which rotates finger bones wrongly in
        # sign frames where the finger empties are far from their rest positions.
        _ik_seeded_bones = {bn for bn, _, _, _ in _saved_ik_seed}
        for pbone in armature.pose.bones:
            if pbone.name in initial_bone_quats and pbone.name in _ik_seeded_bones:
                pbone.rotation_quaternion = initial_bone_quats[pbone.name].copy()
        bpy.ops.object.mode_set(mode='OBJECT')
        _restore_bone_constraints(armature, _saved_ik_seed)

    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    bpy.ops.pose.select_all(action='SELECT')
    if not initial_bone_quats:
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

            # No constraint in this rig modifies bone scale (IK/COPY_ROTATION/DAMPED_TRACK
            # are all rotation-only).  visual_transform_apply() can leave tiny non-unit scale
            # in channels via floating-point error; baking that scale makes bones appear
            # elongated in the viewer.  Force unit scale on every bone.
            sc = (1.0, 1.0, 1.0)

            # Quaternion continuity: if dot product with previous frame is negative,
            # negate so Three.js always SLERPs the short way (<180°).
            if bn in prev_quat:
                if rot_q.dot(prev_quat[bn]) < 0.0:
                    rot_q = -rot_q
            prev_quat[bn] = rot_q.copy()

            rot_out = tuple(rot_q)
            f_basis[bn] = (tuple(loc), rot_out, sc, 'QUATERNION')
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

    return strip



def bake_all_signs_to_glb(
    armature_name = ARMATURE_NAME,
    output_glb    = OUTPUT_GLB,
    signs_filter  = None,
):
    global SIGN_LIBRARY

    blend_dir = bpy.path.abspath("//")

    json_path = os.path.join(blend_dir, "signs.json")
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        SIGN_LIBRARY = json.load(f)

    setup_arm_pole_targets()

    armature = _resolve_armature(armature_name)

    # Capture the correct IK state BEFORE clearing NLA tracks.
    # After clearing NLA tracks the bones are driven only by IK constraints, which
    # can converge to a wrong local minimum on this rig's dual-IK setup.  The saved
    # .blend already has the bones in the correct position, so we snapshot here while
    # the evaluated scene is still correct, then use this as the IK warm-start for
    # every _bake_armature call.
    original_rot_modes = {}
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for pbone in armature.pose.bones:
        original_rot_modes[pbone.name] = pbone.rotation_mode
        pbone.rotation_mode = 'QUATERNION'
    # Capture pre-VTA bone rotations — these are the blend file's saved pre-constraint
    # channels.  IK converges to the correct local minimum when starting from these
    # values (same as fresh file open), so we use them to re-seed IK post-bake.
    _pre_vta_bone_quats = {pbone.name: pbone.rotation_quaternion.copy()
                           for pbone in armature.pose.bones}
    bpy.ops.pose.select_all(action='SELECT')
    bpy.context.view_layer.update()
    bpy.ops.pose.visual_transform_apply()
    _ik_warm_start = {pbone.name: pbone.rotation_quaternion.copy()
                      for pbone in armature.pose.bones}
    bpy.ops.object.mode_set(mode='OBJECT')

    # Snapshot IK-related empty transforms so the post-bake cleanup can restore
    # the exact positions/rotations from the saved file, rather than relying on
    # load_pose() which may set slightly different rotations (causing COPY_ROTATION
    # on LowerArm to land IK at a different evaluated position).
    _ik_empty_names = set()
    for pbone in armature.pose.bones:
        for con in pbone.constraints:
            if con.type == 'IK':
                if con.target:      _ik_empty_names.add(con.target.name)
                if con.pole_target: _ik_empty_names.add(con.pole_target.name)
            elif con.type == 'COPY_ROTATION':
                if con.target:      _ik_empty_names.add(con.target.name)
    # also include arm/hand/shoulder empties and all finger empties.
    # Finger empties are not IK targets but are referenced by DAMPED_TRACK on finger
    # bones.  reset_animation() clears their keyframes but not their physical positions,
    # so without snapshotting them the viewport shows the last baked sign's finger pose.
    for _n in ([RIGHTHAND_EMPTY, RIGHTARM_EMPTY, LEFTHAND_EMPTY, LEFTARM_EMPTY]
               + RIGHT_FINGERS + LEFT_FINGERS):
        _ik_empty_names.add(_n)
    _empty_snapshot = {}
    for _n in _ik_empty_names:
        _obj = bpy.data.objects.get(_n)
        if _obj:
            _empty_snapshot[_n] = {
                'location':       _obj.location.copy(),
                'rotation_euler': _obj.rotation_euler.copy(),
                'rotation_mode':  _obj.rotation_mode,
            }

    # ── Pre-bake snapshot ────────────────────────────────────────────────────
    bpy.context.view_layer.update()
    _pre_depsgraph = bpy.context.evaluated_depsgraph_get()
    _pre_eval      = armature.evaluated_get(_pre_depsgraph)
    # Capture full evaluated bone matrices (in armature-local space) for every bone.
    # These are used in post-bake cleanup: we remove IK, set bones to these matrices
    # directly, then restore IK.  Since the bones start at the correct IK solution,
    # the solver converges to the right local minimum instead of rest-pose minimum.
    _pre_bone_matrices = {pbone.name: _pre_eval.pose.bones[pbone.name].matrix.copy()
                          for pbone in armature.pose.bones
                          if pbone.name in _pre_eval.pose.bones}

    # Clear all NLA tracks from previous bakes so the GLB only contains fresh clips.
    # Without this, Blender renames new actions to "l.001", "i.001" etc. (because
    # old actions still exist in bpy.data.actions), and the viewer plays the old
    # stale clips instead of the newly baked ones.
    if armature.animation_data:
        stale = list(armature.animation_data.nla_tracks)
        for t in stale:
            armature.animation_data.nla_tracks.remove(t)

    face_obj = bpy.data.objects.get(FACE_MESH_NAME)
    if face_obj and face_obj.data.shape_keys:
        sk = face_obj.data.shape_keys
        if not sk.animation_data:
            sk.animation_data_create()
        stale_sk = list(sk.animation_data.nla_tracks)
        for t in stale_sk:
            sk.animation_data.nla_tracks.remove(t)

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

    baked        = []
    global_ref_quats = None
    _t_start     = _time.time()
    # Accumulate (clip_name, action, slot) here; push all to NLA together after
    # every bake is done.  Pushing to NLA immediately adds muted NLA tracks that
    # slightly bleed through the depsgraph during subsequent bakes (even when
    # muted), causing the IK solver to converge to a slightly different elbow
    # position for sign clips vs Start_Position → visible snap at clip boundaries.
    # By deferring NLA push until all baking is finished every bake runs in the
    # same clean scene state → identical IK convergence → no snap.
    _nla_queue   = []   # (clip_name, action, slot)

    # ── STEP 1: Static clips ──────────────────────────────────────────────────
    for clip_name, pose_name in STATIC_CLIPS.items():
        _t0 = _time.time()
        reset_animation()

        end_frame = _animate_static_clip(pose_name, start_frame=1, hold_frames=6)
        action, slot, ref_quats = _bake_armature(armature, 1, end_frame, global_ref_quats,
                                                  exclude_prefixes=BAKE_EXCLUDE_PREFIXES,
                                                  initial_bone_quats=_pre_vta_bone_quats)

        if action:
            old = bpy.data.actions.get(clip_name)
            if old:
                bpy.data.actions.remove(old)
            action.name = clip_name
            _nla_queue.append((clip_name, action, slot))
            baked.append(clip_name)
            if global_ref_quats is None:
                global_ref_quats = ref_quats
                print(f"[Bake] Static  '{clip_name}'  ({_time.time()-_t0:.2f}s)  — quaternion reference set")
            else:
                print(f"[Bake] Static  '{clip_name}'  ({_time.time()-_t0:.2f}s)")
        else:
            print(f"[Bake] Static  '{clip_name}'  ✗  No action")

    # ── STEP 2: Sign clips ────────────────────────────────────────────────────
    n = len(signs_to_bake)
    w = len(str(n))
    for i, word in enumerate(signs_to_bake, 1):
        _t0 = _time.time()
        data = SIGN_LIBRARY[word]
        reset_animation()

        end_frame = _animate_sign_for_baking(word, data, start_frame=1)
        action, slot, _ = _bake_armature(armature, 1, end_frame, global_ref_quats,
                                          exclude_prefixes=BAKE_EXCLUDE_PREFIXES,
                                          initial_bone_quats=_pre_vta_bone_quats)

        if action:
            old = bpy.data.actions.get(word)
            if old:
                bpy.data.actions.remove(old)
            action.name = word
            _nla_queue.append((word, action, slot))
            baked.append(word)
            print(f"[Bake] [{i:>{w}}/{n}]  '{word}'  →  {end_frame} frames  ({_time.time()-_t0:.2f}s)")
        else:
            print(f"[Bake] [{i:>{w}}/{n}]  '{word}'  ✗  no action")

    # ── STEP 2b: Push all armature actions to NLA now that all baking is done ─
    for _clip_name, _action, _slot in _nla_queue:
        _push_to_nla(armature, _action, _slot)

    # ── STEP 3: Export GLB ────────────────────────────────────────────────────
    glb_path = os.path.join(blend_dir, output_glb)

    # Zero out emission on all materials — VRoid MToon → PBR conversion leaves emission
    # strength set, making the skin appear self-illuminated / washed out in Three.js.
    emission_backup = {}
    import sys as _sys, io as _io, warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.filterwarnings('ignore', category=DeprecationWarning)
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    em_in = node.inputs.get('Emission') or node.inputs.get('Emission Color')
                    st_in = node.inputs.get('Emission Strength')
                    emission_backup[mat.name] = {
                        'color':    tuple(em_in.default_value)  if em_in else None,
                        'strength': st_in.default_value         if st_in else None,
                        'node':     node.name,
                    }
                    if em_in:   em_in.default_value = (0, 0, 0, 1)
                    if st_in:   st_in.default_value = 0.0

    armature.animation_data.action = None

    # Collect every action linked to our baked NLA strips.
    _our_actions = set()
    for t in armature.animation_data.nla_tracks:
        for s in t.strips:
            if s.action:
                _our_actions.add(s.action.name)
    _fobj = bpy.data.objects.get(FACE_MESH_NAME)
    if _fobj and _fobj.data.shape_keys and _fobj.data.shape_keys.animation_data:
        for t in _fobj.data.shape_keys.animation_data.nla_tracks:
            for s in t.strips:
                if s.action:
                    _our_actions.add(s.action.name)
    # Clear NLA tracks from any other armature objects (e.g. hidden Mixamo rig).
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != armature and obj.animation_data:
            for t in list(obj.animation_data.nla_tracks):
                obj.animation_data.nla_tracks.remove(t)
    # Remove all actions not linked to our NLA strips — this suppresses both
    # "Animation target pose.bones[mixamorig:*] not found" and
    # "Multiple rotation mode detected" GLTF exporter warnings.
    _purged = 0
    for _action in list(bpy.data.actions):
        if _action.name not in _our_actions:
            bpy.data.actions.remove(_action)
            _purged += 1
    saved_constraints = _remove_bone_constraints(armature)

    _t_bake_end = _time.time()
    _t_export_start = _time.time()
    print(f"[Bake] Exporting '{output_glb}' ({len(baked)} clips)... (this might take a while)")
    _saved_stdout = _sys.stdout
    try:
        _sys.stdout = _io.StringIO()
        with _warnings.catch_warnings():
            _warnings.filterwarnings('ignore', category=DeprecationWarning)
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
        _sys.stdout = _saved_stdout
        _restore_bone_constraints(armature, saved_constraints)
        with _warnings.catch_warnings():
            _warnings.filterwarnings('ignore', category=DeprecationWarning)
            for mat in bpy.data.materials:
                if not mat.use_nodes or mat.name not in emission_backup:
                    continue
                bk   = emission_backup[mat.name]
                node = mat.node_tree.nodes.get(bk['node'])
                if not node:
                    continue
                em_in = node.inputs.get('Emission') or node.inputs.get('Emission Color')
                st_in = node.inputs.get('Emission Strength')
                if em_in and bk['color']:   em_in.default_value = bk['color']
                if st_in and bk['strength'] is not None: st_in.default_value = bk['strength']

    bpy.context.scene.frame_set(1)
    reset_animation()
    # Restore arm and finger empties to Start_Position rather than from the snapshot.
    # The snapshot captures blend-file-saved positions, which may be from any frame the
    # user last had open (not necessarily Start_Position). Using load_pose is deterministic.
    _apply_start_position("right", None)
    _apply_start_position("left",  None)
    # Mute all NLA tracks so the viewport is driven purely by IK.
    if armature.animation_data:
        for track in armature.animation_data.nla_tracks:
            track.mute = True

    # Re-seed IK to the correct local minimum for the viewport (same approach as the
    # bake seeding).  Only remove IK and COPY_ROTATION — NOT DAMPED_TRACK on finger
    # bones.  Removing all constraints via _remove_bone_constraints and restoring them
    # can fail to perfectly restore DAMPED_TRACK, leaving fingers broken in the viewport.
    _saved_post = []
    for pbone in armature.pose.bones:
        for con in list(pbone.constraints):
            if con.type not in ('IK', 'COPY_ROTATION'):
                continue
            props = {}
            for prop in con.bl_rna.properties:
                if prop.identifier in ('rna_type', 'type', 'name') or prop.is_readonly:
                    continue
                try:
                    props[prop.identifier] = getattr(con, prop.identifier)
                except Exception:
                    pass
            _saved_post.append((pbone.name, con.type, con.name, props))
            pbone.constraints.remove(con)
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    _post_seeded_bones = {bn for bn, _, _, _ in _saved_post}
    for pbone in armature.pose.bones:
        if pbone.name in _pre_vta_bone_quats and pbone.name in _post_seeded_bones:
            pbone.rotation_quaternion = _pre_vta_bone_quats[pbone.name]
        if pbone.name in original_rot_modes:
            pbone.rotation_mode = original_rot_modes[pbone.name]
        pbone.scale = (1.0, 1.0, 1.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    _restore_bone_constraints(armature, _saved_post)
    bpy.context.view_layer.update()

    _t_end = _time.time()
    print(f"[Bake] ✓  Done!  {len(baked)} clips baked.")
    print(f"[Bake]    Bake: {_t_bake_end - _t_start:.1f}s   Export: {_t_end - _t_export_start:.1f}s   Total: {_t_end - _t_start:.1f}s")
    print(f"[Bake]    {baked}")
    print(f"{bar}\n")
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
