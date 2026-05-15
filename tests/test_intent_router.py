import unittest

from intent_router import IntentRouter, normalize_text


class IntentRouterTest(unittest.TestCase):
    def test_direct_camera_close(self):
        intent = IntentRouter().route("fechar a câmera", now=100)

        self.assertEqual(intent.action, "fechar")
        self.assertEqual(intent.target, "camera")
        self.assertFalse(intent.needs_clarification)

    def test_pending_close_completed_by_target(self):
        router = IntentRouter()

        first = router.route("fechar", now=100)
        second = router.route("a câmera", now=104)

        self.assertTrue(first.needs_clarification)
        self.assertEqual(second.action, "fechar")
        self.assertEqual(second.target, "camera")
        self.assertEqual(second.source, "pending_context")

    def test_recent_context_closes_camera(self):
        router = IntentRouter()

        router.route("abre a camera", now=100)
        intent = router.route("fecha", now=105)

        self.assertEqual(intent.action, "fechar")
        self.assertEqual(intent.target, "camera")
        self.assertEqual(intent.source, "recent_context")

    def test_plain_close_without_context_asks(self):
        intent = IntentRouter().route("fecha", now=100)

        self.assertTrue(intent.needs_clarification)
        self.assertIsNone(intent.target)

    def test_shutdown_requires_rony_or_farewell(self):
        router = IntentRouter()

        shutdown = router.route("fecha o Rony", now=100)
        ambiguous = router.route("fecha", now=120)

        self.assertEqual(shutdown.target, "rony")
        self.assertTrue(ambiguous.needs_clarification)

    def test_normalize_text_removes_accents(self):
        self.assertEqual(normalize_text("Câmera, por favor!"), "camera por favor")


if __name__ == "__main__":
    unittest.main()
