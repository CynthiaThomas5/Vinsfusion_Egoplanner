# N10.3/#444：真实瞬时物理状态只读链路

新增自维护 uav_debug_truth Gazebo system：每物理步读取 canonical link 的真实世界速度，通过 SDK 点变换得到模型原点速度；只发布 /debug_truth/model_kinematics，无控制/力/速度命令。可选运行内模型overlay仅给最终wrapper增加该插件，不改变机体碰撞和安装。D435I_N10_KINEMATICS=1 经 project.sh 透传并启用overlay/JSONL记录，默认关闭；缺字段/错误只令离线证据不足，不新增拒飞分支。

记录器检查明确元数据、有限值、单位四元数；离线读取核对完整run/goal/epoch/map/runtime身份、ledger SHA、插件binary/source与runtime-contract、记录数/顺序、每个所需物理步、与原truth同戳同点位姿。旧OdometryPublisher平滑twist只保留诊断，不能通过连续区间验收。正确瞬时记录且原模型/接触/正下界全部通过，才允许 interval_bound_verified=true；着陆接触仍分开。

验证：bash tools/project.sh build ros，18包通过；bash tools/project.sh test，581单元+2 ROS集成通过；实际安装插件自由落体500个连续4ms状态通过（旋转且偏置canonical link）；实际x500 wrapper无动力/无PX4测试250个瞬时状态，249个与旧truth同戳位姿完全一致。结构检查、py_compile、bash -n、git diff --check通过。初次宿主py_compile遇容器所有权cache权限，改用独立/tmp pycache后通过，未修改权限。

产物：artifacts/n10-prepared/n10-20261028-444-kinematics-observer-prototype、n10-20261028-444-installed-observer-smoke、n10-20261028-444-x500-reference-smoke。源码src/own/uav_debug_truth、tools/debug_truth/kinematics_evidence.py及相关记录/评估/启动工具。测试明确不是导航飞行或N10.5干净重建。

本子项实现/物理smoke完成，正常飞行ledger尚待与下一次综合校准合并采集，未把旧数据变成已验证连续净空。运动RPE仍未达原0.05m；父N10/N10.3保持in_progress。下一#445只改离线gyr_w，依据理想IMU无随机游走而估计gyro bias显著；保留#442 gyr_n候选，其余固定，仍不部署。

后续链路复核：总判断器也已接入区间报告，核对生成器SHA、8项原始输入SHA与瞬时ledger SHA；仅离散样本PASS不再误判完整净空PASS，缺区间界为不足，原直接碰撞失败保留。acceptance草案revision5只修离线判断语义，原0.10m净空、0.05m RPE、0.01m/s hold数值及故障排除不变。新增测试覆盖缺界、ledger变更、区间低于原阈值和直接碰撞保留。

最终复核：582单元+2 ROS集成全部通过，日志project-tests-final-r02.log；首次全量检查发现旧reference fixture未包含新必需interval报告，补齐fixture后重跑通过，不改判据。

旋转补充验证：真实安装库在旋转/偏置canonical link的刚体夹具500个连续4ms状态全部通过；由独立SDF ApplyLinkWrench持久力矩激励，非UAV。模型原点world速度+omega叉乘lever与解析质心自由落体速度最大差1.14e-13m/s，角速度与力矩/各向同性惯量最大差1.03e-15rad/s，旋转参考点速度差峰值0.04914m/s。补足原零角速freefall未充分激励的lever项，见artifacts/n10-prepared/n10-20261028-444-rotating-offset-smoke。
