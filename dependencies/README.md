# 固定依赖

`dependencies/sources.json` 是唯一版本与补丁应用清单。`tools/fetch_dependencies.py` 验证commit、补丁SHA256、许可文件和关键修复文件；临时目录重建成功后才移动至目标，已有目标一律拒绝覆盖。

```bash
bash tools/project.sh fetch
# 只获取某个缺失依赖
python3 tools/fetch_dependencies.py --source ego_planner
```

ROS依赖：VINS只物化camera_models／vins，EGO只物化5个规划包，另有px4_msgs、Agent和spdlog；PX4保持独立的固定源码及递归submodule gitlinks。旧实验区是只读来源，不被构建或启动器引用。

本次有效VINS链为0001–0005→0009→0011→0012→0013→0014（仅构建打包），EGO为原15补丁→0035→0036；逐项哈希与应用上下文在清单中。不叠加全部历史候选。未采用的补丁已移出活跃树，恢复位置和哈希见`retired-code-20261021.json`，其本地归档不属于运行输入。

第三方许可独立保留。房间源`ego_world`的上游未声明许可，不能将其标成已获GPL或其他授权。固定容器的可移交归档与约束见[构建环境](../docker/README.md)。
