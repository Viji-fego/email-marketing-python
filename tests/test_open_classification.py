"""Tests for open event classification and prefetch detection."""

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pytest

from app.services.event_processor import (
    classify_open_event,
    is_stale_user_agent,
    has_scanner_pattern,
)


class TestOpenClassification:
    """Test suite for open event classification."""

    def test_classify_fast_open_as_prefetch(self):
        """Open within 5 seconds of send = likely_prefetch."""
        now = datetime.now(tz=timezone.utc)
        payload = {
            "ts_event": int(now.timestamp()),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        contact = Mock()
        contact.sent_at = now - timedelta(seconds=3)

        result = classify_open_event(payload, contact, prefetch_threshold_seconds=10)
        assert result == "likely_prefetch", "Fast opens should be classified as prefetch"

    def test_classify_normal_timing_open_as_genuine(self):
        """Open after normal delay + modern browser = genuine."""
        now = datetime.now(tz=timezone.utc)
        payload = {
            "ts_event": int(now.timestamp()),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.6099.129 Safari/537.36"
        }
        contact = Mock()
        contact.sent_at = now - timedelta(minutes=5)

        result = classify_open_event(payload, contact, prefetch_threshold_seconds=10)
        assert result == "genuine", "Normal timing with modern browser should be genuine"

    def test_classify_stale_chrome_as_bot(self):
        """Chrome version < 90 = likely_bot_scan."""
        now = datetime.now(tz=timezone.utc)
        payload = {
            "ts_event": int((now - timedelta(seconds=100)).timestamp()),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/85.0.4183.102 Safari/537.36"
        }
        contact = Mock()
        contact.sent_at = now - timedelta(seconds=110)

        result = classify_open_event(payload, contact, prefetch_threshold_seconds=10)
        assert result == "likely_bot_scan", "Stale Chrome version should be flagged as bot"

    def test_classify_scanner_ua_as_bot(self):
        """Scanner patterns in UA = likely_bot_scan."""
        now = datetime.now(tz=timezone.utc)
        payload = {
            "ts_event": int((now - timedelta(minutes=5)).timestamp()),
            "user_agent": "python-requests/2.28.0"
        }
        contact = Mock()
        contact.sent_at = now - timedelta(minutes=10)

        result = classify_open_event(payload, contact, prefetch_threshold_seconds=10)
        assert result == "likely_bot_scan", "python-requests should be flagged as bot"

    def test_classify_bot_crawler_pattern(self):
        """Crawler pattern in UA = likely_bot_scan."""
        now = datetime.now(tz=timezone.utc)
        payload = {
            "ts_event": int((now - timedelta(minutes=5)).timestamp()),
            "user_agent": "Mozilla/5.0 Crawler/1.0"
        }
        contact = Mock()
        contact.sent_at = now - timedelta(minutes=10)

        result = classify_open_event(payload, contact, prefetch_threshold_seconds=10)
        assert result == "likely_bot_scan", "Crawler UA should be flagged as bot"


class TestUserAgentDetection:
    """Test suite for stale user-agent detection."""

    def test_is_stale_chrome_85(self):
        """Chrome 85 should be flagged as stale."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/85.0.4183.102 Safari/537.36"
        assert is_stale_user_agent(ua) is True, "Chrome 85 is over 18 months old"

    def test_is_not_stale_chrome_120(self):
        """Chrome 120 should not be flagged as stale."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.6099.129 Safari/537.36"
        assert is_stale_user_agent(ua) is False, "Chrome 120 is recent"

    def test_empty_ua_not_stale(self):
        """Empty user-agent should return False."""
        assert is_stale_user_agent("") is False


class TestScannerDetection:
    """Test suite for scanner pattern detection."""

    def test_has_bot_pattern(self):
        """User-agent containing 'bot' should be detected."""
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1)"
        assert has_scanner_pattern(ua) is True

    def test_has_crawler_pattern(self):
        """User-agent containing 'crawler' should be detected."""
        ua = "Mozilla/5.0 Crawler/1.0"
        assert has_scanner_pattern(ua) is True

    def test_has_python_requests_pattern(self):
        """python-requests should be detected."""
        ua = "python-requests/2.28.0"
        assert has_scanner_pattern(ua) is True

    def test_normal_browser_not_detected(self):
        """Normal browser UA should not be flagged."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.6099.129 Safari/537.36"
        assert has_scanner_pattern(ua) is False

    def test_empty_ua_not_detected(self):
        """Empty user-agent should return False."""
        assert has_scanner_pattern("") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
