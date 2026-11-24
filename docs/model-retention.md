# 三月七模型保留与同步清单

2026-11-24 按用户在清单核对后的指令，删除此前已列举并明确否定的模型，补充同步已认可版本至现有私有仓库 `dolls-lab/bjd-modeling`。

## 保留与同步

版本号按尺寸独立计数。四分 v15 的删除不涉及三分 v15；四分 v16 与特六 v16 也是不同模型。

| 尺寸 | 模型 | 依据 |
| --- | --- | --- |
| 四分 | [v14 素头](../characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/march7-bjd-head-v0.14-draft.blend) | 明确认可并提交；初始形状基准 |
| 四分 | [v14 妆面最终浅肤色版（妆面 v5）](../characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14-makeup/v5-fair-skin/march7-v14-fair-skin-original-hair.blend) | 明确认可并提交；局部妆面、眼杯、原发型预览 |
| 四分 | [v18](../characters/march-7th/1-4/versions/v18-lip-only/march7-bjd-head-1-4-v18.blend) | 明确要求与 v19 两版均保留 |
| 四分 | [v19](../characters/march-7th/1-4/versions/v19-lip-refine/march7-bjd-head-1-4-v19.blend) | 明确要求保留；后续三尺寸的形状基线 |
| 四分 | [v31 大后盖版](../characters/march-7th/1-4/versions/v31-large-rear-cap/march7-bjd-head-1-4-v31.blend) | 最新认可并要求同步 GitHub |
| 三分 | [v1](../characters/march-7th/1-3/versions/v1/march7-bjd-head-1-3-v1.blend) | 明确认可并提交的初版 |
| 三分 | [v3（由四分 v19 派生）](../characters/march-7th/1-3/versions/v3-from-v19/march7-bjd-head-1-3-v3.blend) | 按用户指定基线制作，作为已采用的形状版本保留 |
| 三分 | [v15 大后盖版](../characters/march-7th/1-3/versions/v15-large-rear-cap/march7-bjd-head-1-3-v15.blend) | 最新认可并要求同步 GitHub |
| 特六 | [v4（由四分 v19 派生）](../characters/march-7th/1-6-special/versions/v4-from-v19/march7-bjd-head-1-6-special-v4.blend) | 按用户指定基线制作，作为已采用的形状版本保留 |
| 特六 | [v16 大后盖版](../characters/march-7th/1-6-special/versions/v16-large-rear-cap/march7-bjd-head-1-6-special-v16.blend) | 最新认可并要求同步 GitHub |

四分 v18、v19 是用户明确说“两版都保留”的版本；其他提交认可与指定派生的依据如上，不将目录中的所有历史文件都视为用户满意。

最新结构说明及预览见 [大后盖交付](latest-models.md)。三分 v3、特六 v4 的来源与对比见 [v19 三尺寸记录](../characters/march-7th/reviews/v19-size-sync-2026-11-11/README.md)。历史版本内“待确认”的文字保留生成时原文，确认状态以本清单及最新交付说明为准。

## 删除范围

- 四分 v1–v11：此前已从本地删除，本次将其 694 个已跟踪文件的删除提交并同步。完整历史删除记录含当时的缓存、重复包等共 735 个文件，见 [逐文件记录](retired-versions-2026-11-11.json)。
- 四分 v15、v17：此前已删除，当前本地与 Git 跟踪树均没有对应版本目录。
- 本轮不扩大到此前清单以外的结构迭代或其他尺寸；没有明确列入删除范围的历史稿维持原状，未确认的本地草稿不一并上传。
- 普通 Git 提交记录删除，不改写历史提交；旧提交仍可用于回溯。

## 必要输入与复核

四分 v16 被用户认可过，且是 v18 的直接输入。本次同步其 Blender、头壳/后盖 STL、参数、来源与原有报告，作为最小只读输入快照；没有把它列为用户明确要求长期保留的最终版。该目录原 README 的完整重建步骤、历史截图链接不表示快照包含完整旧工作目录。

特六 v1 的 `validate_model.py` 被 v18/v19 作为几何辅助代码加载，仅同步该脚本，不补交特六 v1 的未确认模型。v19 依赖 v18，三分 v3、特六 v4 依赖四分 v19；相关源文件一并保留。

早期版本删除后，保留 [v12 数值输入](../characters/march-7th/references/derived/v12-build-inputs/README.md) 和 [v16 数值输入](../characters/march-7th/references/derived/v16-build-inputs/README.md)，这些是后续模型使用的数值数据，不恢复被否定版本的完整模型目录。最新大后盖版在此前提交中保存的三份直接输入快照也继续保留。

本轮不重新建模：模型、STL、历史验证报告及截图按原字节保存。已复核保留目录的原校验记录，迁移验证工具会逐文件区分已授权删除和应保留文件。历史脚本可能依赖 Blender/Python 库与原本地路径，重建前需配置运行环境；已保存 `.blend` 可直接打开。数字核验不代表实物打印、装配或承载已验证。
