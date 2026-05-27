import sys
import bpy
from pathlib import Path


ASSET_DIR = Path(__file__).resolve().parent
PUBLISHED_PATH = ASSET_DIR.parent / "published" / "lil_material_contracts.blend"
GENERATED_DIR = ASSET_DIR / "generated"
GENERATED_PATH = GENERATED_DIR / "lil_material_contracts.generated.blend"
ASSET_AUTHOR = "HoGLTF"

SOCKET_SEMANTICS = {
    "BaseColor": "group=mainColor; role=colorFactor; blend=BaseTex*BaseColor",
    "BaseTex": "group=mainColor; role=texture; blend=BaseTex*BaseColor",
    "BaseTexUV": "group=mainColor; role=uv",
    "Alpha": "group=alpha; role=scalarFactor",
    "_BaseTexAlpha": "group=blenderPreview; role=baseTextureAlpha; source=BaseTex.a; blend=_BaseTexAlpha*Alpha; export=false; hidden=true",
    "AlphaCutoff": "group=alpha; role=cutoff",
    "ShadowColor": "group=shadow; role=colorFactor; blend=ShadowTex*ShadowColor",
    "ShadowTex": "group=shadow; role=texture; blend=ShadowTex*ShadowColor",
    "ShadowBorder": "group=shadow; role=threshold",
    "ShadowBlur": "group=shadow; role=softness",
    "ShadowStrength": "group=shadow; role=scalarFactor",
    "RimColor": "group=rim; role=colorFactor; blend=RimTex*RimColor",
    "RimTex": "group=rim; role=texture; blend=RimTex*RimColor",
    "RimBorder": "group=rim; role=threshold",
    "RimBlur": "group=rim; role=softness",
    "RimFresnelPower": "group=rim; role=fresnelPower",
    "EmissionColor": "group=emission; role=colorFactor; blend=EmissionTex*EmissionColor*EmissionBlend",
    "EmissionTex": "group=emission; role=texture; blend=EmissionTex*EmissionColor*EmissionBlend",
    "EmissionBlend": "group=emission; role=scalarFactor",
    "OutlineColor": "group=outline; role=colorFactor; blend=OutlineTex*OutlineColor",
    "OutlineTex": "group=outline; role=texture; blend=OutlineTex*OutlineColor",
    "OutlineWidth": "group=outline; role=width",
    "OutlineWidthMask": "group=outline; role=widthMask; blend=OutlineWidth*OutlineWidthMask",
    "Roughness": "group=reflection; role=roughnessFactor; blend=RoughnessTex*Roughness",
    "RoughnessTex": "group=reflection; role=roughnessTexture; blend=RoughnessTex*Roughness",
    "Metallic": "group=reflection; role=metallicFactor; blend=MetallicTex*Metallic",
    "MetallicTex": "group=reflection; role=metallicTexture; blend=MetallicTex*Metallic",
    "Reflectance": "group=reflection; role=reflectanceFactor",
    "IOR": "group=reflection; role=ior",
    "NormalTex": "group=normal; role=texture",
    "NormalScale": "group=normal; role=scale",
    "MatCapColor": "group=matcap; role=colorFactor; blend=MatCapTex*MatCapColor*MatCapBlend",
    "MatCapTex": "group=matcap; role=texture; blend=MatCapTex*MatCapColor*MatCapBlend",
    "MatCapBlend": "group=matcap; role=scalarFactor",
    "SSSColor": "group=sss; role=colorFactor",
    "SSSStrength": "group=sss; role=scalarFactor",
    "SSSThicknessTex": "group=sss; role=thicknessTexture",
    "Main2ndColor": "group=mainColor2nd; role=colorFactor; blend=Main2ndTex*Main2ndColor",
    "Main2ndTex": "group=mainColor2nd; role=texture; blend=Main2ndTex*Main2ndColor",
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for datablock_collection in (
        bpy.data.materials,
        bpy.data.meshes,
        bpy.data.node_groups,
        bpy.data.images,
    ):
        for item in list(datablock_collection):
            if item.users == 0:
                datablock_collection.remove(item)


def set_iface_defaults(socket, default=None, minimum=None, maximum=None, description=""):
    if hasattr(socket, "description"):
        socket.description = description
    if "hidden=true" in description and hasattr(socket, "hide_value"):
        socket.hide_value = True
    if default is not None and hasattr(socket, "default_value"):
        socket.default_value = default
    if minimum is not None and hasattr(socket, "min_value"):
        socket.min_value = minimum
    if maximum is not None and hasattr(socket, "max_value"):
        socket.max_value = maximum


def add_input(group, name, socket_type, default=None, minimum=None, maximum=None, priority="", target=""):
    sock = group.interface.new_socket(name=name, in_out="INPUT", socket_type=socket_type)
    desc_parts = []
    if priority:
        desc_parts.append(f"priority={priority}")
    if target:
        desc_parts.append(f"target={target}")
    if name in SOCKET_SEMANTICS:
        desc_parts.append(SOCKET_SEMANTICS[name])
    desc = "; ".join(desc_parts)
    set_iface_defaults(sock, default, minimum, maximum, desc)
    return sock


def add_output(group, name, socket_type):
    return group.interface.new_socket(name=name, in_out="OUTPUT", socket_type=socket_type)


def socket_type_for(contract_type):
    if contract_type == "Color":
        return "NodeSocketColor"
    if contract_type == "Texture2D":
        return "NodeSocketColor"
    if contract_type == "Enum":
        return "NodeSocketInt"
    if contract_type == "Vector":
        return "NodeSocketVector"
    return "NodeSocketFloat"


def make_group(name, sockets, group_color, variant=""):
    group = bpy.data.node_groups.new(name, "ShaderNodeTree")
    group.color_tag = group_color
    group.description = "HoGLTF lil material contract node group draft 0.3"
    group["HoGLTFContract"] = "lil-material"
    if variant:
        group["HoLilToonVariant"] = variant

    for item in sockets:
        socket_type = socket_type_for(item["type"])
        add_input(
            group,
            item["name"],
            socket_type,
            item.get("default"),
            item.get("min"),
            item.get("max"),
            item.get("priority", ""),
            item.get("target", ""),
        )

    add_output(group, "Shader", "NodeSocketShader")
    add_output(group, "Color", "NodeSocketColor")
    add_output(group, "Alpha", "NodeSocketFloat")

    nodes = group.nodes
    links = group.links
    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-900, 0)
    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (520, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (220, 80)

    # Keep the demo shader simple, but preserve the important grouped contract:
    # main color preview = BaseTex * BaseColor. Full lilToon semantics still
    # live in metadata and the Unity importer.
    base_color_output = build_main_color_preview(nodes, links, group_input)
    if base_color_output is not None and "Base Color" in bsdf.inputs:
        links.new(base_color_output, bsdf.inputs["Base Color"])
    if "Roughness" in group_input.outputs and "Roughness" in bsdf.inputs:
        links.new(group_input.outputs["Roughness"], bsdf.inputs["Roughness"])
    if "Metallic" in group_input.outputs and "Metallic" in bsdf.inputs:
        links.new(group_input.outputs["Metallic"], bsdf.inputs["Metallic"])
    alpha_output = build_alpha_preview(nodes, links, group_input)
    if alpha_output is not None and "Alpha" in bsdf.inputs:
        links.new(alpha_output, bsdf.inputs["Alpha"])
    if "Shader" in group_output.inputs and "BSDF" in bsdf.outputs:
        links.new(bsdf.outputs["BSDF"], group_output.inputs["Shader"])
    if base_color_output is not None and "Color" in group_output.inputs:
        links.new(base_color_output, group_output.inputs["Color"])
    if alpha_output is not None and "Alpha" in group_output.inputs:
        links.new(alpha_output, group_output.inputs["Alpha"])

    mark_asset(group, f"{name} material contract node group")
    return group


def build_main_color_preview(nodes, links, group_input):
    has_base_color = "BaseColor" in group_input.outputs
    has_base_tex = "BaseTex" in group_input.outputs
    if has_base_color and has_base_tex:
        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (-240, 160)
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 1.0
        links.new(group_input.outputs["BaseTex"], mix.inputs["Color1"])
        links.new(group_input.outputs["BaseColor"], mix.inputs["Color2"])
        return mix.outputs["Color"]
    if has_base_tex:
        return group_input.outputs["BaseTex"]
    if has_base_color:
        return group_input.outputs["BaseColor"]
    return None


def build_alpha_preview(nodes, links, group_input):
    has_alpha = "Alpha" in group_input.outputs
    has_base_tex_alpha = "_BaseTexAlpha" in group_input.outputs
    if has_alpha and has_base_tex_alpha:
        multiply = nodes.new("ShaderNodeMath")
        multiply.location = (-240, -40)
        multiply.operation = "MULTIPLY"
        links.new(group_input.outputs["_BaseTexAlpha"], multiply.inputs[0])
        links.new(group_input.outputs["Alpha"], multiply.inputs[1])
        return multiply.outputs["Value"]
    if has_alpha:
        return group_input.outputs["Alpha"]
    if has_base_tex_alpha:
        return group_input.outputs["_BaseTexAlpha"]
    return None


def mark_asset(datablock, description):
    datablock.asset_mark()
    datablock.asset_data.description = description
    datablock.asset_data.author = ASSET_AUTHOR


def merge_socket_lists(*lists):
    merged = []
    seen = set()
    for socket_list in lists:
        for item in socket_list:
            if item["name"] in seen:
                continue
            merged.append(dict(item))
            seen.add(item["name"])
    return merged


def sockets_by_name(source, names):
    lookup = {item["name"]: item for item in source}
    missing = [name for name in names if name not in lookup]
    if missing:
        raise KeyError(f"Missing socket definitions: {', '.join(missing)}")
    return [lookup[name] for name in names]


def override_sockets(sockets, overrides):
    result = []
    for item in sockets:
        item = dict(item)
        if item["name"] in overrides:
            item.update(overrides[item["name"]])
        result.append(item)
    return result


SHARED = [
    {"name": "AlphaMode", "type": "Enum", "min": 0, "max": 3, "default": 0, "priority": "S", "target": "shader variant / _RenderingMode"},
    {"name": "Alpha", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "S", "target": "_Color.a"},
    {"name": "_BaseTexAlpha", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "internal", "target": "Blender preview only"},
    {"name": "AlphaCutoff", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "S", "target": "_Cutoff"},
    {"name": "CullMode", "type": "Enum", "min": 0, "max": 2, "default": 2, "priority": "S", "target": "_Cull"},
    {"name": "ZWriteOverride", "type": "Float", "min": -1, "max": 1, "default": -1, "priority": "A", "target": "_ZWrite"},
    {"name": "AlphaToMaskOverride", "type": "Float", "min": -1, "max": 1, "default": -1, "priority": "A", "target": "_AlphaToMask"},
    {"name": "RenderQueueOffset", "type": "Float", "min": -100, "max": 100, "default": 0, "priority": "B", "target": "material renderQueue"},
    {"name": "TargetShaderVariant", "type": "Enum", "min": 0, "max": 9, "default": 0, "priority": "S", "target": "shader selection metadata"},
    {"name": "TransparentMode", "type": "Enum", "min": 0, "max": 2, "default": 0, "priority": "A", "target": "_TransparentMode / shader selection metadata"},
]

LILTOON = [
    {"name": "BaseColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "S", "target": "_Color"},
    {"name": "BaseTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "S", "target": "_MainTex"},
    {"name": "BaseTexUV", "type": "Enum", "min": 0, "max": 3, "default": 0, "priority": "A", "target": "_MainTex UV"},
    {"name": "NormalTex", "type": "Texture2D", "default": (0.5, 0.5, 1, 1), "priority": "A", "target": "_BumpMap"},
    {"name": "NormalScale", "type": "Float", "min": -10, "max": 10, "default": 1, "priority": "A", "target": "_BumpScale"},
    {"name": "UseShadow", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "S", "target": "_UseShadow"},
    {"name": "ShadowColor", "type": "Color", "default": (0.82, 0.76, 0.85, 1), "priority": "S", "target": "_ShadowColor"},
    {"name": "ShadowTex", "type": "Texture2D", "default": (0, 0, 0, 1), "priority": "S", "target": "_ShadowColorTex"},
    {"name": "ShadowBorder", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "S", "target": "_ShadowBorder"},
    {"name": "ShadowBlur", "type": "Float", "min": 0, "max": 1, "default": 0.1, "priority": "S", "target": "_ShadowBlur"},
    {"name": "ShadowStrength", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "S", "target": "_ShadowStrength"},
    {"name": "ShadowReceive", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "A", "target": "_ShadowReceive"},
    {"name": "UseRim", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "A", "target": "_UseRim"},
    {"name": "RimColor", "type": "Color", "default": (0.66, 0.5, 0.48, 1), "priority": "A", "target": "_RimColor"},
    {"name": "RimTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_RimColorTex"},
    {"name": "RimBorder", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "A", "target": "_RimBorder"},
    {"name": "RimBlur", "type": "Float", "min": 0, "max": 1, "default": 0.65, "priority": "A", "target": "_RimBlur"},
    {"name": "RimFresnelPower", "type": "Float", "min": 0.01, "max": 50, "default": 3.5, "priority": "A", "target": "_RimFresnelPower"},
    {"name": "UseOutline", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "S", "target": "_UseOutline"},
    {"name": "OutlineColor", "type": "Color", "default": (0.6, 0.56, 0.73, 1), "priority": "S", "target": "_OutlineColor"},
    {"name": "OutlineTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_OutlineTex"},
    {"name": "OutlineWidth", "type": "Float", "min": 0, "max": 1, "default": 0.08, "priority": "S", "target": "_OutlineWidth"},
    {"name": "OutlineWidthMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_OutlineWidthMask"},
    {"name": "OutlineFixWidth", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "A", "target": "_OutlineFixWidth"},
    {"name": "UseEmission", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "A", "target": "_UseEmission"},
    {"name": "EmissionColor", "type": "Color", "default": (0, 0, 0, 1), "priority": "A", "target": "_EmissionColor"},
    {"name": "EmissionTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "A", "target": "_EmissionMap"},
    {"name": "EmissionBlend", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "B", "target": "_EmissionBlend"},
    {"name": "Roughness", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "B", "target": "_Smoothness"},
    {"name": "RoughnessTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_SmoothnessTex"},
    {"name": "Metallic", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_Metallic"},
    {"name": "MetallicTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "C", "target": "_MetallicGlossMap"},
    {"name": "Reflectance", "type": "Float", "min": 0, "max": 1, "default": 0.04, "priority": "B", "target": "_Reflectance"},
    {"name": "IOR", "type": "Float", "min": 1, "max": 3, "default": 1.5, "priority": "B", "target": "_Reflectance / _OpenPBRIOR"},
    {"name": "UseSSS", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_UseSSS"},
    {"name": "SSSColor", "type": "Color", "default": (1, 0.42, 0.32, 1), "priority": "B", "target": "_SSSColor"},
    {"name": "SSSStrength", "type": "Float", "min": 0, "max": 2, "default": 0.35, "priority": "B", "target": "_SSSStrength"},
    {"name": "SSSThicknessTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_SSSThicknessMap"},
    {"name": "UseMatCap", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_UseMatCap"},
    {"name": "MatCapColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "B", "target": "_MatCapColor"},
    {"name": "MatCapTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_MatCapTex"},
    {"name": "MatCapBlend", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "B", "target": "_MatCapBlend"},
    {"name": "ParallaxTex", "type": "Texture2D", "default": (0.5, 0.5, 0.5, 1), "priority": "C", "target": "_ParallaxMap"},
    {"name": "ParallaxScale", "type": "Float", "min": 0, "max": 1, "default": 0.02, "priority": "C", "target": "_Parallax"},
    {"name": "BackfaceColor", "type": "Color", "default": (0, 0, 0, 0), "priority": "B", "target": "_BackfaceColor"},
    {"name": "UseMain2ndTex", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "_UseMain2ndTex"},
    {"name": "Main2ndTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "reserved", "target": "_Main2ndTex"},
    {"name": "Main2ndColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "reserved", "target": "_Color2nd"},
    {"name": "UseBacklight", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_UseBacklight"},
    {"name": "BacklightColor", "type": "Color", "default": (0.85, 0.8, 0.7, 1), "priority": "C", "target": "_BacklightColor"},
    {"name": "UseGlitter", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_UseGlitter"},
    {"name": "GlitterColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_GlitterColor"},
    {"name": "UseDissolve", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "_DissolveParams"},
    {"name": "DissolveMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "reserved", "target": "_DissolveMask"},
    {"name": "UseRefraction", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "refraction variant"},
    {"name": "RefractionStrength", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "refraction properties"},
    {"name": "UseGem", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "gem variant"},
    {"name": "UseFur", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "fur variant"},
    {"name": "DistanceFade", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "_DistanceFade"},
    {"name": "StencilRef", "type": "Float", "min": 0, "max": 255, "default": 0, "priority": "reserved", "target": "_StencilRef"},
    {"name": "OpenPBRCoatWeight", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "_OpenPBRCoatWeight"},
    {"name": "OpenPBRTransmissionWeight", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "_OpenPBRTransmissionWeight"},
]

LILTOON_TESSELLATION = [
    {"name": "UseTessellation", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "tessellation variant"},
    {"name": "TessellationStrength", "type": "Float", "min": 0, "max": 1, "default": 0.1, "priority": "C", "target": "_TessStrength"},
    {"name": "TessellationEdgeLength", "type": "Float", "min": 1, "max": 50, "default": 10, "priority": "C", "target": "_TessEdgeLength"},
    {"name": "TessellationShrink", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_TessShrink"},
]

LILTOON_REFRACTION = [
    {"name": "RefractionFresnelPower", "type": "Float", "min": 0.01, "max": 50, "default": 5, "priority": "C", "target": "_RefractionFresnelPower"},
    {"name": "RefractionColorFromMain", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "C", "target": "_RefractionColorFromMain"},
    {"name": "RefractionColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_RefractionColor"},
]

LILTOON_GEM = [
    {"name": "GemChromaticAberration", "type": "Float", "min": 0, "max": 1, "default": 0.02, "priority": "C", "target": "_GemChromaticAberration"},
    {"name": "GemEnvContrast", "type": "Float", "min": 0, "max": 10, "default": 1, "priority": "C", "target": "_GemEnvContrast"},
    {"name": "GemEnvColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_GemEnvColor"},
    {"name": "GemParticleLoop", "type": "Float", "min": 0, "max": 10, "default": 1, "priority": "C", "target": "_GemParticleLoop"},
    {"name": "GemParticleColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_GemParticleColor"},
    {"name": "GemVRParallaxStrength", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_GemVRParallaxStrength"},
]

LILTOON_FUR = [
    {"name": "FurNoiseMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "C", "target": "_FurNoiseMask"},
    {"name": "FurMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "C", "target": "_FurMask"},
    {"name": "FurLengthMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "C", "target": "_FurLengthMask"},
    {"name": "FurVectorTex", "type": "Texture2D", "default": (0.5, 0.5, 1, 1), "priority": "C", "target": "_FurVectorTex"},
    {"name": "FurVectorScale", "type": "Float", "min": -10, "max": 10, "default": 1, "priority": "C", "target": "_FurVectorScale"},
    {"name": "FurVector", "type": "Vector", "default": (0, 0, 0), "priority": "C", "target": "_FurVector"},
    {"name": "VertexColor2FurVector", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_VertexColor2FurVector"},
    {"name": "FurGravity", "type": "Float", "min": -1, "max": 1, "default": 0, "priority": "C", "target": "_FurGravity"},
    {"name": "FurRandomize", "type": "Float", "min": 0, "max": 1, "default": 0.1, "priority": "C", "target": "_FurRandomize"},
    {"name": "FurAO", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_FurAO"},
    {"name": "FurLayerNum", "type": "Float", "min": 1, "max": 64, "default": 10, "priority": "C", "target": "_FurLayerNum"},
    {"name": "FurRootOffset", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_FurRootOffset"},
    {"name": "FurCutoutLength", "type": "Float", "min": 0, "max": 1, "default": 0.2, "priority": "C", "target": "_FurCutoutLength"},
    {"name": "FurTouchStrength", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_FurTouchStrength"},
    {"name": "FurRimColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_FurRimColor"},
    {"name": "FurRimFresnelPower", "type": "Float", "min": 0.01, "max": 50, "default": 5, "priority": "C", "target": "_FurRimFresnelPower"},
    {"name": "FurRimAntiLight", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_FurRimAntiLight"},
]

LILTOON_MULTI = [
    {"name": "UseMulti", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "reserved", "target": "multi variant"},
]

LILTOON_FAKE_SHADOW = [
    {"name": "FakeShadowColor", "type": "Color", "default": (0, 0, 0, 1), "priority": "C", "target": "_FakeShadowColor"},
    {"name": "FakeShadowVector", "type": "Vector", "default": (0, -1, 0), "priority": "C", "target": "_FakeShadowVector"},
    {"name": "FakeShadowMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "C", "target": "_FakeShadowMask"},
]

STANDARD_SOCKET_NAMES = [
    "BaseColor",
    "BaseTex",
    "BaseTexUV",
    "NormalTex",
    "NormalScale",
    "UseShadow",
    "ShadowColor",
    "ShadowTex",
    "ShadowBorder",
    "ShadowBlur",
    "ShadowStrength",
    "ShadowReceive",
    "UseRim",
    "RimColor",
    "RimTex",
    "RimBorder",
    "RimBlur",
    "RimFresnelPower",
    "UseOutline",
    "OutlineColor",
    "OutlineTex",
    "OutlineWidth",
    "OutlineWidthMask",
    "OutlineFixWidth",
    "UseEmission",
    "EmissionColor",
    "EmissionTex",
    "EmissionBlend",
    "Roughness",
    "RoughnessTex",
    "Metallic",
    "MetallicTex",
    "Reflectance",
    "IOR",
    "UseSSS",
    "SSSColor",
    "SSSStrength",
    "SSSThicknessTex",
    "UseMatCap",
    "MatCapColor",
    "MatCapTex",
    "MatCapBlend",
    "ParallaxTex",
    "ParallaxScale",
    "BackfaceColor",
    "UseMain2ndTex",
    "Main2ndTex",
    "Main2ndColor",
    "UseBacklight",
    "BacklightColor",
    "UseGlitter",
    "GlitterColor",
    "UseDissolve",
    "DissolveMask",
    "DistanceFade",
    "StencilRef",
    "OpenPBRCoatWeight",
    "OpenPBRTransmissionWeight",
]

LITE_SOCKET_NAMES = [
    "BaseColor",
    "BaseTex",
    "BaseTexUV",
    "UseShadow",
    "ShadowColor",
    "ShadowTex",
    "ShadowBorder",
    "ShadowBlur",
    "ShadowStrength",
    "UseRim",
    "RimColor",
    "RimBorder",
    "RimBlur",
    "RimFresnelPower",
    "UseOutline",
    "OutlineColor",
    "OutlineWidth",
    "OutlineFixWidth",
    "UseEmission",
    "EmissionColor",
    "EmissionTex",
    "UseMatCap",
    "MatCapColor",
    "MatCapTex",
    "MatCapBlend",
]

FAKE_SHADOW_BASE_NAMES = [
    "BaseColor",
    "BaseTex",
    "BaseTexUV",
    "Alpha",
    "AlphaCutoff",
    "CullMode",
]

STANDARD_SOCKETS = sockets_by_name(LILTOON, STANDARD_SOCKET_NAMES)
LITE_SOCKETS = sockets_by_name(LILTOON, LITE_SOCKET_NAMES)

LILPBR = [
    {"name": "BaseColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "S", "target": "_Color"},
    {"name": "BaseTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "S", "target": "_MainTex"},
    {"name": "BaseTexUV", "type": "Enum", "min": 0, "max": 3, "default": 0, "priority": "A", "target": "UV metadata"},
    {"name": "VertexColorMode", "type": "Enum", "min": 0, "max": 2, "default": 0, "priority": "B", "target": "_VertexColorMode"},
    {"name": "UVMode", "type": "Enum", "min": 0, "max": 2, "default": 0, "priority": "B", "target": "_UVMode"},
    {"name": "NormalTex", "type": "Texture2D", "default": (0.5, 0.5, 1, 1), "priority": "A", "target": "_BumpMap"},
    {"name": "NormalScale", "type": "Float", "min": 0, "max": 4, "default": 1, "priority": "A", "target": "_BumpScale"},
    {"name": "TextureMode", "type": "Enum", "min": 0, "max": 1, "default": 0, "priority": "A", "target": "_TextureMode"},
    {"name": "PBRMap", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "A", "target": "_PBRMap"},
    {"name": "PBRPreset", "type": "Enum", "min": 0, "max": 3, "default": 0, "priority": "A", "target": "_PBRInputPreset"},
    {"name": "Metallic", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "A", "target": "_Metallic"},
    {"name": "MetallicTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "A", "target": "_MetallicGlossMap"},
    {"name": "MetallicChannel", "type": "Enum", "min": 0, "max": 3, "default": 0, "priority": "B", "target": "_MetallicChannel"},
    {"name": "Roughness", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "A", "target": "_Glossiness"},
    {"name": "RoughnessTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "A", "target": "_SmoothnessMap"},
    {"name": "SmoothnessChannel", "type": "Enum", "min": 0, "max": 3, "default": 3, "priority": "B", "target": "_SmoothnessChannel"},
    {"name": "OcclusionStrength", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "A", "target": "_OcclusionStrength"},
    {"name": "OcclusionTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "A", "target": "_OcclusionMap"},
    {"name": "OcclusionChannel", "type": "Enum", "min": 0, "max": 3, "default": 1, "priority": "B", "target": "_OcclusionChannel"},
    {"name": "HeightScale", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_Parallax"},
    {"name": "HeightTex", "type": "Texture2D", "default": (0, 0, 0, 1), "priority": "B", "target": "_ParallaxMap"},
    {"name": "HeightChannel", "type": "Enum", "min": 0, "max": 3, "default": 2, "priority": "C", "target": "_HeightChannel"},
    {"name": "Reflectance", "type": "Float", "min": 0, "max": 1, "default": 0.04, "priority": "A", "target": "_Reflectance"},
    {"name": "IOR", "type": "Float", "min": 1, "max": 3, "default": 1.5, "priority": "B", "target": "_IOR"},
    {"name": "EmissionColor", "type": "Color", "default": (0, 0, 0, 1), "priority": "A", "target": "_EmissionColor"},
    {"name": "EmissionTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "A", "target": "_EmissionMap"},
    {"name": "BackfaceOverride", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_BackfaceOverride"},
    {"name": "BackfaceColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "B", "target": "_BackfaceColor"},
    {"name": "BackfaceTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_BackfaceTex"},
    {"name": "ClearCoat", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_ClearCoat"},
    {"name": "ClearCoatMask", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "B", "target": "_ClearCoatMask"},
    {"name": "ClearCoatRoughness", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "B", "target": "_ClearCoatSmoothness"},
    {"name": "ClearCoatReflectance", "type": "Float", "min": 0, "max": 1, "default": 0.04, "priority": "C", "target": "_ClearCoatReflectance"},
    {"name": "Anisotropy", "type": "Float", "min": -1, "max": 1, "default": 0, "priority": "C", "target": "_Anisotropy"},
    {"name": "AnisotropyTex", "type": "Texture2D", "default": (0.5, 0.5, 1, 1), "priority": "C", "target": "_AnisotropyDirection"},
    {"name": "Cloth", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_Cloth"},
    {"name": "ClothColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_ClothColor"},
    {"name": "ClothFuzz", "type": "Float", "min": 0, "max": 1, "default": 0.5, "priority": "C", "target": "_ClothFuzz"},
    {"name": "Translucent", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_Translucent"},
    {"name": "TranslucentColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_TranslucentColor"},
    {"name": "Subsurface", "type": "Float", "min": 0, "max": 1, "default": 0, "priority": "C", "target": "_SubsurfaceScattering"},
    {"name": "SubsurfaceTex", "type": "Texture2D", "default": (1, 1, 1, 1), "priority": "C", "target": "_SubsurfaceMap"},
    {"name": "SubsurfaceColor", "type": "Color", "default": (1, 1, 1, 1), "priority": "C", "target": "_SubsurfaceColor"},
    {"name": "SubsurfaceThickness", "type": "Float", "min": 0, "max": 1, "default": 1, "priority": "C", "target": "_SubsurfaceThickness"},
]


def toon_variant_sockets(toon_sockets, variant_id, extra_sockets=None, overrides=None):
    overrides = dict(overrides or {})
    overrides.setdefault("TargetShaderVariant", {"default": variant_id})
    sockets = merge_socket_lists(SHARED, toon_sockets, extra_sockets or [])
    return override_sockets(sockets, overrides)


def create_material_with_group(name, group, x):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (1, 1, 1, 1)
    material["HoGLTFContractGroup"] = group.name
    nodes = material.node_tree.nodes
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (360, 0)
    group_node = nodes.new("ShaderNodeGroup")
    group_node.node_tree = group
    group_node.location = (-120, 0)
    group_node.label = group.name
    material.node_tree.links.new(group_node.outputs["Shader"], output.inputs["Surface"])
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0, 0))
    obj = bpy.context.object
    obj.name = name.replace("_Material", "_Cube")
    obj.data.materials.append(material)
    return material


def parse_args():
    args = sys.argv
    if "--" not in args:
        return {
            "output_path": GENERATED_PATH,
        }

    tail = args[args.index("--") + 1:]
    output_path = None
    index = 0
    while index < len(tail):
        arg = tail[index]
        if arg == "--publish":
            raise ValueError(
                "--publish is disabled. Generate a draft, verify it, then manually copy it to "
                f"{PUBLISHED_PATH}"
            )
        elif arg == "--output":
            index += 1
            if index >= len(tail):
                raise ValueError("--output requires a path")
            output_path = Path(tail[index])
        else:
            raise ValueError(f"Unknown argument: {arg}")
        index += 1

    if output_path is None:
        output_path = GENERATED_PATH

    return {
        "output_path": output_path,
    }


def main():
    args = parse_args()
    output_path = Path(args["output_path"]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clear_scene()

    full_toon = merge_socket_lists(
        LILTOON,
        LILTOON_TESSELLATION,
        LILTOON_REFRACTION,
        LILTOON_GEM,
        LILTOON_FUR,
        LILTOON_MULTI,
        LILTOON_FAKE_SHADOW,
    )
    variant_specs = [
        ("HoLilToonMax", toon_variant_sockets(full_toon, 0), "max"),
        ("HoLilToonStandard", toon_variant_sockets(STANDARD_SOCKETS, 1), "standard"),
        ("HoLilToonLite", toon_variant_sockets(LITE_SOCKETS, 2), "lite"),
        (
            "HoLilToonTessellation",
            toon_variant_sockets(
                STANDARD_SOCKETS,
                3,
                LILTOON_TESSELLATION,
                {"UseTessellation": {"default": 1}},
            ),
            "tessellation",
        ),
        (
            "HoLilToonRefraction",
            toon_variant_sockets(
                STANDARD_SOCKETS,
                4,
                merge_socket_lists(
                    sockets_by_name(LILTOON, ["UseRefraction", "RefractionStrength", "OpenPBRTransmissionWeight"]),
                    LILTOON_REFRACTION,
                ),
                {
                    "AlphaMode": {"default": 3},
                    "UseRefraction": {"default": 1},
                    "RefractionStrength": {"default": 0.1},
                    "OpenPBRTransmissionWeight": {"default": 0.2},
                },
            ),
            "refraction",
        ),
        (
            "HoLilToonGem",
            toon_variant_sockets(
                STANDARD_SOCKETS,
                5,
                merge_socket_lists(
                    sockets_by_name(LILTOON, ["UseGem", "UseRefraction", "RefractionStrength"]),
                    LILTOON_REFRACTION,
                    LILTOON_GEM,
                ),
                {
                    "AlphaMode": {"default": 3},
                    "UseGem": {"default": 1},
                    "UseRefraction": {"default": 1},
                    "RefractionStrength": {"default": 0.25},
                },
            ),
            "gem",
        ),
        (
            "HoLilToonFur",
            toon_variant_sockets(
                STANDARD_SOCKETS,
                6,
                merge_socket_lists(sockets_by_name(LILTOON, ["UseFur"]), LILTOON_FUR),
                {"UseFur": {"default": 1}},
            ),
            "fur",
        ),
        (
            "HoLilToonFurOnly",
            toon_variant_sockets(
                STANDARD_SOCKETS,
                7,
                merge_socket_lists(sockets_by_name(LILTOON, ["UseFur"]), LILTOON_FUR),
                {"UseFur": {"default": 1}},
            ),
            "furOnly",
        ),
        (
            "HoLilToonMulti",
            toon_variant_sockets(
                STANDARD_SOCKETS,
                8,
                LILTOON_MULTI,
                {"UseMulti": {"default": 1}},
            ),
            "multi",
        ),
        (
            "HoLilToonFakeShadow",
            toon_variant_sockets(
                sockets_by_name(LILTOON, ["BaseColor", "BaseTex", "BaseTexUV"]),
                9,
                LILTOON_FAKE_SHADOW,
            ),
            "fakeShadow",
        ),
    ]

    toon_groups = [
        make_group(name, sockets, "SHADER", variant)
        for name, sockets, variant in variant_specs
    ]
    pbr_group = make_group("HoLilPBR", SHARED + LILPBR, "SHADER")

    spacing = 1.45
    start_x = -spacing * (len(toon_groups) / 2)
    for index, group in enumerate(toon_groups):
        create_material_with_group(f"{group.name}_Contract_Material", group, start_x + index * spacing)
    create_material_with_group("HoLilPBR_Contract_Material", pbr_group, start_x + len(toon_groups) * spacing)

    bpy.ops.object.light_add(type="AREA", location=(0, -3, 4))
    bpy.context.object.name = "ContractDemo_AreaLight"
    bpy.context.object.data.energy = 350
    bpy.context.object.data.size = 4

    bpy.ops.object.camera_add(location=(0, -6, 3), rotation=(1.1, 0, 0))
    bpy.context.scene.camera = bpy.context.object

    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    print(f"Saved {output_path}")
    print(f"Generated draft only. Publish manually after verification: {PUBLISHED_PATH}")
    for group in toon_groups:
        print(f"{group.name} sockets: {len(group.interface.items_tree) - 3} inputs")
    print(f"HoLilPBR sockets: {len(SHARED) + len(LILPBR)} inputs")


if __name__ == "__main__":
    main()
