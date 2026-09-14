"""Prove games leave the real Screen Time ledger unchanged using local fixtures.

Set SCREEN_TIME_PLATFORM_SOURCE to a platform checkout. No service is installed.
"""
from copy import deepcopy
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import test_game_services as cases
from test_game_services import PROVIDERS

SOURCE = os.environ.get('SCREEN_TIME_PLATFORM_SOURCE')


@unittest.skipUnless(SOURCE, 'set SCREEN_TIME_PLATFORM_SOURCE for the real ledger check')
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
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.core = self.api.Core(g.root/'etc-platform', g.root/'ledger-platform',
            g.root/'platform', clock=lambda: g.now, verifier=lambda _: True)
        config = self.core.config()
        profile = deepcopy(self.api.DEFAULT_PROFILE)
        profile.update(philosophy='limits', blocked_periods=[])
        profile['credits'] = {'enabled': True, 'daily_cap_minutes': 30, 'providers': {
            p[0]: {'enabled': True, 'seconds_per_event': 45, 'daily_cap_minutes': 10}
            for p in PROVIDERS.values()}}
        config['users'][g.user] = {'profile': 'default'}
        config['profiles']['default'] = profile
        config['providers'] = {p[0]: {'name': p[1], 'unit': p[2]} for p in PROVIDERS.values()}
        self.api.write(self.core.etc/'config.json', config)
        self.api.write(self.core.run/str(g.uid)/'runtime.json', {'paused': False, 'updated_at': g.now,
            'session': {'present': True, 'active': True, 'locked': False}})
        user, key, profile = self.core.account(g.uid, config)
        self.ledger_path, day = self.core.day(user, key, profile)
        self.core.publish(user, profile, day, config)
        historical = self.core.award(g.user, 'peterholko.pawberry', 'historical-receipt-01', day['day'])
        self.assertEqual(historical['credited_seconds'], 45)
        self.before = self.ledger_path.read_bytes()
        # A restored integration path would reach the actual ledger and fail
        # the byte-for-byte assertion, even with all game providers enabled.
        g.host.platform = SimpleNamespace(
            settle=lambda user, provider, receipt: self.core.award(user, provider, receipt['id'], receipt['reward_day'])['credited_seconds'],
            status=lambda *_: {'available': True, 'active': True, 'enabled': True, 'minutes_per_problem': 1, 'daily_cap_minutes': 10})

    def test_games_and_replays_do_not_change_enabled_platform_balance(self):
        g = self.game
        pet = g.pawberry()
        self.assertEqual(g.solve_pet(pet)['reward_seconds'], 0)
        self.assertTrue(g.solve_pet(pet)['already_completed'])
        g.send('grove', 'begin', grade=6)
        pending = g.host.services['grove'].account(g.uid)['pending']
        g.advance()
        self.assertTrue(g.send('grove', 'complete', id=pending['id'], answer=pending['answer'])['correct'])
        self.assertEqual(g.send('grove', 'complete', id=pending['id'], answer=pending['answer'])['reward_seconds'], 0)
        mail = g.send('typing', 'begin', lesson='words')
        events = [{'key': char, 'ms': (i+1)*200} for i, char in enumerate(mail['text'])]
        g.advance(len(events)*.2+2)
        self.assertTrue(g.send('typing', 'complete', id=mail['id'], events=events)['correct'])
        self.assertEqual(g.send('typing', 'complete', id=mail['id'], events=events)['reward_seconds'], 0)
        self.assertEqual(self.ledger_path.read_bytes(), self.before)

    def test_restart_retires_pending_credits_without_touching_historical_balance(self):
        g = self.game
        for service in g.host.services.values():
            state = deepcopy(service.account(g.uid))
            state['receipts']['queued-old-credit'] = {'id': 'queued-old-credit', 'backend': 'platform',
                'reward_day': '2026-09-14', 'reward_seconds': None}
            service.persist(g.uid, state)
            service.accounts.clear()
        g.host.refresh(g.now)
        self.assertEqual(self.ledger_path.read_bytes(), self.before)
        for service in g.host.services.values():
            self.assertEqual(service.account(g.uid)['receipts']['queued-old-credit']['reward_seconds'], 0)
