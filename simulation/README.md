# 仿真资源

模型：`models/x500_d435i`固定安装单D435i，几何与外参从SDF派生；`models/d435i`包含双目、深度、RGB和相机IMU。

默认场景`worlds/ego.sdf`来自用户指定的DongnanHu6556/ego-planner-ros2-sim固定commit，约20×20m四墙和19柱。精确来源／哈希／Harmonic补丁及上游未声明许可状态见`dependencies/sources.json`的ego_world条目。标定单墙保留给传感器／几何回归，不是默认导航房间。

`textures/floor.png`与`textures/obstacles.png`为本项目确定性生成的纹理，与#051三连基线字节一致。场景生成器统一附着纹理，断言碰撞几何不变；不再从旧run目录复制。

虚拟IMU250Hz与原PX4物理4ms对齐，解决已测接地冲量相位漏采样；强度图near0.02m、深度near0.2m，其他标定保持。该频率仅为SITL等效配置，未外推真实D435i设置。模型检查、源码构建、当前房间导航与正式多场景／实机验收分别记录。
