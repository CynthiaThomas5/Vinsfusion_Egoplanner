# #514 特征预算离线实验

关联[对话](../../collaboration/dialogues/2026-10-29-514-n12-feature-budget.md)。保存#512正式FAIL证据和#507回放数值分析，不部署16迭代。新建baseline512/features300_512后发现继承镜像OpenCV64，与正式4不匹配；两组正常结束并保留。新baseline512_t4/features300_512_t4明确VINS_OPENCV_THREADS=4，只改变max_cnt220→300，复用已构建只读native trace/可靠输入副本，8迭代和40ms预算及所有物理/标定固定。当前等完整回放、原生输入核对、实际失败段误差与资源数据；没有新飞行或在线参数变更，N12仍2/3。计划artifacts/runs/n12-20261029-514-feature-budget/experiment-plan.json。
