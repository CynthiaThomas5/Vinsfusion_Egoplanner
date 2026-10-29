# #336 N10.3 长航程校准协议

建立 N10.3 唯一主要变量协议：扩展任务距离／时间范围，固定 single-D435i official_ego、PX4 bridge 与低速 EGO 输入。明确 16 m 单程、3 sim-s dwell、600 sim-s active hold、独立真值判据、超时及异常落地条件。

验证：profile JSON、Python 编译、Bash 语法和 `git diff --check` 通过。该检查只验证运行输入与脚本结构；校准飞行尚未执行。

产物：[N10.3 校准协议](../evidence/n10-independent-calibration-protocol-20261026-336.md)。
