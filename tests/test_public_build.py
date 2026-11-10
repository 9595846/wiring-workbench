import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_suite

class PublicBuildTests(unittest.TestCase):
    def test_public_does_not_copy_any_personal_data(self):
        with patch.object(build_suite,'copy_missing') as copy:
            build_suite.seed_user_data(Path('unused'),public=True)
            copy.assert_not_called()
            build_suite.seed_user_data(Path('unused'),public=False)
            self.assertEqual(copy.call_count,6)

    def test_existing_output_refused_and_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'suite';target.mkdir()
            marker=target/'personal.json';marker.write_text('keep')
            with self.assertRaises(ValueError):build_suite.prepare_destination(target,public=True)
            self.assertEqual(marker.read_text(),'keep')
            build_suite.prepare_destination(Path(folder)/'new',public=True)

if __name__=='__main__':unittest.main()
