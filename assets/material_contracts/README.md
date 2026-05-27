# HoGLTF 材质契约资产流程

本目录存放 HoGLTF 内置材质契约资产。它不是 MMD 专属目录；MMD 只是当前第一条适配链路。未来 VRM、PMX、Blender Principled、OpenPBR 或其他 DCC 材质桥接都应该复用这里的契约资产体系。

## 目录职责

| 路径 | 职责 | 是否稳定 |
| --- | --- | --- |
| `../published/lil_material_contracts.blend` | 正式发布资产，插件运行时加载它，Blender Asset Browser 只扫描 `assets/published/`。 | 稳定 |
| `ho_lil_material_node_contract.md` | 契约文档，记录节点组、socket、变体和映射规则。 | 稳定 |
| `create_holil_material_blend.py` | 契约资产重建脚本，只作为开发/迁移工具。 | 工具 |
| `generated/` | 默认生成草稿输出目录，用于调试和验收。 | 临时 |
| `_blender_backups/` | 手动备份目录，只放人工确认要保留的 `.blend`。 | 手动 |

不要把 `.blend1` 当作正式备份。`.blend1` 是 Blender 自动保存副产物，本流程里生成脚本会设置 `save_version = 0`，避免刷新资产时产生它。

## 默认调试流程

修改契约脚本或 socket 定义后，先生成草稿：

```powershell
& 'D:\Blender\blender-4.5.8-windows-x64\blender.exe' --factory-startup --background --python 'C:\Users\hhh12\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\HoGLTF\assets\material_contracts\create_holil_material_blend.py'
```

默认输出：

```text
assets/material_contracts/generated/lil_material_contracts.generated.blend
```

这个命令不覆盖正式发布资产。

## 验收检查

发布前至少检查：

1. 生成日志里的节点组数量和 socket 数量符合预期。
2. 打开 generated `.blend`，确认 `HoLilToon*`、`HoLilPBR` 节点组可作为资产看到。
3. 检查节点组 `TargetShaderVariant` 默认值是否正确。
4. 确认 `asset_data` 标记只存在于节点组；材质样例不作为 Asset Browser 资产。
5. 如涉及 MMD 映射，确认 `adapters/mmd` 下的扫描报告或测试数据仍能解释这次变更。

可用后台快速检查资产标记：

```powershell
& 'D:\Blender\blender-4.5.8-windows-x64\blender.exe' --factory-startup --background 'C:\Users\hhh12\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\HoGLTF\assets\material_contracts\generated\lil_material_contracts.generated.blend' --python-expr "import bpy; print(len([x for x in list(bpy.data.node_groups)+list(bpy.data.materials) if getattr(x, 'asset_data', None) is not None]))"
```

## 发布流程

只有在 generated 文件验收通过后，才允许手动覆盖正式发布资产。生成脚本不再提供自动 `--publish`，避免误把未验收草稿写进正式资产库。

```powershell
Copy-Item -LiteralPath 'C:\Users\hhh12\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\HoGLTF\assets\material_contracts\generated\lil_material_contracts.generated.blend' -Destination 'C:\Users\hhh12\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\HoGLTF\assets\published\lil_material_contracts.blend' -Force
```

手动发布会覆盖：

```text
assets/published/lil_material_contracts.blend
```

如果需要写到自定义位置，可以使用：

```powershell
& 'D:\Blender\blender-4.5.8-windows-x64\blender.exe' --factory-startup --background --python 'C:\Users\hhh12\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\HoGLTF\assets\material_contracts\create_holil_material_blend.py' -- --output 'C:\Temp\ho_lil_contract_test.blend'
```

## 手动备份规则

需要保留某个正式版本时，手动复制到 `_blender_backups/`，并使用可读名字，例如：

```text
_blender_backups/lil_material_contracts_2026-05-20_before_fur_refactor.blend
```

不要把 `generated/` 的草稿文件、`.blend1`、临时测试文件放进 `_blender_backups/`。

## 插件资产库注册

HoGLTF 插件提供手动资产库注册按钮：

```text
偏好设置 -> 插件 -> HoGLTF -> 注册内置资产库
```

注册路径是：

```text
HoGLTF/assets/published
```

注册逻辑会按路径防重复；重复点击不会新增第二个资产库条目。插件启动和手动注册时会清理旧的 `HoGLTF/assets` 宽路径和 `HoGLTF/assets/material_contracts` 开发目录。不要注册这两个目录，否则 `generated/`、`_blender_backups/` 和开发文件会一起被 Asset Browser 扫到。
