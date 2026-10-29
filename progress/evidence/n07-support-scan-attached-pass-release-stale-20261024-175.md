# N07 #175：12/12 支架与 attached gate 通过，release 后 odom stale

## 结论

#175沿用分离返回路线且不启动额外高频probe，完成12/12全机支架扫描；VINS normalized-cost峰值0.83558、accel-bias峰值0.095803 m/s²，未触发现有健康门。attached N05 online/offline gate均fresh通过，原因`all_entry_phases_known_and_clear`，epoch/map identity一致。

fixture移除后定位锁存`telemetry_stale`，post-release N05 live check因缺少optimized odom超时；没有release gate正向结果、解锁、飞行或hover。N07连续合格数保持0/3。该结果说明#174的pitch代价尖峰并非每次都复现，但不能证明额外probe是其原因；本次随后又出现与#173相似的adapter odometry缺失。

## 运行身份与支架结果

- Run `n07-20261024-175-01`，epoch `20dbae9ad0404377bb577bda2e776ed5`；镜像 SHA-256 `099ab9afecd28b7354f6d6494944b1db30c7c67c973e9b93b03f87aca7ad6f8`，runtime contract SHA-256 `856bf1f2222a5286493813c9702731f7e5166844eb2bfd98c6f525f3f36924eb`。
- `wall_box_column`，spawn `-6.5,0,0.3,0,0,0`，profile `n06_full_airframe_retreat_240_oblique_separated_return`；#175相对#174只移除全程额外read-only stream probe。健康阈值和N05 gates未改。
- 初始N05 online/offline一致拒绝`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；全程没有以此拒绝为由绕过入口。
- 支架12/12阶段完成，ready marker确认attached、无truth输入、无control/goal发布。fixture记录bias最大0.09580297 m/s²、normalized cost最大0.835579；末次fixture localization仍TRACKING/valid。
- attached gate fresh接受`all_entry_phases_known_and_clear`，online与offline一致。attached快照、扫描身份和map identity为同一epoch/map。

## release后失败与安全回读

runner在fixture已经发出detach、Gazebo remove service请求后，因最后的`step()`缺少fresh DISARMED status，以`fresh DISARMED status is required for every fixture command`结束；它记录12/12、`attachment_states=[attached,detached]`、模型不存在、`fixture_may_remain_attached=false`、landed=true和vehicle state `[1]`，但自身`verified_detached=false`。独立回读随后确认场景中没有`preflight_scan_fixture`，PX4 fresh arming state为1、landed=true，bridge `DISABLED`、`armed=false`、`control_enabled=false`。据此只运行了只读post-release检查并安全停止。

post-release检查超时：`missing=['odom']`，已收到bridge、clock、localization和map。回读中的localization status为state 4、`telemetry_stale`，source stamp 435.304s，而status header/clock为606.676s；随后raw VINS telemetry和raw odometry单次只读样本更新到stamp约620.272/620.932s，optimized odom仍无输出。raw源恢复不能解锁adapter或替代fresh N05 release admission，因此不飞。

支架runner自身记录到约sim399.104–401.876s的2.772s telemetry/source gap；由于该记录器的最后样本为sim402.736s，而adapter status之后仍更新至source435.304s，现有记录不能判断这段gap是否被adapter接收，也不能定位`telemetry_stale`的首个输入缺口。post-release单次raw回读只说明读取时raw话题新鲜。

`n05-run-summary.json`的`diagnostic_pass=true`仅表示该辅助报告的支架/地图诊断数据齐全；同一报告中`post_release_entry_accepted=false`。N07所需的release准入及飞行验收仍未通过。

容器按项目stop流程退出码0，无活动项目容器。健康门、N05门与地图/控制配置均未修改。原始数据和SHA-256见同名JSON及`artifacts/runs/n07-20261024-175-01/`。
