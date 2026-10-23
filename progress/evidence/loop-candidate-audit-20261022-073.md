# #073：回环候选到几何验证的只读审计

**结论：运行数据把通过率差异定位到候选后的`findConnection()`几何连接验证；缺少逐候选诊断，无法确认内部具体失败条件。**

## 对照结果

| 运行 | 关键帧 | 候选数 | 通过验证 | 未通过验证 | 验证成功帧 |
|---|---:|---:|---:|---:|---|
| 070-02 | 94 | 43 | 2 | 41 | KF74→旧KF7；KF80→旧KF0 |
| 072-01 | 94 | 43 | 1 | 42 | KF57→旧KF0 |

两个运行都在当前KF51–93各产生43次候选计数。stage文件中的47段标签、cycle和目标序列相同。070-02两次成功分别出现在cycle 6 inbound和cycle 7 outbound；072只有cycle 5 inbound一次成功。它们不是同一关键帧／同一轮次上的确定性复现。

补丁`dependencies/patches/vins/0015-loop-observer-transport.patch`的计数点为：`loop_index != -1`时先增加`loop_candidates`，再调用`cur_kf->findConnection(old_kf)`；仅调用返回true后增加`verified_loops`并进入后续回环边处理。因此两轮候选提出数一致、验证接受数不同，门级差异可以由计数位置确定。补丁README说明BRIEF、PnP等数值算法沿用固定上游实现，未在本轮修改。

## 对照完整性与证据缺口

两轮`runtime-contract.json` SHA均为`6a5ce037e496ecd58fd298440462257a5650fa0ff021bd883085e42c8b370cdb`；observer executable、配置摘要、依赖摘要、BRIEF资源、参数限制和`session.settings_sha256`相同。epoch专属session文件哈希集合不同，故本报告不称所有run文件逐字节相同。评估器对两轮均报告相机曝光一致和队列有界；loop status最大image/pose gap为1ns、`dropped_sync=0`。现有数据没有候选丢失或同步空窗的迹象。

`loop-observation.status`只保存keyframe、candidate、verified、optimization计数、队列／同步计数和最大配对间隙；graph快照保留通过后的关键帧约束，但不保留失败候选的旧帧索引或内部几何统计。因此目前能确认失败返回发生于`findConnection()`这一步，不能进一步说是BRIEF匹配不足、PnP/RANSAC内点不足、重投影门限或其他具体原因。点云中的每帧点数不是BRIEF内点或PnP内点。

只做了记录解析、counter转变重算、SHA-256核对及stage映射；未启动仿真，未做构建／回归，未改任何源文件或参数。此审计不证明更广场景的回环鲁棒性，也不改变072的误差比较结论。

可复核的机器报告见[JSON证据](loop-candidate-audit-20261022-073.json)；原始文件位于`artifacts/runs/real-loop-20261022-070-02/`和`artifacts/runs/real-loop-20261022-072-01/`。建议下一目标为新增只读候选几何验证统计并fresh epoch复测；批准前不实施。
