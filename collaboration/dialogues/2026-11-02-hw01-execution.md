# HW01 ARM/Foxy 构建实施

用户授权按 `docs/hardware-agent-workbook.md` 完成 HW01：在 Nano 独立目录构建当前固定 VINS/EGO 和必要自维护包，验证核心 Python 入口；不启动传感器或 PX4 控制，保留工作区已有改动。

调查确认目标为 Nano4GB、Ubuntu 20.04.6、Foxy/aarch64。已有 Ceres 2.1.0、OpenCV 4.2.0 与同基准 VINS 历史构建；它们只作为可追溯依赖复用，不替代当前仓库源码构建。实测 Foxy 缺少当前导航代码使用的 EventsExecutor/SignalHandlerOptions/Executor.create_future，cv_bridge 仅提供 cv_bridge.h。

实施采用独立 `~/D435i-VINS-EGO-ROS2-hardware` 工作区、串行 Release 构建；为 Python/RCLPY API 和 cv_bridge 头文件加入窄兼容，并提供干净 shell 运行环境加载脚本；Gazebo bridge 依赖仅在 ARM 构建配置排除。编译、入口导入与交接结果以 `progress/evidence/hw01-arm-foxy-20261102.md` 为准。

## 执行结果

HW01于2026-11-02完成：Jetson Nano/Foxy独立工作区15包VINS/EGO/own闭包构建通过；干净shell的Python导入、配置CLI和ROS入口检查通过；四个核心二进制动态链接无缺库。为修复实际构建/导入错误登记了VINS 0023、EGO 0062–0065补丁并更新ARM构建入口。证据见 `progress/evidence/hw01-arm-foxy-20261102.md`。未启动传感器、PX4运行或飞行；唯一下一模块HW02。
