# N07 #173：缩短斜视暴露的路线复核

## 用户约束

- Goal完成模式，范围N07，持续至N07全部出口通过。
- 不放宽VINS健康门或N05准入条件；初始raw unknown拒绝不能绕过。
- 使用PX4 SITL；N05 released gate未通过前不解锁、不做悬停。

## 证据与本项决定

#166/#171/#172在同一full-airframe `oblique_early_view` route第7段返程时触发`accel_bias_norm_exceeded`；#165/#167/#168/#170同route完成。stage6 pitch归零期间bias先增长，失败运行随后在stage7越过0.15 m/s²。历史`oblique_separated_return`减少长时斜视，在wall #138（旧相机安装坐标）和corridor #148均完成12/12且bias低于0.09；#138 N05 raw-ground拒绝发生在#142模型坐标修复之前。

#173固定版本、wall world、spawn、门限和gate流程，仅改用已存在的`n06_full_airframe_retreat_240_oblique_separated_return` profile。记录完整VINS bias时序；只有fresh release N05 online/offline一致接受后才进入N07 hover。

## 结果

短斜视profile完成12/12，bias峰值0.083839，没有复现#171/#172的0.15越线。初始N05拒绝raw unknown。attached及post-release gate都因缺少adapted `odom`超时；localization锁存`telemetry_stale`。之后raw VINS telemetry/odometry恢复到当前clock附近，但adapter仍锁在旧source stamp 386.136，bridge DISABLED。支架确认拆除、PX4 DISARMED/landed，容器exit0；没有hover，计数0/3。详见`progress/evidence/n07-support-scan-telemetry-stale-20261024-173.md`。

下一步#174沿用短斜视路线，用已有只读stream probe全程记录raw telemetry、raw/adapted odometry、localization status和clock，区分上游topic gap与adapter侧停止发布；不调健康门。只有attached/released gates fresh通过才可继续悬停。
