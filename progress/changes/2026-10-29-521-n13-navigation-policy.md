# #521 N13功能验收设置

目标：落实用户批准的设置，普通有界模式，仅离线配置/评估器/文档；不启动飞行。对话：[授权摘要](../../collaboration/dialogues/2026-10-29-521-n13-navigation-policy.md)。

实际改动：config/acceptance_n13.json升revision13，十类独立质量/资源/几何指标设diagnostic；旧数值移入diagnostic_reference字段，旧配置归档config/history/acceptance_n13_revision12.json。tools/n13_navigation_policy.py重算同身份原始接触与正常终态，将原密集几何和其它诊断结果嵌套保留；修改公共评估器的N13显式策略分支，去除旧动态注入身份、可选密集几何参考点报告和诊断输入哈希的隐含前置，核心身份/参考点/输入哈希仍校验。可选记录损坏按不足诊断，实际碰撞、动作失败、异常终态继续FAIL。旧#520测试固定读取归档revision12，新增15项策略测试。GOAL、规则清单、CURRENT、milestones同步设置与唯一下一项；N13保持not_started、正式0次。

验证：84项新旧单测PASS、四文件py_compile PASS；#518/#512原始输入只读复放，整体INSUFFICIENT，三类核心项PASS，#512速度诊断FAIL仍保留。python3 tools/project_status.py与git diff --check见证据及检查日志。构建/SITL/实机未运行，本轮不修改ROS/PX4/VINS运行源码或运动参数。

局限/下一步：N13实际错位多障碍/地图更新/替换轨迹执行证据协议尚pending；不能拿旧N12通过解除此状态。N13.1实现并绑定协议和评估器后才开始可见GUI正式测试。未修复历史漂移、地图或队列问题；只改变授权范围内的离线判据。停止原因：本轮设置交付完成。
