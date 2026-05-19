from __future__ import annotations

import json
from dataclasses import dataclass

import bpy

from . import asset_registry


MMD_SHADER_GROUP_HINTS = {"MMDShaderDev", "MMDShader"}
CONTRACT_GROUPS = {
    "lilToon": "HoLilToonStandard",
    "lilPBR": "HoLilPBR",
}


@dataclass
class MMDMaterialInfo:
    material: bpy.types.Material
    shader_node: bpy.types.Node
    base_image: bpy.types.Image | None
    toon_image: bpy.types.Image | None
    diffuse_color: tuple[float, float, float, float]
    ambient_color: tuple[float, float, float, float]
    alpha: float
    double_sided: bool


def collect_scope_materials(context, scope):
    if scope == "ACTIVE":
        material = getattr(context, "material", None)
        return [material] if material is not None else []

    if scope == "ALL":
        return list(bpy.data.materials)

    materials = []
    seen = set()
    for obj in getattr(context, "selected_objects", []):
        for slot in getattr(obj, "material_slots", []):
            material = slot.material
            if material is None or material.name in seen:
                continue
            materials.append(material)
            seen.add(material.name)
    return materials


def convert_mmd_materials(materials, target_family="lilToon", activate_output=True, duplicate_material=False):
    converted = []
    skipped = []

    for material in materials:
        if material is None:
            continue
        info = inspect_mmd_material(material)
        if info is None:
            skipped.append(material.name)
            continue
        if duplicate_material:
            converted_material = convert_mmd_material_copy(info, target_family=target_family)
        else:
            converted_material = append_mmd_contract_to_material(
                info,
                target_family=target_family,
                activate_output=activate_output,
            )
        converted.append((material, converted_material))

    return {
        "converted": converted,
        "skipped": skipped,
    }


def inspect_mmd_material(material):
    node_tree = getattr(material, "node_tree", None)
    if node_tree is None:
        return None

    shader_node = find_mmd_shader_node(node_tree)
    if shader_node is None:
        return None

    return MMDMaterialInfo(
        material=material,
        shader_node=shader_node,
        base_image=find_linked_image(shader_node, "Base Tex"),
        toon_image=find_linked_image(shader_node, "Toon Tex"),
        diffuse_color=color_input(shader_node, "Diffuse Color", (1, 1, 1, 1)),
        ambient_color=color_input(shader_node, "Ambient Color", (0.82, 0.76, 0.85, 1)),
        alpha=float_input(shader_node, "Alpha", 1.0),
        double_sided=bool(round(float_input(shader_node, "Double Sided", 1.0))),
    )


def find_mmd_shader_node(node_tree):
    for node in node_tree.nodes:
        group = getattr(node, "node_tree", None)
        if group is None:
            continue

        group_name = getattr(group, "name", "")
        if group_name in MMD_SHADER_GROUP_HINTS or group_name.startswith("MMDShader"):
            return node

        input_names = {socket.name for socket in getattr(node, "inputs", [])}
        if {"Base Tex", "Base Alpha", "Toon Tex", "Double Sided"}.issubset(input_names):
            return node

    return None


def find_linked_image(node, input_name):
    socket = node.inputs.get(input_name)
    if socket is None or not socket.is_linked:
        return None

    for link in socket.links:
        source = link.from_node
        if getattr(source, "type", "") == "TEX_IMAGE":
            return source.image
    return None


def color_input(node, input_name, fallback):
    socket = node.inputs.get(input_name)
    if socket is None or not hasattr(socket, "default_value"):
        return fallback
    value = tuple(float(v) for v in socket.default_value)
    if len(value) == 3:
        return value + (1.0,)
    return value[:4]


def float_input(node, input_name, fallback):
    socket = node.inputs.get(input_name)
    if socket is None or not hasattr(socket, "default_value"):
        return fallback
    try:
        return float(socket.default_value)
    except TypeError:
        return fallback


def convert_mmd_material_copy(info, target_family="lilToon"):
    if target_family not in CONTRACT_GROUPS:
        raise ValueError(f"Unsupported target material family: {target_family}")

    group = ensure_contract_group(CONTRACT_GROUPS[target_family])
    material = bpy.data.materials.new(unique_material_name(f"{info.material.name}_{target_family}"))
    material.use_nodes = True
    material.diffuse_color = info.diffuse_color
    material["HoGLTFConvertedFrom"] = info.material.name
    material["HoGLTFConverter"] = "MMDMaterial"

    if hasattr(material, "hogltf"):
        material.hogltf.export_contract = True
        material.hogltf.target_shader_family = target_family
        material.hogltf.contract_json = build_contract_json(info, target_family)

    build_contract_node_tree(material, group, info, target_family)
    return material


