# N08 取消停车目标参考锚点

## 项目任务摘要

按用户授权的 N08 Goal 完成模式继续单 D435i 仿真验收。普通单目标到达后停止并结束；返航仅在用户另发第二段命令时进行。N07通过结果不复测。

## 用户约束与决定

- 运动取消前在同一冷启动完成N05全机支架扫描、夹具移除和释放后准入。
- #288保持失败：其N05、preflight、current-area和前向地图门通过，caller cancel被正确请求，但EGO三次以局部目标距离低于固定0.2m拒绝停止轨迹。
- 失败由取消时EGO参考点比PX4实际位置前进约5.9cm导致：按实际位置生成的0.246m停车目标，从EGO当前参考起点看只有约0.187m。
- 0047仅把停车目标锚定到取消时活动EGO样条的参考位置。停车距离公式、速度界、地图／完整曲线／terminal-hold证书和既有故障安全行为保持。参考样条无效就fail-safe abort。

## 当前状态与待办

#0047 ROS 17包构建、348项单测和navigation-adapter integration通过。当前#289须以全新冷启动重做同一N05前置流程，并验证stop spline生成和认证、旧轨迹不再输出、PX4真实停车／保持、终点landing准入及最终disarmed/landed。之后继续hold／compute-only／execute因果对照、N05/N06预算回填和同一冻结版本的三次独立terminal-stop通过。N08仍未完成。


## #289前置结果

全新N05扫描在阶段3/6回程触发既有`accel_bias_norm_exceeded`=0.150019（门限0.15）；未完成夹具释放后准入，因此没有N08任务。夹具已移除、PX4 landed/disarmed、bridge DISABLED、独立读回的3类控制消息均为0，容器已停止。与#288同profile最大bias 0.090592相比，本次VINS bias在outbound和return持续升高；原因未归因，门限不改。下一步#290只换fresh VINS epoch重复原profile；通过N05后才继续取消停车测试。
