#!/usr/bin/env python3
"""Read-only MAVLink identity/parameters and a fixed NSH diagnostic allowlist."""
import argparse,json,os,re,struct,time
from pathlib import Path

COMMANDS=('ver all','param status','mavlink status','uxrce_dds_client status',
          'uxrce_dds_client','param show UXRCE_DDS*','param show SYS_USB_AUTO',
          'param show MAV_SYS_ID','ls /fs/microsd')
def shell_command_complete(text, command):
 clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text).replace('\r','')
 if '\x1b' in clean:return False  # A partial terminal escape is not a complete prompt.
 echo=re.search(r'(?:^|\n)(?:nsh>\s*)?'+re.escape(command)+r'\n',clean)
 # Background logger output can follow the completed shell prompt.
 return bool(echo and re.search(r'(?:^|\n)nsh>(?:\s|$)',clean[echo.end():]))

def decode_parameter(value, kind, bytewise):
 if kind==9:return value  # MAV_PARAM_TYPE_REAL32
 formats={1:'B',2:'b',3:'H',4:'h',5:'I',6:'i'}
 if bytewise and kind in formats:
  fmt='<'+formats[kind];return struct.unpack(fmt,struct.pack('<f',value)[:struct.calcsize(fmt)])[0]
 raise ValueError('Unsupported parameter encoding/type '+str(kind))

def main():
 os.environ['MAVLINK20']='1';os.environ['MAVLINK_DIALECT']='common'
 from pymavlink import mavutil
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--device',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=True)
 link=mavutil.mavlink_connection(a.device,baud=115200,source_system=245,source_component=190)
 log=(a.output/'mavlink.jsonl').open('a',buffering=1)
 def receive(timeout=.2):
  m=link.recv_match(blocking=True,timeout=timeout)
  if m and m.get_type() not in ('BAD_DATA',):
   if m.get_type() in ('HEARTBEAT','AUTOPILOT_VERSION','PARAM_VALUE','SERIAL_CONTROL','COMMAND_ACK'):
    log.write(json.dumps({'monotonic_s':time.monotonic(),'message':m.to_dict()})+'\n')
  return m
 try:
  end=time.monotonic()+10;heartbeat=None
  while time.monotonic()<end:
   m=receive()
   if m and m.get_type()=='HEARTBEAT' and m.autopilot==mavutil.mavlink.MAV_AUTOPILOT_PX4:heartbeat=m;break
  if heartbeat is None:raise RuntimeError('No PX4 heartbeat')
  if heartbeat.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:raise RuntimeError('Expected disarmed PX4')
  system=heartbeat.get_srcSystem();component=heartbeat.get_srcComponent()
  link.mav.command_long_send(system,component,mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,0,148,0,0,0,0,0,0)
  version=None;end=time.monotonic()+6
  while time.monotonic()<end:
   m=receive()
   if m and m.get_type()=='AUTOPILOT_VERSION':version=m;break
  if version is None:raise RuntimeError('AUTOPILOT_VERSION absent')
  (a.output/'identity.json').write_text(json.dumps({'heartbeat':heartbeat.to_dict(),'system_id':system,'component_id':component,'version':version.to_dict()},indent=2)+'\n')
  bytewise=bool(version.capabilities&mavutil.mavlink.MAV_PROTOCOL_CAPABILITY_PARAM_ENCODE_BYTEWISE)
  link.mav.param_request_list_send(system,component);params={};indices={};count=None;end=time.monotonic()+65;last=time.monotonic()
  while time.monotonic()<end:
   m=receive()
   if m and m.get_type()=='PARAM_VALUE':
    count=m.param_count
    if not 0<=m.param_index<count:
     continue  # PX4 _HASH_CHECK is metadata, not a restorable parameter.
    value=decode_parameter(m.param_value,m.param_type,bytewise)
    params[m.param_id]={'value':value,'type':m.param_type,'wire_float_hex':struct.pack('<f',m.param_value).hex(),'index':m.param_index}
    indices[m.param_index]=m.param_id;last=time.monotonic()
   if count and len(indices)==count:break
   if count and time.monotonic()-last>1:
    missing=next(i for i in range(count) if i not in indices);link.mav.param_request_read_send(system,component,b'',missing);last=time.monotonic()
  (a.output/'parameters-before.json').write_text(json.dumps({'complete':len(indices)==count,'expected_count':count,'received_count':len(indices),'bytewise_encoding':bytewise,'parameters':params},indent=2,allow_nan=False)+'\n')
  if len(indices)!=count:raise RuntimeError('Incomplete parameter backup')
  with (a.output/'parameters-before.params').open('w') as f:
   f.write('# HW07 full MAVLink parameter backup, typed decoded values\n')
   for name,x in sorted(params.items()):f.write(f"{system}\t{component}\t{name}\t{x['value']}\t{x['type']}\n")
  for command in COMMANDS:
   data=(command+'\n').encode()
   for start in range(0,len(data),70):
    chunk=data[start:start+70]
    link.mav.serial_control_send(10,6,0,0,len(chunk),list(chunk)+[0]*(70-len(chunk)))
   text='';deadline=time.monotonic()+10
   while time.monotonic()<deadline:
    m=receive(.1)
    if m and m.get_type()=='SERIAL_CONTROL':
     text+=bytes(m.data[:m.count]).decode(errors='replace')
     if shell_command_complete(text,command):break
   (a.output/(command.split()[0]+'-'+str(COMMANDS.index(command))+'.txt')).write_text(text)
   print(command,repr(text[:900]),flush=True)
   if not shell_command_complete(text,command):
    raise RuntimeError('NSH command did not complete: '+command)
 finally:
  link.mav.serial_control_send(10,0,0,0,0,[0]*70);link.close();log.close()
if __name__=='__main__':main()
