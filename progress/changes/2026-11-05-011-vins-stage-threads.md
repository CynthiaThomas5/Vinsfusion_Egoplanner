# HW10-STAGE-011 / 010.2

实际修改：硬件vins_hardware.json OpenCV线程1→2；既有参数传递测试期望更新；新增仅硬件诊断补丁/精确基准说明，未加入SITL默认补丁。原vendor与安装binary已恢复，永久数值算法/门限/固件无修改。

原生构建、五阶段计时与两组120s地面比较完成，跟踪中位116.446→82.220ms，估计3.989→5.454Hz。再用原版binary/2线程新epoch地面120s回归，优化接收约5.495Hz、最大332ms，无测量窗口内锁定。更多CPU消耗与全链路效果须后续验证；未发EV/控制。

验证：原链接基线逐字节复现；主机/ARM rig测试各4项，主机会话测试5项，源安装16项一致，脚本编译/patch dry-run/project_status/diff检查通过。原始大对象保留Nano同名artifacts，轻量证据已同步。

[报告](../evidence/hw10-stage-20261105-011.md)；[对话](../../collaboration/dialogues/2026-11-05-011-vins-stage-threads.md)。停止原因：本轮子项完成；下一010.3两线程EV/EKF集成回归，不提高门限、不直接改固件。自有进程全停，Agent保留，无提交/推送。
