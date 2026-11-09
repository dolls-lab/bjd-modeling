# BJD 建模仓库协作约定

- 主开发目录是本仓库。BJD 头壳工作不再写入相邻的 `hksr_database`。
- 采用 `characters/<character-id>/<scale>/versions/<version>/` 布局；角色参考放在 `characters/<character-id>/references/local/`。尺寸标签如 `1-4`、`1-3` 仅作分类，实际毫米尺寸和颈部接口必须记录在版本参数里。
- 已有 origin 为 `https://github.com/dolls-lab/bjd-modeling.git`。本次三分制作和目录整理只在本地进行，不改远端、不自动提交或推送。后续提交、同步和公开范围按用户新指示处理，不从已有远端推断额外授权。
- 三月七已确认四分素头位于 `characters/march-7th/1-4/versions/march7-bjd-1-4-v0.14/`；已确认妆面位于同级 `march7-bjd-1-4-v0.14-makeup/v5-fair-skin/`。后续修改新建版本，保留此前确认的模型。
- 三月七三分版本在 `characters/march-7th/1-3/versions/` 独立保存，以四分 v14 为基线；按用户要求保持面部和头型，通过等比缩放调整整体尺寸，颈部接口单独适配并记录局部变化。
- 结构要求：空心头壳、两眼洞、可拆后盖、颈口。局部妆面画在真实头壳上，眼内用半球眼杯预览；不要用整张原角色脸覆盖头壳。
- 所有尺寸使用 mm；数字网格核验与实物打印、试装验证分开记录。未知娃体尺寸标为设计假设，不写成实测或已适配。
- 原模型使用说明、来源和版本校验记录随模型保留；不把来源限制改写成允许公开发布。
- 三月七的 `references/local/official-models/` 是共享来源的独立副本。不要修改相邻娃衣仓库或 GSC 仓库的素材。
- 历史模型、报告和脚本保持原始字节。历史绝对路径仅作溯源；重跑旧版前按 `docs/layout-reorganization.md` 检查路径与临时输入。原迁移清单保持原样，由 `docs/layout-map.json` 映射到当前路径。
- 只暂存当前任务相关文件，不提交缓存、凭据或重复 ZIP 包。不改写旧仓库历史，不强制推送。
