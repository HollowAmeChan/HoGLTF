bl_info = {
    "name": "HoGLTF",
    "author": "Hollow",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "文件 > 导出 > glTF 2.0",
    "description": "Hollow glTF 导出桥接，用于 lilToon/lilPBR 材质契约。",
    "category": "导入-导出",
}

import sys
from pathlib import Path

import bpy

from . import asset_registry
from . import asset_conversion
from .adapters import blender_ir
from .material_contract import build_material_contract
from .material_contract import should_export_material_contract

VENDORED_GLTF_ADDONS_DIR = Path(__file__).resolve().parent / "glTF-Blender-IO" / "addons"
VENDORED_GLTF_ADDONS_PATH = str(VENDORED_GLTF_ADDONS_DIR)

EXTENSION_NAME = "HO_materials_principled_lil"
LEGACY_EXTENSION_NAME = "HO_materials_openpbr_lil"
UI_PANEL_KEY = "HoGLTF 材质契约"


def _use_vendored_gltf():
    if VENDORED_GLTF_ADDONS_PATH not in sys.path:
        sys.path.insert(0, VENDORED_GLTF_ADDONS_PATH)


class HoGLTFExportSettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="HoGLTF",
        description="启用 Hollow glTF 导出扩展钩子。",
        default=True,
    ) # type: ignore

    export_material_contracts: bpy.props.BoolProperty(
        name="材质契约",
        description="把 Hollow 材质契约写入 glTF 材质扩展。",
        default=True,
    ) # type: ignore

    target_shader_family: bpy.props.EnumProperty(
        name="目标材质",
        description="材质没有单独指定时，Unity 侧默认使用的材质类型。",
        items=(
            ("auto", "自动", "让 Unity 导入器根据契约选择 lilToon 或 lilPBR。"),
            ("lilToon", "lilToon", "导入时优先使用 lilToon。"),
            ("lilPBR", "lilPBR", "导入时优先使用 lilPBR。"),
            ("URP/Lit", "URP/Lit", "用于测试的临时回退目标。"),
        ),
        default="auto",
    ) # type: ignore

    write_debug_fields: bpy.props.BoolProperty(
        name="调试字段",
        description="在契约里写入 Blender 材质名和自定义属性提示。",
        default=True,
    ) # type: ignore


class HoGLTFMaterialSettings(bpy.types.PropertyGroup):
    export_contract: bpy.props.BoolProperty(
        name="导出 HoGLTF 契约",
        description="为这个材质导出 Hollow glTF 材质契约扩展。",
        default=False,
    ) # type: ignore

    target_shader_family: bpy.props.EnumProperty(
        name="目标材质",
        description="这个材质在 Unity 侧使用的材质类型。",
        items=(
            ("inherit", "继承", "使用场景导出设置。"),
            ("auto", "自动", "让 Unity 导入器根据契约选择。"),
            ("lilToon", "lilToon", "导入时优先使用 lilToon。"),
            ("lilPBR", "lilPBR", "导入时优先使用 lilPBR。"),
            ("URP/Lit", "URP/Lit", "用于测试的临时回退目标。"),
        ),
        default="inherit",
    ) # type: ignore

    contract_json: bpy.props.StringProperty(
        name="契约 JSON",
        description="可选的原始 JSON 对象，会合并到导出的 HoGLTF 材质契约中。",
        default="",
    ) # type: ignore


class HOGLTF_OT_register_asset_library(bpy.types.Operator):
    bl_idname = "hogltf.register_asset_library"
    bl_label = "注册 HoGLTF 内置资产库"
    bl_description = "将 HoGLTF 内置资产库注册到 Blender 资产库中，可在资产浏览器中使用材质契约节点组"

    def execute(self, context):
        asset_path = asset_registry.ASSETS_ROOT
        if asset_registry.asset_library_exists(asset_path):
            self.report({"INFO"}, "HoGLTF 内置资产库已经注册过了")
            return {"CANCELLED"}

        if not asset_registry.register_asset_library(asset_registry.BUILTIN_ASSET_LIBRARY_NAME, asset_path):
            self.report({"ERROR"}, f"HoGLTF 内置资产库不存在：{asset_path}")
            return {"CANCELLED"}

        self.report({"INFO"}, "HoGLTF 内置资产库已注册")
        return {"FINISHED"}


class HoGLTFAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.alert = True
        row.operator(HOGLTF_OT_register_asset_library.bl_idname, text="注册内置资产库")
        row.alert = False

        col = layout.column(align=True)
        col.label(text=f"资产目录：{asset_registry.ASSETS_ROOT}")
        col.label(text=f"契约资产：{asset_registry.LIL_MATERIAL_CONTRACT_BLEND.name}")


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


class glTF2ExportUserExtension:
    def __init__(self):
        self.scene_props = bpy.context.scene.hogltf_export

    def gather_material_hook(self, gltf2_material, blender_material, export_settings):
        _use_vendored_gltf()
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension

        if blender_material is None:
            return

        material_props = blender_material.hogltf
        if not self.scene_props.enabled:
            return
        if not self.scene_props.export_material_contracts:
            return
        if not should_export_material_contract(self.scene_props, material_props, blender_material):
            return

        if gltf2_material.extensions is None:
            gltf2_material.extensions = {}

        gltf2_material.extensions[EXTENSION_NAME] = Extension(
            name=EXTENSION_NAME,
            extension=build_material_contract(EXTENSION_NAME, self.scene_props, blender_material),
            required=False,
        )


def register():
    _use_vendored_gltf()
    from io_scene_gltf2 import exporter_extension_layout_draw

    bpy.utils.register_class(HoGLTFExportSettings)
    bpy.utils.register_class(HoGLTFMaterialSettings)
    bpy.utils.register_class(HOGLTF_OT_register_asset_library)
    bpy.utils.register_class(HoGLTFAddonPreferences)
    bpy.utils.register_class(HOGLTF_PT_material_settings)

    bpy.types.Scene.hogltf_export = bpy.props.PointerProperty(type=HoGLTFExportSettings)
    bpy.types.Material.hogltf = bpy.props.PointerProperty(type=HoGLTFMaterialSettings)

    exporter_extension_layout_draw[UI_PANEL_KEY] = draw_export_settings
    asset_conversion.register()
    blender_ir.register()
    asset_registry.ensure_builtin_asset_library()


def unregister():
    try:
        _use_vendored_gltf()
        from io_scene_gltf2 import exporter_extension_layout_draw

        exporter_extension_layout_draw.pop(UI_PANEL_KEY, None)
    except Exception:
        pass

    blender_ir.unregister()
    asset_conversion.unregister()

    del bpy.types.Material.hogltf
    del bpy.types.Scene.hogltf_export

    bpy.utils.unregister_class(HOGLTF_PT_material_settings)
    bpy.utils.unregister_class(HoGLTFAddonPreferences)
    bpy.utils.unregister_class(HOGLTF_OT_register_asset_library)
    bpy.utils.unregister_class(HoGLTFMaterialSettings)
    bpy.utils.unregister_class(HoGLTFExportSettings)
