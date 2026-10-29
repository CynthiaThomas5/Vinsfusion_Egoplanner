# #528 N13只读归档评估链

Goal完成模式。新增tools/debug_truth/prepare_n13_evaluation.py，原始归档通过只读引用进入独立派生目录，所有重算输出及日志先排除旧symlink，避免覆盖原始报告。串联arrival/odometry/raw velocity/tracking/cross-run及N13正式判断器。首次真实#518复放识别旧tracking要求动态文件名；复用真实静态世界并从真实静态观察器建立明确标注的身份兼容视图，不伪造动态注入。第二次真实全链复放errors=[]，原归档已有派生报告哈希未变，旧单柱仍不能取得N13正式资格。

产物artifacts/reanalysis/n13-20261029-528-pipeline-check与pipeline-recheck，保留首轮错误。验证：实际CLI全链（第二次无工具错误）、py_compile、project_status、git diff --check。未飞行，正式0次。下一步可冻结协议/配置/评估器和首轮脚本身份，启动可见GUI；真实三柱正例和三次正式验收仍待完成，Goal保持active。
