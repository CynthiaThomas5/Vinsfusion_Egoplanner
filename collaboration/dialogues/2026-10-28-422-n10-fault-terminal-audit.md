# N10-20261028-422 对话摘要：#415 故障终态路径审计

- #415链路确认：adapter在121.088s因`propagated_invalid_quaternion`锁存；EGO最后地图更新121.080s，121.516s超过原生0.400s深度/里程计超时并中止，桥进入LANDING。具体错误传播四元数没有保存，源头仍未知。
- 源码审计发现当前状态机将PX4 `DESCEND`视作landing-active，因此不再重发NAV_LAND；但只有`landed && !armed`才进入LANDED，没有观察到的非终态有界处理路径。
- r11同域只读读回8秒仍为armed/failsafe DESCEND、XY无效、EV未融合、land_detected=false。2秒Gazebo truth约在地面高度，但存在0.1066m端点XY位移，不能证明接触或PX4终态。最终r12读回又持续6秒，依旧无terminal；最后验证alignment pair已老化约1799.9 wall秒。
- 没有新增控制、门限或运行源码更改；一次性disarm授权已在#391使用，#415仍需原生终态或新的明确授权安全收尾。N10保持in_progress。
