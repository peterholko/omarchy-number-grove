"""Local protocol tests. No system install, sudo, network, or desktop required."""
from copy import deepcopy
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import pwd
import random
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'service'))
from omarchy_kids.core import paths, storage
from omarchy_kids.core.auth import ParentAuth
from omarchy_kids.core.daemon import Daemon
from omarchy_kids.core.game_platform import Platform, PROVIDERS
from omarchy_kids.pawberry import work
from omarchy_kids.pawberry.service import answer_for


class Games(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.uid = os.getuid() or pwd.getpwnam('nobody').pw_uid
        self.user = pwd.getpwuid(self.uid).pw_name
        self.now = time.time()
        self.host = Daemon(paths.detect(self.root), modules=['pawberry', 'grove', 'typing'], log=lambda *args: None)
        self.host.clock.now = lambda: self.now
        self.host.auth = ParentAuth(verifier=lambda username, password: password == 'parent-secret')
        self.ledger, self.calls = {}, []
        self.host.platform.close()
        self.host.platform = Platform(self.root / 'platform', self.credit, clock=lambda: self.now, trusted_owner=os.getuid())
        self.addCleanup(self.host.platform.close)
        for module in PROVIDERS:
            self.assertTrue(self.send(module, 'users.set', peer=0, user=self.user, enabled=True)['ok'])
        self.publish()

    def publish(self, **updates):
        data = {'ok': True, 'plugin_id': 'peterholko.screen-time', 'api_version': 1, 'phase': 'running',
            'philosophy': 'limits', 'remaining_seconds': 600, 'credits': {'enabled': True, 'room_seconds': 300,
            'providers': {provider[0]: {'enabled': True, 'seconds_per_event': 60,
                'daily_cap_minutes': 5, 'credited_today_seconds': 0} for provider in PROVIDERS.values()}}}
        data.update(updates)
        self.status_path = self.root / 'platform' / str(self.uid) / 'status.json'
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(json.dumps(data))
        os.utime(self.status_path, (self.now, self.now))

    def advance(self, seconds=10):
        self.now += seconds
        if self.status_path.exists():
            os.utime(self.status_path, (self.now, self.now))

    def credit(self, user, provider, identifier, day):
        key = (user, provider, identifier, day)
        self.calls.append(key)
        if day != datetime.fromtimestamp(self.now).date().isoformat():
            return {'ok': False, 'error': 'wrong_day'}
        self.ledger.setdefault(key, {'ok': True, 'credited_seconds': 60})
        return self.ledger[key]

    def send(self, scope, cmd, peer=None, **message):
        return self.host.dispatch(self.uid if peer is None else peer, {'scope': scope, 'cmd': cmd, **message})

    def settled(self, scope, identifier):
        for _ in range(200):
            status = self.send(scope, 'status')
            for receipt in status.get('receipts', status.get('reward_receipts', [])):
                if receipt['id'] == identifier and receipt['reward_seconds'] is not None:
                    return receipt['reward_seconds']
            time.sleep(.005)
        self.fail('reward did not settle')

    def pawberry(self, operation='add', **extra):
        a, b = (18, 3) if operation == 'divide' else (8, 7) if operation == 'multiply' else (61, 29)
        return self.send('pawberry', 'begin', protocol=2, problem={'operation': operation, 'a': a, 'b': b}, **extra)

    def solve_pet(self, started):
        self.advance()
        return self.send('pawberry', 'complete', id=started['id'], answer=answer_for(started['problem']), steps=work.expected_steps(started['problem']))

    def enable_pet(self):
        result = self.send('pawberry', 'settings.set', password='parent-secret', screen_time={'enabled': True, 'backend': 'platform'})
        self.assertTrue(result['ok'], result)

    def test_only_requested_games_are_loaded_and_cannot_grant_arbitrary_time(self):
        self.assertEqual(set(self.host.services), {'pawberry', 'grove', 'typing'})
        for module in self.host.services:
            self.assertFalse(self.send(module, 'grant', seconds=3600)['ok'])
            self.assertFalse(self.send(module, 'users.set', user='root', enabled=True)['ok'])
        self.assertFalse(self.send('time', 'status')['ok'])
        result = self.send('grove', 'begin', grade=6, user='root', correct=True, seconds=3600)
        self.assertTrue(result['ok'])
        self.assertNotIn('answer', result['question'])
        self.assertFalse(self.ledger)

    def test_pawberry_parent_limits_and_settings_keep_todays_work(self):
        self.enable_pet()
        started = self.pawberry('multiply')
        self.assertTrue(self.solve_pet(started)['ok'])
        self.assertEqual(self.settled('pawberry', started['id']), 60)
        bad = self.send('pawberry', 'limits.set', limits={'multiply': 0}, password='wrong')
        self.assertEqual(bad['error'], 'bad_password')
        saved = self.send('pawberry', 'limits.set', limits={'add': 5, 'subtract': 5, 'multiply': 1}, password='parent-secret')
        self.assertEqual(saved['completed']['multiply'], 1)
        self.assertEqual(saved['remaining']['multiply'], 0)
        self.assertEqual(self.pawberry('multiply')['error'], 'daily_limit')
        self.assertTrue(self.pawberry('divide')['ok'])
        replay = self.solve_pet(started)
        self.assertTrue(replay['already_completed'])
        self.assertEqual(replay['completed']['multiply'], 1)
        self.assertEqual(len(self.ledger), 1)

    def test_pawberry_requires_all_work_and_server_issued_problem(self):
        self.enable_pet()
        started = self.pawberry()
        pending = self.host.services['pawberry'].account(self.uid)['pending']
        self.assertEqual(started['problem']['a'], pending['a'])
        identifier, problem = started['id'], started['problem']
        correct = answer_for(problem)
        self.advance()
        for steps in (None, [], [{'kind': 'final', 'value': correct}], [{'kind': 'final', 'value': True}]):
            self.assertEqual(self.send('pawberry', 'complete', id=identifier, answer=correct, steps=steps)['error'], 'incomplete_work')
        self.assertEqual(self.send('pawberry', 'complete', id=identifier, answer=correct+1, steps=work.expected_steps(problem))['error'], 'incorrect_answer')
        self.assertFalse(self.ledger)
        self.assertTrue(self.solve_pet(started)['ok'])
        self.assertEqual(self.settled('pawberry', identifier), 60)
        legacy = self.send('pawberry', 'begin', problem={'operation': 'add', 'a': 11, 'b': 12})
        self.assertEqual(legacy['error'], 'update_game_required')

    def test_pawberry_backend_switch_does_not_credit_same_problem_elsewhere(self):
        self.enable_pet()
        started = self.pawberry()
        # Changing the backend cannot retarget an already issued challenge.
        self.send('pawberry', 'settings.set', password='parent-secret', screen_time={'enabled': False, 'backend': 'legacy'})
        result = self.solve_pet(started)
        self.assertTrue(result['ok'])
        self.assertEqual(result['reward_seconds'], 0)
        self.assertFalse(self.ledger)

    def test_grove_grades_answers_and_replays(self):
        grove = self.host.services['grove']
        for grade in (5, 6):
            for _ in range(80):
                problem = grove.challenge({'grade': grade})
                self.assertTrue('×' in problem['text'] or '÷' in problem['text'])
                self.assertEqual(len(set(problem['choices'])), 6)
        for grade in (True, '5', {}, 0, 7):
            self.assertEqual(self.send('grove', 'begin', grade=grade)['error'], 'invalid_challenge')
        started = self.send('grove', 'begin', grade=5)
        pending = grove.account(self.uid)['pending']
        self.assertEqual(self.send('grove', 'complete', id=pending['id'], answer=pending['answer'])['error'], 'too_fast')
        self.advance()
        self.assertFalse(self.send('grove', 'complete', id=pending['id'], answer=True)['ok'])
        result = self.send('grove', 'complete', id=pending['id'], answer=pending['answer'])
        self.assertTrue(result['correct'])
        self.assertEqual(self.settled('grove', pending['id']), 60)
        replay = self.send('grove', 'complete', id=pending['id'], answer=0)
        self.assertTrue(replay['already_completed'])
        self.assertEqual(replay['reward_seconds'], 60)
        self.assertEqual(len(self.ledger), 1)
        self.send('grove', 'begin', grade=5)
        pending = grove.account(self.uid)['pending']; self.advance()
        wrong = next(n for n in pending['choices'] if n != pending['answer'])
        self.assertFalse(self.send('grove', 'complete', id=pending['id'], answer=wrong)['correct'])
        self.assertFalse(self.send('grove', 'complete', id=pending['id'], answer=pending['answer'])['correct'])
        self.assertEqual(len(self.ledger), 1)

    def test_typing_checks_text_accuracy_timing_and_only_game_input(self):
        self.assertEqual(self.send('typing', 'begin', lesson={})['error'], 'invalid_challenge')
        started = self.send('typing', 'begin', lesson='home')
        self.assertGreaterEqual(len(started['text']), 12)
        events = [{'key': char, 'ms': (i+1)*200} for i, char in enumerate(started['text'])]
        self.advance(len(events)*.2+2)
        for data in ([], [{'key': started['text'], 'ms': 2000}], events[:-1]):
            result = self.send('typing', 'complete', id=started['id'], events=data, correct=True, wpm=200)
            self.assertFalse(result['ok'])
        self.assertFalse(self.send('typing', 'complete', id=started['id'], events=[{**e, 'ms': 0} for e in events])['ok'])
        result = self.send('typing', 'complete', id=started['id'], events=events)
        self.assertTrue(result['correct'])
        self.assertEqual(self.settled('typing', started['id']), 60)
        started = self.send('typing', 'begin', lesson='words')
        keys = list('zzzzzzzzzz') + ['Backspace']*10 + list(started['text'])
        self.advance(len(keys)*.2+2)
        result = self.send('typing', 'complete', id=started['id'], events=[{'key': c, 'ms': (i+1)*200} for i,c in enumerate(keys)])
        self.assertTrue(result['ok']); self.assertFalse(result['correct'])
        self.assertEqual(result['reward_seconds'], 0)
        self.assertEqual(len(self.ledger), 1)

    def test_missing_disabled_stale_and_wrong_identity_status(self):
        for updates in ({'phase': 'paused'}, {'philosophy': 'together'}, {'credits': {'enabled': False}}, {'api_version': 2}):
            self.publish(**updates)
            self.assertFalse(self.send('grove', 'begin', grade=5)['ok'])
        self.publish(); os.utime(self.status_path, (self.now-31, self.now-31))
        self.assertFalse(self.send('typing', 'begin', lesson='words')['ok'])
        self.publish(plugin_id='other.screen-time')
        self.assertFalse(self.send('grove', 'status')['available'])
        self.status_path.unlink()
        self.assertTrue(self.solve_pet(self.pawberry())['ok'], 'ordinary Pawberry practice must remain available')
        self.assertFalse(self.ledger)

    def test_uncertain_response_restart_and_replay_credit_only_once(self):
        attempted = threading.Event()
        def lose_ack(*args):
            self.credit(*args); attempted.set()
            raise OSError('reply lost after commit')
        self.host.platform.transport = lose_ack
        started = self.send('grove', 'begin', grade=5)
        pending = self.host.services['grove'].account(self.uid)['pending']; self.advance()
        self.send('grove', 'complete', id=pending['id'], answer=pending['answer'])
        self.assertTrue(attempted.wait(2))
        self.host.platform.close()
        self.host.platform = Platform(self.root/'platform', self.credit, clock=lambda:self.now, trusted_owner=os.getuid())
        self.addCleanup(self.host.platform.close)
        self.host.services['grove'].accounts.clear()
        self.host.services['grove'].tick(self.now, 0)
        self.assertEqual(self.settled('grove', pending['id']), 60)
        self.assertEqual(len(self.ledger), 1)
        self.assertEqual(len(set(self.calls)), 1)

    def test_external_credit_wait_does_not_block_verifier_lock(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def waiting(*args):
            entered.set(); release.wait(2); return self.credit(*args)
        self.host.platform.transport = waiting
        self.send('grove', 'begin', grade=5)
        pending = self.host.services['grove'].account(self.uid)['pending']; self.advance()
        self.send('grove', 'complete', id=pending['id'], answer=pending['answer'])
        self.assertTrue(entered.wait(1))
        before = time.monotonic()
        self.assertTrue(self.pawberry()['ok'])
        self.assertLess(time.monotonic()-before, .5)
        release.set()

    def test_existing_pawberry_config_and_counters_survive_enrollment(self):
        service = self.host.services['pawberry']
        old = {'add': 5, 'subtract': 8, 'multiply': 2, 'screen_time': {'enabled': True, 'minutes_per_problem': 3, 'daily_cap_minutes': 20}}
        service.config['users'][self.user] = deepcopy(old)
        state = service.account(self.uid); state['counts']['add'] = 4; service.persist(self.uid, state)
        self.send('pawberry', 'users.set', peer=0, user=self.user, enabled=True)
        self.assertEqual(service.config['users'][self.user], old)
        self.assertEqual(self.send('pawberry', 'status')['remaining']['add'], 1)
        self.assertEqual(service.reward_settings(self.user)['backend'], 'legacy')


class Packaging(unittest.TestCase):
    def test_fresh_game_module_selection_does_not_enable_a_clock(self):
        spec = importlib.util.spec_from_file_location('game_manage', ROOT/'service/manage.py')
        manage = importlib.util.module_from_spec(spec); spec.loader.exec_module(manage)
        for game in PROVIDERS:
            modules, selected = manage.selected_modules({}, game)
            self.assertEqual(modules, [game]); self.assertEqual(selected, {game})
        modules, _ = manage.selected_modules({'modules': ['school', 'time']}, 'typing')
        self.assertEqual(set(modules), {'school', 'time', 'typing', 'pawberry'})
        modules, _ = manage.selected_modules({'version': '3.0.0', 'modules': ['school', 'time']}, 'typing')
        self.assertNotIn('pawberry', modules, 'an explicitly removed module must stay removed')
        self.assertEqual(manage.config_path('pawberry').name, 'pawberry.json')

    @unittest.skipUnless((ROOT/'WorkSteps.js').exists(), 'Pawberry owns the arithmetic view')
    def test_python_verification_agrees_with_actual_javascript_working(self):
        rng = random.Random(371)
        problems = [{'a': 300, 'b': 156, 'operation': 'subtract'}]
        for op in ('add','subtract','multiply','divide'):
            for _ in range(500):
                a,b = rng.randrange(10,1000),rng.randrange(10,1000)
                if op == 'subtract': a,b = max(a,b),min(a,b)
                if op == 'divide': b=rng.randrange(2,10); a=b*rng.randrange(5,10)
                problems.append({'a':a,'b':b,'operation':op})
        problems += [{'a':a,'b':b,'operation':'multiply'} for a in range(1,10) for b in range(1,10)]
        script = "const fs=require('fs'),w=require('./WorkSteps.js');process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(p=>w.build(p.a,p.b,p.operation).steps.map(s=>({kind:s.kind,value:s.expected})))));"
        expected = json.loads(subprocess.check_output(['node','-e',script], input=json.dumps(problems).encode(), cwd=ROOT))
        for problem, steps in zip(problems, expected):
            self.assertEqual(work.expected_steps(problem), steps, problem)

if __name__ == '__main__':
    unittest.main()
