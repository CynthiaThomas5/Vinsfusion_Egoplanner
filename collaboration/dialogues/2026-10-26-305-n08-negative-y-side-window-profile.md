# N08 #305 负Y视角替换静态profile

## 依据
#300同一支架路线完成且 post-release/current-area N05 通过，但前向方向证书在goal/enable前拒绝，unknown集中在odom y=−1.05m薄层。#302/303的加长路线能到负Y侧视但多次在长扫描晚段触发原VINS cost门；#304在负侧视前触发cost门，未能测试短驻留。

## 决定
复用#300整条已知路线和同样总时长，仅将现有+Y侧观察窗口改为−Y水平观察，回中和后续步骤保持。这样不在原路线后增加观察时间，直接针对已测得的unknown方向。

## 静态验证
39项profile tests、JSON解析、shell语法、项目结构检查和diff check通过。下一步是一次新冷启动；N05/N08门不过不发目标或解锁。

证据：[静态报告](../../progress/evidence/n08-negative-y-side-window-profile-20261026-305.md)。
