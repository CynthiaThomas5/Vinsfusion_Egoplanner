#!/usr/bin/env python3
"""Install user launchers, retaining the previous ROS wrapper scripts."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess

root = Path(__file__).absolute().parents[1]
home = Path.home()
binary = home/'.local/bin'; binary.mkdir(parents=True,exist_ok=True)
entry = root/'tools/groundstation.sh'
for name,subcommand in [('uav-groundstation',''),('ros2','ros'),('rviz2','rviz'),('qgroundcontrol-uav','qgc')]:
    target = binary/name
    content = '#!/usr/bin/env bash\n# D435i project groundstation launcher\nexec '+shlex.quote(str(entry))+' '+subcommand+' "$@"\n'
    if target.exists() and target.read_text() != content:
        backup = target.with_name(target.name+'.before-uav-20261104')
        if not backup.exists(): shutil.copy2(target,backup)
    target.write_text(content); target.chmod(0o755)
status = binary/'uav-groundstation-status'
status.write_text('#!/usr/bin/env bash\n'+shlex.quote(str(entry))+' status\nread -rp "按回车关闭窗口…"\n')
status.chmod(0o755)
apps = home/'.local/share/applications'; apps.mkdir(parents=True,exist_ok=True)
desktop = Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
desktop.mkdir(parents=True,exist_ok=True)
for name,label,command,terminal,icon in [
    ('experiment','启动VINS绕圈实验',str(binary/'uav-groundstation')+' experiment-start',True,'applications-science'),
    ('view','无人机定位视图',str(binary/'uav-groundstation')+' view',True,'applications-science'),
    ('map','无人机占据地图',str(binary/'uav-groundstation')+' map-view',True,'applications-science'),
    ('status','无人机运行状态',str(status),True,'utilities-system-monitor'),
    ('nano','Nano终端',str(binary/'uav-groundstation')+' nano-shell',True,'utilities-terminal'),
    ('qgc','QGroundControl',str(binary/'qgroundcontrol-uav'),False,'applications-science'),
]:
    content = ('[Desktop Entry]\nType=Application\nName='+label+'\nExec='+command+
               '\nTerminal='+str(terminal).lower()+'\nIcon='+icon+'\nCategories=Science;\n')
    for target in (apps/('d435i-'+name+'.desktop'),desktop/('d435i-'+name+'.desktop')):
        target.write_text(content); target.chmod(0o755)
        subprocess.run(['gio','set',str(target),'metadata::trusted','true'],capture_output=True)
print('Installed project launchers and backed up replaced wrappers:',binary,desktop)
