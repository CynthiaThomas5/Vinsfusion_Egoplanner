# N10.3/#435：实际应用inflation halo/索引修复

在用户#434取消当前故障校准、停止#428仿真后，核对本项目无活动容器，将#431/#432已验证的候选注册为dependencies/patches/ego/0060-inflation-source-halo-and-bounds.patch。

## 来源与行为

基准ego-planner-swarm 23a8d5a191711dd65633df689bd00f55d4dea8f9，在0059后、upstream/src目录以-p1应用，GPL-3.0-only。主源码应用前SHA与#431记录一致；dry-run/apply成功，应用后完整grid_map.cpp SHA与#432隔离真实包候选一致。sources.json登记补丁顺序、上下文、补丁SHA和最终源码SHA；README说明基准及行为。

清空local_bound内inflation后，扩展inf_step读取raw occupied source halo，避免框外来源漏膨胀；在flat address计算前拒绝逐轴越界目标，避免错误跨轴标记。没有改变raw occupied/free/unknown规则、inflation值、trajectory或控制发布者。

## 验证

- bash tools/project.sh build ros：17包成功，约50.4秒；现有plan_env deprecated ConstPtr警告保留。属于增量构建，不代替N10.5。
- 用#432的真实GridMap fixture二进制加载当前/workspace/install/plan_env/lib/libplan_env.so，ldd核验路径；10案例全部通过、exit0。
- PYTHONPATH=tools python3 -m unittest tools.test_n10_acceptance tools.test_official_ego_policy tools.test_n10_occupancy_snapshot tools.test_n10_voxel_trace -q：42项通过（包含#434范围变化测试）。
- patch/source hash锁核验通过；正常SITL尚未执行，不能声明导航碰撞已解决。

产物：artifacts/n10-prepared/n10-20261028-435-map-inflation-repair/applied-manifest.json、ros-build.log、ldd.log、actual-library-test.log。主库SHA、补丁SHA及前后source SHA在manifest。

## 下一步与范围

#436只执行正常导航校准：核对当前source/install/config身份，纠正观察器协议/实际柱ROI记录，完整采集地图、参考/实际轨迹、VIO、净空、资源并做离线判断；不再新增故障注入或等待事故后原生终态来完成故障校准。正常飞行失败/接触仍记录FAIL，未验证部分仍不足。N10.3保持未完成。
