# #379 SITL prelaunch freeze

状态：**容器启动前已冻结**；这是相同制动协议的独立重复样本2/3，不改运行或测量参数。

- 新建run id `n10-20261027-379-speed060-repeat02`，要求新的PX4/Gazebo/VINS冷启动与新epoch/goal identity。
- Runtime `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`；planner `config/components/mapping/n10_horizon5_speed080_calibration.json`（0.8/0.25/horizon5/official_ego）；spawn `[-8.0, 0.0, 0.3, 0.0, 0.0, 0.0]`。
- PX4水平触发窗保持 `[0.60,0.66] m/s`；stop band、真值、contact、safe readback与#378相同。
- Protocol SHA `a626ab9eb8df47ea3771d8d6275559dd17f5defa44c4ba2a15985545dcbd86df`；prelaunch SHA `ed72af150ecc3a56e39066db695152b8d683f1135c62e31ee100c14e26411528`；run-local driver SHA `ef594fd9d69beed64e5e6446fc06f28f9aacc52cdf6fe93d76541831cf99540c`。
- 冻结哈希或实际加载身份不符时，目标不发送。
