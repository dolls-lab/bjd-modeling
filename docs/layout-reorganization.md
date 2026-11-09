# 按角色、尺寸和版本整理仓库

2026-11-09，为独立制作三月七三分版，并为以后新增其他角色保留清晰结构，采用 `characters/<character-id>/<scale>/versions/<version>/` 布局。

## 原文件的新位置

| 原路径前缀 | 当前路径前缀 |
| --- | --- |
| `outputs/` | `characters/march-7th/1-4/versions/` |
| `references/local/official-models/` | `characters/march-7th/references/local/official-models/` |

原四分系列 16 个目录整体移动，目录名称及内部文件不重命名。四分素头、妆面预览和原角色参考文件没有重新保存；原模型形状、材质、贴图、脚本与历史核验内容保持原始字节。

新三分版存于 `characters/march-7th/1-3/versions/v1/`，其参数、模型和验证报告独立于四分历史文件。新增其他角色时使用新的角色标识目录；各角色共用仓库级工具，不混用角色素材或尺寸参数。

## 历史记录与路径兼容

`migration-manifest.json`、`reference-copy-manifest.json` 以及 `migration-verification.json` 是原迁入事件的记录，仍保留原路径与哈希，不改写为本次路径。`layout-map.json` 记录原路径到当前路径的映射，`tools/verify_migration.py` 应用映射后核对文件内容。

原迁入清单包含 1,225 个系列文件，参考副本清单包含 25 个文件；共 1,250 个历史文件可按现有磁盘内容核对。未纳入 Git 的缓存和重复 ZIP 在本机仍保留；重新检出仓库时，这些可选文件缺失不会判为模型丢失。新三分文件不属于旧迁入清单，其验证由三分版本自身的记录负责。

最新四分 v5、v4 的主要生成和渲染脚本基于 `__file__` 查找同级或邻近版本，整体移动保留了这些相对关系。最新 v5 `.blend` 的 5 张贴图已打包，独立打开不依赖旧绝对路径。

早期求解脚本、部分报告索引仍使用当时的绝对路径或 `/private/tmp/` 中间输入，原版本内容不作批量替换。**本次重整不表示所有历史过程均已验证可从零重跑。** 需要重跑时，在新工作版本中使用当前相对路径，并核实所需中间数据；历史文件继续作为原交付证据保存。

原 `source_pmx` 参数有些指向同级 `character-doll-workshop` 的原素材路径，该原件仍然保留。本仓库角色参考副本现在位于 `characters/march-7th/references/local/official-models/`，新脚本优先使用这个位置。此次未修改娃衣或 GSC 仓库。

## 验证和同步

运行 `python3 tools/verify_migration.py` 核对历史文件的字节数与 SHA-256。目录重整不改变旧模型校验值；根 README 与角色 README 提供当前路径入口。

本次移动完成后已执行校验，结果为 `PASS: 1250 preserved files match migration SHA-256 records.`；两个原迁移清单及原迁移验证记录与 Git 中的原件逐字节一致。四分及参考资料的入口链接已核对存在。

当前 Git 已配置 `origin` 指向 `https://github.com/dolls-lab/bjd-modeling.git`；此前迁移文档中的“未配置远端”描述的是原迁移时的状态。本次操作不改远端，不自动提交或推送，也不改变素材使用限制。
