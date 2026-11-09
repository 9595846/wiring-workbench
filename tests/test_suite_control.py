import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import suite_control

class Tests(unittest.TestCase):
 def test_only_exact_suite_paths_are_targets(self):
  root=Path(tempfile.gettempdir())/'suite-a'
  paths=suite_control.allowed_paths(root)
  self.assertEqual(len(paths),2)
  self.assertIn(str((root/'OLEDWorkbench/OLEDWorkbench.exe').resolve()).casefold(),paths)
  self.assertNotIn(str((root.parent/'suite-b/OLEDWorkbench/OLEDWorkbench.exe').resolve()).casefold(),paths)
 def test_close_is_wm_close_and_never_force_kill(self):
  user=Mock();user.PostMessageW.return_value=1
  with patch.object(suite_control,'windows',return_value=[{'hwnd':123,'pid':456,'path':'example'}]),patch.object(suite_control.ctypes,'WinDLL',return_value=user):
   self.assertEqual(suite_control.request_close('.'),{'found':1,'requested':1})
   user.PostMessageW.assert_called_once_with(123,0x0010,0,0)
   self.assertEqual(len(user.method_calls),1)
 def test_no_windows_is_safe_noop(self):
  user=Mock()
  with patch.object(suite_control,'windows',return_value=[]),patch.object(suite_control.ctypes,'WinDLL',return_value=user):
   self.assertEqual(suite_control.request_close('.'),{'found':0,'requested':0})
   user.PostMessageW.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
