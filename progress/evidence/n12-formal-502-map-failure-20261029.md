# #502 N12 正式04：地图分类FAIL保留

完整GUI冷启动、单柱绕行、独立到达3.572sim秒、20sim秒保持及正常降落均完成；独立LANDED/disarmed/control-disabled/终态后零控制通过后安全停止。完整机体无接触区间净空下界0.621706m，零违规接触。平移RPE实测0.051904m仅记录，不参与否决；其余定位/跟踪/资源/身份等通过。

唯一失败为raw地图分类：7张末段快照累计501个“当前视角全体素遮挡却为raw free”计数（重复快照计数，不声明501个独立体素），标准0。地面/墙体实心全包含free计数0，墙面几何误差0.063997m通过。完整合同保留FAIL，不计第三次合格；N12仍2/3。

#503针对历史可见性的假设进行原始数据核对：全部问题集中前墙Wall_1附近x约10.070…10.072m、z约0.065…2.065m，墙顶2.5m；没有体素整体位于墙顶以上，逐张更早真实深度源时刻相机姿态/完整FOV/全障碍遮挡及当时raw-free检查未找到合法历史可见见证。因此不以“曾经看到”消除该失败，也不改零错误门限。

[完整合同](../../artifacts/reanalysis/n12-20261029-502-formal04-evaluation/n12-20261029-502-formal04/n12-scene-acceptance.json)、[逐体素历史核对](../../artifacts/runs/n12-20261029-503-map-review/occluded-history-review.json)、[对应源时刻位姿误差](../../artifacts/runs/n12-20261029-503-map-review/source-pose-error-at-affected-snapshots.json)。下一独立正式资格验证#504；该次真实误分类及其尚未唯一确认的实现根因保留。
