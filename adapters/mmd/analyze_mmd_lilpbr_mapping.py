import json
from collections import Counter, defaultdict
from pathlib import Path

SCENE_BUNDLE_PATH = Path(r"D:\Unity_Fork\mmd_probe\scene_fresh.scene_asset.json")
ALPHA_SCAN_PATH = Path(r"D:\Unity_Fork\mmd_probe\texture_alpha_scan.json")
REPORT_PATH = Path(r"D:\Unity_Fork\mmd_probe\mmd_lilpbr_mapping_report.md")


def walk_tree(tree):
    yield tree
    for node in tree.get("nodes", []):
        group_tree = node.get("group_tree")
        if group_tree:
            yield from walk_tree(group_tree)


def node_group_name(node):
    return ((node.get("group_tree") or {}).get("name") or node.get("group_name") or "")


def linked_image(socket):
    for link in socket.get("links", []):
        from_node = link.get("from_node") or {}
        if from_node.get("bl_idname") == "ShaderNodeTexImage":
            image = from_node.get("image") or {}
            return {
                "node": from_node.get("name"),
                "label": from_node.get("label") or from_node.get("name"),
                "image": image.get("name"),
                "filepath": image.get("filepath"),
                "colorspace": image.get("colorspace"),
                "alpha_mode": image.get("alpha_mode"),
            }
    return None


def root_alpha_sources(root):
    sources = []
    image_nodes = {
        node.get("name"): node
        for node in root.get("nodes", [])
        if node.get("bl_idname") == "ShaderNodeTexImage"
    }
    for link in root.get("links", []):
        to_socket = link.get("to_socket") or {}
        from_socket = link.get("from_socket") or {}
        if to_socket.get("name") not in {"Base Alpha", "Toon Alpha", "Sphere Alpha"}:
            continue
        if from_socket.get("name") != "Alpha":
            continue
        image_node = image_nodes.get(link.get("from_node"))
        if not image_node:
            continue
        image = image_node.get("image") or {}
        sources.append(
            {
                "socket": to_socket.get("name"),
                "node": image_node.get("name"),
                "label": image_node.get("label") or image_node.get("name"),
                "image": image.get("name"),
                "filepath": image.get("filepath"),
                "colorspace": image.get("colorspace"),
                "alpha_mode": image.get("alpha_mode"),
            }
        )
    return sources


def collect_material(record):
    ir = record.get("ir") or {}
    root = ir.get("node_tree") or {}
    result = {
        "name": record.get("name"),
        "base_texture": None,
        "toon_texture": None,
        "ambient_color": None,
        "diffuse_color": None,
        "specular_color": None,
        "reflect": None,
        "base_tex_fac": None,
        "toon_tex_fac": None,
        "sphere_tex_fac": None,
        "sphere_mul_add": None,
        "double_sided": None,
        "alpha": None,
        "root_alpha_sources": [],
        "uv1_referenced": False,
        "subtex_uv_consumed": False,
    }

    root_links = root.get("links", [])
    result["root_alpha_sources"] = root_alpha_sources(root)
    for node in root.get("nodes", []):
        if node.get("bl_idname") == "ShaderNodeTexImage":
            image = node.get("image") or {}
            role = node.get("label") or node.get("name")
            tex = {
                "node": node.get("name"),
                "role": role,
                "image": image.get("name"),
                "filepath": image.get("filepath"),
                "colorspace": image.get("colorspace"),
                "alpha_mode": image.get("alpha_mode"),
            }
            if role == "Mmd Base Tex":
                result["base_texture"] = tex
            elif role == "Mmd Toon Tex":
                result["toon_texture"] = tex

        if node.get("bl_idname") == "ShaderNodeGroup" and node_group_name(node).startswith("MMDShaderDev"):
            values = {socket.get("name"): socket.get("default_value") for socket in node.get("inputs", [])}
            result["ambient_color"] = values.get("Ambient Color")
            result["diffuse_color"] = values.get("Diffuse Color")
            result["specular_color"] = values.get("Specular Color")
            result["reflect"] = values.get("Reflect")
            result["base_tex_fac"] = values.get("Base Tex Fac")
            result["toon_tex_fac"] = values.get("Toon Tex Fac")
            result["sphere_tex_fac"] = values.get("Sphere Tex Fac")
            result["sphere_mul_add"] = values.get("Sphere Mul/Add")
            result["double_sided"] = values.get("Double Sided")
            result["alpha"] = values.get("Alpha")
        if node.get("bl_idname") == "ShaderNodeGroup" and node_group_name(node).startswith("MMDTexUV"):
            group_tree = node.get("group_tree") or {}
            for sub_tree in walk_tree(group_tree):
                for sub_node in sub_tree.get("nodes", []):
                    if sub_node.get("bl_idname") == "ShaderNodeUVMap":
                        result["uv1_referenced"] = sub_node.get("properties", {}).get("uv_map") == "UV1"

    for link in root_links:
        if link.get("from_node") == "mmd_tex_uv" and (link.get("from_socket") or {}).get("name") == "SubTex UV":
            result["subtex_uv_consumed"] = True

    return result


