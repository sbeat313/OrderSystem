import tempfile
import unittest

from booking_manager import BookingManager


class BookingManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = BookingManager(db_path=f"{self.tmp.name}/test.db")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_seed_venues(self):
        venues = self.manager.list_venues()
        self.assertEqual(len(venues), 6)
        self.assertEqual(venues[0].name, "1號場")

    def test_seed_purposes(self):
        purposes = self.manager.list_purposes()
        self.assertEqual(
            [p.name for p in purposes],
            ["單月租", "雙月租", "臨租", "月租球友續租", "股東價", "連假專案", "寒暑假專案", "過年專案"],
        )

    def test_add_booking_success(self):
        booking = self.manager.add_booking(
            venue_id=1,
            customer="王小明",
            purpose="臨租",
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertEqual(booking.booking_id, 1)
        self.assertEqual(len(self.manager.list_bookings("2026-04-01")), 1)

    def test_conflict_booking_raises_error(self):
        self.manager.add_booking(1, "王小明", "2026-04-01 09:00", "2026-04-01 11:00", "臨租")
        with self.assertRaises(ValueError):
            self.manager.add_booking(1, "李小華", "2026-04-01 10:30", "2026-04-01 12:00", "臨租")

    def test_persistence(self):
        self.manager.add_booking(2, "王小明", "2026-04-01 09:00", "2026-04-01 10:00", "臨租")
        manager2 = BookingManager(db_path=f"{self.tmp.name}/test.db")
        self.assertEqual(len(manager2.list_bookings("2026-04-01")), 1)


if __name__ == "__main__":
    unittest.main()

