# 任务对话摘要

- 日期与任务 ID：2026-10-20，当前 EGO vendor 重建与动态运行复核 #280–#281。
- 用户目标与明确约束：继续完成 GOAL.md；保护用户已有修改；旧外部来源只读；保持无真值在线输入、无 PX4/控制，验收阈值不因一次结果而调整。
- 发现：#279动态快照使用`p2-map-input-build-20261016-01/install`中的EGO预构建，二进制哈希与当前锁定vendor源码不匹配，且不含patch 0010同步诊断字符串；该run的51条EGO timeout不代表当前源码版本行为。
- 实施：#280使用当前`uav_interfaces` overlay从固定EGO revision `23a8d5a...`新建5包overlay，构建5/5通过；旧base下接口缺失的失败尝试保留。#281用新overlay运行35.015秒动态D435i，无goal/PX4/控制。
- 结果：#281 MapStatus 153/153 ready、定位695/695 valid TRACKING、深度1338/1338 ready；运动记录期间占据点数变化159次；捕获1193点同epoch快照并精确float32回读。EGO仅3条启动期no-odom，随后0条输入timeout、WAIT_TARGET且干净SIGINT退出。与旧#279形成版本化差异，但单轮对照不证明根因。
- 未完成：未发planner goal，未验证绕障/轨迹净空；free/unknown、地图覆盖和正式阈值仍待办。下一步先核对安全走廊，再做planner-only无控制目标诊断。
- 对应改动记录：`progress/changes/2026-10-20-040-p2-current-ego-vendor-runtime.md`。
