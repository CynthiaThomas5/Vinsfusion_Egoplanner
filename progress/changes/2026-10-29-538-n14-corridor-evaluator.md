# #538 N14实际通道判断器

Goal完成模式，范围N14全部出口。新增tools/debug_truth/evaluate_n14_route.py：核对实际双侧墙尺寸/位姿，检查实际和参考完整入口/出口及中间样本在两墙间、未飞越，匹配goal/epoch样条已执行；穿越前同身份同快照raw/inflated支持两侧墙，保持源时序/hash/路径检查。零违规接触/正常终态需核心评估另验，不将中心样本冒充完整机体连续净空。

验证：13项N14/N13几何测试PASS；实际N13三柱归档作为负例INSUFFICIENT，不产生窄道资格；py_compile、project_status及git diff --check。产物artifacts/runs/n14-20261029-538-evaluator。未飞行，正式0/3，尚无真实窄道正例；下一步N14功能配置/核心场景绑定和独立评估入口集成，然后隔离部署及GUI正式运行。Goal active未完成。关联collaboration/dialogues/2026-10-29-538-n14-corridor-evaluator.md。
