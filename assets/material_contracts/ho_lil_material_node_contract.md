# HoGLTF lil 材质节点契约草案

状态：Draft 0.3

这份文档定义 Blender 节点组 socket 契约，用于把 MMD 类材质通过 HoGLTF 导出到
lilToon / lilPBR。Socket 名面向 DCC，应该保持稳定；Unity shader property 名是导入目标。

约定：

- `Float` 型布尔值使用 `0 = false`、`1 = true`。
- `Enum` socket 以整数值 float 导出。
- 除非标记为贴图颜色输入，颜色均使用 linear RGBA。
- Texture socket 没有数值上下限。HoGLTF 应读取连接的 Image Texture 节点，并写出贴图引用和色彩空间 metadata。
- 外部创作侧使用 `Roughness`；Unity 导入时转换为 `Smoothness`。
- 优先级表示“对最终效果的重要性”：`S` 是当前 MMD 桥接关键项，`A` 是常用主效果，`B` 是高保真增强，`C` 是特殊效果，`预留` 是先占接口位置。

## lilToon Shader Family / Variant 选择

lilToon 不是单个 shader，而是一组由 `BaseShaderResources/*.lilinternal` 生成的 shader family。Blender 侧应该提供多个专用节点组，同时保留一个最大兼容节点组；HoGLTF / Unity importer 必须把节点组名和部分 socket 当作“选 shader 底子”的信号，而不是普通材质参数。

当前观察到的主族谱：

| 家族 | 代表 `.lilinternal` | 代表 shader name | Properties block | URP SubShader block | 适用场景 |
| --- | --- | --- | --- | --- | --- |
| Standard Opaque | `lts.lilinternal` | `lilToon` | `Default` + `DefaultOpaque` | `DefaultUsePass` | 常规不透明。 |
| Standard Cutout | `lts_cutout.lilinternal` | `Hidden/lilToonCutout` | `Default` + `DefaultCutout` | `DefaultUsePass` | 二值 alpha。 |
| Standard Transparent | `lts_trans.lilinternal` | `Hidden/lilToonTransparent` | `Default` + `DefaultTransparent` | `DefaultUsePassOIT` | 普通透明；URP 下带 OIT 路径。 |
| OnePass Transparent | `lts_onetrans.lilinternal` | `Hidden/lilToonOnePassTransparent` | `Default` + `DefaultTransparent` | `DefaultUsePassOIT` | 一遍透明。 |
| TwoPass Transparent | `lts_twotrans.lilinternal` | `Hidden/lilToonTwoPassTransparent` | `Default` + `DefaultTransparent` | `DefaultUsePassTwoSideOIT` | 两遍透明，常用于复杂双面透明。 |
| Outline variants | `*_o.lilinternal` | `Hidden/*Outline` | 同主体 properties | `DefaultUsePassOutline*` | 需要描边时选 outline 版 shader，而不仅是设 `_UseOutline`。 |
| Outline-only variants | `*_oo.lilinternal` | `_lil/[Optional] lilToonOutlineOnly*` | 同主体 properties | `DefaultUsePassOutlineOnly*` | 只画描边的特殊材质。 |
| Lite | `ltsl*.lilinternal` | `Hidden/lilToonLite*` | `DefaultLite` + mode block | `DefaultUsePass*` | 精简参数、轻量渲染；不是全量 `Default`。 |
| Tessellation | `lts_tess*.lilinternal` | `Hidden/lilToonTessellation*` | `Default` + mode block | `DefaultUsePass*` | 带 tessellation 参数。 |
| Refraction | `lts_ref*.lilinternal` | `Hidden/lilToonRefraction*` | `Default` + `DefaultRefraction` | `DefaultRefraction*` | 折射，不等价于普通 alpha。 |
| Gem | `lts_gem.lilinternal` | `Hidden/lilToonGem` | `Default` + `DefaultGem` | `DefaultGem` | 宝石/加色折射类。 |
| Fur | `lts_fur*.lilinternal` | `Hidden/lilToonFur*` | `Default` + `DefaultFur*` | `DefaultFur*` | 毛发 shell 类。 |
| Fur-only | `lts_furonly*.lilinternal` | `_lil/[Optional] lilToonFurOnly*` | `Default` + `DefaultFur*` | `DefaultUsePassFurOnly*` | 只画毛层。 |
| Multi | `ltsmulti*.lilinternal` | `_lil/lilToonMulti` / `Hidden/lilToonMulti*` | `Default` + mode block | `DefaultMulti*` | 单材质里通过 `_TransparentMode` 切换多个模式。 |
| FakeShadow | `lts_fakeshadow.lilinternal` | `_lil/[Optional] lilToonFakeShadow` | `DefaultFakeShadow` | `DefaultFakeShadow` | 假阴影，不应作为普通 MMD 材质目标。 |

Importer 推荐的目标选择：

1. 先看显式 `TargetShaderFamily` / `TargetShaderVariant` metadata。
2. 如果没有显式目标，则按材质语义推断：
   - `UseGem > 0`：选 `Gem`。
   - `UseRefraction > 0` 或 `OpenPBRTransmissionWeight > 0`：选 `Refraction`，不要降级成普通 Transparent。
   - `UseFur > 0`：选 `Fur` / `FurCutout` / `FurTwoPass`。
   - `AlphaMode = Transparent`：选 `Transparent`、`OnePassTransparent` 或 `TwoPassTransparent`。
   - `AlphaMode = Cutout` 或 `Dither`：选 `Cutout`。
   - 其他：选 `Opaque`。
