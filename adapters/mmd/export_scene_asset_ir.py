import importlib.util
import sys
import types
from pathlib import Path

import bpy


SPECIAL_TOOLS_DIR = Path(
    r"C:\Users\hhh12\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\HoTools\SpecialTools"
)
OUT_BASE = Path(r"D:\Unity_Fork\mmd_probe\scene_fresh")


def load_specialtools_module(module_name):
    package_name = "_hotools_specialtools"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(SPECIAL_TOOLS_DIR)]
        sys.modules[package_name] = package

    qualified_name = f"{package_name}.{module_name}"
    if qualified_name in sys.modules:
        return sys.modules[qualified_name]

    module_path = SPECIAL_TOOLS_DIR / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(qualified_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


def main():
    object_scene_ir = load_specialtools_module("object_scene_ir")
    data = object_scene_ir.build_scene_asset_ir(
        bpy.context,
        include_material_groups=True,
        include_evaluated_mesh=False,
        include_geometry_nodes=True,
    )
    paths = object_scene_ir.write_scene_asset_ir(data, str(OUT_BASE), "BOTH")
    print(
        "EXPORTED_SCENE_ASSET_IR",
        paths,
        "objects=",
        data["export"]["object_count"],
        "materials=",
        data["export"]["material_count"],
        "material_failures=",
        len(data.get("material_export_failures", [])),
        "geometry_failures=",
        len(data.get("geometry_node_export_failures", [])),
    )


if __name__ == "__main__":
    main()
