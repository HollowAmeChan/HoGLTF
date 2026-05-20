# HoGLTF -> UnityGLTF 材质契约

本文档定义 Blender HoGLTF 导出端写入 glTF material extension 的 JSON 结构，以及 Unity 端 `lilToon-UnityGLTF-Extensions` 当前实际读取的字段。

Unity 端仓库：

```text
D:/Unity_Fork/lilToon-UnityGLTF-Extensions
```

Blender 端插件：

```text
C:/Users/hhh12/AppData/Roaming/Blender Foundation/Blender/4.5/scripts/addons/HoGLTF
```

## Extension 名称

主扩展名：

```text
HO_materials_principled_lil
```

旧名只用于 Unity 导入兼容历史文件：

```text
HO_materials_openpbr_lil
```

Blender 新导出一律写主扩展名，不再写旧名。

写入位置：

```text
materials[i].extensions.HO_materials_principled_lil
```

该 extension 不应标记为 required。标准 glTF PBR 材质仍作为 fallback 存在，HoGLTF extension 只补充 Unity/lilToon/lilPBR 需要的元数据。

## 当前 Unity 端读取能力

Unity 导入模块入口：

```text
Runtime/HoMaterialsPrincipledLilImport.cs
Runtime/HoMaterialContractParser.cs
Runtime/HoMaterialContractAsset.cs
```

当前导入流程：

1. `HoMaterialsPrincipledLilImport.OnAfterImportMaterial` 在 UnityGLTF 导入材质后检查 `GLTFMaterial.Extensions`。
2. 优先读取 `HO_materials_principled_lil`，找不到时兼容 `HO_materials_openpbr_lil`。
3. 原始 extension JSON 会保存到 `HoMaterialContractAsset.Json`。
4. 解析出的关键字段会保存到 `HoMaterialContractAsset` 的结构化字段。
5. 导入后的 Unity `Material` 会写入以下 override tag：

```text
HO_MaterialContract      = extensionName
HO_TargetShaderFamily   = target.shaderFamily
HO_HasHoGLTFNode        = True/False
HO_HoGLTFNodeGroup      = hogltf.nodeGroup
```

当前 parser 强解析字段只有：

| JSON 字段 | Unity 字段 | 说明 |
| --- | --- | --- |
| `schema` | `HoMaterialContractAsset.Schema` | 建议等于 extension 名称。 |
| `schemaVersion` | `HoMaterialContractAsset.SchemaVersion` | 当前版本写 `1`。 |
| `target.shaderFamily` | `HoMaterialContractAsset.TargetShaderFamily` | `auto` / `lilToon` / `lilPBR` / `URP/Lit`。 |
| `hogltf.node` | `HoMaterialContractAsset.HoGltfNode` | Blender 材质节点树里的节点实例名。 |
| `hogltf.nodeLabel` | `HoMaterialContractAsset.HoGltfNodeLabel` | 节点 label。 |
| `hogltf.nodeGroup` | `HoMaterialContractAsset.HoGltfNodeGroup` | 节点组名，例如 `HoLilToonStandard` / `HoLilPBR`。 |
| `hogltf.sockets[]` | `HoMaterialContractAsset.HoGltfInputs` | 优先读取，保留 socket 名称、identifier、类型、链接状态和值。 |
| `hogltf.inputs` | `HoMaterialContractAsset.HoGltfInputs` | 旧/简化格式；仅当 `sockets` 为空时读取。 |

`principled`、`toon`、`unity`、`extras` 当前不会被 Unity parser 结构化解析，但会完整留在 `HoMaterialContractAsset.Json`，供后续 lilToon/lilPBR mapper 使用。

## Blender 端导出触发条件

当前 Blender 端由 `glTF2ExportUserExtension.gather_material_hook` 写入 extension。

材质满足以下任一条件时导出契约：

1. 材质面板 `HoGLTF > 导出 HoGLTF 契约` 已勾选。
2. 材质节点树内能找到 HoGLTF 契约节点组。

HoGLTF 契约节点组识别规则：

- 优先从 active `Material Output.Surface` 的上游链路查找 HoGLTF 契约节点组。
- 只有 active output 上游找不到时，才 fallback 到全节点树扫描。
- 节点组或节点实例有自定义属性 `hogltf_node_group` 且值为 truthy。
- 节点组或节点实例有自定义属性 `HoGLTFContract`。
- 节点组名为 `HoGLTF`、`HoGLTF.###`、`HoLilToon*` 或 `HoLilPBR`。

