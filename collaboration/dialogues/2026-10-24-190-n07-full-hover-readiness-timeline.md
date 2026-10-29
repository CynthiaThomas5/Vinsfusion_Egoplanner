# N07 #190 对话摘要：覆盖释放到hover结果的定位时间线

## 约束

- 继续已授权的N07 Goal完成模式，要求3次连续独立cold start通过。
- 镜像、runtime、spawn、布局、separated-return profile和健康/N05阈值固定；定位失效时不解锁、不飞。

## 下一项

#189 N05三组online/offline通过、14/14总结通过，但probe在sim480.992结束后，bridge于sim555.724进入`external_odometry_stale`，hover前置失败`propagated_stale`。#190按相同profile与门限运行，probe覆盖到`flight.json`后2.039秒；N05 14/14，30秒no-goal hover、EV/no-GNSS ULog与独立误差测量通过。原 evaluator 为10/11：pre-enable graph 快照四个控制话题均为0 publisher，空中及结束快照则均为单一`uav_px4_bridge` publisher；按全快照严格规则，N07仍0/3。Fixture helper报告扫描期间定位失效，但最终状态恢复valid、12/12、释放后门通过、支架移除且PX4 landed/disarmed。

下一项#191保持运行与控制条件不变，只在bridge ACTIVE且armed之后启动未修改的只读ROS graph recorder，避免记录尚未建立publisher的pre-enable窗口；仍用原hover evaluator、ULog analyzer和 N05 门限判定。
