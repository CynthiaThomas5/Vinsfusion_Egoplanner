# GS01 Debian地面站配置

对话：[摘要](../../collaboration/dialogues/2026-11-04-014-gs01-groundstation.md)。普通模式有界软件部署，用户要求配置指定地面站；未修改硬件Goal或验收条件。

## 改动

- 新增tools/groundstation.sh与config/groundstation/debian.env，支持SSH状态、纯计算启动/停止、原生ROS命令、隔离本地ROS、定位/地图显示、QGC和接收方向遥测。不存在自动发目标/解锁/飞行分支。
- tools/install_groundstation_desktop.py安装五个桌面/菜单入口，原有失效ros2/rviz2命令备份后指向本项目。新建Nano专用SSH密钥，授权公钥到Nano；密码/私钥不入仓库。work加入dialout，未全局停ModemManager。
- docker/groundstation.Dockerfile固定现有Jazzy镜像digest，安装显示依赖及pymavlink2.4.49，真实构建uav_interfaces；不把VINS/EGO搬到地面站。
- hardware_live_rviz.py增加主机/远端目录/状态文件参数，SIGTERM进入既有清理路径，保留默认显示行为。新增groundstation_map.py实现原生Foxy订阅→SSH→Jazzy显示；地图保留坐标数值、显示使用接收戳，按epoch/定位有效性清图。参考轨迹只显示采样记录，不声称完整未来曲线。
- 新增qgc_readonly.py，仅将接收字节发往localhost14550，不转发QGC回发。新增三项地面站定向测试入口和中文手册。
- 更新CURRENT的GS01结果；现有HW10.3b记录与父HW08/HW10状态不改。

## 验证与局限

真实容器构建、库和消息导入、SSH/native接口查询、RViz OpenGL4.6与地图窗口、QGC界面启动通过。主机边界/只收遥测2例、地图和既有显示/传输回归通过；真实Foxy序列化经SSH到Jazzy的合成地图解码通过，不创建ROS发布者。结构检查和diff检查通过。完整命令与产物见[证据](../evidence/gs01-debian-20261104.md)。

直接跨版本DDS收包探针两次超时，最终方案不依赖此路径。旧Nano会话在检查中退出，日志末尾bad_alloc；当前另有HW10.3b停旧会话/独占相机任务，退出因果未确定，本轮不重启或改门限。所有GS01测试窗口和地图relay已退出；不清理其他任务的state/rmem。

不构成有效实时建图/规划、完整负载、双向MAVLink或实飞资格。QGC语音后端加载警告保留，串口新组权限需桌面重新登录。停止原因：软件部署和限定验证完成。下一步按HW10.3b继续，其有效数据链恢复后才验证完整实时地面站。
