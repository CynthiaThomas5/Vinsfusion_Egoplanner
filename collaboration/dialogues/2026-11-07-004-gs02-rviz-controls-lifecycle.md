# GS02.3 静止 RViz 控件与生命周期检查

## 用户约束

用户说将外出，希望先完成不需要本人辅助的工作，回来后再继续；本轮不要求或假定用户移动设备。保持无武装、无飞行、无EV/控制、无PX4固件/参数修改。

## 本轮决定与结果

继续已授权的GS02 Goal，在现有Debian固定入口做静止RViz视点操作、重复启动拒绝和停止归属检查。旋转/平移/缩放均观察到3D视口像素变化；第二次启动被拒绝；stop-view后计算会话保留且relays异步退出，随后experiment-stop正常停机。Nano服务microxrce-agent.service仍active于CH340/TELEM1。原始数据与指标见[证据](../../progress/evidence/gs02-rviz-controls-lifecycle-20261107.md)。

## 待用户回来

运动期屏幕是否卡顿仍未观察，且此前动态reader长滞后根因未明。用户回来后再做短动态捕获并实时观察屏幕；在该证据完成前，GS02.3和GS02继续保持未完成。

## 迁移复核

新增overlay含196个唯一文件，已同步到Debian固定入口；release 380项校验、目标结构检查和地面站check/status通过。旧overlay包元数据已备份。设备会话保持停止状态。

## 上下文一致性

复核时发现Debian接续页把静止paint描述为未测，已同步修正接续页和操作手册，明确静止绘制已验证、运动期连续性仍待用户观察。
