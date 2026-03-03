from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

TIME_FORMAT = "%Y-%m-%d %H:%M"


@dataclass
class Booking:
    booking_id: int
    venue: str
    customer: str
    start_time: datetime
    end_time: datetime

    def overlaps(self, other: "Booking") -> bool:
        if self.venue != other.venue:
            return False
        return self.start_time < other.end_time and other.start_time < self.end_time


class BookingManager:
    def __init__(self) -> None:
        self._bookings: Dict[int, Booking] = {}
        self._next_id = 1

    def add_booking(self, venue: str, customer: str, start: str, end: str) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        new_booking = Booking(
            booking_id=self._next_id,
            venue=venue.strip(),
            customer=customer.strip(),
            start_time=start_time,
            end_time=end_time,
        )
        self._assert_no_conflict(new_booking)
        self._bookings[new_booking.booking_id] = new_booking
        self._next_id += 1
        return new_booking

    def cancel_booking(self, booking_id: int) -> bool:
        return self._bookings.pop(booking_id, None) is not None

    def list_bookings(self, venue: str | None = None) -> List[Booking]:
        items = list(self._bookings.values())
        if venue:
            items = [booking for booking in items if booking.venue == venue]
        return sorted(items, key=lambda booking: booking.start_time)

    def _assert_no_conflict(self, candidate: Booking) -> None:
        for existing in self._bookings.values():
            if existing.overlaps(candidate):
                raise ValueError(
                    "時段衝突："
                    f"{existing.venue} 已有預約 "
                    f"({existing.start_time.strftime(TIME_FORMAT)} - "
                    f"{existing.end_time.strftime(TIME_FORMAT)})"
                )

    @staticmethod
    def _parse_time_range(start: str, end: str) -> tuple[datetime, datetime]:
        try:
            start_time = datetime.strptime(start.strip(), TIME_FORMAT)
            end_time = datetime.strptime(end.strip(), TIME_FORMAT)
        except ValueError as exc:
            raise ValueError(f"時間格式錯誤，請使用 {TIME_FORMAT}") from exc

        if end_time <= start_time:
            raise ValueError("結束時間必須晚於開始時間")

        return start_time, end_time


def print_bookings(bookings: List[Booking]) -> None:
    if not bookings:
        print("目前沒有預約資料。")
        return

    print("\n=== 預約清單 ===")
    for booking in bookings:
        print(
            f"#{booking.booking_id} | {booking.venue} | {booking.customer} | "
            f"{booking.start_time.strftime(TIME_FORMAT)} -> "
            f"{booking.end_time.strftime(TIME_FORMAT)}"
        )


def run_cli() -> None:
    manager = BookingManager()
    menu = """
場地預定管理系統
1) 新增預約
2) 查看全部預約
3) 依場地查詢
4) 取消預約
5) 離開
"""

    while True:
        print(menu)
        choice = input("請輸入選項：").strip()

        if choice == "1":
            try:
                venue = input("場地名稱：")
                customer = input("預約人：")
                start = input(f"開始時間 ({TIME_FORMAT})：")
                end = input(f"結束時間 ({TIME_FORMAT})：")
                booking = manager.add_booking(venue, customer, start, end)
                print(f"新增成功！預約編號：{booking.booking_id}")
            except ValueError as exc:
                print(f"新增失敗：{exc}")

        elif choice == "2":
            print_bookings(manager.list_bookings())

        elif choice == "3":
            venue = input("請輸入場地名稱：").strip()
            print_bookings(manager.list_bookings(venue=venue))

        elif choice == "4":
            booking_id = input("請輸入要取消的預約編號：").strip()
            if booking_id.isdigit() and manager.cancel_booking(int(booking_id)):
                print("取消成功。")
            else:
                print("找不到該預約編號。")

        elif choice == "5":
            print("感謝使用，再見！")
            break

        else:
            print("無效選項，請重新輸入。")


if __name__ == "__main__":
    run_cli()
