# #600 NavRL多柱场景与材质证据

## 来源与场景

- 来源：NavRL `generated_env/generated_env_static.world`，commit `3725bcc2e7c1be4ecf1455d922299ae85042603a`；源文件 SHA256 `faf1a73c704fe9d81c30fc897ff8352fbd5485b4f90a5d695ddeb667527d6821`，MIT许可见dependencies。
- 场景含ground和60根柱（30圆柱、30方柱）。上游柱子只有visual没有collision；本项目运行时为60个primitive逐个按可见几何生成匹配碰撞体，world.json记录全部碰撞对应关系。场景加载后核实模型数61、新增柱体collision 60。
- 材质采用浅暖色细颗粒地面（8m平铺）与蓝绿/砂色柱身，浅色环仅用于视觉。材质资产SHA256 `84e881d6748159d3ea7d08e71d09118d442699dc5f1a6546136811c0a83bd21f`；生成提示词在[材质记录](../../simulation/textures/natural_terrazzo.json)。
- 出生点(-8,0,0.3)，目标相对ENU(+16,0,0)。运行时配置为official EGO collision policy。

## 验证

- `bash tools/project.sh build ros`：18 packages finished。
- `python3 -m unittest discover -s tools -p test_pillars_scene.py`：2项PASS。
- `bash tools/project.sh test`：751单测及3项ROS集成PASS。
- `python3 tools/project_status.py`：Structure/design check PASS；`git diff --check` PASS。
- `./start.sh start pillars`：GUI成功加载新场景；world.json显示natural材质、60根柱的同形碰撞。
- `./start.sh fly pillars`：qualification **PASS**，7项检查全通过：native action、独立到达、接触、正常落地上锁、终态/运行身份、唯一控制发布者。16m任务独立真值核验最低误差0.04796m（阈值0.30m），连续驻留要求3.0sim秒通过；违规接触0次。PX4正常落地并上锁，独立安全停止读回PASS。该单次日常导航qualification的`formal_count_eligible`为false，不累计正式场景/时长资格次数。离线真值仅评估，未作为在线控制输入。

## 产物

- run：`artifacts/runs/gui-20261030-154042-3829973`。
- [Gazebo截图](../../artifacts/runs/gui-20261030-154042-3829973/scene-gazebo.png)、[RViz截图](../../artifacts/runs/gui-20261030-154042-3829973/scene-rviz.png)、[机器可读证据和SHA](navrl-pillars-20261030-600.json)。
- GUI仍保持打开供用户查看；飞行已落地上锁。

## 限制

仅做一条16m路线一次GUI运行；不是完整迷宫/多路线/重复时长资格。材质为生成的固定albedo，不是实测物理纹理，也未做纹理间VINS对照基准。
