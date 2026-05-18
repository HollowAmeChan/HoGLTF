# HoGLTF Blender Export 计划

HoGLTF 是 Blender 侧的导出桥接插件。它负责把我们自己的材质契约写进 glTF，Unity 侧再由 `Liltoon-UnityGLTF-Extensions` 在 UnityGLTF 导入流程里读取这些契约，并生成 lilToon、lilPBR 或临时 URP/Lit 材质。

## 当前目标

第一阶段只做最小闭环：

1. Blender 能启用 `HoGLTF` 插件。
2. glTF 导出面板里出现 `HoGLTF Material Contract` 折叠区。
3. 材质属性面板里出现 `HoGLTF` 设置。
4. 勾选材质上的 `Export HoGLTF Contract` 后，导出的 glTF material 会带：

```json
"extensions": {
  "HO_materials_principled_lil": {}
}
```

Unity 侧插件读取的 extension 名称也是：

```text
HO_materials_principled_lil
```

保留旧名只用于兼容历史文件：

```text
HO_materials_openpbr_lil
```

## 这次加了什么

`__init__.py` 里现在有：

- `bl_info`，让 Blender 能识别这是一个 Add-on。
- `HoGLTFExportSettings`，挂在 `bpy.types.Scene.hogltf_export`。
- `HoGLTFMaterialSettings`，挂在 `bpy.types.Material.hogltf`。
- `exporter_extension_layout_draw`，把 HoGLTF 设置画进 glTF 导出界面。
- `glTF2ExportUserExtension`，这是 glTF-Blender-IO 要求的精确类名。
- `gather_material_hook`，在每个 glTF material 生成后追加我们的 material extension。

`material_contract.py` 里现在有：

- 查找材质节点树中的 `HoGLTF` 自定义节点组。
- 读取这个节点组的输入 socket 默认值。
- 把输入写入 `HO_materials_principled_lil` extension 的 `hogltf.inputs`。

当前导出的 JSON 形状类似：

```json
{
  "extensions": {
    "HO_materials_principled_lil": {
      "schema": "HO_materials_principled_lil",
      "schemaVersion": 1,
      "target": {
        "shaderFamily": "auto"
      },
      "hogltf": {
        "nodeGroup": "HoGLTF",
        "inputs": {
          "Param1": 0.42
        }
      }
    }
  }
}
```

当前合同 JSON 是轻量骨架，不硬猜完整材质语义。真正的节点读取和字段映射应该对齐 `D:/Unity_Fork/lilToon/接口契约.md` 后再写。

## 为什么走 glTF extension，不只用 extras

`extras` 适合非常局部、私有、不需要工具链显式识别的数据。

这里我们要做的是一条 Blender -> glTF -> UnityGLTF -> lilToon/lilPBR 的稳定管线，Unity 侧需要明确判断“这个材质有 Hollow 材质契约”。所以更适合写在：

```text
material.extensions.HO_materials_principled_lil
```

这样 UnityGLTF import plugin 能直接在 `GLTFMaterial.Extensions` 里接住它。

## extension 命名注意

Khronos 的命名规则是：

- `KHR` 是 Khronos ratified 或计划 ratified 的 extension。
- `EXT` 是多厂商 extension。
- Vendor extension 使用注册过的 vendor prefix。
- 名字应是 `PREFIX_lowercase_snake_case`。

所以长期看，`HO_materials_principled_lil` 最好去 Khronos glTF repo 提一个 prefix issue，把 `HO` 或更正式的前缀注册掉。短期内部链路可以先用，但公开发布前建议注册。

## 参考资料

Blender glTF 2.0 手册：

https://docs.blender.org/manual/zh-hans/4.5/addons/import_export/scene_gltf2.html

重点看：

- glTF 支持的材质范围。
- Blender Principled BSDF 到 glTF PBR 的导出限制。
- Blender exporter 对 KHR material extensions 的支持情况。
- Custom Properties 与 Extensions 的差别。

Khronos glTF extension registry：

https://github.com/KhronosGroup/glTF/tree/main/extensions

重点看：

- 现有 `KHR_materials_*` 能表达哪些标准材质参数。
- 什么情况下 extension 应该放进 `extensionsUsed`。
- material extension 通常不应该 required，因为 core PBR 可以作为 fallback。

Khronos Prefixes：

https://github.com/KhronosGroup/glTF/blob/main/extensions/Prefixes.md

重点看：

- prefix 注册方式。
- 已注册 vendor prefix。
- `KHR` / `EXT` / vendor prefix 的边界。

官方 glTF-Blender-IO example add-ons：

https://github.com/KhronosGroup/glTF-Blender-IO/tree/main/example-addons/

重点看：

- `example_gltf_exporter_extension/__init__.py`
- `glTF2ExportUserExtension` 类名必须精确匹配。
- `exporter_extension_layout_draw` 可以把 UI 放进 glTF 导出面板。
- `Extension` 类会让 exporter 自动维护 `extensionsUsed` / `extensionsRequired`。

## 后续实现建议

### 1. 先定合同字段

从 `D:/Unity_Fork/lilToon/接口契约.md` 收敛一份 Blender 侧要导出的字段。建议分块：

```text
principled
textures
toon
unity
extras
```

不要一上来直接读所有 Blender 节点。先定字段，后接节点读取。

### 2. 增加材质读取模块

建议拆成：

```text
contract.py
material_reader.py
texture_reader.py
ui.py
__init__.py
```

当前单文件骨架适合起步，等逻辑变多就拆。

### 3. 不破坏标准 glTF PBR fallback

导出时仍让 Blender 官方 exporter 正常写 core material：

- baseColor
- metallic
- roughness
- normal
- occlusion
- emissive
- alphaMode

我们的 extension 只补充 Unity/lilToon/lilPBR 需要但标准 glTF 表达不了的东西。

### 4. 材质选择策略

当前 UI 里有：

```text
auto
lilToon
lilPBR
URP/Lit
```

Unity 侧可以这样解释：

1. `lilToon`：直接转 lilToon。
2. `lilPBR`：直接转 lilPBR。
3. `auto`：看 toon block 是否存在或启用。
4. `URP/Lit`：仅作为过渡测试。

### 5. 验证链路

建议每次改导出逻辑后做：

1. Blender 导出 `.gltf`。
2. 用文本搜索 `HO_materials_principled_lil`。
3. 用 Khronos glTF Validator 检查格式。
4. 在 UnityGLTF 中导入。
5. 确认 Unity 侧 `HoMaterialContractAsset` 子资源存在。
6. 再确认材质 mapper 是否按 contract 生成目标 shader。

## 资料位置

本插件目录：

```text
C:/Users/hhh12/AppData/Roaming/Blender Foundation/Blender/4.5/scripts/addons/HoGLTF
```

Unity 侧插件仓库：

```text
D:/Unity_Fork/Liltoon-UnityGLTF-Extensions
```

临时右键材质转换器：

```text
D:/Unity_Fork/lilToon-URP-Extensions/Editor/LilMatConvert
```
