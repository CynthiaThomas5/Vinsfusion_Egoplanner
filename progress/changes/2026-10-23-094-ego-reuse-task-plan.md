# EGO 复用与剩余任务规划 v3.1

- 任务 ID／日期：#094／2026-10-23。
- 对话摘要：[本轮项目约束与决定](../../collaboration/dialogues/2026-10-23-094-ego-reuse-task-plan.md)。
- 执行模式与范围：仅规划；此前 Goal 完成模式的 N06 范围保持供后续恢复，本轮不运行它。
- 修改前状态：`progress/CURRENT.md`、`progress/milestones.json` 和 N06 代码／配置／工具已有未提交修改，均视为用户已有工作。本轮修改前副本位于 `/tmp/ego-plan-094-before-20261023`，用于区分 #094 文档增量；不回滚、提交或混入其代码改动。

## 实际改动

- [执行书](../../docs/remaining-small-goals.md)修订为实施规划 v3.1：固定上游来源，逐模块明确保留／调整／不进入主链；列出 N01–N17 已有交付、原工作替换方式和剩余出口；新增变更影响回归矩阵。
- N01–N05 的初始任务措辞补上已有交付承接，避免重新执行同一诊断。N05 no-go、N04 分类风险和 N02 未解根因仍完整保留。
- N06 接续细化为 N06.3 unknown／readiness 分类、必要 N06.4 最小修复／合法观测，再恢复未通过的 N06.2 两布局活动曲线集成；不跳过到 N07，不修改 unknown 拒绝、N05 预算或控制出口。
- N07–N10／N17 明确复用已有视觉定位转换、PX4 桥、action、构建与交付工具，按实际缺口修复和验证。N11–N16 正式矩阵原样保留；不把上游演示或历史 run 抵扣正式次数。
- [GOAL](../../GOAL.md)更新 N01–N06 现状与下一项描述，修正旧的“下一项 N02”；GOAL 版本和最终 A–H 字节保持不变。[CURRENT](../CURRENT.md)同步规划入口和唯一下一子项 N06.3，保留 #093 原始结果；将落后的固定膨胀数值改为引用唯一配置。
- [milestones](../milestones.json)只更新 `execution_plan.revision` 与 `implementation_review` 元数据；N／P／S 状态、依赖、证据、`next_goal=N06` 和 goal checklist 不变。

## 核对依据与局限

上游源码沿用前轮已下载并审阅的提交 `23a8d5a191711dd65633df689bd00f55d4dea8f9`，本轮再次核对固定构建配置；来源与主要文件链接已落在执行书。其五个核心包已经被本项目使用，无需再次迁入；源码存在不能代替运行验收。

本地依据为 N01 #083、N02 #089、N03 #090、N04 #091、N05 #092、N06 #093 的原证据报告、当前里程碑、依赖清单和机体配置。N06.3 列出的是待检验原因，不是已确认根因。合法入口仍未证明，正式仿真和全部实机出口未因本次更新而通过。

## 验证

验证类型：文档／JSON／结构和计划一致性；未运行代码测试、构建、回放、SITL 或实机。

- `python3 tools/project_status.py`：**PASS**；仍有 80 个可选历史 artifact 链接缺失提示，未新增该类提示。该结果只证明结构／设计一致，不代表构建、SITL 或飞行。
- 一次性只读 Python 比较 `/tmp/ego-plan-094-before-20261023` 与本轮文件：**PASS**。移除新增 review 元数据并恢复原 revision 后，整个 milestones 对象与修改前相同；GOAL 最终条款、goal checklist、全部原 `**出口**` 行以及 N11–N16 完整协议均未变。17 个 N 任务仍为 N01–N05 passed、N06 in_progress、N07–N17 not_started，依赖／证据与 `next_goal=N06` 未变。
- `git diff --check`：**PASS**。逐项审阅了相对修改前副本的 GOAL、CURRENT、milestones 增量；修改只落在本轮规划／状态描述。最终 `git status --short --branch` 仍保留既有 N06 代码／配置／工具改动，本轮未归入提交，也未触及它们。

用于复查的未变文本摘要 SHA-256：

| 内容与计算方式 | SHA-256 |
| --- | --- |
| GOAL.md 按 `## 最终回收标准` 分隔后的 UTF-8 正文 | `616c89b33d6970205326cdfa0abf9a8fdae688088b005d7bbc84e98f78104af2` |
| 执行书全部行首 `**出口**` 行，按原顺序用 `json.dumps(..., ensure_ascii=False)` 编码 | `b7013881d367763191d01cd115c0517a5acc9a805d46fd7082191f24eb4fcb4f` |

主文件最终 SHA-256：GOAL.md 为 `e9e06027cc482801577655999a45e4bf839aecf01f1500d43f6a90482328b92b`，执行书为 `11703e801768490c43d742667026d7ef2e2d91e5a48098f1768b48c5bbfceeef`，CURRENT 为 `4758be1b51cd182c1ebb6e437eb76f4fdde6b04e2d16c9d2d1f7ccac3af1b8c5`，milestones 为 `20646ed9106d4d24ba7a381d5a2f5da3beb509a5f03ea374f722659198665aa7`。这些是规划审阅记录，不加入 N 任务运行通过证据。

## 未解项、停止原因与下一步

未解项仍为 #093 的实际入口／保持体积 unknown、wall live query readiness、corridor live odometry 及 N06 两布局正向出口；N02／N04 历史限制和 N07–N17 尚缺验收按执行书保留。

停止原因：本轮实施规划交付完成后停止，不连带执行仿真。下一执行子项 N06.3：先复用 #092／#093 数据区分未知来源与 live readiness，再以新证据决定必要修复／观测方案；PX4、桥和控制在取得动作资格前保持不启动。本次不作运行通过结论。
