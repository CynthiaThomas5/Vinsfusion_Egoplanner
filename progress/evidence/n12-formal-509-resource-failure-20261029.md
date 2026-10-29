# #509 N12 资源失败

新规则下地图表面实测、分类、绕行、到达与净空全部通过；native source lag最大0.388s>0.2s且source gap0.332s>0.2s，FAIL，不计合格。独立落地/上锁/控制归零后安全停止容器。源图像收据在51–55sim s最大间隔0.036s，不能归因Gazebo相机源断流；异常native stamp53.164s发生在PRESTREAM55.74s之前，完整会话标准保持，不删该段。详见[JSON](n12-formal-509-resource-failure-20261029.json)。