def fmt_float(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3g}"
    return str(value)


def main():
    data = json.loads(SCENE_BUNDLE_PATH.read_text(encoding="utf-8"))
    alpha_scan = []
    if ALPHA_SCAN_PATH.exists():
        alpha_scan = json.loads(ALPHA_SCAN_PATH.read_text(encoding="utf-8"))
    alpha_by_image = {item.get("name"): item for item in alpha_scan if not item.get("missing")}
    materials = [collect_material(record) for record in data.get("materials", [])]

    base_textures = Counter((m.get("base_texture") or {}).get("image") for m in materials)
    toon_textures = Counter((m.get("toon_texture") or {}).get("image") for m in materials)
    double_sided = defaultdict(list)
    for material in materials:
        double_sided[material["double_sided"]].append(material["name"])

    alpha_sources = Counter()
    for material in materials:
        for source in material["root_alpha_sources"]:
            alpha_sources[(source["socket"], source["image"], source["alpha_mode"])] += 1

    lines = [
        "# MMD Scene -> lilPBR/lilToon Mapping Notes",
        "",
        "Source: `scene_fresh.scene_asset.json` exported from `场景处理导出.blend` with HoTools Scene Bundle.",
        "",
        "## Scene Material Shape",
        "",
        f"- Materials: `{len(materials)}`",
        "- Shared node groups: `MMDShaderDev` and `MMDTexUV` on every material.",
        f"- Base textures: `{dict(base_textures)}`",
        f"- Toon textures: `{dict(toon_textures)}`",
        f"- Double Sided values: `{ {str(k): v for k, v in double_sided.items()} }`",
        f"- Root alpha sources: `{dict(alpha_sources)}`",
        f"- Texture alpha scan: `{ {name: {'min': item.get('min_alpha'), 'max': item.get('max_alpha'), 'cutout': item.get('has_cutout_alpha'), 'blend': item.get('has_blend_alpha')} for name, item in alpha_by_image.items()} }`",
        "- `MMDTexUV` references invalid `UV1` on `SubTex UV`, but no root material consumes `SubTex UV`; treat it as inactive preset residue.",
        "",
        "## Scene-Level Mapping",
        "",
        "| MMD evidence | Contract field | lilPBR property | lilToon property | Notes |",
        "| --- | --- | --- | --- | --- |",
        "| `Mmd Base Tex` | `principled.baseColor.texture` | `_MainTex` | `_MainTex` | sRGB. This scene uses `TEXB10.png` for 27 materials and `TEXA2.png` for floor/wall. |",
        "| `Diffuse Color` | `principled.baseColor.factor` | `_Color.rgb` | `_Color.rgb` | All values are white in this scene. |",
        "| `Ambient Color` | `toon.shadow.color` or `extras.mmd.ambientColor` | metadata / optional baked tint | `_ShadowColor` candidate | MMD group adds ambient+diffuse before textures; for lilPBR do not bake as lighting unless matching Blender preview. |",
        "| `Mmd Toon Tex` / `T.png` | `toon.shadow.texture` or `extras.mmd.toonTexture` | metadata | `_ShadowColorTex` candidate | lilPBR should preserve metadata only; lilToon can use it as a toon/shadow LUT-like input. |",
        "| `Specular Color = 0` | `principled.specular` / `extras.mmd.specularColor` | `_Metallic=0`, low reflection | `_Metallic=0`, low `_Reflectance` | No scene pressure to add specular support. |",
        "| `Reflect = 50` with specular black | `extras.mmd.reflect` | metadata | metadata | Shader divides by reflect for glossy roughness, but glossy color is black here. |",
        "| `Sphere Tex Fac = 0` | `toon.matcap.enabled=false` / `extras.mmd.sphere` | metadata | `_UseMatCap=0` | No sphere/matcap mapping needed for this scene. |",
        "| `Alpha = 1`, image alpha linked | `principled.alpha` + `alphaMode` | `_RenderingMode`, `_Cutoff`, blend fields | render variant + `_Cutoff` / alpha mask | This scene scans fully opaque; keep OPAQUE. For future MMD assets, scan base/toon/sphere alpha. |",
        "| `Double Sided` | `unity.doubleSided` | `_Cull` | `_Cull` | Use `_Cull=0` for double-sided, `_Cull=2` for normal back-face culling. |",
        "",
        "## Per-Material Render Hints",
        "",
        "| Material | Base | Toon | Alpha | Double Sided | Suggested `_Cull` | Suggested alpha mode |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for material in materials:
        ds = material["double_sided"]
        cull = 0 if ds == 1.0 else 2
        base = (material.get("base_texture") or {}).get("image") or ""
        toon = (material.get("toon_texture") or {}).get("image") or ""
        texture_names = [
            (material.get("base_texture") or {}).get("image"),
            (material.get("toon_texture") or {}).get("image"),
        ]
        alpha_items = [alpha_by_image.get(name) for name in texture_names if alpha_by_image.get(name)]
        has_cutout = any(item.get("has_cutout_alpha") for item in alpha_items)
        has_blend = any(item.get("has_blend_alpha") for item in alpha_items)
        alpha_mode = "BLEND" if has_blend else ("MASK/CUTOUT" if has_cutout else "OPAQUE")
        lines.append(
            f"| {material['name']} | {base} | {toon} | {fmt_float(material['alpha'])} | {fmt_float(ds)} | {cull} | {alpha_mode} |"
        )

    lines += [
        "",
        "## Transparency And Culling Decisions",
        "",
        "- MMD shader computes output alpha as `min(max(backfacing < 0.5, Double Sided), Alpha * BaseAlpha * ToonAlpha * SphereAlpha)`. For Unity mapping, that means culling and alpha are coupled in Blender's preview graph.",
        "- For production contract, separate them: `unity.doubleSided` controls `_Cull`; texture/material alpha controls render mode.",
        "- In this scene, `TEXB10.png`, `TEXA2.png`, and `T.png` all scanned as alpha 1.0 everywhere. Use OPAQUE for every material.",
        "- For future MMD scenery: if alpha has only 0/1 pixels, prefer Cutout/Mask; if it has mid-alpha pixels, use Transparent/Blend.",
        "- lilPBR already has the fields needed for this: `_RenderingMode`, `_Cutoff`, `_Cull`, `_ZWrite`, `_SrcBlend`, `_DstBlend`, `_SrcBlendAlpha`, `_DstBlendAlpha`, `_AlphaToMask`.",
        "- lilToon also already has the low-level fields/variants for this, but the importer contract needs a clear MMD alpha policy: image alpha may come from base, toon, and sphere textures, even when material `Alpha` is 1.",
        "",
        "## Candidate Contract Block",
        "",
        "```json",
        "{",
        '  "target": { "shaderFamily": "lilToon" },',
        '  "principled": {',
        '    "baseColor": { "texture": { "role": "Mmd Base Tex", "colorSpace": "srgb" }, "factor": [1,1,1,1] },',
        '    "metallic": { "factor": 0 },',
        '    "roughness": { "factor": 1 },',
        '    "alpha": { "factor": 1 },',
        '    "alphaMode": "OPAQUE_OR_CUTOUT_AFTER_TEXTURE_ALPHA_SCAN"',
        "  },",
        '  "toon": {',
        '    "mode": "toon",',
        '    "shadow": { "texture": { "role": "Mmd Toon Tex", "colorSpace": "srgb" } },',
        '    "matcap": { "enabled": false }',
        "  },",
        '  "unity": { "doubleSided": true },',
        '  "extras": { "mmd": { "shaderGroup": "MMDShaderDev", "texUvGroup": "MMDTexUV" } }',
        "}",
        "```",
    ]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {REPORT_PATH}")


if __name__ == "__main__":
    main()
