# 固定依赖

`dependencies/sources.json` 是唯一版本与补丁应用清单。`tools/fetch_dependencies.py` 验证commit、补丁SHA256、许可文件和关键修复文件；临时目录重建成功后才移动至目标，已有目标一律拒绝覆盖。

```bash
bash tools/project.sh fetch
# 只获取某个缺失依赖
python3 tools/fetch_dependencies.py --source ego_planner
```

ROS依赖：VINS只物化camera_models／vins，EGO只物化5个规划包，另有px4_msgs、Agent和spdlog；PX4保持独立的固定源码及递归submodule gitlinks。旧实验区是只读来源，不被构建或启动器引用。

本次有效VINS链为0001–0005→0009→0011–0019；其中0014仅作构建打包，0015–0019增加只读回环／残差诊断，不改变生产定位数值。EGO链为0001–0011→0017–0019→0021→0035–0043→0045–0049→0050–0053。逐项哈希与应用上下文以`dependencies/sources.json`为准。0044曾加入最终样条动力学复核及硬拒绝，现已按用户要求从有效链移除；0053继续移除项目自加的整条曲线raw occupancy／地图就绪准入，并恢复上游规划失败重试。EGO本身的膨胀占据碰撞、轨迹碰撞回调、深度超时和紧急停车仍保留。运行代码恢复上游的一次可行性检查和一次时间重分配流程。0045为EGO定点航向轨迹；0048让简单航点统一走带身份／地图校验的NavigateToPose action；0049按官方 EGO 规则使用膨胀占据层，raw unknown 不单独判碰撞；0050只为上游原有可行性检查输出诊断数据，不改阈值或轨迹。取消停车与 N08 低速测量仍限于各自报告的范围。没有把全部历史候选叠加进运行源码。未采用的补丁已移出活跃树，恢复位置和哈希见`retired-code-20261021.json`，其本地归档不属于运行输入。

第三方许可独立保留。房间源`ego_world`的上游未声明许可，不能将其标成已获GPL或其他授权。固定容器的可移交归档与约束见[构建环境](../docker/README.md)。

## N17许可证核对

7个src/own ROS包的package.xml已经声明Apache-2.0，整理保持这些现有声明，并提供[许可证全文](licenses/Apache-2.0.txt)。旧README“自维护未指定许可”的概括与包级声明不一致，以实际包级声明为准；未据此给所有工具、文档、场景或第三方文件另授一份全仓库许可证。

VINS和EGO的GPL、PX4/px4_msgs的BSD、Micro XRCE-DDS Agent的Apache、spdlog的MIT按sources.json与各自LICENSE保留，补丁的派生版权和应用顺序不变。默认ego世界的锁定上游未声明许可，这一事实仍明确保留，不将其改标为Apache或GPL。发布不改变现有仓库访问权限；接收方需要取得仓库及固定环境分支的访问权限。
