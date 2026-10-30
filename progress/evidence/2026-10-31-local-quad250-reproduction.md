# 本机 Quad250 柱群 GUI 单次复现

源码：sim-nav-quad250-2026-10-30，88a9d0888fc4f17a234795d01bc594e8598b0fd6。宿主GPU：RTX3060 Laptop。固定容器内容身份检查通过。

使用独立clone，复用本轮此前构建的未变依赖与产物；应用新增EGO0061补丁后，全部patched_files_sha256匹配。执行 `bash tools/project.sh build`：18ROS包增量构建通过，PX4 ninja no work to do；本轮没有重复751单测和3套集成，不声明新的干净构建证据。

执行 `./start.sh fly pillars`，run gui-20261031-010821-59721。flight PASS，action_success及landed_and_disarmed均true；qualification passed=true，native_mission/independent_arrival/contact/normal_landed_disarmed/terminal_identity/runtime_identity/unique_control_publishers全部通过。

原始产物：/tmp/d435i-vins-gui-standalone-20261030/artifacts/runs/gui-20261031-010821-59721

qualification.json SHA256：192bf4c4fe348dc166258d511396df77694cd95cc76250894236af98f786165a

限制：一次日常任务，formal_count_eligible=false；日志有一次IMU重复时间戳错误，未据此修改门限。旧运行曾确认Gazebo暂停；未证明暂停由何处触发。新运行时钟推进并完成任务。GUI按用户要求保留，已独立确认落地上锁。