3. 再叠加 `UseOutline`：需要描边时选对应 `_o` shader；不是只设置 `_UseOutline`。
4. `UseLite`、`UseTessellation`、`UseMulti` 应作为明确 opt-in，不要由 MMD 自动推断。
5. MMD 场景首轮默认目标应是 `Standard Opaque/Cutout/Transparent + optional Outline`，不要默认走 Lite、Multi、Fur、Gem、Refraction。

建议在 HoGLTF 扩展 metadata 里写：

```json
{
  "target": {
    "shaderFamily": "lilToon",
    "shaderVariant": "standard",
    "renderingMode": "Opaque",
    "transparentMode": "Normal",
    "outline": false,
    "lite": false,
    "tessellation": false,
    "multi": false
  }
}
```

## Blender 节点组拆分

HoLilToon 不再只是一种节点组。推荐在 Blender 里同时提供“窄接口变体组”和“最大接口组”：

| 节点组 | 默认 `TargetShaderVariant` | 主要目标 | 使用建议 |
| --- | ---: | --- | --- |
| `HoLilToonMax` | `0 Auto` | 全量兼容 / 调试 / 未来扩展 | 保留所有已知 Standard、Tessellation、Refraction、Gem、Fur、Multi、FakeShadow socket。它不是 MMD 默认创作入口。 |
| `HoLilToonStandard` | `1 Standard` | `lilToon` / Cutout / Transparent / Outline variants | MMD 首轮桥接默认使用；承接 base、toon shadow、alpha、cull、outline、rim 等核心效果。 |
| `HoLilToonLite` | `2 Lite` | `Hidden/lilToonLite*` | 明确想走轻量 shader 时使用；接口应比 Standard 更窄。 |
| `HoLilToonTessellation` | `3 Tessellation` | `Hidden/lilToonTessellation*` | 需要 tessellation 时使用；不要由普通 MMD 材质自动推断。 |
| `HoLilToonRefraction` | `4 Refraction` | `Hidden/lilToonRefraction*` | 真实折射语义；不要降级成普通 Transparent。 |
| `HoLilToonGem` | `5 Gem` | `Hidden/lilToonGem` | 宝石类材质；包含 Gem 专属 socket 和折射相关 socket。 |
| `HoLilToonFur` | `6 Fur` | `Hidden/lilToonFur*` | 主体材质带毛层。 |
| `HoLilToonFurOnly` | `7 FurOnly` | `_lil/[Optional] lilToonFurOnly*` | 只画毛层的特殊材质。 |
| `HoLilToonMulti` | `8 Multi` | `_lil/lilToonMulti` / `Hidden/lilToonMulti*` | 明确需要 `_TransparentMode` 多模式切换时使用。 |
| `HoLilToonFakeShadow` | `9 FakeShadow` | `_lil/[Optional] lilToonFakeShadow` | 假阴影专用，不作为普通 MMD 材质目标。 |

Importer 识别优先级建议：

1. 如果节点组名是 `HoLilToon*` 专用组，优先采用节点组名决定目标变体。
2. 如果使用 `HoLilToonMax` 或未知兼容组，再读取 `TargetShaderVariant`。
3. 如果节点组名和 `TargetShaderVariant` 冲突，记录 warning；默认信任节点组名，因为 Blender 作者选择了更明确的接口。
4. `AlphaMode`、`TransparentMode`、`UseOutline` 再叠加决定 Opaque / Cutout / Transparent / OnePass / TwoPass / Outline shader。
5. `HoLilToonStandard` 是当前 MMD 预设基准的默认落点；`HoLilToonMax` 用于迁移未知材质、回归测试和接口兼容。

## 共享渲染 Socket

这些 socket 应同时存在于所有 `HoLilToon*` 节点组和 `HoLilPBR`。

| Socket | 类型 | 最小值 | 最大值 | 默认值 | 优先级 | Unity 目标 | 说明 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `AlphaMode` | Enum | 0 | 3 | 0 | S | shader variant / `_RenderingMode` | `0 Opaque`、`1 Cutout`、`2 Dither`、`3 Transparent`。 |
| `Alpha` | Float | 0 | 1 | 1 | S | `_Color.a` | 乘到基础贴图 alpha 上。 |
| `AlphaCutoff` | Float | 0 | 1 | 0.5 | S | `_Cutoff` | Cutout / Dither 使用。 |
| `CullMode` | Enum | 0 | 2 | 2 | S | `_Cull` | Unity 值：`0 Off`、`1 Front`、`2 Back`。MMD 双面映射到 `0`。 |
| `ZWriteOverride` | Float | -1 | 1 | -1 | A | `_ZWrite` | `-1` 表示由 importer 根据 alpha mode 自动选择；`0/1` 表示强制指定。 |
| `AlphaToMaskOverride` | Float | -1 | 1 | -1 | A | `_AlphaToMask` | `-1` 表示由 importer 自动选择；Cutout 通常为 `1`，Transparent 为 `0`。 |
| `RenderQueueOffset` | Float | -100 | 100 | 0 | B | material renderQueue | 可选，用于处理透明排序和特殊层级。 |
| `TargetShaderVariant` | Enum | 0 | 9 | 0 | S | shader selection metadata | `0 Auto`、`1 Standard`、`2 Lite`、`3 Tessellation`、`4 Refraction`、`5 Gem`、`6 Fur`、`7 FurOnly`、`8 Multi`、`9 FakeShadow`。 |
| `TransparentMode` | Enum | 0 | 2 | 0 | A | shader selection metadata / `_TransparentMode` | `0 Normal`、`1 OnePass`、`2 TwoPass`；仅 Transparent/Fur/Multi 路径消费。 |

