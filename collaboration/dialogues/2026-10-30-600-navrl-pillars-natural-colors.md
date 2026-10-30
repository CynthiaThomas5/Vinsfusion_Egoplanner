# #600 多柱场景与自然材质

- 用户先要求接入NavRL `floorplan2_static`，随后明确改为“很多柱子那个”，并希望更换world颜色。
- 本轮范围：选用NavRL generated_env_static，沿用其他场景切换方式；柱体视觉与真实碰撞匹配；新建非棋盘格浅暖色地面材质与自然色柱身；启动GUI供查看并验证16m任务。
- NavRL来源固定commit `3725bcc2e7c1be4ecf1455d922299ae85042603a`。用户原本希望的原始world字节保持；该world的60根柱子只有visual，本项目运行时按其box/cylinder geometry生成碰撞体。
- 当前GUI run：`gui-20261030-154042-3829973`。其它已确认场景仍可选：room/floorplan2/pillars。
- 材质由image_gen生成，完整提示词、文件hash保存在 `simulation/textures/natural_terrazzo.json`。

- 最终结果：18包构建、751单测+3项ROS集成PASS；pillar GUI的16m任务7项日常qualification通过，位置误差0.04796m、违规接触0、正常落地上锁。正式资格计数仍为false。GUI保持打开供用户查看。报告见`progress/evidence/navrl-pillars-20261030-600.md`。
