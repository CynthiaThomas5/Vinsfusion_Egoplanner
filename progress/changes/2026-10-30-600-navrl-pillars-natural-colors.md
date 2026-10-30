# #600 NavRL 多柱场景与自然材质

- 用户范围/模式：普通单项；希望使用很多柱子的world，并替换原有棋盘格观感；保留既有场景。对话摘要见[600对话](../../collaboration/dialogues/2026-10-30-600-navrl-pillars-natural-colors.md)。
- 资产：上游 `generated_env_static.world` 原字节保存为 `simulation/worlds/navrl/generated_env_static.world`；固定NavRL提交 `3725bcc2e7c1be4ecf1455d922299ae85042603a`，MIT许可复用，来源/哈希在dependencies登记。源共60柱（30圆柱、30方柱），源world没有柱体collision。
- 实现：新增运行时primitive物理化与自然材质合成；柱体按源visual几何添加等形collision，地面以25块8m纹理瓦片铺满40x40m视觉区域，碰撞仍由原ground collision提供；柱身着蓝/绿/砂色并增加仅视觉浅色环。新场景出生(-8,0,0.3)、目标相对+16m；切换入口 `./start.sh start|fly pillars`。
- 材质：新增 `simulation/textures/natural_terrazzo.png`，图像由内置image_gen按配套JSON中记录的提示词生成；原棋盘格资源保留给未修改的场景。
- 静态验证：`bash tools/project.sh build ros` 18包PASS；针对场景2项单测PASS；`bash tools/project.sh test` 751单测及3项ROS集成PASS。宿主裸Python整仓收集因缺少rclpy失败（12个ROS测试模块无法导入），该失败不代表项目容器测试失败。
- GUI run `artifacts/runs/gui-20261030-154042-3829973`已启动，world.json确认 `pillars`、60个柱体collision及natural材质profile；Gazebo/RViz截图已保存。16m飞行检查正在执行，资格结果待任务自动终态后补记。
- 局限：该候选场景目前仅计划单路线单次GUI验证；image_gen输出是固定albedo而非实测物理材质。
