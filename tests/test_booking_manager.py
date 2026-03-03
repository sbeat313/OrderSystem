import unittest

from booking_manager import BookingManager


class BookingManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = BookingManager()

    def test_add_booking_success(self):
        booking = self.manager.add_booking(
            venue="A館",
            customer="王小明",
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertEqual(booking.booking_id, 1)
        self.assertEqual(len(self.manager.list_bookings()), 1)

    def test_conflict_booking_raises_error(self):
        self.manager.add_booking("A館", "王小明", "2026-04-01 09:00", "2026-04-01 11:00")
        with self.assertRaises(ValueError):
            self.manager.add_booking("A館", "李小華", "2026-04-01 10:30", "2026-04-01 12:00")

    def test_different_venue_can_overlap(self):
        self.manager.add_booking("A館", "王小明", "2026-04-01 09:00", "2026-04-01 11:00")
        self.manager.add_booking("B館", "李小華", "2026-04-01 10:30", "2026-04-01 12:00")
        self.assertEqual(len(self.manager.list_bookings()), 2)

    def test_cancel_booking(self):
        booking = self.manager.add_booking("A館", "王小明", "2026-04-01 09:00", "2026-04-01 11:00")
        self.assertTrue(self.manager.cancel_booking(booking.booking_id))
        self.assertFalse(self.manager.cancel_booking(999))


if __name__ == "__main__":
    unittest.main()
