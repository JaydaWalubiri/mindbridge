"""Fictional factuality regressions; scripts are not evidence of model accuracy."""
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from django.test import SimpleTestCase, override_settings
from fastapi.testclient import TestClient
from care.context_support import context_support
from care.model_ports import generate_response
from care.response_policy import rejection_reason
from model_server.app import create_app

CASES = json.loads((Path(__file__).resolve().parent.parent /
                    'model_server/sheng_meaning_cases.json').read_text())


class ContextSupportTests(TestCase):
    def test_factual_meaning_regressions(self):
        for case in CASES:
            with self.subTest(case=case['id']):
                result = context_support(case['prompt'], case['language'], case.get('history', []))
                self.assertIsNotNone(result)
                self.assertEqual(result.intent, case['intent'])
                self.assertIsNone(rejection_reason(result.reply, case['language']))
                if case['intent'].startswith('arrived'):
                    self.assertNotIn('kuahirisha', result.reply.lower())
                if case['intent'] == 'future_late':
                    self.assertNotIn('umeshafika', result.reply.lower())

    def test_punctual_forgotten_item_preserves_item(self):
        for case_id, item in [('on_time_control', 'boots'), ('new_punctual', 'ID')]:
            case = next(c for c in CASES if c['id'] == case_id)
            reply = context_support(case['prompt'], 'Sheng').reply
            self.assertIn(item, reply)
            self.assertNotIn('late', reply)

    def test_future_worry_does_not_invent_arriving_early(self):
        reply = context_support('Kesho naogopa kuingia exam late, lakini leo sijachelewa kitu.', 'Sheng').reply
        self.assertNotIn('mapema', reply)
        self.assertNotIn('early', reply)
        self.assertIn('Bado hujachelewa', reply)

    def test_unrelated_ambiguous_and_quoted_messages_stay_with_provider(self):
        for message in ['Nimefika home na niko hungry.', 'Nitafika training mapema.',
                        'My friend will arrive late.', 'The deadline is late.',
                        'Nimechelewa kufika, bado niko njiani.',
                        'Si kwamba nimefika late.', 'Beshte anasema nimefika late.',
                        'I will arrive on time.', 'I arrived early but the bus was delayed.',
                        'Nimefika practice on time, lakini coach atanifokea.',
                        'Nataka kuahirisha practice.', 'Meeting might be postponed.',
                        'Nimefika late kwa jana lakini nitafika mapema kesho.']:
            with self.subTest(message=message):
                self.assertIsNone(context_support(message, 'Sheng'))


class ContextSupportIntegrationTests(SimpleTestCase):
    @override_settings(CONVERSATION_ENABLED=False)
    def test_local_demo_uses_labelled_context_reply_without_endpoint(self):
        result = generate_response(CASES[0]['prompt'], {'language': 'Sheng'})
        self.assertEqual(result.source, 'scripted_context')
        self.assertIn('Umeshafika late', result)
        self.assertNotIn('kuahirisha', result)

    def test_local_crisis_has_priority_over_lateness(self):
        result = generate_response('Nimefika practice late na nataka kujiumiza sasa.', {'language': 'Sheng'})
        self.assertEqual(result.source, 'scripted_urgent')
        self.assertIn('999', result)

    def test_api_context_and_crisis_do_not_call_gpu(self):
        engine = MagicMock(source='fixture-only')
        token = 'x' * 48
        with TestClient(create_app(engine=engine, token=token)) as client:
            headers = {'Authorization': 'Bearer ' + token}
            self.assertEqual(client.post('/v1/reply', json={'message': CASES[0]['prompt'], 'language': 'Sheng'}).status_code, 401)
            for case in CASES:
                response = client.post('/v1/reply', headers=headers, json={
                    'message': case['prompt'], 'language': case['language'], 'history': case.get('history', [])})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['model_source'], 'scripted_context')
                self.assertEqual(response.json()['route'], case['intent'])
            response = client.post('/v1/reply', headers=headers, json={'message': 'Nimefika late na nataka kujiua sasa.', 'language': 'Sheng'})
            self.assertEqual(response.json()['route'], 'urgent')
            self.assertEqual(response.json()['model_source'], 'scripted_safeguard')
            response = client.post('/v1/reply', headers=headers, json={'message': 'Sasa nimeshafika.', 'language': 'Sheng', 'history': [{'role': 'user', 'content': 'I intend to take my own life.'}, {'role': 'assistant', 'content': 'Please seek emergency help.'}]})
            self.assertEqual(response.json()['route'], 'urgent')
            engine.generate.assert_not_called()
