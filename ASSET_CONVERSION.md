# HoGLTF 资产转换模块

模块入口：

```text
HoGLTF/asset_conversion.py
```

UI 入口：

```text
View3D -> Sidebar -> HoGLTF -> HoGLTF Asset Conversion
```

第一版功能是把 MMD 预设材质转换为 HoGLTF 材质契约节点组。转换默认不新建材质、不替换材质 slot，而是在原材质节点树旁边追加一组 HoGLTF 契约节点和一个新的 `Material Output`，并把这个新输出设为 active。原 MMD 节点树和原输出节点保留在同一个材质里，方便用户对照、留档和手动回退。

## 支持范围

当前识别以下 MMD 材质形状：

- 根材质节点树里存在 `ShaderNodeGroup`。
- 组名是 `MMDShaderDev` / `MMDShader`，或以 `MMDShader` 开头。
- 或者组输入包含 `Base Tex`、`Base Alpha`、`Toon Tex`、`Double Sided`。

## MMD -> HoLilToonStandard

| MMD 来源 | HoGLTF socket / metadata |
| --- | --- |
| `Diffuse Color` | `BaseColor` |
| `Alpha` | `Alpha` |
| `Alpha < 0.999` | `AlphaMode = Transparent` |
| `Alpha >= 0.999` | `AlphaMode = Opaque` |
| `Double Sided = true` | `CullMode = 0` |
| `Double Sided = false` | `CullMode = 2` |
| `Base Tex` 链接的 Image Texture | `BaseTex` |
| `Toon Tex` 链接的 Image Texture | `ShadowTex` |
| `Ambient Color` | `ShadowColor` |
| MMD 原材质信息 | `contract_json.extras.mmd` |

目标节点组：

```text
HoLilToonStandard
```

## MMD -> HoLilPBR

| MMD 来源 | HoGLTF socket / metadata |
| --- | --- |
| `Diffuse Color` | `BaseColor` |
| `Alpha` | `Alpha` |
| `Double Sided` | `CullMode` |
| `Base Tex` 链接的 Image Texture | `BaseTex` |
| `Toon Tex` | 不接入 PBR shader，保存在 `extras.mmd.toonTexture` |
| 默认 PBR 参数 | `Metallic = 0`、`Roughness = 0.5` |

目标节点组：

```text
HoLilPBR
```

## 转换方式

默认方式：

- 在原材质节点树中追加 `HoGLTF MMD -> lilToon/lilPBR` frame。
- frame 内包含契约节点组、复用同一 Image datablock 的贴图节点、新的 Material Output。
- 新 Material Output 默认设为 `is_active_output = True`。
- 原来的 MMD 节点、旧 Material Output、材质 slot 都不删除、不替换。

可选方式：

- 关闭“设为活动输出”：只追加节点簇，不切换 active output，适合纯留档。
- 打开“创建材质副本”：创建新的契约材质副本，原材质不变。这个模式主要用于批量对比，不推荐作为默认转换方式。

## Python 用法

```python
from HoGLTF import asset_conversion

materials = list(bpy.data.materials)
result = asset_conversion.convert_mmd_materials(
    materials,
    target_family="lilToon",
    activate_output=True,
    duplicate_material=False,
)
print(result["converted"], result["skipped"])
```

## 设计边界

- 这是资产转换模块，不属于 glTF 导出模块。导出只负责读取转换后的契约。
- 当前不直接生成 Unity 材质，不直接写 lilToon/lilPBR shader property。
- 当前不扫描贴图 alpha 像素；透明判断只使用 MMD 材质 `Alpha` 标量。贴图 alpha 扫描应作为后续增强接入。
- 当前不替换材质 slot。默认在原材质内部追加节点并激活新的 Material Output。
- 当前保留 `bpy.ops.ho.*` IR operator 历史 id，不影响本模块的 `bpy.ops.hogltf.convert_mmd_materials`。

## Undo 安全

所有会新增/删除/替换 Blender datablock 的转换 operator 必须声明：

```python
bl_options = {"REGISTER", "UNDO"}
```

MMD 转换会从内置资产 `.blend` 追加契约 `NodeGroup`，并在材质节点树里创建新节点和 active `Material Output`。这些操作必须作为一个 Blender undo 事务进入撤回栈；否则交互式撤回可能遇到半托管 datablock 状态，表现为节点树残留、输出状态错乱，严重时导致 Blender 崩溃。
