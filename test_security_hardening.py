import os
import sys
import unittest
import html
import re

from pydantic import ValidationError
from database import (
    encrypt_sensitive, decrypt_sensitive,
    verify_user_ownership, create_weakness_profile,
    generate_adaptive_practice, submit_practice_answer,
    complete_practice_session
)
from app import (
    ConceptPracticeRequest, PracticeAnswerRequest,
    detect_cheating_attempt, log_security_event,
    check_ip_rate_limit, generate_signed_token,
    verify_signed_token
)

class TestSecurityHardening(unittest.TestCase):

    def test_jwt_signed_token_roundtrip(self):
        payload = {"user_id": 42, "email": "test@bennett.edu.in", "role": "student"}
        token = generate_signed_token(payload, exp_seconds=3600)
        self.assertIn(".", token)
        verified = verify_signed_token(token)
        self.assertIsNotNone(verified)
        self.assertEqual(verified["user_id"], 42)
        self.assertEqual(verified["email"], "test@bennett.edu.in")

    def test_signed_token_tamper_defense(self):
        payload = {"user_id": 42, "email": "test@bennett.edu.in"}
        token = generate_signed_token(payload, exp_seconds=3600)
        parts = token.split(".")
        tampered_token = parts[0] + "tampered." + parts[1]
        self.assertIsNone(verify_signed_token(tampered_token))

    def test_concept_request_anti_sql_injection(self):
        # Valid concept
        req = ConceptPracticeRequest(concept="Eigenvalues and Eigenvectors", difficulty="hard")
        self.assertEqual(req.concept, "Eigenvalues and Eigenvectors")
        self.assertEqual(req.difficulty, "hard")

        # Dangerous SQL injection patterns must be blocked
        with self.assertRaises(ValidationError):
            ConceptPracticeRequest(concept="Entropy; DROP TABLE users;--", difficulty="easy")

        # Invalid difficulty enum
        with self.assertRaises(ValidationError):
            ConceptPracticeRequest(concept="Entropy", difficulty="god_mode")

    def test_answer_submission_xss_sanitization(self):
        malicious_input = '<script>alert("hacked")</script><b>True</b>'
        req = PracticeAnswerRequest(
            question_id=1,
            user_answer=malicious_input,
            time_taken=20,
            user_email="student@bennett.edu.in"
        )
        # Verify script tags are stripped and HTML is escaped
        self.assertNotIn("<script>", req.user_answer)
        self.assertNotIn("</script>", req.user_answer)
        self.assertIn("&lt;b&gt;True&lt;/b&gt;", req.user_answer)

    def test_answer_submission_time_bounds(self):
        # Negative time must fail
        with self.assertRaises(ValidationError):
            PracticeAnswerRequest(question_id=1, user_answer="A", time_taken=-5)

        # > 1 hour time must fail
        with self.assertRaises(ValidationError):
            PracticeAnswerRequest(question_id=1, user_answer="A", time_taken=4000)

    def test_data_encryption_at_rest_roundtrip(self):
        secret_payload = "Option B: Closed-loop transfer function pole stability"
        encrypted = encrypt_sensitive(secret_payload)
        self.assertNotEqual(secret_payload, encrypted)
        decrypted = decrypt_sensitive(encrypted)
        self.assertEqual(secret_payload, decrypted)

    def test_rate_limiter_sliding_window(self):
        test_ip = "192.168.1.99"
        # Allow 3 requests
        self.assertTrue(check_ip_rate_limit(test_ip, "test_route", max_requests=3, window_seconds=60))
        self.assertTrue(check_ip_rate_limit(test_ip, "test_route", max_requests=3, window_seconds=60))
        self.assertTrue(check_ip_rate_limit(test_ip, "test_route", max_requests=3, window_seconds=60))
        # 4th request must be rate-limited
        self.assertFalse(check_ip_rate_limit(test_ip, "test_route", max_requests=3, window_seconds=60))

    def test_cheating_detector_anomaly(self):
        # Under 2 seconds triggers security flag
        flagged = detect_cheating_attempt(session_id=101, user_email="speedrunner@bennett.edu.in", time_taken=1)
        self.assertTrue(flagged)

        # Reasonable time does not trigger
        normal = detect_cheating_attempt(session_id=101, user_email="speedrunner@bennett.edu.in", time_taken=25)
        self.assertFalse(normal)

if __name__ == "__main__":
    unittest.main()
