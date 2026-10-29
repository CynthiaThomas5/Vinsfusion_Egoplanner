# N07.8 #162：俯视保持到返程结束

## 依据和假设

#161的pitch转入、15s观察和复位阶段VINS有效；在pitch复位为0后的x返程约22仿真秒，`normalized_cost_exceeded`锁存，且long tracks、stereo features和bias没有明显越限。pitch角的实际raw-map收益尚未测出，因为没有完成post-scan门。

## 决定

复用#161完全相同的1.8m路径、+0.45rad pitch与15s观察，只把pitch复位放到x返程结束后。返程期间持续向下观察，检验能否维持地面边界附近纹理并避免cost锁存。yaw=0、N05门限、health门限和spawn不变。

为了让同一冷启动可在N05释放后续接hover，采用手动N05流程：启动项目容器、扫描前检查、后台支架探针、attached检查、释放、post-release检查和summary。新探针会记PX4 LandDetected；fixture移除后等1仿真秒。若released五阶段在线/离线不一致或不全accept，不启用bridge、不解锁。若gate通过，再在此容器核对EKF2 EV、无GNSS/真值、唯一控制publisher后开始首个≥30仿真秒无目标悬停。

## 结果

run `n07-20261024-162-01` 初始N05拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，online/offline一致。raw-ground平面z=-0.35m；44个完全低于平面的whole-cell已排除。只读审计显示HOLD 566个未知体素中心在地面以上z=0.45..1.25m；TAKEOFF_CONTACT 436个未知体素中心中无一个低于平面。见`progress/evidence/n07-n05-unknown-volume-audit-20261024-162.json`。

支架扫描在pitch转入第3/9阶段中止，health status锁存normalized cost 1.138230。采集到的883条VINS telemetry最高同公式cost为0.694196，无法定位触发锁存的单条样本；下一次复现将逐事件保存LocalizationStatus。fixture已脱离并移除，PX4保持DISARMED，最后新鲜LandDetected=true，容器Exited(0)。没有post-scan N05检查或起飞，hover仍0/3。结果见`progress/evidence/n07-retreat-observation-20261024-162.md`。
