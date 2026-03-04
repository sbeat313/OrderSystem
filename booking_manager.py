from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

TIME_FORMAT = "%Y-%m-%d %H:%M"
DEFAULT_DB_PATH = "booking.db"


@dataclass
class Venue:
    venue_id: int
    name: str


@dataclass
class Purpose:
    purpose_id: int
    name: str


@dataclass
class Booking:
    booking_id: int
    venue_id: int
    venue_name: str
    customer: str
    purpose: str
    start_time: datetime
    end_time: datetime


class BookingManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS venues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS purposes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venue_id INTEGER NOT NULL,
                    customer TEXT NOT NULL,
                    purpose TEXT NOT NULL DEFAULT '',
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    FOREIGN KEY (venue_id) REFERENCES venues(id)
                )
                """
            )
            count = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO venues(name) VALUES (?)",
                    [(f"{index}號場",) for index in range(1, 7)],
                )

            purpose_count = conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[0]
            if purpose_count == 0:
                conn.executemany(
                    "INSERT INTO purposes(name) VALUES (?)",
                    [
                        ("單月租",),
                        ("雙月租",),
                        ("臨租",),
                        ("月租球友續租",),
                        ("股東價",),
                        ("連假專案",),
                        ("寒暑假專案",),
                        ("過年專案",),
                    ],
                )

    def list_venues(self) -> List[Venue]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name FROM venues ORDER BY id").fetchall()
        return [Venue(venue_id=row["id"], name=row["name"]) for row in rows]

    def add_venue(self, name: str) -> Venue:
        venue_name = name.strip()
        if not venue_name:
            raise ValueError("場地名稱不可為空")
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO venues(name) VALUES (?)", (venue_name,))
                venue_id = cursor.lastrowid
            return Venue(venue_id=venue_id, name=venue_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("場地名稱不可重複") from exc

    def update_venue(self, venue_id: int, name: str) -> Venue:
        venue_name = name.strip()
        if not venue_name:
            raise ValueError("場地名稱不可為空")
        try:
            with self._connect() as conn:
                cur = conn.execute("UPDATE venues SET name = ? WHERE id = ?", (venue_name, venue_id))
                if cur.rowcount == 0:
                    raise ValueError("場地不存在")
            return Venue(venue_id=venue_id, name=venue_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("場地名稱不可重複") from exc

    def delete_venue(self, venue_id: int) -> bool:
        with self._connect() as conn:
            used = conn.execute("SELECT COUNT(*) FROM bookings WHERE venue_id = ?", (venue_id,)).fetchone()[0]
            if used > 0:
                raise ValueError("此場地已有預約資料，無法刪除")
            cur = conn.execute("DELETE FROM venues WHERE id = ?", (venue_id,))
            return cur.rowcount > 0

    def list_purposes(self) -> List[Purpose]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name FROM purposes ORDER BY id").fetchall()
        return [Purpose(purpose_id=row["id"], name=row["name"]) for row in rows]

    def add_purpose(self, name: str) -> Purpose:
        purpose_name = name.strip()
        if not purpose_name:
            raise ValueError("用途名稱不可為空")
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO purposes(name) VALUES (?)", (purpose_name,))
                purpose_id = cursor.lastrowid
            return Purpose(purpose_id=purpose_id, name=purpose_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("用途名稱不可重複") from exc

    def update_purpose(self, purpose_id: int, name: str) -> Purpose:
        purpose_name = name.strip()
        if not purpose_name:
            raise ValueError("用途名稱不可為空")
        try:
            with self._connect() as conn:
                cur = conn.execute("UPDATE purposes SET name = ? WHERE id = ?", (purpose_name, purpose_id))
                if cur.rowcount == 0:
                    raise ValueError("用途不存在")
            return Purpose(purpose_id=purpose_id, name=purpose_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("用途名稱不可重複") from exc

    def delete_purpose(self, purpose_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT name FROM purposes WHERE id = ?", (purpose_id,)).fetchone()
            if row is None:
                return False
            purpose_name = row["name"]
            used = conn.execute("SELECT COUNT(*) FROM bookings WHERE purpose = ?", (purpose_name,)).fetchone()[0]
            if used > 0:
                raise ValueError("此用途已有預約資料，無法刪除")
            cur = conn.execute("DELETE FROM purposes WHERE id = ?", (purpose_id,))
            return cur.rowcount > 0

    def add_booking(
        self,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        with self._connect() as conn:
            venue = conn.execute(
                "SELECT id, name FROM venues WHERE id = ?", (venue_id,)
            ).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_name = purpose.strip()
            if not purpose_name:
                raise ValueError("用途不可為空")
            purpose_row = conn.execute(
                "SELECT 1 FROM purposes WHERE name = ?",
                (purpose_name,),
            ).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            conflict = conn.execute(
                """
                SELECT b.id, b.start_time, b.end_time
                FROM bookings b
                WHERE b.venue_id = ?
                  AND b.start_time < ?
                  AND b.end_time > ?
                LIMIT 1
                """,
                (
                    venue_id,
                    end_time.strftime(TIME_FORMAT),
                    start_time.strftime(TIME_FORMAT),
                ),
            ).fetchone()
            if conflict:
                raise ValueError(
                    f"時段衝突：{venue['name']} 已有預約 "
                    f"({conflict['start_time']} - {conflict['end_time']})"
                )

            cursor = conn.execute(
                """
                INSERT INTO bookings(venue_id, customer, purpose, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    start_time.strftime(TIME_FORMAT),
                    end_time.strftime(TIME_FORMAT),
                ),
            )
            booking_id = cursor.lastrowid

        return Booking(
            booking_id=booking_id,
            venue_id=venue["id"],
            venue_name=venue["name"],
            customer=customer.strip(),
            purpose=purpose_name,
            start_time=start_time,
            end_time=end_time,
        )

    def cancel_booking(self, booking_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            return cur.rowcount > 0

    def update_booking(
        self,
        booking_id: int,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            if existing is None:
                raise ValueError("預約不存在")

            venue = conn.execute(
                "SELECT id, name FROM venues WHERE id = ?",
                (venue_id,),
            ).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_name = purpose.strip()
            if not purpose_name:
                raise ValueError("用途不可為空")
            purpose_row = conn.execute(
                "SELECT 1 FROM purposes WHERE name = ?",
                (purpose_name,),
            ).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            conflict = conn.execute(
                """
                SELECT b.id, b.start_time, b.end_time
                FROM bookings b
                WHERE b.venue_id = ?
                  AND b.id != ?
                  AND b.start_time < ?
                  AND b.end_time > ?
                LIMIT 1
                """,
                (
                    venue_id,
                    booking_id,
                    end_time.strftime(TIME_FORMAT),
                    start_time.strftime(TIME_FORMAT),
                ),
            ).fetchone()
            if conflict:
                raise ValueError(
                    f"時段衝突：{venue['name']} 已有預約 "
                    f"({conflict['start_time']} - {conflict['end_time']})"
                )

            cur = conn.execute(
                """
                UPDATE bookings
                SET venue_id = ?, customer = ?, purpose = ?, start_time = ?, end_time = ?
                WHERE id = ?
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    start_time.strftime(TIME_FORMAT),
                    end_time.strftime(TIME_FORMAT),
                    booking_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("預約不存在")

        return Booking(
            booking_id=booking_id,
            venue_id=venue["id"],
            venue_name=venue["name"],
            customer=customer.strip(),
            purpose=purpose_name,
            start_time=start_time,
            end_time=end_time,
        )

    def list_bookings(self, date: Optional[str] = None) -> List[Booking]:
        query = (
            "SELECT b.id, b.venue_id, v.name AS venue_name, b.customer, b.purpose, b.start_time, b.end_time "
            "FROM bookings b JOIN venues v ON b.venue_id = v.id"
        )
        params: tuple = ()
        if date:
            query += " WHERE date(b.start_time) = date(?)"
            params = (date,)
        query += " ORDER BY b.start_time, b.venue_id"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            Booking(
                booking_id=row["id"],
                venue_id=row["venue_id"],
                venue_name=row["venue_name"],
                customer=row["customer"],
                purpose=row["purpose"],
                start_time=datetime.strptime(row["start_time"], TIME_FORMAT),
                end_time=datetime.strptime(row["end_time"], TIME_FORMAT),
            )
            for row in rows
        ]

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


def run_cli() -> None:
    manager = BookingManager()
    while True:
        print("\n場地預定管理系統\n1) 新增預約\n2) 查看今日預約\n3) 取消預約\n4) 離開")
        choice = input("請輸入選項：").strip()

        if choice == "1":
            venues = manager.list_venues()
            print("可用場地：")
            for v in venues:
                print(f"{v.venue_id}) {v.name}")
            try:
                purposes = manager.list_purposes()
                print("可用用途：")
                for p in purposes:
                    print(f"- {p.name}")
                booking = manager.add_booking(
                    venue_id=int(input("場地編號：").strip()),
                    customer=input("預約人：").strip(),
                    purpose=input("用途（請輸入完整名稱）：").strip(),
                    start=input(f"開始時間 ({TIME_FORMAT})：").strip(),
                    end=input(f"結束時間 ({TIME_FORMAT})：").strip(),
                )
                print(f"新增成功，預約編號 #{booking.booking_id}")
            except ValueError as exc:
                print(f"新增失敗：{exc}")
        elif choice == "2":
            today = datetime.now().strftime("%Y-%m-%d")
            bookings = manager.list_bookings(date=today)
            if not bookings:
                print("今日無預約")
            for b in bookings:
                print(
                    f"#{b.booking_id} {b.venue_name} {b.start_time.strftime(TIME_FORMAT)}"
                    f"~{b.end_time.strftime(TIME_FORMAT)} {b.customer}/{b.purpose}"
                )
        elif choice == "3":
            booking_id = input("預約編號：").strip()
            print("取消成功" if booking_id.isdigit() and manager.cancel_booking(int(booking_id)) else "找不到編號")
        elif choice == "4":
            break


if __name__ == "__main__":
    run_cli()
