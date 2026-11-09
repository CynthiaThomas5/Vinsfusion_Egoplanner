# HW10-EV-027

生产源码/固件/默认阈值未改。增加run-local高度参考参数维护/重启与外层恢复、动作标记/高度分析，补docs/hardware-running.md说明已验证基准和当前回退状态，更新CURRENT/milestones。HGT_REF1→3是唯一主要估计器变量，EV/MAG临时设置与026相同；其他源/噪声保留。首次重连失败留存，修正等待真实USB cycle及app by-id、3类模拟状态通过后继续同一候选。

实测10cm升降与返回：EV10.09/PX4local9.98cm、返回残差2.5/3.5mm；408条三路aid全部融合、无拒绝/丢日志；未给完整动态/飞行资格。原参数与参考1已恢复保存/重启，最终1095项零差异/无owned进程，023/024修复保留。

[具体命令/证据/局限/终态/下一项028](../evidence/hw10-ev-height-20261105-027.md)、[对话摘要](../../collaboration/dialogues/2026-11-05-027-height-reference.md)。停止原因：有界检验与恢复完成；未提交/推送。
