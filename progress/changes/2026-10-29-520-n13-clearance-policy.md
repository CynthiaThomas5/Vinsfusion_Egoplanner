# #520 N13净空门取消与附加规则核对

关联[对话](../../collaboration/dialogues/2026-10-29-520-n13-clearance-policy.md)。新增config/acceptance_n13.json revision12，删除4组指标内5处最小机体/规划净空数值比较；旧acceptance_n12.json revision11及原报告不改。更新通用离线评估器，有限非正保守界可作为诊断，保留身份/完整覆盖和零违规碰撞，已观测碰撞不能被缺数据覆盖为不足。重规划几何工具新增显式--acceptance-config，去除新策略的额外0.1m边界余量与替换轨迹净空筛选，保留碰撞边界期限；旧调用仍按原0.1m处理。

新增tools/test_n13_clearance_policy.py共16项策略测试；连同53项历史测试，最终69项PASS。初测动态测试fixture误用了runtime身份标识，已修正fixture而未放松身份检查，初测日志保留。py_compile使用临时pycache路径避免已有root缓存权限问题。复用#501归档只验证策略：跟踪/全机项PASS且数值门关闭；整体INSUFFICIENT是缺N13场景/重规划输入，不能记为N13通过。未新飞行/未改在线控制算法或参数，不需要ROS/PX4重建。

新增[源码规则清单](../../docs/n13-project-restrictions.md)，纠正官方规则对照文档中遗留的起飞前0.1m/s门描述；更新GOAL/CURRENT/实施书/milestones中的新配置指向。完整JSON清单、旧源码字节、SHA与测试/复放/结构检查日志在artifacts/runs/n13-20261029-520-clearance-policy；旧通用评估器字节匹配N12冻结记录。

停止原因：本轮指定的策略修改和核对完成。N13仍not_started、正式0次；下一N13场景与重规划协议准备需显式绑定revision12，旧动态箱体注入评估不能自动成为N13静态场景前置。
