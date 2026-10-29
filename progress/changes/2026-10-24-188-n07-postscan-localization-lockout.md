# N07.34 #188：separated-return通过attached gate后释放阶段定位失效

## 执行模式与范围

Goal完成模式；用户指定范围N07。复用#180/#182用过的 `n06_full_airframe_retreat_240_oblique_separated_return`，固定镜像、runtime contract、spawn、wall layout、悬停程序及所有健康/N05门限，不改变源码或配置。新run为 `n07-20261024-188-01`，N07连续计数从0/3开始。

## 实际结果

初始N05 online/offline一致拒绝起点raw unknown。支架完成12/12，marker字段和身份有效；2.0秒attached settle后online N05接受，offline replay匹配，三项freshness均≤0.4秒。释放时helper原样报错 `fresh DISARMED status is required for every fixture command`。独立读取PX4 DISARMED、landed及Gazebo fixture不存在，但定位已经锁存 `telemetry_stale` / bridge `localization_not_tracking`，故没有运行post-release/current-area checks或任何飞行命令。

失效后12秒只读stream probe显示相机、IMU、VINS raw telemetry、odometry在观察窗持续新鲜；该窗口晚于健康锁存，不能归因触发流。该不确定性作为#189的诊断目标，健康门维持原值。容器经 `bash tools/project.sh stop n07-20261024-188-01` 后exit0，无活动本轮容器。完整数值与哈希见[证据报告](../evidence/n07-preflight-postscan-localization-failure-20261024-188.md)。

## 后续

连续计数为0/3。#189继续同profile、同镜像/runtime和阈值；在ready marker后即启动只读freshness时间线，贯穿释放与post-release/current-area决策，减少定位失效触发时刻未覆盖的问题。健康或准入不通过继续fail-closed，不发送飞行命令。
