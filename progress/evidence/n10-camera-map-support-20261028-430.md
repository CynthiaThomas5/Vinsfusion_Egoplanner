# N10.3/#430 历史地图与相机几何支持审查

## 结果

复用#428原始记录，未飞行。唯一完整snapshot的depth源戳103.556秒，快照103.720秒。以#429固定PRESTREAM SE(3)查询unit_cylinder_4在z=0.5/1.0/1.5m的216个圆周表面采样点：raw occupied22、known-nonoccupied18、unknown176，inflated216。raw表面抽样的free/unknown本身不构成完整体素错误分类证据。

后续130.168、131.168、132.168秒的命令点对应旧snapshot单元均为inflated=true，旧图源龄分别26.612、27.612、28.612秒。由此确认该障碍早期已有占据支持，不能把它解释为全程从未被建图；不能用旧snapshot声称碰撞时仍为occupied/inflated。

采用实际D435i深度相机SDF与当前ROS参数读回：fx/fy337.209640、cx320/cy240，640×480，margin2、skip2、depth0.2–5m、max ray4.5m。相机源文件SHA与run runtime-contract绑定一致。用真值姿态、实际外参作离线理想射线与已声明世界碰撞体/地面/已确认插入方箱求交，结果如下。所有数值是可能的几何射线机会，不能冒充真实depth像素或融合票据。

| 源时刻 | 无遮挡柱体采样射线 | 满足mapper深度/距离条件的射线 | 对应图像区域 |
| --- | ---: | ---: | --- |
| 103.556s | 5140 | 5140 | u444–546,v188–394 |
| 122.168s | 0 | 0 | 无 |
| 127.168s | 0 | 0 | 无 |
| 129.168s | 0 | 0 | 无 |
| 130.168s | 0 | 0 | 无 |
| 131.168s | 0 | 0 | 无 |
| 132.168s首次接触 | 536 | 536 | u632–636,v2–476，最右侧窄条 |

这是离散抽查，不宣称所有相邻时刻都不可见。结果将调查重点指向：已有障碍离开当前视野后的地图保留/膨胀更新、以及参考方向/yaw与感知覆盖的关系。原始ROI在unit_cylinder_0，碰撞目标为4；缺少碰撞时完整数组，仍不能唯一归因。

## 方法、验证与安全状态

新增离线工具tools/debug_truth/evaluate_n10_camera_map_support.py。参数来自运行中节点的只读param dump；渲染、深度噪声、量化与融合概率更新未重放。柱侧面/上下盖、box与ground遮挡均按理想几何处理。3项新单测覆盖射线前后/端盖、平行box slab及距离裁剪、像素margin/skip；连同#429共7项测试通过；归档复算成功，语法检查通过。没有改活动算法、参数或控制。

#428 r04仍armed DESCEND/LANDING，land_detected=false。未收到新一次紧急disarm授权，原#391授权不能复用。已启动host只读安全监护session41790：每分钟在同一容器内采样15秒；仅当独立native terminal全部字段、10秒稳定窗口、零终态后控制和旧轨迹检查均通过，才受控docker stop。它不发送disarm或飞行控制，未安全则保留容器。监护有60窗口上限，过期仍不安全时如实报告，不把超时当终态。

产物：artifacts/runs/n10-20261028-428-integrated-fault-diagnostic/n10-camera-map-support.json（输入SHA与逐时刻结果）；n10-postfault-effective-planner-params.yaml；supervise_closeout.py和n10-closeout-supervision-live.json。下一技术子项#431准备膨胀更新最小修复候选，安全收尾后才可应用/构建/运行验证。
