# #526 N13隔离部署

Goal完成模式。复制合格N12候选到/home/huangxiaocheng/n13-20261029-526-staggered/project，排除旧运行归档；10886个普通文件逐一核对，只有simulation/worlds/ego.sdf变化。runtime_manifest实际生成，新旧files差集也仅该世界文件。共享external保持只读，不修改来源。准备#527首轮脚本/goal/观察器并更新场景名和身份，protocol仍draft未发布。:11和原Xauthority通过xdpyinfo连接检查。

产物artifacts/runs/n13-20261029-526-deployment及artifacts/n13-prepared/n13-20261029-527-formal01。未启动容器或飞行，正式0次。验证：manifest差集断言、普通文件哈希、xdpyinfo、bash -n、project_status、git diff --check。下一步补最终N13发布协议与独立评估运行链的集成验证，检查脚本中的继承元数据后冻结并启动GUI。N13仍in_progress，Goal未完成。
