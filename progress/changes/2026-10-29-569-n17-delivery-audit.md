# N17 #569仓库与迁移审计启动

用户授权Goal完成模式，范围包含现有GitHub上传、可迁移使用和N17收尾。初始2132项变更保存清单，不回滚或全量盲目提交。源码导出3193文件20,377,483bytes；初始快照仅用于干净重建，不是最终发布。

GitHub连接器网络失败，git ls-remote origin HEAD通过，当前远端fd90f3b73e48101ad35c5a0ed9372865392eca7c，仓库CynthiaThomas5/D435i-VINS-EGO-ROS2。尚未写入远端。

发现原导出器依赖不存在的历史镜像归档。修复为：归档存在仍严格校验；不存在时精确校验runtime.json要求的本地image ID，再docker save+zstd导出，以当前归档哈希记入manifest，失败不留完成归档。实际完整导出PASS，3项定向测试PASS。镜像身份未变，不切换未经验证环境。忽略build-*/和根目录临时安全读回文件，文件原件保留。

#570仅解压源码，在独立目录从固定上游开始真实fetch；vins含0022补丁完整重放已通过，EGO完整重放已通过，当前PX4 clone在执行。尚未完成干净构建/运行，不能据此通过N17。

产物：artifacts/runs/n17-20261029-569-audit、artifacts/exports/n17-20261029-569-{source,portable}；执行计划docs/n17-delivery-plan.md。异机连接方式与许可证偏好已询问，独立任务继续。下一步依赖fetch后真实干净build，补当前版本场景/接口回归、最终证据和发布。N17 in_progress；本轮未停止Goal。

对话collaboration/dialogues/2026-10-29-569-n17-delivery.md

追加：空Docker引擎导入及ROS/Gazebo实际运行通过，但image ID显示099ab9af…与1ec91baf…不同；RootFS全部层及Config/Architecture/Os完全一致。新增固定内容指纹校验，不放行不同层/配置/架构。空引擎已停止移除，未影响服务容器。普通navigation缺qualification.json且未独立生成safe-to-stop，已增加只读终态/任务结果评估，并提前启动观察器，不新增飞行决策；9项定向测试PASS。默认16m从x=-6.5会落在x=9.5距墙不足膨胀半径，候选spawn恢复x=-8，并使用已验证0.4m/s、0.25m/s²动力学和native5s驻留；实际验收仍冻结0.3m/15度/3秒。以上默认入口候选尚待真实GUI验证，不计通过。初次构建命令误在主工作区发起，已只停止该增量构建容器，不计干净重建；随后在#570空目录实际构建，session24032，构建日志clean-build.log。

#570已完成18包6min34s及PX4全部1141步干净构建。第一次715tests有3fail/11error：历史物理world测试依赖未分发#398日志、默认profile继承测试硬写1秒、默认planner参数来源hash过时。改为独立最小physics测试fixture并保持真实锁定机体输入、固定测试参数验证继承、复算相同机体包络/膨胀并更新planner来源hash。729tests+两套ROS集成全部PASS，不跳过测试。干净VINS binary等于#566。#571启动真正默认GUI和start.sh fly，结果未定；运行中不改候选source/config。固定环境LFS分支正在上传；无源码主分支提交。

#571未起飞：旧图检查写死2订阅者，被GUI/只读observer共4个订阅正确事实触发拒绝；唯一导航publisher和planner/bridge端点均在。新增结构化端点验证（唯一supervisor publisher、必需planner/bridge subscribers，允许只读订阅者）；3定向tests PASS。#571独立确认DISABLED/landed/disarmed/control disabled后停止归档。#572误在修复复制前启动，同样未飞，独立确认安全后停止归档；不在运行身份变更会话里强行续飞。#573新冷启动使用修正入口，真实start.sh fly执行中。前期有脚本工作目录错误，已统一主工作区绝对路径和调用候选入口的绝对路径，未计为成功验证。
