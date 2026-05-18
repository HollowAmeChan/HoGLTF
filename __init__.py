bl_info = {
    "name": "HoGLTF",
    "author": "Hollow",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "File > Export > glTF 2.0",
    "description": "Hollow glTF export bridge for lilToon/lilPBR material contracts.",
    "category": "Import-Export",
}

import json

import bpy


EXTENSION_NAME = "HO_materials_principled_lil"
LEGACY_EXTENSION_NAME = "HO_materials_openpbr_lil"
UI_PANEL_KEY = "HoGLTF Material Contract"


class HoGLTFExportSettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="HoGLTF",
        description="Enable Hollow glTF export extension hooks.",
        default=True,
    )

    export_material_contracts: bpy.props.BoolProperty(
        name="Material Contracts",
        description="Write Hollow material contracts into glTF material extensions.",
        default=True,
    )

    target_shader_family: bpy.props.EnumProperty(
        name="Target",
        description="Default Unity-side material family when a material does not override it.",
        items=(
            ("auto", "Auto", "Let the Unity importer choose lilToon or lilPBR from the contract."),
            ("lilToon", "lilToon", "Prefer lilToon on import."),
            ("lilPBR", "lilPBR", "Prefer lilPBR on import."),
            ("URP/Lit", "URP/Lit", "Temporary fallback target for testing."),
        ),
        default="auto",
    )

    write_debug_fields: bpy.props.BoolProperty(
        name="Debug Fields",
        description="Include Blender material name and custom-property hints in the contract.",
        default=True,
    )


class HoGLTFMaterialSettings(bpy.types.PropertyGroup):
    export_contract: bpy.props.BoolProperty(
        name="Export HoGLTF Contract",
        description="Export this material with the Hollow glTF material contract extension.",
        default=False,
    )

    target_shader_family: bpy.props.EnumProperty(
        name="Target",
        description="Unity-side material family for this material.",
        items=(
            ("inherit", "Inherit", "Use the scene export setting."),
            ("auto", "Auto", "Let the Unity importer choose from the contract."),
            ("lilToon", "lilToon", "Prefer lilToon on import."),
            ("lilPBR", "lilPBR", "Prefer lilPBR on import."),
            ("URP/Lit", "URP/Lit", "Temporary fallback target for testing."),
        ),
        default="inherit",
    )

    contract_json: bpy.props.StringProperty(
        name="Contract JSON",
        description="Optional raw JSON object to merge into the exported HoGLTF material contract.",
        default="",
    )


class HOGLTF_PT_material_settings(bpy.types.Panel):
    bl_label = "HoGLTF"
    bl_idname = "HOGLTF_PT_material_settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @classmethod
    def poll(cls, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        props = context.material.hogltf
        layout.prop(props, "export_contract")
        layout.prop(props, "target_shader_family")
        layout.prop(props, "contract_json")


def draw_export_settings(context, layout):
    props = context.scene.hogltf_export
    header, body = layout.panel("HOGLTF_export_settings", default_closed=False)
    header.use_property_split = False
    header.prop(props, "enabled")
    if body is not None:
        body.use_property_split = True
        body.prop(props, "export_material_contracts")
        body.prop(props, "target_shader_family")
        body.prop(props, "write_debug_fields")


def _target_shader_family(scene_props, material_props):
    if material_props.target_shader_family == "inherit":
        return scene_props.target_shader_family
    return material_props.target_shader_family


def _parse_contract_json(raw_json, material_name):
    if raw_json.strip() == "":
        return {}

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        print(f"HoGLTF: contract JSON on material '{material_name}' is invalid: {exc}")
        return {}

    if not isinstance(parsed, dict):
        print(f"HoGLTF: contract JSON on material '{material_name}' must be a JSON object.")
        return {}

    return parsed


def _build_material_contract(scene_props, blender_material):
    material_props = blender_material.hogltf
    contract = {
        "schema": EXTENSION_NAME,
        "schemaVersion": 1,
        "source": {
            "tool": "HoGLTF",
            "blenderMaterial": blender_material.name,
        },
        "target": {
            "shaderFamily": _target_shader_family(scene_props, material_props),
        },
        "principled": {},
        "toon": {},
        "unity": {},
        "extras": {},
    }

    contract.update(_parse_contract_json(material_props.contract_json, blender_material.name))

    if scene_props.write_debug_fields:
        contract.setdefault("extras", {})["blenderCustomProperties"] = {
            key: blender_material[key]
            for key in blender_material.keys()
            if isinstance(blender_material[key], (str, int, float, bool))
        }

    return contract


class glTF2ExportUserExtension:
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension

        self.Extension = Extension
        self.scene_props = bpy.context.scene.hogltf_export

    def gather_material_hook(self, gltf2_material, blender_material, export_settings):
        if blender_material is None:
            return

        material_props = blender_material.hogltf
        if not self.scene_props.enabled:
            return
        if not self.scene_props.export_material_contracts:
            return
        if not material_props.export_contract:
            return

        if gltf2_material.extensions is None:
            gltf2_material.extensions = {}

        gltf2_material.extensions[EXTENSION_NAME] = self.Extension(
            name=EXTENSION_NAME,
            extension=_build_material_contract(self.scene_props, blender_material),
            required=False,
        )


def register():
    bpy.utils.register_class(HoGLTFExportSettings)
    bpy.utils.register_class(HoGLTFMaterialSettings)
    bpy.utils.register_class(HOGLTF_PT_material_settings)

    bpy.types.Scene.hogltf_export = bpy.props.PointerProperty(type=HoGLTFExportSettings)
    bpy.types.Material.hogltf = bpy.props.PointerProperty(type=HoGLTFMaterialSettings)

    try:
        from io_scene_gltf2 import exporter_extension_layout_draw
        exporter_extension_layout_draw[UI_PANEL_KEY] = draw_export_settings
    except Exception as exc:
        print(f"HoGLTF: glTF exporter UI hook was not registered: {exc}")


def unregister():
    try:
        from io_scene_gltf2 import exporter_extension_layout_draw
        exporter_extension_layout_draw.pop(UI_PANEL_KEY, None)
    except Exception:
        pass

    del bpy.types.Material.hogltf
    del bpy.types.Scene.hogltf_export

    bpy.utils.unregister_class(HOGLTF_PT_material_settings)
    bpy.utils.unregister_class(HoGLTFMaterialSettings)
    bpy.utils.unregister_class(HoGLTFExportSettings)
