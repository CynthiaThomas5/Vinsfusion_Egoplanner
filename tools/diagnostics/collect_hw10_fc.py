#!/usr/bin/env python3
"""Read-only sensor/heading diagnostics and latest completed ULog over MAVLink FTP."""
import argparse,json,os,re,time
from pathlib import Path
os.environ['MAVLINK20']='1'
from pymavlink import mavutil,mavftp
from probe_hw07_px4 import shell_command_complete
from reboot_unarmed_px4 import require_unarmed_px4


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--device',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 link=mavutil.mavlink_connection(a.device,baud=115200,source_system=245,source_component=190)
 report={'commands':{}}
 def command(text):
  data=(text+'\n').encode()
  for i in range(0,len(data),70):
   chunk=data[i:i+70];link.mav.serial_control_send(10,6,0,0,len(chunk),list(chunk)+[0]*(70-len(chunk)))
  end=time.monotonic()+15;result=''
  while time.monotonic()<end:
   msg=link.recv_match(type='SERIAL_CONTROL',blocking=True,timeout=.1)
   if msg:
    result+=bytes(msg.data[:msg.count]).decode(errors='replace')
    if shell_command_complete(result,text):break
  report['commands'][text]=result;(a.output/'diagnostic.json').write_text(json.dumps(report,indent=2))
  if not shell_command_complete(result,text):raise RuntimeError('No complete NSH result: '+text)
  return result
 try:
  link.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,mavutil.mavlink.MAV_AUTOPILOT_INVALID,0,0,mavutil.mavlink.MAV_STATE_ACTIVE)
  hb=link.wait_heartbeat(timeout=10);require_unarmed_px4(hb);report['heartbeat']=hb.to_dict()
  for text in ('listener sensor_mag 1','sensors status','logger status','ls -l /fs/microsd/etc/extras.txt','ls /fs/microsd/log'):command(text)
  sessions=re.findall(r'\bsess(\d+)\b',report['commands']['ls /fs/microsd/log'])
  if not sessions:raise RuntimeError('No numbered log session; select ULog manually')
  directory='/fs/microsd/log/sess'+str(max(map(int,sessions)))
  entries=command('ls -l '+directory);logs=re.findall(r'\blog(\d+)\.ulg\b',entries)
  if not logs:raise RuntimeError('No ULog in latest session')
  remote=directory+'/log'+str(max(map(int,logs)))+'.ulg';report['remote_ulog']=remote
  (a.output/'diagnostic.json').write_text(json.dumps(report,indent=2))
  link.mav.serial_control_send(10,0,0,0,0,[0]*70)
  ftp=mavftp.MAVFTP(link,1,1);target=a.output/'current.ulg';ftp.cmd_get([remote,str(target)])
  result=ftp.process_ftp_reply('OpenFileRO',timeout=240)
  if result.error_code!=mavftp.FtpError.Success:raise RuntimeError('ULog download failed: '+str(result.error_code))
  with target.open('rb') as f:
   if f.read(7)!=b'ULog\x01\x12\x35':raise RuntimeError('Invalid ULog magic')
  report['ulog_bytes']=target.stat().st_size
 finally:
  link.mav.serial_control_send(10,0,0,0,0,[0]*70);link.close();(a.output/'diagnostic.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({'remote_ulog':report.get('remote_ulog'),'ulog_bytes':report.get('ulog_bytes')}))


if __name__=='__main__':main()
