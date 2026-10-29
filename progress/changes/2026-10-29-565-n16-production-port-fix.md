# N16 #563失败及#564–565修正

#563 GUI正式尝试在起飞初段38.680sim秒VINS exit -11，未派发首个导航目标。完整325秒任务未完成，不计合格。输入超时后桥接器按原有PX4 EV行为进入LANDING，最终LANDED/disarmed/control disabled；独立15秒观察中稳定12.234秒，零控制、无终态违反。无需紧急disarm。safe-to-stop全部检查通过后停止本项目容器，raw及stack已归档artifacts/runs/n16-20261029-563-formal02。

根因：#561生产移植遗漏三个边缘化尺寸处理点：线程Hessian两个9维block仍使用全局9维，而标定模式切空间为6维；先验Evaluate的dx也仍复制9维。属于移植错误；#560成功离线实现已正确处理。保留#561/#563源码、构建和失败，不以离线成功覆盖。

#564在独立候选/home/huangxiaocheng/n16-20261029-564-gyro-fixed/project修正三个点；完整marginalization_factor.cpp逐字节等于成功离线版本。其余生产控制/参数不变。真实colcon vins构建PASS 54.9s；新增外部测试直接链接这次实际生产libvins_lib.a，验证默认关闭及gyro-only模式的完整边缘化/求解和自由速度、自由加速度偏置、固定gyro，PASS。测试调用方启用Eigen边界断言，实际生产库为Release；不能夸称整个生产库已启用断言。

#565重建源锁补丁0022并重新冻结运行身份1c300ba6d00ff7deb7c515081ece6437971dafae91efc796dcc685252da7bb9b，协议/阈值仍300sim秒、独立0.3m/15度/3秒。#566独立GUI冷启动正式第三次尝试已启动，结果待验证。启动器第一次因候选artifacts/runs父目录不存在而在Docker启动前失败，建父目录后启动，不是额外飞行。

产物artifacts/runs/n16-20261029-564-port-fix含corrected-production.patch、source-provenance.json、build.log、production-math-test.log和测试源码；artifacts/runs/n16-20261029-565-release含冻结身份、协议和启动器。N16 in_progress，已完成正式尝试2，合格0，当前#566未结束。停止原因：未停止Goal，继续正式验证。下一步完整归档、诊断曲线与逐项审计。

对话：collaboration/dialogues/2026-10-29-562-n16-zero-gyro-release.md
