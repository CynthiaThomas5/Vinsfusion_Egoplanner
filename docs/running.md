# 构建、运行与分享

## 环境与依赖

Linux／Docker／NVIDIA Container Toolkit。项目保持#051同一固定Jazzy/Harmonic镜像；定位和规划仍为CPU。镜像加载及来源见[容器说明](../docker/README.md)。首次干净源码目录：

```bash
bash tools/project.sh fetch
bash tools/project.sh build
bash tools/project.sh test
```

依赖获取拒绝覆盖已有文件；可用`--source vins_fusion`等选择缺失项。唯一源码在`src/vendor`，唯一ROS安装在`install`，PX4在`external/PX4-Autopilot/build/px4_sitl_default`。不需要历史run、旧项目或多个ROS overlay。下载需要网络，版本和补丁由清单固定；PX4子模块按gitlink恢复。

## 仿真与目标

```bash
bash tools/project.sh sim room-demo-01 --gui
bash tools/project.sh mission room-demo-01
bash tools/project.sh stop room-demo-01
```

仿真启动不会使能或解锁。`mission`是显式飞行请求，前检通过后才起飞；默认执行相对16m目标、驻留、降落上锁。目标与限值仅在`config`修改；坐标和健康门见[接口契约](contracts.md)。每轮使用新ID；同一项目拒绝并行启动第二套控制栈。`--gui`读取当前DISPLAY／XAUTHORITY；无GUI参数仍保留同一GPU传感器渲染路径。

导航、定位及PX4只接视觉估计；任务旁路只读记录Gazebo真值作离线到达／采样净空评估，没有控制或真值回馈。评估器位于`tools/debug_truth`，不属于定位／规划输入。任务结果在`artifacts/runs/<id>/qualification.json`，源、参数、binary哈希在`runtime-contract.json`，原生PX4日志在该轮隔离build/log。失败保留，不能只看action的success。

启动异常用`docker logs d435i-<id>`和该轮各模块log检查；保护锁定后启动新epoch，禁止手动清健康故障继续原目标。只关闭实际不再飞行的会话；本入口仅适用于SITL，不连接实机。

## 本地交付包

```bash
bash tools/project.sh export artifacts/exports/d435i-project
```

默认输出源码归档、固定镜像归档、逐文件manifest和SHA256SUMS；不会上传、提交或推送。`--code-only`仅导出源码，接收方仍需单独取得固定镜像。源码包不包含vendor下载、external源码、build/install、原始运行日志、本机配置或raw聊天；重建通过固定下载清单恢复。交付包内README提供加载与解压步骤。

完整工程状态与测试范围见[当前状态](../progress/CURRENT.md)。原隔离构建的三连基线和整理后构建／SITL分别记证据，不自动外推到其他机器、多场景或实机。第三方授权现状见[依赖说明](../dependencies/README.md)。
