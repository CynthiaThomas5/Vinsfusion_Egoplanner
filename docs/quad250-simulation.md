# 250 级单 D435i 仿真模型（#592）

用户于2026-10-30要求按官方小机体参考配套修改仿真机体与碰撞地图。此版是250级仿真近似模型，不是用户实机的质量、惯量、电机、桨叶或相机安装标定。历史 `sim-nav-v1.0.0` / N17 的 X500 资格只属于原版本；不得自动转给本模型。

## 官方参考与实际选择

[Fast-Drone-250 文档](https://github.com/ZJU-FAST-Lab/Fast-Drone-250/blob/8ff64274b161bb829653faf5946656658e7e2c9f/readme.md)描述250mm轴距平台；轴距不是含桨宽度。官方实机 `src/planner/plan_manage/launch/advanced_param_exp.xml` 的地图分辨率为0.15m、膨胀参数为0.299m、`dist0`为0.5m。本项目采用这三个取值，保留现有0.4m/s、0.25m/s²的规划运动参数。不是采用通用ROS2演示的0.099m膨胀。

- 机体由锁定PX4 X500模型派生：长度为原来的0.5，旋翼中心对角距离约0.2461m；碰撞体、视觉网格、旋翼位置和起落架同步改变。
- 机体各link质量乘0.52，惯量乘0.52×0.5²；含0.072kg相机总质量约1.14544kg。此为仿真假设，不是官方或用户实机惯量。
- 电机推力系数乘0.52、反扭矩系数乘0.5；阻力系数随派生尺度调整。PX4角速度环K取0.5作为该近似模型的初值，必须用实际SITL检查其行为。
- PX4控制分配位置直接读取本地旋翼link，转换FLU→FRD；反扭矩符号与数值由同一电机模型读取。仍由唯一 `uav_px4_bridge` 发布控制。
- D435i外壳、双目基线、图像内参和相机IMU未缩放。相机安装改为base_link的`0 0 0.08`，由wrapper SDF唯一维护；PX4 EV杆臂与离线真值转换均按此推导。
- 含旋翼扫掠的水平包络半径约0.19297m；含起落架的任意姿态球包络约0.21497m，均相对D435i参考点。0.299m≥1.5×水平半径；离散地图每轴每侧膨胀两格，即0.30m。地板仍作为普通占据表面膨胀，不做隐藏地板或语义地面剔除。

## 源文件与兼容命名

`simulation/models/x500_base/model.sdf`、`simulation/models/x500/model.sdf`现在是本项目本地250级派生模型；保留`x500*`名字只是兼容PX4启动和历史接口，不代表仍用原X500尺寸。wrapper为`simulation/models/x500_d435i/model.sdf`。Gazebo资源路径优先选择本项目模型，接触观察overlay同样从本地模型生成。

派生输入为`config/components/simulation/quad250.json`，执行`python3 tools/generate_quad250_models.py`可重新生成两个SDF、来源哈希和差异。相机安装仍以wrapper为准，不在该配置复制一份。地图参数位于`config/components/mapping/ego_planner.json`，EGO补丁0061仅开放地图分辨率参数，未修改碰撞算法。

原始PX4文件未修改。来源commit、SHA256、BSD许可及应用顺序见`dependencies/quad250-model-provenance.json`、`dependencies/patches/simulation/quad250-*.diff`与`simulation/models/QUAD250-PX4-LICENSE`。网格/贴图通过相对符号链接引用已锁定PX4资产，因此新设备仍须先执行项目fetch。

旧X500空间误差实测保留为`historical_x500_*`字段，不再冒充新模型的测量。新膨胀参数扣除几何球半径后的0.08403m只是未分配余量，不是经过验证的定位、建图、跟踪误差上界。N05/N08旧策略诊断继续检查各项预算和几何身份，但当前官方策略不启用它们的raw-known-free飞行门。

## 使用与验证边界

构建和启动入口仍为`bash tools/project.sh build ros`、`./start.sh fly`。已有运行会话必须先正常结束、确认落地上锁，再使用全新会话，避免将旧模型/地图epoch与新参数混用。当前验证状态与实际运行证据见`progress/evidence/quad250-adaptation-20261030-592.md`。

转真实设备前仍需实际测量含桨/桨保尺寸、总质量、动力与相机安装。此变更只涉及仿真，没有修改实机配置、执行实机飞行或替换现有ROS2/PX4控制架构。
