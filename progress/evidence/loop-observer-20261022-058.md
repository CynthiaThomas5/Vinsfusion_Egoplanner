# VINS 回环后端：单会话观察接入

本次小目标完成：接通真实关键帧、稀疏特征与位姿图；**尚未验证实际回环、漂移修正或地图复用**。

[机器可读证据](loop-observer-20261022-058.json)／[修改与失败记录](../changes/2026-10-22-058-loop-observer.md)。

## 最终版本的一次冷启动

gpu4090，`loop-observer-20261022-058-04`。按最终可重建依赖清单，从新容器、新PX4可变状态和新VINS epoch执行当前room相对16m任务；同时运行独立观察后端。任务退出0、原有9项检查全部通过、正常落地上锁，后端SIGINT退出0，随后仿真正常关闭，当前无运行中的项目会话。

| 项目 | 本次测量 |
| --- | --- |
| 图节点 | 67个关键帧 |
| 顺序连接 | 258条可视化顺序边，对应同序列近邻 |
| 图覆盖位置跨度 | X 15.74m，Y 1.44m，Z 1.98m |
| 稀疏特征数量 | 单关键帧最多122个，最后一帧29个 |
| 图像／关键帧配对最大源时间差 | 1ns |
| 几何验证回环／优化次数 | **0／0**；地点候选也是0 |
| 原始／修正位置同源比较 | 1831对，差异最大0m，符合无回环时应无全局修正 |
| 后端队列上限／关键帧上限 | 每路64／1000，记录均在上限内 |
| x86服务器后端进程峰值RSS | 469.11MiB；不是Nano测量 |
| x86平均CPU（100%=一个核） | 1.66%；不包含另行部署性能承诺 |

![实际后端输出的位姿图与当前关键帧特征](../../artifacts/runs/loop-observer-20261022-058-04/loop-graph.png)

蓝色为后端真实关键帧／顺序连接；黄色为**最后一个关键帧**的特征点XY投影，不能视为完整三维环境地图。观察器虽具备回环检测与优化代码，本次单向路线没有建立经过验证的回环边，因此不宣称优化降低了漂移。

## 接口与隔离

- 同一锁定 `zinuok/VINS-Fusion-ROS2` commit `72023bc5d2abb14faa4c02a5c040d84f996b587a`，GPL-3.0；不添加第二份VINS。保留KeyFrame／DBoW／PnP及数值优化，改动由0015补丁记录。
- 输入为当前epoch的原始VINS odometry、keyframe_pose、keyframe_point和D435i左图；原始文件／模型／设置均核验哈希。当前分支的 `pubTF()` 提前return，没有实际extrinsic消息；固定外参从同一份session配置读取，要求 `estimate_extrinsic=0`，若消息出现则额外验证一致性。
- 输出只在 `/loop_observer/s_0a7e0aab843a4eda8b2f7c7c176ec132`，frame为 `loop_0a7e0aab843a4eda8b2f7c7c176ec132_map`。运行期发现图确认没有控制／TF发布、没有真值订阅；所有PX4控制仍为唯一bridge。
- 对比#057，已有源码／配置及安装二进制哈希都未改变；仅依赖清单变更，新增loop配置、RViz预设和loop节点二进制。新的运行合同为 `9d14860aa693d92bcacdcbed364aecc9e3adfcadfed2573dc8df2375b973481f`。
- 最终节点二进制SHA256：`d2f7cbc3b12bb5800a9a2813a609ec9ca0cbf7aa4f6b875b6492ddc108ec93b2`，与最终隔离探针一致。固定镜像未变，不需要安装新库。
- 启动入口：`bash tools/project.sh loop RUN_ID`，可选且不自动起飞；默认start／fly不增加此负载。操作和独立RViz预设见[运行文档](../../docs/running.md)。本轮验证了预设生成／YAML和实际消息绘图，没有验证真实RViz界面渲染。

## 分开的验证证据

- **源码重建**：实际运行 `python3 tools/fetch_dependencies.py --source vins_fusion --target artifacts/runs/loop-backend-20261022-058-fetch-check`，完整固定上游和补丁顺序应用成功，222个文件与canonical vendor逐字节一致；28个KeyFrame／DBoW等算法文件与原始上游完全相同。GPL许可文件及BRIEF资源哈希已校验。
- **构建**：固定容器中实际构建17个ROS包。最终runtime构建见checks/build-05.log，退出0；最后的补丁基准修正只改变重建描述，不改变源码或二进制；最终清单另经04冷启动验证。
- **单元与ROS集成**：最终 `bash tools/project.sh test` 退出0，157项回归＋真实action／250Hz clock测试通过，最大pose接收龄0.054s。新增配置／隔离检查单元不是SITL证据。
- **隔离的合成传输探针**：ROS_DOMAIN_ID=185，与项目84分离，真实已编译节点验证有界图像缓存、时间倒退及错误frame退出2、正常SIGINT退出0；没有控制或SLAM精度证据的含义。
- **SITL／真实记录离线分析**：04原导航9项与后端15项观察检查全部通过；03诊断轮也得到65节点／250顺序边。图形和后端检查均读取真实ROS记录，不造特征或路径。
- **失败保留**：01导航成功但外参话题等待导致图节点0；02起飞前telemetry_stale，未解锁、未发目标；03成功后补齐可重建清单，04以最终清单复测成功。不能把这些结果描述为四连稳定通过。详见changes与checks/run-summary.json。

原始消息、图形、报告：[最终run](../../artifacts/runs/loop-observer-20261022-058-04/)；[检查与失败日志](../../artifacts/runs/loop-backend-20261022-058-checks/)；逐文件哈希见其中artifact-sha256.json。ULog保留服务器，路径／哈希在execution-results.json。

## 未完成与下一小点

没有回环边，尚未执行实际图优化；没有返回旧视角、地图保存／重定位、map→odom接入、5分钟、Nano或实机验证。初始化前十个配对沿用上游warmup；stationary时淘汰旧图像缓存不等于丢失已入图关键帧。当前输出云只包含当前关键帧特征，没有对完整历史地标做全局重建。

02的遥测交付空窗说明冷启动仍有敏感性；让记录器随栈早启动后03／04成功，仅是观测，不能作为根因已经修复的证据。健康门未放宽，故障后没有清锁或拼接epoch。正式P0–P6／A–H状态不升级。

建议下一小点在同一room设计一次回到已观察区域、视角相近的短往返，仍只旁路观察，核验一次真正的回环边和修正量；本轮到此为止。
