import bpy, numpy as np

def rebuild_skin_direct(mesh_keyword, mat_keyword, base_img_name, out_name,
                        darken=0.85, warm_gb=0.92):
    obj = next((o for o in bpy.data.objects if o.type=='MESH' and mesh_keyword in o.name), None)
    if not obj: print(f"No mesh: {mesh_keyword}"); return
    mat = next((s.material for s in obj.material_slots
                if s.material and mat_keyword in s.material.name), None)
    if not mat: print(f"No mat: {mat_keyword}"); return
    base = bpy.data.images.get(base_img_name)
    if not base: print(f"No image: {base_img_name}"); return
    w, h = base.size
    px = np.array(base.pixels[:]).reshape(w*h, 4)
    result = px.copy()
    result[:, 0] = np.clip(px[:, 0] * darken, 0, 1)
    result[:, 1] = np.clip(px[:, 1] * darken * warm_gb, 0, 1)
    result[:, 2] = np.clip(px[:, 2] * darken * warm_gb, 0, 1)
    old = bpy.data.images.get(out_name)
    if old: bpy.data.images.remove(old)
    baked = bpy.data.images.new(out_name, w, h, alpha=True)
    baked.pixels[:] = result.flatten().tolist()
    baked.pack()
    mat.node_tree.nodes.clear()
    out_node = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf    = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    tex     = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = baked
    bsdf.inputs['Roughness'].default_value = 0.9
    bsdf.inputs['Metallic'].default_value  = 0.0
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    mat.node_tree.links.new(bsdf.outputs['BSDF'], out_node.inputs['Surface'])
    print(f"Done: {mat.name} → {out_name}")

# Body: more darkening — front-lit arms look near-white
rebuild_skin_direct('Body', 'Body_00_SKIN', '_10', 'body_skin_v3', darken=0.78, warm_gb=0.87)
# Face: less darkening — face is already more acceptable
rebuild_skin_direct('Face', 'Face_00_SKIN', '_04', 'face_skin_v3', darken=0.86, warm_gb=0.92)
print("Check Material Preview.")
# Mouth/tongue interior: heavy darken + redder tint
rebuild_skin_direct('Face', 'FaceMouth', '_01', 'mouth_skin_v1', darken=0.55, warm_gb=0.78)

# Torso (LauraB body skin): same darkening as main Body
rebuild_skin_direct('Torso', 'Body_00_SKIN', '_10.002', 'torso_skin_v1', darken=0.78, warm_gb=0.87)
# Shirt_CropTop: multiply near-white texture to gray (no warm tint — neutral gray)
rebuild_skin_direct('Shirt_CropTop', 'Tops_01_CLOTH', '_13.002', 'shirt_croptop_v1', darken=0.40, warm_gb=1.0)