def append_mmd_contract_to_material(info, target_family="lilToon", activate_output=True):
    if target_family not in CONTRACT_GROUPS:
        raise ValueError(f"Unsupported target material family: {target_family}")

    material = info.material
    material.use_nodes = True
    material.diffuse_color = info.diffuse_color
    material["HoGLTFConvertedFrom"] = material.name
    material["HoGLTFConverter"] = "MMDMaterial"

    if hasattr(material, "hogltf"):
        material.hogltf.export_contract = True
        material.hogltf.target_shader_family = target_family
        material.hogltf.contract_json = build_contract_json(info, target_family)

    group = ensure_contract_group(CONTRACT_GROUPS[target_family])
    build_contract_node_cluster(material, group, info, target_family, activate_output=activate_output)
    return material


def ensure_contract_group(group_name):
    group = bpy.data.node_groups.get(group_name)
    if group is not None:
        return group

    blend_path = asset_registry.LIL_MATERIAL_CONTRACT_BLEND
    if not blend_path.exists():
        raise FileNotFoundError(f"HoGLTF material contract asset not found: {blend_path}")

    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        if group_name not in data_from.node_groups:
            raise KeyError(f"Node group '{group_name}' not found in {blend_path}")
        data_to.node_groups = [group_name]

    group = bpy.data.node_groups.get(group_name)
    if group is None:
        raise RuntimeError(f"Failed to load node group '{group_name}'")
    return group


def build_contract_node_tree(material, group, info, target_family):
    nodes = material.node_tree.nodes
    nodes.clear()
    build_contract_node_cluster(material, group, info, target_family, activate_output=True, origin=(0, 0))


def build_contract_node_cluster(material, group, info, target_family, activate_output=True, origin=None):
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    if origin is None:
        origin = next_cluster_origin(nodes)
    ox, oy = origin

    frame = nodes.new("NodeFrame")
    frame.label = f"HoGLTF MMD -> {target_family}"
    frame.name = unique_node_name(nodes, f"HoGLTF_{target_family}_Frame")
    frame.location = (ox - 720, oy + 180)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = unique_node_name(nodes, f"HoGLTF_{target_family}_Output")
    output.label = f"HoGLTF {target_family} Active Output"
    output.location = (ox + 420, oy)
    output.parent = frame
    output["HoGLTFGenerated"] = "MMDMaterial"
    if activate_output:
        output.is_active_output = True

    contract = nodes.new("ShaderNodeGroup")
    contract.name = unique_node_name(nodes, f"HoGLTF_{target_family}_Contract")
    contract.node_tree = group
    contract.location = (ox - 160, oy)
    contract.label = group.name
    contract.parent = frame
    contract["hogltf_node_group"] = True
    contract["HoGLTFGenerated"] = "MMDMaterial"

    if "Shader" in contract.outputs:
        links.new(contract.outputs["Shader"], output.inputs["Surface"])

    set_contract_input(contract, "BaseColor", info.diffuse_color)
    set_contract_input(contract, "Alpha", max(0.0, min(1.0, info.alpha)))
    set_contract_input(contract, "AlphaMode", 3 if info.alpha < 0.999 else 0)
    set_contract_input(contract, "CullMode", 0 if info.double_sided else 2)

    if target_family == "lilToon":
        set_contract_input(contract, "UseShadow", 1.0)
        set_contract_input(contract, "ShadowColor", info.ambient_color)
    else:
        set_contract_input(contract, "Metallic", 0.0)
        set_contract_input(contract, "Roughness", 0.5)

    if info.base_image is not None:
        image_node = make_image_node(nodes, info.base_image, (ox - 620, oy + 120), "MMD Base Tex")
        image_node.parent = frame
        link_if_possible(links, image_node, "Color", contract, "BaseTex")

    if target_family == "lilToon" and info.toon_image is not None:
        toon_node = make_image_node(nodes, info.toon_image, (ox - 620, oy - 120), "MMD Toon Tex")
        toon_node.parent = frame
        link_if_possible(links, toon_node, "Color", contract, "ShadowTex")


def set_contract_input(node, input_name, value):
    socket = node.inputs.get(input_name)
    if socket is None or not hasattr(socket, "default_value"):
        return
    socket.default_value = value


def make_image_node(nodes, image, location, label):
    node = nodes.new("ShaderNodeTexImage")
    node.image = image
    node.location = location
    node.label = label
    return node


def link_if_possible(links, from_node, from_socket, to_node, to_socket):
    if from_socket in from_node.outputs and to_socket in to_node.inputs:
        links.new(from_node.outputs[from_socket], to_node.inputs[to_socket])


