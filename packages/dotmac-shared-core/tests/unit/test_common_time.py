"""
Unit tests for dotmac_shared_core.common.time module.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dotmac_shared_core.common.time import isoformat, to_utc, utcnow


class TestUtcNow:
    """Test the utcnow function."""

    def test_returns_datetime(self):
        """Test that utcnow returns a datetime object."""
        result = utcnow()
        assert isinstance(result, datetime)

    def test_returns_utc_timezone(self):
        """Test that utcnow returns UTC timezone."""
        result = utcnow()
        assert result.tzinfo == timezone.utc

    def test_current_time(self):
        """Test that utcnow returns current time."""
        before = datetime.now(timezone.utc)
        result = utcnow()
        after = datetime.now(timezone.utc)

        # Should be between before and after calls
        assert before <= result <= after

    def test_multiple_calls_increase(self):
        """Test that multiple calls show time progression."""
        import time

        time1 = utcnow()
        time.sleep(0.001)  # Sleep 1ms to ensure time difference
        time2 = utcnow()

        assert time2 > time1

    def test_microsecond_precision(self):
        """Test that utcnow includes microsecond precision."""
        result = utcnow()
        # Should have microsecond component
        assert hasattr(result, 'microsecond')


class TestToUtc:
    """Test the to_utc function."""

    def test_naive_datetime_assumed_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        naive_dt = datetime(2023, 6, 15, 12, 0, 0)
        result = to_utc(naive_dt)

        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0

    def test_utc_datetime_unchanged(self):
        """Test that UTC datetime is returned unchanged."""
        utc_dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_utc(utc_dt)

        assert result == utc_dt
        assert result.tzinfo == timezone.utc

    def test_timezone_conversion(self):
        """Test conversion from other timezones to UTC."""
        # Create datetime in Eastern Time (UTC-5 standard, UTC-4 daylight)
        eastern = ZoneInfo("America/New_York")
        et_dt = datetime(2023, 6, 15, 8, 0, 0, tzinfo=eastern)  # Summer (EDT)

        result = to_utc(et_dt)

        assert result.tzinfo == timezone.utc
        # In summer, Eastern is UTC-4, so 8 AM Eastern is 12 PM UTC
        assert result.hour == 12

    def test_different_timezones(self):
        """Test conversion from various timezones."""
        # Pacific Time
        pacific = ZoneInfo("America/Los_Angeles")
        pt_dt = datetime(2023, 6, 15, 5, 0, 0, tzinfo=pacific)  # Summer (PDT)
        result = to_utc(pt_dt)
        # In summer, Pacific is UTC-7, so 5 AM Pacific is 12 PM UTC
        assert result.hour == 12
        assert result.tzinfo == timezone.utc

    def test_fixed_offset_timezone(self):
        """Test conversion from fixed offset timezone."""
        from datetime import timedelta

        # Create timezone with +5 hours offset
        plus_five = timezone(timedelta(hours=5))
        offset_dt = datetime(2023, 6, 15, 17, 0, 0, tzinfo=plus_five)

        result = to_utc(offset_dt)

        assert result.tzinfo == timezone.utc
        # 17:00 +5 is 12:00 UTC
        assert result.hour == 12

    def test_microseconds_preserved(self):
        """Test that microseconds are preserved during conversion."""
        dt = datetime(2023, 6, 15, 12, 0, 0, 123456, tzinfo=timezone.utc)
        result = to_utc(dt)
        assert result.microsecond == 123456


class TestIsoFormat:
    """Test the isoformat function."""

    def test_utc_datetime_formatting(self):
        """Test ISO formatting of UTC datetime."""
        dt = datetime(2023, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = isoformat(dt)

        assert result == "2023-06-15T12:30:45+00:00"

    def test_naive_datetime_formatting(self):
        """Test ISO formatting of naive datetime (treated as UTC)."""
        dt = datetime(2023, 6, 15, 12, 30, 45)
        result = isoformat(dt)

        assert result == "2023-06-15T12:30:45+00:00"

    def test_timezone_datetime_converted(self):
        """Test that timezone-aware datetime is converted to UTC first."""
        from datetime import timedelta

        # Create datetime in +3 timezone
        plus_three = timezone(timedelta(hours=3))
        dt = datetime(2023, 6, 15, 15, 30, 45, tzinfo=plus_three)
        result = isoformat(dt)

        # Should be converted to UTC: 15:30 +3 = 12:30 UTC
        assert result == "2023-06-15T12:30:45+00:00"

    def test_microseconds_handling(self):
        """Test ISO formatting with microseconds."""
        dt = datetime(2023, 6, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
        result = isoformat(dt)

        # Should include microseconds
        assert result == "2023-06-15T12:30:45.123456+00:00"

    def test_zero_microseconds(self):
        """Test ISO formatting with zero microseconds."""
        dt = datetime(2023, 6, 15, 12, 30, 45, 0, tzinfo=timezone.utc)
        result = isoformat(dt)

        # Should not include .000000 for zero microseconds
        assert result == "2023-06-15T12:30:45+00:00"

    def test_various_dates(self):
        """Test ISO formatting with various dates."""
        test_cases = [
            (datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
             "2023-01-01T00:00:00+00:00"),
            (datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
             "2023-12-31T23:59:59+00:00"),
            (datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc),  # Leap year
             "2024-02-29T12:00:00+00:00"),
        ]

        for dt, expected in test_cases:
            result = isoformat(dt)
            assert result == expected


class TestTimeIntegration:
    """Integration tests for time functions working together."""

    def test_utcnow_to_iso(self):
        """Test converting current UTC time to ISO format."""
        now = utcnow()
        iso_str = isoformat(now)

        # Should be valid ISO format
        assert "T" in iso_str
        assert iso_str.endswith("+00:00")

        # Should be able to parse back
        parsed = datetime.fromisoformat(iso_str)
        assert parsed.tzinfo == timezone.utc

    def test_timezone_roundtrip(self):
        """Test timezone conversion roundtrip."""
        # Start with timezone-aware datetime
        eastern = ZoneInfo("America/New_York")
        original = datetime(2023, 6, 15, 8, 0, 0, tzinfo=eastern)

        # Convert to UTC
        utc_dt = to_utc(original)

        # Convert to ISO
        iso_str = isoformat(utc_dt)

        # Parse back
        parsed = datetime.fromisoformat(iso_str)

        # Should equal the UTC version
        assert parsed == utc_dt
        assert parsed.tzinfo == timezone.utc

    def test_full_workflow(self):
        """Test complete workflow of time handling."""
        # Get current time
        current = utcnow()

        # Ensure it's UTC
        utc_time = to_utc(current)

        # Format as ISO
        iso_string = isoformat(utc_time)

        # Parse back and verify
        parsed = datetime.fromisoformat(iso_string)

        assert parsed.tzinfo == timezone.utc
        # Should be very close to original (within seconds due to processing time)
        time_diff = abs((parsed - current).total_seconds())
        assert time_diff < 1.0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_leap_year_handling(self):
        """Test leap year date handling."""
        leap_day = datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc)

        utc_converted = to_utc(leap_day)
        iso_formatted = isoformat(leap_day)

        assert utc_converted.day == 29
        assert "2024-02-29" in iso_formatted

    def test_year_boundaries(self):
        """Test year boundary dates."""
        new_year = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        old_year = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        assert isoformat(new_year) == "2024-01-01T00:00:00+00:00"
        assert isoformat(old_year) == "2023-12-31T23:59:59+00:00"

    def test_dst_transition(self):
        """Test daylight saving time transition."""
        eastern = ZoneInfo("America/New_York")

        # Before DST (standard time, UTC-5)
        before_dst = datetime(2023, 3, 11, 6, 0, 0, tzinfo=eastern)
        # After DST (daylight time, UTC-4)
        after_dst = datetime(2023, 3, 13, 6, 0, 0, tzinfo=eastern)

        utc_before = to_utc(before_dst)
        utc_after = to_utc(after_dst)

        # Before DST: 6 AM EST = 11 AM UTC
        # After DST: 6 AM EDT = 10 AM UTC
        assert utc_before.hour == 11  # Standard time
        assert utc_after.hour == 10   # Daylight time
