# v16 构建所需的数值输入

四分 v15 模型版本已按用户要求删除。本目录仅保留 v16 的构建与独立核验确实依赖的 `mouth-field.npz` 数值场，不包含 v15 的 Blender 模型、STL 或截图，也不作为可用模型版本。

该文件字节与 v16 的 `surface-field-report.json` 中 `lip_field_source_sha256` 完全一致。SHA-256：`bf4ae0b2f305e8947076ff7df8bbafc4fe065428d3b4ca83dedd55fa4c81be17`。

## 历史路径映射

v16 原有文件保持原始字节，因此 `prepare_surface.py`、`build_model.py`、`validate_model.py` 仍写有旧输入路径。需要重跑时，应在临时工作副本中将输入映射到本文件，再输出新目录；不要直接在保留的 v16 目录执行会覆盖模型的历史脚本。

| 旧输入 | 当前保留文件 |
| --- | --- |
| `1-4/versions/v15-mouth-soft/mouth-field.npz` | `references/derived/v16-build-inputs/mouth-field.npz` |

上述路径均相对 `characters/march-7th/`。v16 的已保存模型可直接使用，无需本输入即可打开。原 `render_preview.py` 的 v15 对照模型已删除，不能再运行旧 v15/v16 渲染；现有 v14/v16 对比位于 `reviews/quarter-v14-v16-2026-11-11/`。

删除及哈希记录见 [cleanup-record.json](cleanup-record.json)。历史其他目录中已经生成的对比记录按原字节保留，不代表 v15 模型仍可用。
