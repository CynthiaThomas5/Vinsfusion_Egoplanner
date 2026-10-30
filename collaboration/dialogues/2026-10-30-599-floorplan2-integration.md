# #599 接入NavRL floorplan2静态房间

用户在#598只读选型后明确要求接入floorplan2_static。决定添加可选场景并保留原room；采用NavRL固定commit3725bcc2e7c1be4ecf1455d922299ae85042603a原始world与子包MIT许可，只迁静态几何。保持250级D435i/VINS/EGO/PX4及唯一控制链，不使用NavRL机器人/策略/真值/PCD。场景绑定世界、出生点和任务；先测试(-8,-8)到(+8,-8)16m绕墙路线，自动降落后保留GUI查看。

实际只有一个候选、一次导航飞行，独立到达/零违规接触/正常终态等全部通过；未将其算作正式多场景资格。本摘要不是通过证据，见progress/evidence/floorplan2-integration-20261030-599.md。无提交/推送。
