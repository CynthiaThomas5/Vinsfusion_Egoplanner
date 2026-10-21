# 唯一第三方源码目录

从项目根运行`bash tools/project.sh fetch`，按`dependencies/sources.json`获取固定版本、验证补丁与许可并物化源码。已有目标不覆盖。

VINS只保留camera_models／vins，EGO只保留5个规划包，避免同名ROS包和多个算法副本。px4_msgs、Agent、spdlog亦由同一工具获取；PX4在`external/`独立构建。所有ROS包统一进入项目`build/`、`install/`，不再source历史实验overlay。

下载源码不进入本项目Git；共享时包含获取工具、完整补丁、配置与许可来源清单。
