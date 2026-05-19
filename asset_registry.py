import os
from pathlib import Path


ADDON_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = ADDON_ROOT / "assets"
MATERIAL_CONTRACTS_DIR = ASSETS_ROOT / "material_contracts"
LIL_MATERIAL_CONTRACT_BLEND = MATERIAL_CONTRACTS_DIR / "lil_material_contracts.blend"
BUILTIN_ASSET_LIBRARY_NAME = "HoGLTF Builtin Assets"


def builtin_assets():
    return (
        {
            "id": "lil_material_contracts",
            "name": "lil Material Contracts",
            "kind": "blend",
            "path": LIL_MATERIAL_CONTRACT_BLEND,
            "description": "HoLilToon and HoLilPBR material contract node groups.",
        },
    )


def asset_library_exists(path):
    try:
        import bpy
    except Exception:
        return False

    path = _norm_path(path)
    for library in bpy.context.preferences.filepaths.asset_libraries:
        if _norm_path(bpy.path.abspath(library.path)) == path:
            return True
    return False


def register_asset_library(name, path):
    try:
        import bpy
    except Exception:
        return False

    path = Path(path)
    if not path.exists():
        return False
    if asset_library_exists(path):
        return True

    prefs = bpy.context.preferences.filepaths
    libraries = prefs.asset_libraries
    directory = str(path)

    try:
        # Blender 4.x
        libraries.new(name=name, directory=directory)
    except TypeError:
        # Blender 3.x compatibility, matching HoTools' registration style.
        libraries.new(name=name, path=directory)
    return True


def ensure_builtin_asset_library():
    """Register the HoGLTF assets folder as a Blender asset library if possible."""
    if asset_library_exists(ASSETS_ROOT):
        return True

    ok = register_asset_library(BUILTIN_ASSET_LIBRARY_NAME, ASSETS_ROOT)
    if not ok:
        print("HoGLTF: failed to register builtin asset library.")
        return False
    return True


def _norm_path(path):
    return os.path.normcase(os.path.normpath(str(path)))