这个优先级很重要：自动转换会在原材质旁边追加新的 `HoLilToon*` / `HoLilPBR` 节点组和新的 active `Material Output`。导出端必须读取真正连到 active output 的 HoLil 组，不能误读旧 MMD 节点树或旁边未启用的候选组。

## 最小合法 JSON

这是 Unity 当前可以识别并保存的最小形状：

```json
{
  "schema": "HO_materials_principled_lil",
  "schemaVersion": 1,
  "target": {
    "shaderFamily": "auto"
  },
  "hogltf": {
    "node": "HoGLTF_lilToon_Contract",
    "nodeLabel": "HoLilToonStandard",
    "nodeGroup": "HoLilToonStandard",
    "inputs": {
      "BaseColor": [1.0, 1.0, 1.0, 1.0],
      "Alpha": 1.0
    }
  }
}
```

推荐导出 `hogltf.sockets`，因为 Unity 端会优先读取 `sockets`，它能保留 socket identifier、类型、是否链接和原始值。

## 推荐完整 JSON

Blender 当前导出端应写出如下结构。空对象可以保留，方便版本演进和人工调试：

```json
{
  "schema": "HO_materials_principled_lil",
  "schemaVersion": 1,
  "source": {
    "tool": "HoGLTF",
    "blenderMaterial": "Material"
  },
  "target": {
    "shaderFamily": "lilToon",
    "shaderVariant": "standard",
    "renderingMode": "Opaque"
  },
  "principled": {},
  "toon": {},
  "unity": {},
  "extras": {},
  "hogltf": {
    "node": "HoGLTF_lilToon_Contract",
    "nodeLabel": "HoLilToonStandard",
    "nodeGroup": "HoLilToonStandard",
    "inputs": {
      "BaseColor": [1.0, 0.8, 0.7, 1.0],
      "Alpha": 1.0,
      "AlphaMode": 0,
      "CullMode": 2,
      "UseShadow": 1.0,
      "ShadowColor": [0.82, 0.76, 0.85, 1.0]
    },
    "sockets": [
      {
        "name": "BaseColor",
        "identifier": "BaseColor",
        "type": "NodeSocketColor",
        "linked": false,
        "value": [1.0, 0.8, 0.7, 1.0],
        "link": null
      },
      {
        "name": "BaseTex",
        "identifier": "BaseTex",
        "type": "NodeSocketColor",
        "linked": true,
        "value": [0.0, 0.0, 0.0, 0.0],
        "link": {
          "fromNode": "MMD Base Tex",
          "fromNodeType": "ShaderNodeTexImage",
          "fromSocket": "Color",
          "image": {
            "name": "body_diffuse.png",
            "filepath": "//textures/body_diffuse.png",
            "source": "FILE",
            "colorspace": "sRGB"
          }
        }
      }
    ]
  }
}
```

## 字段规则

### `schema`

必须写：

```json
"schema": "HO_materials_principled_lil"
```

Unity 不用它选择 extension，但会保存到 `HoMaterialContractAsset.Schema`，便于后续工具检查版本。

### `schemaVersion`

当前写：

```json
"schemaVersion": 1
```

破坏性变更才增加主版本。新增可选字段不需要改变旧文件读取能力。

### `source`

用于记录来源，不参与当前 Unity 导入逻辑。

推荐字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `tool` | string | 固定 `HoGLTF`。 |
| `blenderMaterial` | string | Blender 材质名。 |

### `target`

Unity 当前只读取 `shaderFamily`。

| 字段 | 类型 | 允许值 | 说明 |
| --- | --- | --- | --- |
| `shaderFamily` | string | `auto` / `lilToon` / `lilPBR` / `URP/Lit` | Unity 目标材质族。 |
| `shaderVariant` | string | 可选 | 例如 `standard`、`pbr`。当前 Unity 仅保留原始 JSON。 |
| `renderingMode` | string | `Opaque` / `Cutout` / `Transparent` | 当前 Unity 仅保留原始 JSON。 |

`shaderFamily` 来源优先级：

1. 材质级 `Material.hogltf.target_shader_family`，如果不是 `inherit`。
2. 场景级 `Scene.hogltf_export.target_shader_family`。

### `hogltf`

