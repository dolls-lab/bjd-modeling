# BJD 建模工作区

按角色、尺寸和版本管理 BJD 头壳、妆面预览、建模脚本与核验记录。当前角色为三月七。

| 尺寸 | 最新模型 | 保留的形状版本 |
| --- | --- | --- |
| 四分 | [v31 大后盖](characters/march-7th/1-4/versions/v31-large-rear-cap/README.md) | v14 素头、v14 最终妆面、v18、v19 |
| 三分 | [v15 大后盖](characters/march-7th/1-3/versions/v15-large-rear-cap/README.md) | v1、基于四分 v19 的 v3 |
| 特六 | [v16 大后盖](characters/march-7th/1-6-special/versions/v16-large-rear-cap/README.md) | 基于四分 v19 的 v4 |

完整模型链接与用户确认依据见 [保留与同步清单](docs/model-retention.md)，最新结构、截图和实物适配状态见 [大后盖交付](docs/latest-models.md)。四分 v1–v11、v15、v17 已按用户要求移除；其余未明确列入删除的历史资料保留。不同尺寸的版本号独立计数。

使用 Blender「文件 → 打开」查看 `.blend`。妆面预览基于四分 v14，包含局部妆面、内部眼杯和原发型，不替代素头打印结构。各尺寸的面雕、接口、参数与核验范围以其版本说明为准。

## 目录

`characters/<character-id>/<scale>/versions/<version>/` 保存每个角色和尺寸的独立版本；共享来源位于角色的 `references/`，对比与审核位于 `reviews/`。增加其他角色时新建独立角色目录，保留已确认模型，后续修改另存版本。

## 来源与同步

沿用现有私有仓库 [dolls-lab/bjd-modeling](https://github.com/dolls-lab/bjd-modeling)，作为 `origin`。按用户要求提交和推送，不改变仓库归属或可见性。

来源说明与使用限制随模型保留，见 [原使用说明](characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/source-usage-rules.txt)。迁移与整理不改变来源限制。缓存、备份和重复 ZIP 不纳入本次提交。

[三月七目录](characters/march-7th/README.md) · [迁移说明](docs/migration.md) · [布局与历史路径](docs/layout-reorganization.md)。执行 `python3 tools/verify_migration.py` 核对保留的原迁移文件及已授权删除记录，不会重新建模或改写模型。
