# GOAL C 第二障碍布局同刻快照复测 #321

沿用#320第二障碍布局、#318 patch 0029 planner binary、目标与运行参数，在新VINS epoch重新运行。只读probe收到2条不同trajectory ID；两份 snapshot请求均在第一次调用接受，start_time差分别+1 ms和0 ms，depth source age为130 ms和99 ms。使用SciPy重建曲线并每10 ms查询配对raw/inflated栅格：两条中心线各447/458点，全部在图内且known-free，raw occupied和inflation mask命中均为0；到occupied voxel box的最近离散样点距离0.542/0.592 m，对既有0.482 m名义球半径余量约60/110 mm。目标前另有一个候选被新增guard以unknown/inflated拒绝。

决定：该结果支持第二布局两条中心线与当前已知栅格mask一致，但全图known仅约0.58–0.59%，样点并未扫掠机体体积，地图真值、动态误差、跟踪和控制执行未测。patch 0029继续保持experimental，不改变GOAL C/D/F或里程碑状态。
