# N10.3/#431 膨胀重建缺口的隔离复现与候选

## 已证明的实现缺陷

直接从当前GridMap源码提取clearAndInflateLocalMap和header中的inflatePoint（无修改的baseline），在最小GridMap数据支架中执行。raw occupied来源位于local_bound框外，但其inflation cube应覆盖框内query点。baseline先清框内inflated，再只扫描框内raw occupied，六个面测试均出现raw仍occupied、query却不inflated。

另外，当前只校验flat address范围；某轴负索引仍可映射为有效flat address，导致其他位置被错误标inflated。y/z两项边界负控制均复现错误标记。

## 候选与测试结果

隔离patch仅将重膨胀的occupied来源范围扩大inf_step个cell并裁至map bounds；inflated目标在toAddress前逐轴检查界。测试使用实际inflation0.730617917m、resolution0.1m（inf_step8），没有改变raw分类、unknown策略或规划/验收数值。

10个案例：六个更新框面外来源、一项框内occupied正控制、一项超inflation距离负控制、两项map边界flat-address alias负控制。baseline产生8项不变量失败（exit1），candidate全部通过（exit0）。提取函数之外仅有最小数据、索引和边界支架，无ROS、传感器、规划器或真实碰撞时地图重放；测试不能声称#428根因已唯一归因。

## 部署与局限

候选尚未应用到活动vendor源码；原源码SHA保持manifest记录值。没有ROS/PX4包构建或新飞行，未建立最终补丁链。此前第一次生成脚本的文本匹配多含一个空行，assert拒绝后未生成/运行测试；已改成精确提取循环边界后成功。随后增加真实inflation参数与map边界负控制，最终结果以test-results.json为准。

修复可能增加occupied source扫描/膨胀工作量，资源回归待测；raw frustum外的清图策略仍未变，不能声称保持所有历史障碍。下一步必须在#428安全收尾后把候选纳入固定补丁链、按真实ROS GridMap集成测试/构建，再以缺失的当前地图/轨迹证据校准，不能以此孤立检查替代SITL。

## 可复算产物

- artifacts/n10-prepared/n10-20261028-431-inflation-halo-candidate/build_check.py：提取当前函数，g++编译baseline/candidate并执行。
- 同目录manifest.json：基线源文件和header SHA。
- baseline.cpp、candidate.cpp、repair.patch、baseline-test.log、candidate-test.log、test-results.json。

执行：python3 artifacts/n10-prepared/n10-20261028-431-inflation-halo-candidate/build_check.py（基线预期失败、候选预期通过；汇总脚本exit0）。这关闭隔离缺陷复现/候选准备子项，不关闭N10.3，也不改变#428无安全终态状态。