这是当前最重要的桥接块。Unity parser 已经读取并结构化保存。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `node` | string | 建议 | Blender 节点实例名。 |
| `nodeLabel` | string | 建议 | Blender 节点 label。 |
| `nodeGroup` | string | 必填 | 节点组名，是 Unity 后续 mapper 选择映射表的关键依据。 |
| `nodeGroupContract` | string | 建议 | 节点组自定义属性 `HoGLTFContract`，例如 `lil-material`。 |
| `nodeGroupVariant` | string | 建议 | 节点组自定义属性 `HoLilToonVariant`，例如 `standard`、`fur`、`pbr`。 |
| `inputs` | object | 建议 | `socket.name -> value` 的简化映射。 |
| `sockets` | array | 推荐 | 完整 socket 列表；Unity 当前优先读取它。 |

如果同时存在 `sockets` 和 `inputs`，Unity 当前只使用 `sockets` 构建 `HoGltfInputs`。`inputs` 仍建议保留，方便人工查看和简单工具读取。

### `hogltf.sockets[]`

单个 socket 对象：

| 字段 | 类型 | Unity 当前是否读取 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | socket 显示名。 |
| `identifier` | string | 是 | Blender socket identifier；Unity 映射应优先用它做稳定 key。 |
| `type` | string | 是 | Blender socket 类型，例如 `NodeSocketFloat`、`NodeSocketColor`。 |
| `description` | string | 是 | Blender socket description 原文。 |
| `metadata` | object | 是 | 从 description 解析出的键值，例如 `priority`、`target`、`group`、`role`、`blend`。 |
| `priority` | string | 是 | 常用 metadata 快捷字段。 |
| `target` | string | 是 | 常用 metadata 快捷字段，通常是目标 Unity shader property 或用途。 |
| `group` | string | 是 | 常用 metadata 快捷字段，例如 `mainColor`、`shadow`。 |
| `role` | string | 是 | 常用 metadata 快捷字段，例如 `texture`、`colorFactor`。 |
| `blend` | string | 是 | 常用 metadata 快捷字段，例如 `BaseTex*BaseColor`。 |
| `min` | number/null | 否 | socket 最小值，能读取时写出。 |
| `max` | number/null | 否 | socket 最大值，能读取时写出。 |
| `linked` | bool | 是 | socket 是否有输入链接。 |
| `value` | any | 是 | 默认值。Unity 会记录 value kind、原始 JSON 和常用 typed value。 |
| `link` | object/null | 否 | Blender 侧链接来源信息，当前只保存在原始 JSON。 |

`value` 类型约定：

| Blender 值 | JSON 值 | Unity value kind |
| --- | --- | --- |
| float/int | number | `Number` |
| bool | boolean | `Boolean` |
| string/enum | string | `String` |
| color/vector | number array | `Array`，Unity 读入 `Vector4`，不足 4 位补 0。 |
| object | object | `Object`，仅保留 `ValueJson`。 |
| none | null | `Null`。 |

### `hogltf.sockets[].link`

用于保留 Blender 节点链接来源。Unity 当前不结构化读取这个块，但后续 texture resolver 可以从原始 JSON 里使用。

当前 Blender 端会写：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `fromNode` | string | 来源节点名。 |
| `fromNodeType` | string | 来源节点类型。 |
| `fromSocket` | string | 来源 socket 名。 |
| `image.name` | string | 来源图片 datablock 名。 |
| `image.filepath` | string | Blender 图片路径。 |
| `image.source` | string | Blender 图片 source。 |
| `image.colorspace` | string | Blender colorspace 名称。 |

贴图最终仍应优先依赖 glTF 标准 texture/image 导出结果。`link.image` 是调试和后续解析辅助，不应作为唯一贴图来源。

### `principled`

预留给 Blender Principled BSDF / glTF PBR 语义。当前 Unity 只保存原始 JSON。

第一阶段建议字段：

```text
principled.baseColor.factor
principled.baseColor.texture
principled.metallic.factor
principled.roughness.factor
principled.normal.texture
principled.normal.scale
principled.emission.color
principled.emission.strength
principled.alpha
principled.alphaMode
principled.alphaCutoff
principled.geometry.occlusion
principled.geometry.height
principled.packed.preset
principled.packed.texture
```

规则：

