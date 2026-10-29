# N08 #293 取消停止终端hold判据

## 用户约束

持续完成N08当前Goal出口；普通单目标不隐含返航。返航若需执行，用户会单独发命令，先停止EGO、原地转180°，再按机头前向EGO返回。N07已通过项不复测，速度/健康/地图/stop/landing门限不降低。

## #292结果

N05 6/6、post-release、40.0145s只读preflight与current-area N05通过。motion-cancel在0.0400 m/s触发，调用方取消结果正确；EGO生成新ID停止曲线并通过速度、reference tube、raw-map证书。独立真值测得cancel-stop距离0.2985m、实际峰值速度0.0879m/s、最大跟踪误差0.0913m；PX4速度样本显示停住并低速保持。run最终仍FAIL：runner等`COMPLETED`，但traj_server在末端保持位置/零导数时仍发布READY，超时后operator-disable，未完成native 3秒hold出口和stop后landing。

另修正离线evaluator对cancel action status/outcome/reason字段的混淆。354项仓库测试和8项snapshot专项通过。下一步新冷启动#293实测修复后的终点判定、3秒hold与stop后landing。N08保持in_progress。
