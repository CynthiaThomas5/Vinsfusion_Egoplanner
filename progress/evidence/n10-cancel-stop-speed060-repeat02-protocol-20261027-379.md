# N10.3 #379 braking repeat 2 of 3

状态：**SITL 启动前冻结**。#378 是当前 runtime 下第一份完整制动样本：实际触发0.600867m/s，stop band 4.844仿真秒进入，真值水平路径1.376716m。#379 用新的 Gazebo/PX4/VINS cold start 完全重复同一协议，积累独立样本；不改变速度窗、planner、spawn、goal、stop band、observer或验收标准。

触发窗仍为 `[0.60,0.66] m/s`，只作为量测选择器。完成标准仍为取消确认、不同EGO轨迹、PX4停带覆盖、真值覆盖、contact零违规及安全独立末态。单次/两次重复都不构成通用停止保证。

协议SHA `a626ab9eb8df47ea3771d8d6275559dd17f5defa44c4ba2a15985545dcbd86df`；prelaunch SHA `ed72af150ecc3a56e39066db695152b8d683f1135c62e31ee100c14e26411528`；driver SHA `ef594fd9d69beed64e5e6446fc06f28f9aacc52cdf6fe93d76541831cf99540c`。Runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`，planner horizon5/0.8/0.25 official_ego，spawn `[-8,0,0.3,0,0,0]`。
