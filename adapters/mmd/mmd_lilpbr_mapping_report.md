# MMD Scene -> lilPBR/lilToon Mapping Notes

Source: `scene_fresh.scene_asset.json` exported from `场景处理导出.blend` with HoTools Scene Bundle.

## Scene Material Shape

- Materials: `29`
- Shared node groups: `MMDShaderDev` and `MMDTexUV` on every material.
- Base textures: `{'TEXB10.png': 27, 'TEXA2.png': 2}`
- Toon textures: `{'T.png': 27, None: 2}`
- Double Sided values: `{'1.0': ['琴', '柱子', '窗框', '月相', '窗景', '垂布', '三角旗', '彩带线', '气球', '气球线', '星星', '星星线', '背景线', '背景线2', '吊饰', '吊饰线', '兔兔', '兔兔围脖', '兔兔裙摆', '盘子', '杯子', '杯子茶', '杯子星星', '琴星星', '琴线'], '0.0': ['地板', '墙壁', '地毯', '云朵']}`
- Root alpha sources: `{('Base Alpha', 'TEXB10.png', 'NONE'): 27, ('Toon Alpha', 'T.png', 'NONE'): 27, ('Base Alpha', 'TEXA2.png', 'STRAIGHT'): 2}`
- Texture alpha scan: `{'TEXB10.png': {'min': 1.0, 'max': 1.0, 'cutout': False, 'blend': False}, 'TEXA2.png': {'min': 1.0, 'max': 1.0, 'cutout': False, 'blend': False}, 'T.png': {'min': 1.0, 'max': 1.0, 'cutout': False, 'blend': False}}`
- `MMDTexUV` references invalid `UV1` on `SubTex UV`, but no root material consumes `SubTex UV`; treat it as inactive preset residue.

## Scene-Level Mapping

| MMD evidence | Contract field | lilPBR property | lilToon property | Notes |
| --- | --- | --- | --- | --- |
| `Mmd Base Tex` | `principled.baseColor.texture` | `_MainTex` | `_MainTex` | sRGB. This scene uses `TEXB10.png` for 27 materials and `TEXA2.png` for floor/wall. |
| `Diffuse Color` | `principled.baseColor.factor` | `_Color.rgb` | `_Color.rgb` | All values are white in this scene. |
| `Ambient Color` | `toon.shadow.color` or `extras.mmd.ambientColor` | metadata / optional baked tint | `_ShadowColor` candidate | MMD group adds ambient+diffuse before textures; for lilPBR do not bake as lighting unless matching Blender preview. |
| `Mmd Toon Tex` / `T.png` | `toon.shadow.texture` or `extras.mmd.toonTexture` | metadata | `_ShadowColorTex` candidate | lilPBR should preserve metadata only; lilToon can use it as a toon/shadow LUT-like input. |
| `Specular Color = 0` | `principled.specular` / `extras.mmd.specularColor` | `_Metallic=0`, low reflection | `_Metallic=0`, low `_Reflectance` | No scene pressure to add specular support. |
| `Reflect = 50` with specular black | `extras.mmd.reflect` | metadata | metadata | Shader divides by reflect for glossy roughness, but glossy color is black here. |
| `Sphere Tex Fac = 0` | `toon.matcap.enabled=false` / `extras.mmd.sphere` | metadata | `_UseMatCap=0` | No sphere/matcap mapping needed for this scene. |
| `Alpha = 1`, image alpha linked | `principled.alpha` + `alphaMode` | `_RenderingMode`, `_Cutoff`, blend fields | render variant + `_Cutoff` / alpha mask | This scene scans fully opaque; keep OPAQUE. For future MMD assets, scan base/toon/sphere alpha. |
| `Double Sided` | `unity.doubleSided` | `_Cull` | `_Cull` | Use `_Cull=0` for double-sided, `_Cull=2` for normal back-face culling. |

## Per-Material Render Hints

| Material | Base | Toon | Alpha | Double Sided | Suggested `_Cull` | Suggested alpha mode |
| --- | --- | --- | --- | --- | --- | --- |
| 琴 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 地板 | TEXA2.png |  | 1 | 0 | 2 | OPAQUE |
| 墙壁 | TEXA2.png |  | 1 | 0 | 2 | OPAQUE |
| 地毯 | TEXB10.png | T.png | 1 | 0 | 2 | OPAQUE |
| 云朵 | TEXB10.png | T.png | 1 | 0 | 2 | OPAQUE |
| 柱子 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 窗框 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 月相 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 窗景 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 垂布 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 三角旗 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 彩带线 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 气球 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 气球线 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 星星 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 星星线 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 背景线 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 背景线2 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 吊饰 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 吊饰线 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 兔兔 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 兔兔围脖 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 兔兔裙摆 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 盘子 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 杯子 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 杯子茶 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 杯子星星 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 琴星星 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |
| 琴线 | TEXB10.png | T.png | 1 | 1 | 0 | OPAQUE |

## Transparency And Culling Decisions

- MMD shader computes output alpha as `min(max(backfacing < 0.5, Double Sided), Alpha * BaseAlpha * ToonAlpha * SphereAlpha)`. For Unity mapping, that means culling and alpha are coupled in Blender's preview graph.
- For production contract, separate them: `unity.doubleSided` controls `_Cull`; texture/material alpha controls render mode.
- In this scene, `TEXB10.png`, `TEXA2.png`, and `T.png` all scanned as alpha 1.0 everywhere. Use OPAQUE for every material.
- For future MMD scenery: if alpha has only 0/1 pixels, prefer Cutout/Mask; if it has mid-alpha pixels, use Transparent/Blend.
- lilPBR already has the fields needed for this: `_RenderingMode`, `_Cutoff`, `_Cull`, `_ZWrite`, `_SrcBlend`, `_DstBlend`, `_SrcBlendAlpha`, `_DstBlendAlpha`, `_AlphaToMask`.
- lilToon also already has the low-level fields/variants for this, but the importer contract needs a clear MMD alpha policy: image alpha may come from base, toon, and sphere textures, even when material `Alpha` is 1.

## Candidate Contract Block

```json
{
  "target": { "shaderFamily": "lilToon" },
  "principled": {
    "baseColor": { "texture": { "role": "Mmd Base Tex", "colorSpace": "srgb" }, "factor": [1,1,1,1] },
    "metallic": { "factor": 0 },
    "roughness": { "factor": 1 },
    "alpha": { "factor": 1 },
    "alphaMode": "OPAQUE_OR_CUTOUT_AFTER_TEXTURE_ALPHA_SCAN"
  },
  "toon": {
    "mode": "toon",
    "shadow": { "texture": { "role": "Mmd Toon Tex", "colorSpace": "srgb" } },
    "matcap": { "enabled": false }
  },
  "unity": { "doubleSided": true },
  "extras": { "mmd": { "shaderGroup": "MMDShaderDev", "texUvGroup": "MMDTexUV" } }
}
```