推荐 alpha 判定：

| 来源条件 | AlphaMode | Unity 行为 |
| --- | --- | --- |
| 没有 alpha 贴图且 `Alpha >= 0.999` | `0 Opaque` | `_ZWrite = 1`，blend One/Zero。 |
| alpha 基本是二值 | `1 Cutout` | 设置 `_Cutoff`、`_AlphaToMask = 1`。 |
| 软 alpha / 类玻璃颜色 alpha | `3 Transparent` | lilPBR 设置 `_ZWrite = 0`；lilToon 选择 transparent shader variant。 |
| 软 alpha 但不能接受透明排序问题 | `2 Dither` | 使用 Cutout queue，并启用 dither keyword/mode。 |

## 成组参数语义

lilToon 的很多输入不是单个 property 独立生效，而是“贴图 + 颜色因子”或“贴图 + 标量因子”的组合。Blender 节点组里的 socket 仍然保持扁平命名，方便 HoGLTF 读取；但 importer 必须按组理解它们，不能只看单个 socket。

当前契约约定：

| 组 | Texture socket | Factor socket | Unity 目标 | 组合语义 |
| --- | --- | --- | --- | --- |
| `mainColor` | `BaseTex` | `BaseColor` | `_MainTex` + `_Color` | 主色应按 `BaseTex * BaseColor` 理解。正式资产里的 Blender 预览也按这个规则接到 Principled BSDF。 |
| `shadow` | `ShadowTex` | `ShadowColor` / `ShadowStrength` | `_ShadowColorTex` + `_ShadowColor` + `_ShadowStrength` | MMD toon texture 放进 `ShadowTex`，不要烘进 `BaseTex`。 |
| `rim` | `RimTex` | `RimColor` | `_RimColorTex` + `_RimColor` | 边缘光颜色贴图与颜色因子相乘。 |
| `emission` | `EmissionTex` | `EmissionColor` / `EmissionBlend` | `_EmissionMap` + `_EmissionColor` + `_EmissionBlend` | emission strength 现阶段可烘入 HDR `EmissionColor`，但仍保留 blend 因子。 |
| `outline` | `OutlineTex` / `OutlineWidthMask` | `OutlineColor` / `OutlineWidth` | `_OutlineTex` + `_OutlineColor` / `_OutlineWidthMask` + `_OutlineWidth` | 描边颜色和宽度都是组合参数；`UseOutline` 还会影响 shader variant。 |
| `reflection` | `RoughnessTex` / `MetallicTex` | `Roughness` / `Metallic` | `_SmoothnessTex` + `_Smoothness` / `_MetallicGlossMap` + `_Metallic` | 外部契约使用 roughness，Unity 导入时转换到 smoothness；贴图与系数共同决定结果。 |
| `normal` | `NormalTex` | `NormalScale` | `_BumpMap` + `_BumpScale` | 法线贴图存在时应启用 bump map，`NormalScale = 0` 可近似禁用。 |
| `matcap` | `MatCapTex` | `MatCapColor` / `MatCapBlend` | `_MatCapTex` + `_MatCapColor` + `_MatCapBlend` | MatCap 是贴图、颜色和混合系数组合。 |
| `mainColor2nd` | `Main2ndTex` | `Main2ndColor` | `_Main2ndTex` + `_Color2nd` | 第二层主色/贴花预留，后续需要补 blend mode、mask、decal 参数。 |

这些分组也写入 Blender socket description，例如 `group=mainColor; role=texture; blend=BaseTex*BaseColor`。description 是辅助 metadata，不替代稳定 socket 名；HoGLTF 导出仍应以 socket 名作为主契约。

## HoLilToon Socket

这是建议给 Blender `HoLilToonMax` 节点组暴露的完整 Standard socket 表。专用节点组可以从这里裁剪子集；当前 MMD 场景主要依赖 `S/A` 项，`B/C/预留` 项先留接口，避免以后扩展时改名。