- roughness 保持外部标准值；Unity 写入 smoothness 时使用 `1 - roughness`。
- base color 和 emission 贴图按 sRGB 语义。
- metallic、roughness、AO、height、mask 贴图按 linear 语义。
- normal 贴图按 normal map 语义。

### `toon`

预留给 lilToon 风格化语义。当前 Unity 只保存原始 JSON。

建议先覆盖：

```text
toon.shadow
toon.rim
toon.outline
```

如果 `target.shaderFamily == auto`，后续 Unity mapper 可以用 `toon` block 是否启用来选择 lilToon。

### `unity`

预留给 Unity 渲染状态。当前 Unity 只保存原始 JSON。

建议字段：

```text
unity.doubleSided
unity.renderQueue
unity.cullMode
```

`CullMode` socket 和 `unity.cullMode` 的约定值建议对齐 Unity：

| 值 | 含义 |
| --- | --- |
| `0` | Off / Double Sided |
| `1` | Front |
| `2` | Back |

### `extras`

非核心来源信息和转换历史放这里。当前 Unity 只保存原始 JSON。

MMD 转换器当前会写：

```json
{
  "extras": {
    "mmd": {
      "sourceMaterial": "mmd_mat",
      "sourceNodeGroup": "MMDShaderDev",
      "baseTexture": "body.png",
      "toonTexture": "toon.png",
      "doubleSided": true,
      "alpha": 1.0,
      "alphaSources": ["materialAlpha", "baseTextureAlpha", "toonTextureAlpha"]
    }
  }
}
```

当场景导出设置 `write_debug_fields` 开启时，Blender 端还会写：

```text
extras.blenderCustomProperties
```

该字段仅用于调试，不应作为 Unity mapper 的稳定输入。

## MMD 转换结果约定

当前 `asset_conversion.py` 会把 MMD 材质转换为 HoGLTF 契约节点组。

目标 `lilToon`：

| MMD 来源 | HoGLTF socket / metadata |
| --- | --- |
| `Diffuse Color` | `BaseColor` |
| `Alpha` | `Alpha` |
| `Alpha < 0.999` | `AlphaMode = 3` |
| `Alpha >= 0.999` | `AlphaMode = 0` |
| `Double Sided = true` | `CullMode = 0` |
| `Double Sided = false` | `CullMode = 2` |
| `Base Tex` 链接的 Image Texture | `BaseTex` |
| `Toon Tex` 链接的 Image Texture | `ShadowTex` |
| `Ambient Color` | `ShadowColor` |
| MMD 原始信息 | `extras.mmd` |

目标 `lilPBR`：

| MMD 来源 | HoGLTF socket / metadata |
| --- | --- |
| `Diffuse Color` | `BaseColor` |
| `Alpha` | `Alpha` |
| `Double Sided` | `CullMode` |
| `Base Tex` 链接的 Image Texture | `BaseTex` |
| 默认 PBR 参数 | `Metallic = 0`、`Roughness = 0.5` |
| `Toon Tex` | 不接入 PBR shader，保存在 `extras.mmd.toonTexture` |

目标节点组：

```text
lilToon -> HoLilToonStandard
lilPBR  -> HoLilPBR
```

## 合并规则

Blender 端 `Material.hogltf.contract_json` 是高级覆盖入口。它必须是 JSON object。

当前实现顺序：

1. 先构建默认 contract。
2. 如果存在 HoGLTF 节点，写入 `hogltf`。
3. 再把 `contract_json` 用浅层 `dict.update(...)` 合并到根对象。
4. 最后在 `extras.blenderCustomProperties` 写入调试字段。

因此 `contract_json` 可以覆盖根级字段，例如 `target`、`extras`、`toon`。注意这是浅合并，覆盖 `extras` 会替换整个默认 `extras` 对象。

## 版本兼容要求

Blender 导出端必须保持：

- 主扩展名固定为 `HO_materials_principled_lil`。
- `schemaVersion` 当前写 `1`。
- `target.shaderFamily` 必须存在。
- 发现 HoGLTF 节点时必须写 `hogltf.nodeGroup`。
- `hogltf.sockets[].value` 必须是 JSON 可序列化值。
- 不依赖 `extras.blenderCustomProperties` 做关键语义。

Unity 导入端当前必须保持：

- 优先读取 `HO_materials_principled_lil`。
- 兼容读取 `HO_materials_openpbr_lil`。
- 保存原始 JSON 到 `HoMaterialContractAsset.Json`。
- `sockets` 存在时优先用 `sockets`，否则回退到 `inputs`。

