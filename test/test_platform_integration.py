"""Optional integration against a checkout of the actual Screen Time service.

SCREEN_TIME_PLATFORM_SOURCE=/path/to/omarchy-screen-time-platform python3 -m unittest discover -s test -p 'test_platform_integration.py' -v
All configuration, runtime and ledgers are temporary; no installed services run.
"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
import test_game_services as cases
from test_game_services import PROVIDERS, Platform

SOURCE = os.environ.get('SCREEN_TIME_PLATFORM_SOURCE')


@unittest.skipUnless(SOURCE, 'set SCREEN_TIME_PLATFORM_SOURCE to test the actual platform ledger')
class PlatformIntegration(unittest.TestCase):
    def setUp(self):
        self.game = cases.Games()
        self.game.setUp()
        self.addCleanup(self.game.doCleanups)
        g = self.game
        source = Path(SOURCE) / 'service'
        sys.path.insert(0, str(source))
        self.addCleanup(lambda: sys.path.remove(str(source)))
        spec = importlib.util.spec_from_file_location('real_screen_time_core', source / 'core.py')
        self.api = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.api)
        self.core = self.api.Core(g.root/'etc-platform', g.root/'ledger-platform', g.root/'platform', clock=lambda:g.now, verifier=lambda _:True)
        config = self.core.config()
        profile = deepcopy(self.api.DEFAULT_PROFILE)
        profile.update(philosophy='limits', blocked_periods=[])
        profile['budget_minutes'] = {key:60 for key in ('mon','tue','wed','thu','fri','sat','sun')}
        profile['credits'] = {'enabled':True, 'daily_cap_minutes':2, 'providers': {
            provider[0]: {'enabled':True, 'seconds_per_event':45, 'daily_cap_minutes':1} for provider in PROVIDERS.values()}}
        config['users'][g.user] = {'profile':'default'}
        config['profiles']['default'] = profile
        config['providers'] = {provider[0]: {'name':provider[1], 'unit':provider[2]} for provider in PROVIDERS.values()}
        self.api.write(self.core.etc/'config.json', config)
        g.host.platform.close()
        def credit(*args):
            result = self.core.award(*args)
            os.utime(g.status_path, (g.now, g.now))
            return result
        g.host.platform = Platform(self.core.run, credit, clock=lambda:g.now, trusted_owner=os.getuid())
        g.addCleanup(g.host.platform.close)
        original_advance = g.advance
        def advance(seconds=10):
            original_advance(seconds); self.session()
        g.advance = advance
        self.session()

    def session(self, paused=False):
        g = self.game
        self.api.write(self.core.run/str(g.uid)/'runtime.json', {'paused':paused,'updated_at':g.now,
            'session':{'present':True,'active':True,'locked':False}})
        config = self.core.config(); user,key,profile = self.core.account(g.uid,config)
        _, day = self.core.day(user,key,profile)
        self.core.publish(user,profile,day,config)
        os.utime(g.status_path,(g.now,g.now))

    def total(self):
        config=self.core.config(); user,key,profile=self.core.account(self.game.uid,config)
        return self.core.day(user,key,profile)[1]['credited_seconds']

    def test_all_three_verifiers_share_real_provider_and_global_caps(self):
        g=self.game; g.enable_pet()
        for expected in (45,15):
            started=g.pawberry(); result=g.solve_pet(started)
            self.assertTrue(result['ok'],result)
            self.assertEqual(g.settled('pawberry',started['id']),expected)
            self.assertEqual(g.solve_pet(started)['reward_seconds'],expected)
        self.assertEqual(self.total(),60)
        g.send('grove','begin',grade=6)
        pending=g.host.services['grove'].account(g.uid)['pending']; g.advance()
        self.assertTrue(g.send('grove','complete',id=pending['id'],answer=pending['answer'])['correct'])
        self.assertEqual(g.settled('grove',pending['id']),45)
        started=g.send('typing','begin',lesson='words')
        self.assertTrue(started['ok'],started)
        events=[{'key':char,'ms':(i+1)*200} for i,char in enumerate(started['text'])]
        g.advance(len(events)*.2+2)
        self.assertTrue(g.send('typing','complete',id=started['id'],events=events)['correct'])
        self.assertEqual(g.settled('typing',started['id']),15)
        self.assertEqual(self.total(),120)
        self.assertEqual(g.send('grove','begin',grade=5)['error'],'daily_cap_reached')
        self.assertTrue(g.send('typing','complete',id=started['id'],events=events)['already_completed'])
        self.assertEqual(self.total(),120)

    def test_paused_at_completion_records_zero_even_after_resume(self):
        g=self.game
        g.send('grove','begin',grade=5)
        pending=g.host.services['grove'].account(g.uid)['pending']; g.advance()
        self.session(paused=True)
        self.assertTrue(g.send('grove','complete',id=pending['id'],answer=pending['answer'])['correct'])
        self.assertEqual(g.settled('grove',pending['id']),0)
        self.session(paused=False)
        self.assertEqual(g.send('grove','complete',id=pending['id'],answer=pending['answer'])['reward_seconds'],0)
        self.assertEqual(self.total(),0)

if __name__ == '__main__':
    unittest.main()
