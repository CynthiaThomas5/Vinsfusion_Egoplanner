# #599 接入可选floorplan2静态房间

- 用户范围/模式：普通单项，接入NavRL floorplan2_static并保留旧room；[对话摘要](../../collaboration/dialogues/2026-10-30-599-floorplan2-integration.md)。
- 资产：固定原world字节与MIT许可、来源commit/哈希/diff空记录；不迁NavRL ROS1包或控制栈。
- 代码/配置：新增scene_config.py、scenes.json、floorplan2_spawn.json/16m_goal.json；世界合成和出生解析按scene选择；project.sh/start.sh绑定实际scene与任务、支持安全切换并复用活动场景。旧room合成字节保持。
- 验证：build ros18包PASS；project.sh test749单测+3ROS集成PASS；来源/碰撞/物理/PBR/入口状态单测；实际GUI与新房间16m绕墙飞行qualification全部7项PASS，独立驻留5.252sim秒、目标最小误差0.04290m、违规接触0、正常落地上锁/唯一控制通过。详见[证据](../evidence/floorplan2-integration-20261030-599.md)。
- 产物：progress/evidence/floorplan2-integration-20261030-599.{md,json}；artifacts/runs/gui-20261030-150047-3805409（含实际截图/路线诊断）与floorplan2-20261030-599-checks。
- 局限：一条路线、一次GUI运行，不是全迷宫或正式重复资格；纹理为本项目适配。原定位/规划/控制/阈值不改。
- 停止：限定目标完成；新场景GUI已正常落地上锁后保留供查看；无自动下一任务、提交或推送。
