# N17 #569仓库与迁移审计启动

用户授权Goal完成模式，范围包含现有GitHub上传、可迁移使用和N17收尾。初始2132项变更保存清单，不回滚或全量盲目提交。源码导出3193文件20,377,483bytes；初始快照仅用于干净重建，不是最终发布。

GitHub连接器网络失败，git ls-remote origin HEAD通过，当前远端fd90f3b73e48101ad35c5a0ed9372865392eca7c，仓库CynthiaThomas5/D435i-VINS-EGO-ROS2。尚未写入远端。

发现原导出器依赖不存在的历史镜像归档。修复为：归档存在仍严格校验；不存在时精确校验runtime.json要求的本地image ID，再docker save+zstd导出，以当前归档哈希记入manifest，失败不留完成归档。实际完整导出PASS，3项定向测试PASS。镜像身份未变，不切换未经验证环境。忽略build-*/和根目录临时安全读回文件，文件原件保留。

#570仅解压源码，在独立目录从固定上游开始真实fetch；vins含0022补丁完整重放已通过，EGO完整重放已通过，当前PX4 clone在执行。尚未完成干净构建/运行，不能据此通过N17。

产物：artifacts/runs/n17-20261029-569-audit、artifacts/exports/n17-20261029-569-{source,portable}；执行计划docs/n17-delivery-plan.md。异机连接方式与许可证偏好已询问，独立任务继续。下一步依赖fetch后真实干净build，补当前版本场景/接口回归、最终证据和发布。N17 in_progress；本轮未停止Goal。
