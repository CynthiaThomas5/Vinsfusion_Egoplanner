# N08 #295：same-stamp certified handoff evaluator fix

## #294回放

修正旧/new轨迹同一source stamp的解释后，对#294原始flight、truth和odometry做只读独立重放，35项检查全部通过。实测cancel-to-stop行程0.30992m、响应2.852s、最大独立跟踪误差0.09020m；runner原生记录PX4速度门连续3秒且bridge ACTIVE。final destination candidate接受，认证停稳后发landing command，独立读回LANDED/disarmed、控制消息0，容器停止。

差异透明保留：#294当时锁定的离线evaluator SHA为旧版本；重放使用的是修正后的新SHA。运动runner和原始输入未改变。新报告明确记录两种SHA；原始evaluator FAIL也保留。修改只影响离线对已认证same-stamp样条交接的解释，不放宽数值门限。

## 下一步

359项全仓测试与navigation-adapter integration通过。继续审计固定hold、compute-only和execute的历史证据；整合三次历史正常制动与两次取消制动测量，确定只由证据支持的范围和N05/N06消费参数；随后按冻结版本跑三次独立terminal_stop。N08仍in_progress。
