# N07 #189 对话摘要：释放后定位健康时间线

## 约束

- 在用户授权的N07 Goal完成范围内继续，累计3次连续cold start通过。
- #188的镜像/runtime、spawn、wall layout、separated-return profile及全部健康/N05门限固定。
- 健康或准入失败时不解锁、不飞；保留原始失败状态并安全停止。

## 结果与下一项

#189三组N05 gate online/offline都接受，14/14 summary通过。ready marker后启动的只读probe在N05 current-area结束时停止，窗口内LocalizationStatus仍valid；之后no-goal hover前置失败`vio_bridge_map_preconditions_not_ready`，状态时间线记录bridge `external_odometry_stale`于sim 555.724，定位state4 `propagated_stale`。没有service call、解锁或起飞，PX4保持DISARMED/landed，容器exit0；N07仍0/3。详见[证据报告](../../progress/evidence/n07-postscan-propagated-stale-20261024-189.md)。

#190沿用同profile、门限和runtime；唯一诊断变量是把只读freshness probe结束标记延长到`flight.json`生成后，并在N05 summary 14/14完成后立即运行既有hover probe，覆盖失效发生的前置等待阶段。