| Socket | 类型 | 最小值 | 最大值 | 默认值 | 优先级 | lilToon 目标 | 说明 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `BaseColor` | Color | 0 | HDR | `(1,1,1,1)` | S | `_Color`，mirror `_BaseColor` | 主 albedo 颜色因子。 |
| `BaseTex` | Texture2D | n/a | n/a | white | S | `_MainTex`，mirror `_BaseMap`、`_BaseColorMap` | sRGB。 |
| `BaseTexUV` | Enum | 0 | 3 | 0 | A | `_MainTex` UV path / metadata | 当前 MMD 基准只要求 UV0；其他值先保留。 |
| `NormalTex` | Texture2D | n/a | n/a | bump | A | `_BumpMap` | 法线贴图。连接时启用 `_UseBumpMap`。 |
| `NormalScale` | Float | -10 | 10 | 1 | A | `_BumpScale` | 设为 `0` 可近似禁用法线。 |
| `UseShadow` | Float | 0 | 1 | 1 | S | `_UseShadow` | MMD toon 材质应启用。 |
| `ShadowColor` | Color | 0 | HDR | `(0.82,0.76,0.85,1)` | S | `_ShadowColor` | 没有 toon 贴图时使用或参与相乘。 |
| `ShadowTex` | Texture2D | n/a | n/a | black | S | `_ShadowColorTex` | MMD toon texture 放这里，不要塞进 base color。 |
| `ShadowBorder` | Float | 0 | 1 | 0.5 | S | `_ShadowBorder` | 第一层阴影阈值。 |
| `ShadowBlur` | Float | 0 | 1 | 0.1 | S | `_ShadowBlur` | 阴影软化。 |
| `ShadowStrength` | Float | 0 | 1 | 1 | S | `_ShadowStrength` | 整体阴影强度。 |
| `ShadowReceive` | Float | 0 | 1 | 0 | A | `_ShadowReceive` | MMD baked toon 默认保持较低，除非明确需要接收实时阴影。 |
| `UseRim` | Float | 0 | 1 | 0 | A | `_UseRim` | 可用于近似 MMD specular。 |
| `RimColor` | Color | 0 | HDR | `(0.66,0.5,0.48,1)` | A | `_RimColor` | 边缘光颜色。 |
| `RimTex` | Texture2D | n/a | n/a | white | B | `_RimColorTex` | 可选。 |
| `RimBorder` | Float | 0 | 1 | 0.5 | A | `_RimBorder` | 边缘光阈值。 |
| `RimBlur` | Float | 0 | 1 | 0.65 | A | `_RimBlur` | 边缘光软化。 |
| `RimFresnelPower` | Float | 0.01 | 50 | 3.5 | A | `_RimFresnelPower` | Fresnel 指数。 |
| `UseOutline` | Float | 0 | 1 | 0 | S | outline shader variant / `_UseOutline` | 为 true 时 importer 应选择支持描边的 lilToon shader。 |
| `OutlineColor` | Color | 0 | HDR | `(0.6,0.56,0.73,1)` | S | `_OutlineColor` | MMD edge color 可映射到这里。 |
| `OutlineTex` | Texture2D | n/a | n/a | white | B | `_OutlineTex` | 可选描边贴图。 |
| `OutlineWidth` | Float | 0 | 1 | 0.08 | S | `_OutlineWidth` | 实际 MMD 导入值应小很多，常见为 `0.005-0.03`。 |
| `OutlineWidthMask` | Texture2D | n/a | n/a | white | B | `_OutlineWidthMask` | 可选。 |
| `OutlineFixWidth` | Float | 0 | 1 | 0.5 | A | `_OutlineFixWidth` | 类屏幕宽度稳定。 |
| `UseEmission` | Float | 0 | 1 | 0 | A | `_UseEmission` | 可选。 |
| `EmissionColor` | Color | 0 | HDR | `(0,0,0,1)` | A | `_EmissionColor` | 现阶段把 strength 烘进 HDR color。 |
| `EmissionTex` | Texture2D | n/a | n/a | white | A | `_EmissionMap` | sRGB。 |
| `EmissionBlend` | Float | 0 | 1 | 1 | B | `_EmissionBlend` | 可选。 |
| `Roughness` | Float | 0 | 1 | 0.5 | B | `_Smoothness = 1 - Roughness` | 面向 DCC 的 roughness。 |
| `RoughnessTex` | Texture2D | n/a | n/a | white | B | `_SmoothnessTex` | importer 必须反相或生成 smoothness 数据。 |
| `Metallic` | Float | 0 | 1 | 0 | B | `_Metallic` | MMD 通常为 `0`。 |
| `MetallicTex` | Texture2D | n/a | n/a | white | C | `_MetallicGlossMap` | Linear。 |
| `Reflectance` | Float | 0 | 1 | 0.04 | B | `_Reflectance` | 可由 IOR 推导。 |
| `IOR` | Float | 1 | 3 | 1.5 | B | `_Reflectance`，reserved `_OpenPBRIOR` | `F0 = ((ior-1)/(ior+1))^2`。 |
| `UseSSS` | Float | 0 | 1 | 0 | B | `_UseSSS` | 风格化 subsurface。 |
| `SSSColor` | Color | 0 | HDR | `(1,0.42,0.32,1)` | B | `_SSSColor` | 可选，皮肤/布料桥接。 |
| `SSSStrength` | Float | 0 | 2 | 0.35 | B | `_SSSStrength` | lilToon 范围为 `0-2`。 |
| `SSSThicknessTex` | Texture2D | n/a | n/a | white | B | `_SSSThicknessMap` | Linear。 |
| `UseMatCap` | Float | 0 | 1 | 0 | B | `_UseMatCap` | 可选，风格化高光。 |
| `MatCapColor` | Color | 0 | HDR | `(1,1,1,1)` | B | `_MatCapColor` | 可选。 |
| `MatCapTex` | Texture2D | n/a | n/a | white | B | `_MatCapTex` | sRGB。 |
| `MatCapBlend` | Float | 0 | 1 | 1 | B | `_MatCapBlend` | 可选。 |
| `ParallaxTex` | Texture2D | n/a | n/a | gray | C | `_ParallaxMap` | 连接时启用 `_UseParallax`。 |
| `ParallaxScale` | Float | 0 | 1 | 0.02 | C | `_Parallax` | 角色材质应保持很小。 |
| `BackfaceColor` | Color | 0 | HDR | `(0,0,0,0)` | B | `_BackfaceColor` | 仅在确实需要背面染色时使用。 |

