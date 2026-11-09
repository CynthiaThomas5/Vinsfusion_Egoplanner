from pathlib import Path
import struct,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from probe_hw07_px4 import decode_parameter, shell_command_complete
class DecodeTests(unittest.TestCase):
 def test_bytewise_int32(self):
  for value in (-1,0,123456):
   self.assertEqual(decode_parameter(struct.unpack('<f',struct.pack('<i',value))[0],6,True),value)
 def test_uint32_and_float(self):
  self.assertEqual(decode_parameter(struct.unpack('<f',struct.pack('<I',123456789))[0],5,True),123456789)
  self.assertEqual(decode_parameter(.125,9,True),.125)
 def test_unsupported_encoding_fails_closed(self):
  with self.assertRaises(ValueError):decode_parameter(1.,6,False)
 def test_shell_must_finish_before_next_command(self):
  command='param show USB_MAV_MODE'
  self.assertFalse(shell_command_complete('nsh> \x1b[K',command))
  self.assertFalse(shell_command_complete(command+'\npartial output',command))
  self.assertFalse(shell_command_complete(command+'\nnsh> \x1b[',command))
  self.assertTrue(shell_command_complete(command+'\nvalue\nnsh> \x1b[K',command))
 def test_async_logger_output_after_prompt(self):
  text='logger on\nnsh> \x1b[KINFO  [logger] Start file log\nINFO  [logger] Opened full log file\n'
  self.assertTrue(shell_command_complete(text,'logger on'))
  self.assertFalse(shell_command_complete('nsh> \nlogger on\nwaiting','logger on'))
  self.assertFalse(shell_command_complete('logger on\nvalue contains nsh> text\n','logger on'))
if __name__=='__main__':unittest.main()
