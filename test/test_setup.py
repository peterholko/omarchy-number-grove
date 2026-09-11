"""Exercise file installation and upgrades in a temporary tree, with systemctl mocked."""
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'service'))

class Setup(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('game_setup_fixture',ROOT/'service/manage.py')
        self.manage=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.manage)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for directory in ('lib','etc','state','bin','units'):
            (self.root/directory).mkdir()
        m=self.manage
        self.calls,self.enrollments=[],[]
        self.context=ExitStack();self.addCleanup(self.context.close)
        for key,value in {'PREFIX':self.root/'lib/controls','CONFIG':self.root/'etc','STATE':self.root/'state',
            'MARKER':self.root/'etc/installation.json','PASSWORD_PATH':self.root/'etc/password.json',
            'UNIT':self.root/'units/omarchy-kids-controls.service'}.items():
            self.context.enter_context(patch.object(m,key,value))
        original_wrappers=m.wrappers
        self.context.enter_context(patch.object(m,'wrappers',lambda:{self.root/'bin'/p.name:text for p,text in original_wrappers().items()}))
        self.context.enter_context(patch.object(m,'check_account',lambda user:None))
        self.context.enter_context(patch.object(m,'run',lambda *args,**kwargs:self.calls.append(args)))
        self.context.enter_context(patch.object(m,'enroll',lambda *args:self.enrollments.append(args)))
        self.context.enter_context(patch.object(m,'wait_for_service',lambda:None))
        self.context.enter_context(patch.object(m,'register_providers',lambda modules:None))
        original_is_file=Path.is_file
        self.context.enter_context(patch.object(Path,'is_file',lambda path:True if str(path)=='/usr/share/omarchy/config/omarchy/shell.json' else original_is_file(path)))

    def install(self,module,upgrade=True):
        self.manage.install(SimpleNamespace(user='linnea',module=module,upgrade=upgrade))

    def test_fresh_install_adds_games_without_enrolling_clocks_or_replacing_parent_data(self):
        m=self.manage
        self.install('grove')
        self.assertFalse(m.PASSWORD_PATH.exists(),'Grove needs no separate controls password')
        self.assertEqual(m.installed()['modules'],['grove'])
        self.assertEqual(self.enrollments,[('grove','linnea',True)])
        self.assertFalse(json.loads((m.CONFIG/'screen-time.json').read_text())['users'])
        password='{"keep":"password hash"}\n';quota='{"users":{"linnea":{"add":5,"multiply":7}}}\n'
        m.PASSWORD_PATH.write_text(password);(m.CONFIG/'pawberry.json').write_text(quota)
        (m.STATE/'saved-counts.json').write_text('{"completed":4}')
        self.install('pawberry');self.install('typing')
        self.assertEqual(m.installed()['modules'],['grove','pawberry','typing'])
        self.assertEqual(m.PASSWORD_PATH.read_text(),password)
        self.assertEqual((m.CONFIG/'pawberry.json').read_text(),quota)
        self.assertEqual((m.STATE/'saved-counts.json').read_text(),'{"completed":4}')
        self.assertEqual(set(x[0] for x in self.enrollments),{'grove','pawberry','typing'})
        self.assertIn(('systemctl','restart','omarchy-kids-controls.service'),self.calls)
        self.assertEqual(m.payload_files(m.PREFIX),m.installed()['payload'])

    def test_unknown_files_and_local_service_edits_stop_upgrade(self):
        m=self.manage
        collision=self.root/'bin/omarchy-kids-controls-grove-client'
        collision.write_text('unrelated command')
        with self.assertRaisesRegex(ValueError,'collision'):
            self.install('grove')
        self.assertEqual(collision.read_text(),'unrelated command')
        collision.unlink()
        self.install('grove')
        target=m.PREFIX/'runtime.py';target.write_text('local administrator change')
        with self.assertRaisesRegex(ValueError,'local edits'):
            self.install('typing')
        self.assertEqual(target.read_text(),'local administrator change')
        self.assertEqual(m.installed()['modules'],['grove'])

if __name__=='__main__':
    unittest.main()