def build_contract_json(info, target_family):
    variant = "standard" if target_family == "lilToon" else "pbr"
    return json.dumps(
        {
            "target": {
                "shaderFamily": target_family,
                "shaderVariant": variant,
                "renderingMode": "Transparent" if info.alpha < 0.999 else "Opaque",
            },
            "extras": {
                "mmd": {
                    "sourceMaterial": info.material.name,
                    "sourceNodeGroup": getattr(info.shader_node.node_tree, "name", ""),
                    "baseTexture": image_name(info.base_image),
                    "toonTexture": image_name(info.toon_image),
                    "doubleSided": info.double_sided,
                    "alpha": info.alpha,
                    "alphaSources": ["materialAlpha", "baseTextureAlpha", "toonTextureAlpha"],
                }
            },
        },
        ensure_ascii=False,
    )


def image_name(image):
    return image.name if image is not None else None


def next_cluster_origin(nodes):
    if len(nodes) == 0:
        return (0, 0)

    max_x = max(node.location.x for node in nodes)
    min_y = min(node.location.y for node in nodes)
    return (max_x + 520, min_y - 360)


def unique_node_name(nodes, base_name):
    if base_name not in nodes:
        return base_name
    index = 1
    while f"{base_name}.{index:03d}" in nodes:
        index += 1
    return f"{base_name}.{index:03d}"


def unique_material_name(base_name):
    if base_name not in bpy.data.materials:
        return base_name
    index = 1
    while f"{base_name}.{index:03d}" in bpy.data.materials:
        index += 1
    return f"{base_name}.{index:03d}"


class HoGLTFAssetConversionSettings(bpy.types.PropertyGroup):
    target_family: bpy.props.EnumProperty(
        name="目标材质",
        description="MMD 材质转换后的 HoGLTF 契约目标",
        items=(
            ("lilToon", "lilToon", "转换为 HoLilToonStandard 契约材质。"),
            ("lilPBR", "lilPBR", "转换为 HoLilPBR 契约材质。"),
        ),
        default="lilToon",
    ) # type: ignore

    scope: bpy.props.EnumProperty(
        name="范围",
        description="选择要转换哪些材质",
        items=(
            ("SELECTED", "选中物体", "转换选中物体材质槽中的 MMD 材质。"),
            ("ACTIVE", "当前材质", "只转换当前上下文材质。"),
            ("ALL", "全部材质", "扫描当前文件中的全部材质。"),
        ),
        default="SELECTED",
    ) # type: ignore

    activate_output: bpy.props.BoolProperty(
        name="设为活动输出",
        description="在原材质旁边生成 HoGLTF 契约节点后，将新的 Material Output 设为 active。原 MMD 节点保留。",
        default=True,
    ) # type: ignore

    duplicate_material: bpy.props.BoolProperty(
        name="创建材质副本",
        description="创建新的契约材质副本。关闭时在原材质节点树旁边追加契约节点。",
        default=False,
    ) # type: ignore


class HOGLTF_OT_convert_mmd_materials(bpy.types.Operator):
    bl_idname = "hogltf.convert_mmd_materials"
    bl_label = "转换 MMD 材质"
    bl_description = "按 HoGLTF 材质契约把 MMD 预设材质转换为 lilToon/lilPBR 契约材质"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.hogltf_asset_conversion
        materials = collect_scope_materials(context, settings.scope)
        result = convert_mmd_materials(
            materials,
            target_family=settings.target_family,
            activate_output=settings.activate_output,
            duplicate_material=settings.duplicate_material,
        )
        self.report(
            {"INFO"},
            f"HoGLTF: converted {len(result['converted'])} MMD material(s), skipped {len(result['skipped'])}.",
        )
        return {"FINISHED"}


class HOGLTF_PT_asset_conversion(bpy.types.Panel):
    bl_label = "HoGLTF Asset Conversion"
    bl_idname = "VIEW3D_PT_hogltf_asset_conversion"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "HoGLTF"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.hogltf_asset_conversion
        layout.prop(settings, "target_family")
        layout.prop(settings, "scope")
        layout.prop(settings, "activate_output")
        layout.prop(settings, "duplicate_material")
        layout.operator(HOGLTF_OT_convert_mmd_materials.bl_idname, icon="MATERIAL")


CLASSES = (
    HoGLTFAssetConversionSettings,
    HOGLTF_OT_convert_mmd_materials,
    HOGLTF_PT_asset_conversion,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hogltf_asset_conversion = bpy.props.PointerProperty(type=HoGLTFAssetConversionSettings)


def unregister():
    del bpy.types.Scene.hogltf_asset_conversion
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
