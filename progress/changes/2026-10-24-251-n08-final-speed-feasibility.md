# #251 N08速度关系审计与最终可行性复核

关联对话：collaboration/dialogues/2026-10-24-251-n08-speed-and-braking-test.md。

实际修改：0044第三方补丁与依赖锁，refine后复核最终速度／加速度并有界重试；N08证书读取manifest绑定的试验配置而不写死0.075；新增0.10逐轴／0.12向量校准候选；扫描取消保留ROS上下文与安全清理；增加远端正前上视观测profile；PositionCommand诊断记录源戳、速度、加速度。现有未提交改动保留，不复测N07。

验证：17包ROS构建、全新依赖重建及哈希、53项定向回归、实际C++归档曲线复算与真实ROS取消上下文检查均通过。#252在运行，用于验证新曲线和地图。实际制动测试尚未完成，N08保持in_progress。产物见progress/evidence/n08-speed-final-feasibility-20261024-251.json及artifacts/runs/n08-20261024-251-speed-final-feasibility/。
