# #595 官方室内演示风格与显示层地面抑制

限定功能 **PASS**；原始文件哈希及实际指标见[JSON](history-display-20261030-595.json)。参考为[官方README第三张indoor.gif](https://github.com/ZJU-FAST-Lab/ego-planner/blob/master/pictures/indoor.gif)，对齐显示目的，不声称复制其完整实机系统/算法或获全局SLAM资格。

## 实现

- `history_display.py`从低高度、足够XY支撑的水平raw历史体素层估计平坦地面；隐藏显示地面以上0.20m及以下的带。默认候选z≤0.15m（相对VINS会话起点）、至少40体素、XY各跨度≥0.6m、面覆盖≥0.15；选支撑最多的层。没有支撑则不猜地面、不删显示点。
- `observed_history.py`保留原raw历史并集，另向显示云输出过滤结果；`observed_history_raw`和`history_display_status`提供未过滤数据及估计/数量诊断。全部新增发布位于`/visualization/mapping/`，没有规划/控制/真值输入输出。
- RViz默认白底TopDownOrtho、历史障碍按Z高度彩虹配色；局部膨胀碰撞层默认关闭，仍可勾选。地图坐标不改、历史体素不平移，原局部地图及地面防撞不删除。
- 配置在`config/components/mapping/observed_history.json`；同会话身份/reset/时钟隔离与容量上限沿用#594。

## 验证

| 类型 | 命令 | 结果 |
|---|---|---|
| 构建 | `bash tools/project.sh build ros` | 18包PASS |
| 单元/ROS | `bash tools/project.sh test` | 745单测、3套ROS集成PASS |
| 新单测 | `test_history_display.py` | 平面抑制、障碍/原始数据保留、墙行/稀疏对角墙拒绝、架高桌面不误当低地面、空reset与参数拒绝PASS |
| ROS扩展 | `probe_observed_history.py` | 同会话/晚订阅/旧帧/重置/时间隔离继续PASS，增加真实filtered/raw输出和地面状态检查 |
| GUI/SITL | `./start.sh`、`bash tools/project.sh mission gui-20261030-125353-3586249` | 默认16m任务qualification全部7项PASS，零违规接触、正常落地上锁 |
| 只读显示/保留 | `record_observed_history.py /workspace/artifacts/runs/gui-20261030-125353-3586249` | raw历史保留和地面显示抑制均PASS |
| 真实图像 | 读取当前RViz窗口截图 | 俯视地图显示历史柱/墙轮廓和路径，无大片地板；见下述截图 |
| 结构/格式 | `python3 tools/project_status.py`、`git diff --check` | PASS；不替代运行验证 |

同一运行回读：

| 指标 | 结果 |
|---|---:|
| raw累计历史 | 5803体素 |
| 显示障碍 | 1452体素 |
| 显示中隐藏的地面带 | 4351体素 |
| 估计地面Z | -0.175m |
| 显示裁剪上界Z | 0.025m |
| 初始raw体素最终仍保留 | **598/598** |
| 初始raw体素最终仍在局部地图 | 0/598 |

原始数据为`artifacts/runs/gui-20261030-125353-3586249/observed-history-retention.json`，包含1812帧local、201帧raw history、200帧display；所有显示点高于该显示裁剪面。`qualification.json`独立到达/接触/正常终态/核心身份/唯一控制全部true。实际截图：`artifacts/runs/gui-20261030-125353-3586249/rviz-obstacles-ground-hidden.png`。测试与运行日志位于`artifacts/runs/history-display-20261030-595-checks/`；关键输入SHA256在本报告JSON中。

本轮只有一个显示策略候选、一次实际飞行。没有调整VINS/PX4/EGO数值、降低运行验收阈值或引入在线真值。官方GIF仅作外观参考，当前图只包含相机实际观测到的障碍，不补完整世界地图。

## 局限与收尾

这是平坦室内的显示启发式，不是语义地面分割。显示带内的低矮障碍也被隐藏；原raw历史及规划碰撞数据仍保留。斜地、楼梯和实机未验证。缓存仍限同一会话，不自动跨进程保存，漂移可能产生重影；历史unknown/free不因此改变。

停止原因：本轮有界目标完成。GUI `gui-20261030-125353-3586249`保留供用户查看，已落地上锁/控制关闭；查看后可`./start.sh stop`。无自动下一任务，无提交/推送。
