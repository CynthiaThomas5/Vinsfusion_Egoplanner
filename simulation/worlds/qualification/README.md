# 固定验收场景

empty为已验证单障碍源移除圆柱，保留原floor/walls/lights/textures；single、staggered、corridor保存N12/N13/N14原已验证场景几何。原来源/许可见dependencies/sources.json，未推定上游缺失授权。文件包含在源码内，迁移不需要历史artifacts或旧工作区。导航只接收相机深度，SDF仅由仿真环境加载，不注入完整地图。

默认启动仍使用../ego.sdf的19柱房间。资格场景在隔离验证工作区启动前选择，单次任务期间不修改世界。
