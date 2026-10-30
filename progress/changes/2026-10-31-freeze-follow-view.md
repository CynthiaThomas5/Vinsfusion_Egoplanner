# 保存当前代码与冻结跟随视角

[对话](../../collaboration/dialogues/2026-10-31-freeze-follow-view.md)。

本地保存当前Quad250代码、显示TF/跟随RViz配置、左下外侧(-14,-9)到右上(9,9)航线和60×40×6m地图参数。冻结RViz ThirdPersonFollower、6m、Pitch0.6、Yawπ、零焦点偏移，继续按epoch绑定显示帧。

验证沿用当前相同实现的18包构建、5项显示回归、实际GUI TF回读和两次导航实验；本轮不重复飞行。两次独立到达驻留不足保持FAIL，不将保存快照视为新验收通过。结构检查与git diff --check另执行。

本地分支quad250-follow-2026-10-31，固定标签sim-nav-quad250-follow-2026-10-31；不推送。原始日志仍在此前记录的/tmp独立clone，源码提交不含vendor/build/install/运行大日志或机器凭据。
