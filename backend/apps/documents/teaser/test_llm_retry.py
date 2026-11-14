from django.test import SimpleTestCase

from .llm import LLMError
from .llm_retry import LLMUnavailable, generate_with_retries, is_transient


class Flaky:
    """Fails with the given errors one by one, then succeeds."""

    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def generate_json(self, **kwargs):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return "ok"


def run(client, attempts=4):
    sleeps = []
    result = generate_with_retries(client, system="s", user="u", schema={}, attempts=attempts, sleep=sleeps.append)
    return result, sleeps


class RetryTests(SimpleTestCase):
    def test_classification(self):
        self.assertTrue(is_transient(LLMError("503 Service Unavailable")))
        self.assertTrue(is_transient(LLMError("RESOURCE_EXHAUSTED: quota")))
        self.assertTrue(is_transient(LLMError("Request timed out")))
        self.assertFalse(is_transient(LLMError("400 Bad Request: invalid schema")))
        self.assertFalse(is_transient(LLMError("401 Unauthorized")))
        self.assertFalse(is_transient(LLMError("max tokens 15000 exceeded")))  # "15000" is not a status code

    def test_recovers_after_temporary_errors(self):
        client = Flaky([LLMError("503 Service Unavailable"), LLMError("503 Service Unavailable")])
        result, sleeps = run(client)
        self.assertEqual(result, "ok")
        self.assertEqual(client.calls, 3)
        self.assertEqual(len(sleeps), 2)
        self.assertLess(sleeps[0], sleeps[1])  # backoff grows

    def test_gives_up_with_unavailable(self):
        client = Flaky([LLMError("503 Service Unavailable")] * 10)
        with self.assertRaises(LLMUnavailable):
            run(client, attempts=3)
        self.assertEqual(client.calls, 3)

    def test_permanent_error_is_not_retried(self):
        client = Flaky([LLMError("400 Bad Request")])
        with self.assertRaises(LLMError) as ctx:
            run(client)
        self.assertNotIsInstance(ctx.exception, LLMUnavailable)
        self.assertEqual(client.calls, 1)