## 验证清单

每次修改 Blender meta 写入后，按以下步骤验证：

1. 在 Blender 导出 `.gltf` 或 `.glb`。
2. 搜索 `HO_materials_principled_lil`。
3. 确认对应 material extension 里有 `schemaVersion`、`target.shaderFamily`。
4. 如果材质有 HoGLTF 节点，确认有 `hogltf.nodeGroup` 和 `hogltf.sockets`。
5. 用 glTF Validator 检查文件格式。
6. 在 UnityGLTF 中导入。
7. 确认导入资产下出现 `HoMaterialContractAsset` 子资源。
8. 确认 `HoMaterialContractAsset.TargetShaderFamily` 和 `HoGltfInputs` 有值。
9. 右键使用 Unity 调试菜单打印 HoGLTF 契约输入，确认 socket 名和值符合预期。

## Unity 自动 lilToon 导入约定

Unity 端 `HoMaterialsPrincipledLilImport` 当前会在导入材质时自动判断是否切换到 lilToon：

- `target.shaderFamily == "lilToon"` 时启用 lilToon mapper。
- 或者 `hogltf.nodeGroup` 以 `HoLilToon` 开头时启用 lilToon mapper。
- 找不到目标 lilToon shader 时，不破坏 UnityGLTF 默认材质，只保留 HO override tags 和 `HoMaterialContractAsset`。
- `applyLilToonMapping` 默认为开启；`applyUrpLitFallback` 仅在没有成功切到 lilToon 时才会执行。

当前已映射的 HoLilToon socket：

| HoLilToon socket | Unity lilToon property |
| --- | --- |
| `BaseColor` / `Alpha` / `BaseTex` | `_Color`、`_BaseColor`、`_MainTex` |
| `AlphaMode` / `AlphaCutoff` / `TransparentMode` | shader 选择、`_Cutoff`、blend/ZWrite/renderQueue |
| `CullMode` | `_Cull` |
| `NormalTex` / `NormalScale` | `_BumpMap`、`_BumpScale`、`_UseBumpMap` |
| `UseShadow` / `ShadowColor` / `ShadowTex` | `_UseShadow`、`_ShadowColor`、`_ShadowColorTex` |
| `UseRim` / `RimColor` / `RimTex` | `_UseRim`、`_RimColor`、`_RimColorTex` |
| `UseOutline` / `OutlineColor` / `OutlineTex` / `OutlineWidthMask` | outline shader variant、`_UseOutline`、`_OutlineColor`、`_OutlineTex`、`_OutlineWidthMask` |
| `EmissionColor` / `EmissionTex` / `UseEmission` | `_EmissionColor`、`_EmissionMap`、`_UseEmission` |
| `Metallic` / `MetallicTex` | `_Metallic`、`_MetallicGlossMap` |
| `Roughness` | `_Smoothness = 1 - Roughness` |

注意：`RoughnessTex` 不能直接写入 `_SmoothnessTex`，因为二者语义相反。Unity 端在实现贴图反相或生成 smoothness 贴图前，不应把 `RoughnessTex` 暴力直连到 `_SmoothnessTex`。

## 独立贴图文件夹匹配约定

HoGLTF 导出 `.gltf + .bin + tex/` 或 `.gltf + .bin + textures/` 是常规路径。Blender 端应继续在 `hogltf.sockets[].link.image` 写入：

```json
{
  "name": "body_diffuse.png",
  "filepath": "//textures/body_diffuse.png",
  "source": "FILE",
  "colorspace": "sRGB"
}
```

Unity 端解析顺序：

1. 先使用 UnityGLTF `OnAfterImportTexture` 回调登记的 Texture。
2. 匹配键包括导入后的 `Texture.name`、glTF `texture.name`、glTF `image.name`、`image.uri`、完整相对路径、文件名、无扩展名。
3. Editor 导入时，如果缓存未命中，会从 glTF 资产所在目录查找同名贴图，默认尝试同目录、`textures/`、`Textures/`、`tex/`、`Tex/`。
4. 仍找不到时，使用 UnityGLTF 已经写入 PBR 材质的 base/normal/emission fallback 贴图。

因此 Blender 端不必写 Unity asset GUID；稳定写出 `link.image.name` 和 `link.image.filepath` 即可。