## HoLilToon 额外预留 Socket

这些 socket 不一定马上消费，但建议 HoGLTF 能识别并保存到 `extras.lilToon`。这样后面补 shader/importer 时，不需要重新改 Blender 节点组形状。

| Socket | 类型 | 最小值 | 最大值 | 默认值 | 优先级 | lilToon 目标 | 说明 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `UseMain2ndTex` | Float | 0 | 1 | 0 | 预留 | `_UseMain2ndTex` | 第二层主色/贴花。 |
| `Main2ndTex` | Texture2D | n/a | n/a | white | 预留 | `_Main2ndTex` | 第二层主色贴图。 |
| `Main2ndColor` | Color | 0 | HDR | `(1,1,1,1)` | 预留 | `_Color2nd` | 第二层主色因子。 |
| `UseBacklight` | Float | 0 | 1 | 0 | C | `_UseBacklight` | 背光。 |
| `BacklightColor` | Color | 0 | HDR | `(0.85,0.8,0.7,1)` | C | `_BacklightColor` | 背光颜色。 |
| `UseGlitter` | Float | 0 | 1 | 0 | C | `_UseGlitter` | 亮片/闪光。 |
| `GlitterColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `_GlitterColor` | 闪光颜色。 |
| `UseDissolve` | Float | 0 | 1 | 0 | 预留 | `_DissolveParams` | 只占位；实际需要 mask/noise/params 组合。 |
| `DissolveMask` | Texture2D | n/a | n/a | white | 预留 | `_DissolveMask` | 溶解 mask。 |
| `UseRefraction` | Float | 0 | 1 | 0 | 预留 | refraction shader variant | 需要 refraction 变体，不等价于普通 alpha。 |
| `RefractionStrength` | Float | 0 | 1 | 0 | 预留 | refraction properties | 先作为 metadata。 |
| `UseGem` | Float | 0 | 1 | 0 | 预留 | gem shader variant | 宝石变体占位。 |
| `UseFur` | Float | 0 | 1 | 0 | 预留 | fur shader variant | 毛发变体占位。 |
| `DistanceFade` | Float | 0 | 1 | 0 | 预留 | `_DistanceFade` | 距离淡出占位。 |
| `AudioLinkMask` | Texture2D | n/a | n/a | black | 预留 | `_AudioLinkMask` | VRChat/AudioLink 路线占位。 |
| `StencilRef` | Float | 0 | 255 | 0 | 预留 | `_StencilRef` | 高级渲染状态。 |
| `StencilComp` | Float | 0 | 8 | 8 | 预留 | `_StencilComp` | 高级渲染状态。 |
| `OpenPBRCoatWeight` | Float | 0 | 1 | 0 | 预留 | reserved `_OpenPBRCoatWeight` | 不要用 MatCap 假装 clear coat；先保留语义。 |
| `OpenPBRTransmissionWeight` | Float | 0 | 1 | 0 | 预留 | reserved `_OpenPBRTransmissionWeight` | 不要映射成普通透明；先保留语义。 |
| `OpenPBRSpecularColor` | Color | 0 | HDR | `(1,1,1,1)` | 预留 | reserved `_OpenPBRSpecularColor` | 未来 specular 扩展。 |

## HoLilToon 变体专属 Socket

这些 socket 只建议出现在对应专用节点组，`HoLilToonMax` 则全部保留。当前 MMD 基准场景默认不消费它们。

| Socket | 类型 | 最小值 | 最大值 | 默认值 | 优先级 | 所属节点组 | lilToon 目标 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `UseTessellation` | Float | 0 | 1 | 0 | 预留 | `HoLilToonTessellation` | tessellation variant |
| `TessellationStrength` | Float | 0 | 1 | 0.1 | C | `HoLilToonTessellation` | `_TessStrength` |
| `TessellationEdgeLength` | Float | 1 | 50 | 10 | C | `HoLilToonTessellation` | `_TessEdgeLength` |
| `TessellationShrink` | Float | 0 | 1 | 0 | C | `HoLilToonTessellation` | `_TessShrink` |
| `RefractionFresnelPower` | Float | 0.01 | 50 | 5 | C | `HoLilToonRefraction` / `HoLilToonGem` | `_RefractionFresnelPower` |
| `RefractionColorFromMain` | Float | 0 | 1 | 1 | C | `HoLilToonRefraction` / `HoLilToonGem` | `_RefractionColorFromMain` |
| `RefractionColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `HoLilToonRefraction` / `HoLilToonGem` | `_RefractionColor` |
| `GemChromaticAberration` | Float | 0 | 1 | 0.02 | C | `HoLilToonGem` | `_GemChromaticAberration` |
| `GemEnvContrast` | Float | 0 | 10 | 1 | C | `HoLilToonGem` | `_GemEnvContrast` |
| `GemEnvColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `HoLilToonGem` | `_GemEnvColor` |
| `GemParticleLoop` | Float | 0 | 10 | 1 | C | `HoLilToonGem` | `_GemParticleLoop` |
| `GemParticleColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `HoLilToonGem` | `_GemParticleColor` |
| `GemVRParallaxStrength` | Float | 0 | 1 | 0 | C | `HoLilToonGem` | `_GemVRParallaxStrength` |
| `FurNoiseMask` | Texture2D | n/a | n/a | white | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurNoiseMask` |
| `FurMask` | Texture2D | n/a | n/a | white | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurMask` |
| `FurLengthMask` | Texture2D | n/a | n/a | white | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurLengthMask` |
| `FurVectorTex` | Texture2D | n/a | n/a | normal | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurVectorTex` |
| `FurVectorScale` | Float | -10 | 10 | 1 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurVectorScale` |
| `FurVector` | Vector | n/a | n/a | `(0,0,0)` | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurVector` |
| `VertexColor2FurVector` | Float | 0 | 1 | 0 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_VertexColor2FurVector` |
| `FurGravity` | Float | -1 | 1 | 0 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurGravity` |
| `FurRandomize` | Float | 0 | 1 | 0.1 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurRandomize` |
| `FurAO` | Float | 0 | 1 | 0 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurAO` |
| `FurLayerNum` | Float | 1 | 64 | 10 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurLayerNum` |
| `FurRootOffset` | Float | 0 | 1 | 0 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurRootOffset` |
| `FurCutoutLength` | Float | 0 | 1 | 0.2 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurCutoutLength` |
| `FurTouchStrength` | Float | 0 | 1 | 0 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurTouchStrength` |
| `FurRimColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurRimColor` |
| `FurRimFresnelPower` | Float | 0.01 | 50 | 5 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurRimFresnelPower` |
| `FurRimAntiLight` | Float | 0 | 1 | 0 | C | `HoLilToonFur` / `HoLilToonFurOnly` | `_FurRimAntiLight` |
| `UseMulti` | Float | 0 | 1 | 0 | 预留 | `HoLilToonMulti` | multi variant |
| `FakeShadowColor` | Color | 0 | HDR | `(0,0,0,1)` | C | `HoLilToonFakeShadow` | `_FakeShadowColor` |
| `FakeShadowVector` | Vector | n/a | n/a | `(0,-1,0)` | C | `HoLilToonFakeShadow` | `_FakeShadowVector` |
| `FakeShadowMask` | Texture2D | n/a | n/a | white | C | `HoLilToonFakeShadow` | `_FakeShadowMask` |

## HoLilPBR Socket

源材质是真正 PBR / Principled-like 时使用这组字段。对于 MMD toon 材质，lilPBR 主要接收 base / alpha / cull metadata，并把 toon 字段保存在 extras。

| Socket | 类型 | 最小值 | 最大值 | 默认值 | 优先级 | lilPBR 目标 | 说明 |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `BaseColor` | Color | 0 | HDR | `(1,1,1,1)` | S | `_Color` | 主 albedo 颜色因子。 |
| `BaseTex` | Texture2D | n/a | n/a | white | S | `_MainTex` | sRGB。 |
| `BaseTexUV` | Enum | 0 | 3 | 0 | A | UV selection metadata | Shader 支持 UV mode，但当前基准应优先使用 UV0。 |
| `VertexColorMode` | Enum | 0 | 2 | 0 | B | `_VertexColorMode` | `0 Ignore`、`1 Color`、`2 Occlusion(A)`。 |
| `UVMode` | Enum | 0 | 2 | 0 | B | `_UVMode` | `0 Default`、`1 Planar`、`2 Triplanar`。 |
| `NormalTex` | Texture2D | n/a | n/a | bump | A | `_BumpMap` | 法线贴图。 |
| `NormalScale` | Float | 0 | 4 | 1 | A | `_BumpScale` | lilPBR shader property 是无界 Float；创作侧先限制在合理范围。 |
| `TextureMode` | Enum | 0 | 1 | 0 | A | `_TextureMode` | `0 Packed`、`1 Separate`。 |
| `PBRMap` | Texture2D | n/a | n/a | white | A | `_PBRMap` | 当前 shader 期望可配置的 M/A/H/S 通道。 |
| `PBRPreset` | Enum | 0 | 3 | 0 | A | importer metadata / future `_PBRInputPreset` | `0 MAHS`、`1 ORM`、`2 MRA`、`3 Separate`。 |
| `Metallic` | Float | 0 | 1 | 0 | A | `_Metallic` | Linear scalar。 |
| `MetallicTex` | Texture2D | n/a | n/a | white | A | `_MetallicGlossMap` | Separate mode。 |
| `MetallicChannel` | Enum | 0 | 3 | 0 | B | `_MetallicChannel` | `0 R`、`1 G`、`2 B`、`3 A`。 |
| `Roughness` | Float | 0 | 1 | 0.5 | A | `_Glossiness = 1 - Roughness` | 外部契约保持 roughness 语义。 |
| `RoughnessTex` | Texture2D | n/a | n/a | white | A | `_SmoothnessMap` | 如果输入是 roughness，importer 必须反相/生成 smoothness。 |
| `SmoothnessChannel` | Enum | 0 | 3 | 3 | B | `_SmoothnessChannel` | 转换为 smoothness 后使用的通道。 |
| `OcclusionStrength` | Float | 0 | 1 | 1 | A | `_OcclusionStrength` | AO 强度。 |
| `OcclusionTex` | Texture2D | n/a | n/a | white | A | `_OcclusionMap` | Separate mode。 |
| `OcclusionChannel` | Enum | 0 | 3 | 1 | B | `_OcclusionChannel` | 当前 packed 默认是 G。 |
| `HeightScale` | Float | 0 | 1 | 0 | B | `_Parallax` | 高度/parallax 强度。 |
| `HeightTex` | Texture2D | n/a | n/a | black | B | `_ParallaxMap` | Separate mode。 |
| `HeightChannel` | Enum | 0 | 3 | 2 | C | `_HeightChannel` | 当前 packed 默认是 B。 |
| `Reflectance` | Float | 0 | 1 | 0.04 | A | `_Reflectance` | 有 IOR 时由 IOR 推导。 |
| `IOR` | Float | 1 | 3 | 1.5 | B | `_Reflectance`，future `_IOR` | 原始值保存在契约 metadata 中。 |
| `EmissionColor` | Color | 0 | HDR | `(0,0,0,1)` | A | `_EmissionColor` | 现阶段把 emission strength 烘进 HDR color。 |
| `EmissionTex` | Texture2D | n/a | n/a | white | A | `_EmissionMap` | sRGB。 |
| `BackfaceOverride` | Float | 0 | 1 | 0 | B | `_BackfaceOverride` | 双面表面需要不同背面颜色时使用。 |
| `BackfaceColor` | Color | 0 | HDR | `(1,1,1,1)` | B | `_BackfaceColor` | 可选。 |
| `BackfaceTex` | Texture2D | n/a | n/a | white | B | `_BackfaceTex` | 可选。 |
| `ClearCoat` | Float | 0 | 1 | 0 | B | `_ClearCoat` | Coat 权重/smoothness 混合。 |
| `ClearCoatMask` | Texture2D | n/a | n/a | white | B | `_ClearCoatMask` | Linear。 |
| `ClearCoatRoughness` | Float | 0 | 1 | 0 | B | `_ClearCoatSmoothness = 1 - Roughness` | 面向 DCC 的 roughness。 |
| `ClearCoatReflectance` | Float | 0 | 1 | 0.04 | C | `_ClearCoatReflectance` | 可选。 |
| `Anisotropy` | Float | -1 | 1 | 0 | C | `_Anisotropy` | 仅在非零或连接贴图时启用。 |
| `AnisotropyTex` | Texture2D | n/a | n/a | bump | C | `_AnisotropyDirection` | Tangent/direction map。 |
| `Cloth` | Float | 0 | 1 | 0 | C | `_Cloth` | fuzz/sheen 类资产的近似。 |
| `ClothColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `_ClothColor` | 可选。 |
| `ClothFuzz` | Float | 0 | 1 | 0.5 | C | `_ClothFuzz` | 可选。 |
| `Translucent` | Float | 0 | 1 | 0 | C | `_Translucent` | Fake translucent，不是真正 transmission。 |
| `TranslucentColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `_TranslucentColor` | 可选。 |
| `Subsurface` | Float | 0 | 1 | 0 | C | `_SubsurfaceScattering` | Fake SSS。 |
| `SubsurfaceTex` | Texture2D | n/a | n/a | white | C | `_SubsurfaceMap` | Linear。 |
| `SubsurfaceColor` | Color | 0 | HDR | `(1,1,1,1)` | C | `_SubsurfaceColor` | 可选。 |
| `SubsurfaceThickness` | Float | 0 | 1 | 1 | C | `_SubsurfaceThickness` | 当前 lilPBR shader 只有 scalar。 |

## MMD 映射备注

对于当前 MMD 预设节点场景：

- `MMD Diffuse/Base Tex` -> `BaseTex`、`BaseColor`。
- `MMD Toon Tex` -> `HoLilToon.ShadowTex`。
- `MMD Double Sided = true` -> `CullMode = 0`。
- `MMD Double Sided = false` -> `CullMode = 2`。
- 如果贴图 alpha 扫描结果全为 `1.0`，导出 `AlphaMode = 0`。
- 如果 MMD alpha 或贴图 alpha 是二值，导出 `AlphaMode = 1`。
- 如果 MMD alpha 是软透明，导出 `AlphaMode = 3`；lilToon 应选择 transparent shader variant，lilPBR 应设置 `_RenderingMode = 3`。
- MMD specular 初期可以映射到 `Rim`，也可以保留为 `extras.mmd.specular`；不要强行塞进 PBR metallic。
- MMD 节点组内部未消费的 UV1 socket 应保留为 inactive metadata，不应导出为硬依赖。

## Blender MMD 预设形状基准

这一节记录当前测试场景里的 MMD 预设节点形状，后续可以作为 HoGLTF 读取和 Unity 导入回归基准。

来源：

- Blender 文件来自 `E:\BaiduSyncdisk\在做工程\渲染研究\资产迁移测试\mmd场景\导出`。
- 新导出 IR：`D:\Unity_Fork\mmd_probe\scene_fresh.scene_asset.json`。
- Blender 版本：`4.5.8 LTS`。
- 场景材质数：29。

根材质节点形状：

| 节点名 | label | bl_idname | 节点组 | 数量/备注 |
| --- | --- | --- | --- | --- |
| `mmd_shader` | empty | `ShaderNodeGroup` | `MMDShaderDev` | 常规材质都有，16 inputs / 3 outputs。 |
| `mmd_tex_uv` | empty | `ShaderNodeGroup` | `MMDTexUV` | 常规材质都有，0 inputs / 4 outputs。 |
| `mmd_base_tex` | `Mmd Base Tex` | `ShaderNodeTexImage` | n/a | base color / alpha 来源。 |
| `mmd_toon_tex` | `Mmd Toon Tex` | `ShaderNodeTexImage` | n/a | toon color / alpha 来源；地板、墙壁等少数材质可能没有。 |
| `Material Output` | empty | `ShaderNodeOutputMaterial` | n/a | 接收 `mmd_shader.Shader`。 |

根材质关键连线：

| From | From Socket | To | To Socket | 消费状态 |
| --- | --- | --- | --- | --- |
| `mmd_shader` | `Shader` | `Material Output` | `Surface` | active |
| `mmd_base_tex` | `Color` | `mmd_shader` | `Base Tex` | active |
| `mmd_base_tex` | `Alpha` | `mmd_shader` | `Base Alpha` | active |
| `mmd_tex_uv` | `Base UV` | `mmd_base_tex` | `Vector` | active |
| `mmd_toon_tex` | `Color` | `mmd_shader` | `Toon Tex` | active when node exists |
| `mmd_toon_tex` | `Alpha` | `mmd_shader` | `Toon Alpha` | active when node exists |
| `mmd_tex_uv` | `Toon UV` | `mmd_toon_tex` | `Vector` | active when node exists |

`MMDShaderDev` 输入基准：

| 输入 | 默认值/当前代表值 | 语义 | 建议映射 |
| --- | --- | --- | --- |
| `Ambient Color` | `(0.7529,0.7529,0.7529,1)` | 环境/阴影底色参与组内混合 | `ShadowColor` 或 `extras.mmd.ambientColor`。 |
| `Diffuse Color` | `(1,1,1,1)` | 漫反射颜色 | `BaseColor`。 |
| `Specular Color` | `(0,0,0,1)` | MMD 高光颜色 | 可映射 `RimColor` 或保留 metadata；当前场景为黑。 |
| `Reflect` | `50` | MMD 反射/高光粗糙相关参数 | `extras.mmd.reflect`，不要强行映射 metallic。 |
| `Base Tex Fac` | `1` | base 贴图混合强度 | `BaseTex` 权重 metadata。 |
| `Base Tex` | linked color | base 贴图颜色 | `BaseTex`。 |
| `Toon Tex Fac` | `1` | toon 贴图混合强度 | `ShadowTex` 权重 metadata。 |
| `Toon Tex` | linked color | toon 贴图颜色 | `ShadowTex`。 |
| `Sphere Tex Fac` | `0` | sphere/matcap 混合强度 | `UseMatCap = 0` 或 `extras.mmd.sphere`。 |
| `Sphere Tex` | unlinked/default | sphere/matcap 颜色 | 未来可接 `MatCapTex`。 |
| `Sphere Mul/Add` | `0` | sphere 混合模式 | `extras.mmd.sphereBlendMode`。 |
| `Double Sided` | `1` 或 `0` | 双面开关 | true 时 `CullMode = 0`，false 时 `CullMode = 2`。 |
| `Alpha` | `1` | 材质 alpha 因子 | `Alpha`。 |
| `Base Alpha` | linked alpha | base 贴图 alpha | alpha 扫描输入。 |
| `Toon Alpha` | linked alpha | toon 贴图 alpha | alpha 扫描输入。 |
| `Sphere Alpha` | `1` | sphere 贴图 alpha | alpha 扫描输入或 metadata。 |

`MMDShaderDev` 输出基准：

| 输出 | 用途 | 当前消费 |
| --- | --- | --- |
| `Shader` | Blender preview surface | 连接到 `Material Output.Surface`。 |
| `Color` | 组内计算后的颜色 | 根材质未直接消费；可作为 debug/metadata。 |
| `Alpha` | 组内计算后的 alpha | 根材质未直接消费；alpha 语义应从输入与贴图扫描重建。 |

`MMDTexUV` 输出和内部形状：

| 输出 | 内部来源 | 当前消费 | 说明 |
| --- | --- | --- | --- |
| `Base UV` | `Texture Coordinate.UV` | active | 连接 base texture vector。 |
| `Toon UV` | `Texture Coordinate.Normal -> Vector Transform -> Mapping` | active when toon node exists | 当前 toon 按法线方向映射。 |
| `Sphere UV` | same Mapping as `Toon UV` | inactive in this scene | 可作为 sphere/matcap metadata。 |
| `SubTex UV` | `UV Map` node, `uv_map = "UV1"` | inactive in this scene | Blender 中显示 UV1 错误，但根材质未消费，不应作为硬依赖。 |

当前场景材质分布：

- 27 个材质使用 `TEXB10.png` 作为 base、`T.png` 作为 toon。
- 2 个材质使用 `TEXA2.png` 作为 base，且没有 toon 贴图。
- `Double Sided = 1` 的 25 个材质应导入为 `_Cull = 0`。
- `Double Sided = 0` 的 4 个材质：`地板`、`墙壁`、`地毯`、`云朵`，应导入为 `_Cull = 2`。
- alpha 扫描显示 `TEXB10.png`、`TEXA2.png`、`T.png` 当前全为不透明，因此本场景建议 `AlphaMode = 0 Opaque`。
