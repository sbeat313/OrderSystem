from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
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
class ExtraIncome:
    income_id: int
    customer: str
    item: str
    amount: float
    note: str
    income_time: datetime
    contact_phone: str = ""
    racket_model: str = ""
    string_tension: Optional[int] = None
    payment_status: str = ""
    racket_status: str = ""
    pickup_date: str = ""

@dataclass
class Booking:
    booking_id: int
    venue_id: int
    venue_name: str
    customer: str
    purpose: str
    price: float
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
                    price REAL NOT NULL DEFAULT 0,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    FOREIGN KEY (venue_id) REFERENCES venues(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS extra_incomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer TEXT NOT NULL,
                    item TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    income_time TEXT NOT NULL,
                    contact_phone TEXT NOT NULL DEFAULT '',
                    racket_model TEXT NOT NULL DEFAULT '',
                    string_tension INTEGER,
                    payment_status TEXT NOT NULL DEFAULT '',
                    racket_status TEXT NOT NULL DEFAULT '',
                    pickup_date TEXT NOT NULL DEFAULT ''
                )
                """
            )
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()]
            if "price" not in columns:
                conn.execute("ALTER TABLE bookings ADD COLUMN price REAL NOT NULL DEFAULT 0")
            if "rental_group_id" not in columns:
                conn.execute("ALTER TABLE bookings ADD COLUMN rental_group_id TEXT")

            extra_columns = [row["name"] for row in conn.execute("PRAGMA table_info(extra_incomes)").fetchall()]
            if "contact_phone" not in extra_columns:
                conn.execute("ALTER TABLE extra_incomes ADD COLUMN contact_phone TEXT NOT NULL DEFAULT ''")
            if "racket_model" not in extra_columns:
                conn.execute("ALTER TABLE extra_incomes ADD COLUMN racket_model TEXT NOT NULL DEFAULT ''")
            if "string_tension" not in extra_columns:
                conn.execute("ALTER TABLE extra_incomes ADD COLUMN string_tension INTEGER")
            if "payment_status" not in extra_columns:
                conn.execute("ALTER TABLE extra_incomes ADD COLUMN payment_status TEXT NOT NULL DEFAULT ''")
            if "racket_status" not in extra_columns:
                conn.execute("ALTER TABLE extra_incomes ADD COLUMN racket_status TEXT NOT NULL DEFAULT ''")
            if "pickup_date" not in extra_columns:
                conn.execute("ALTER TABLE extra_incomes ADD COLUMN pickup_date TEXT NOT NULL DEFAULT ''")

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
        price: float = 0,
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
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
                INSERT INTO bookings(venue_id, customer, purpose, price, start_time, end_time, rental_group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    booking_price,
                    start_time.strftime(TIME_FORMAT),
                    end_time.strftime(TIME_FORMAT),
                    None,
                ),
            )
            booking_id = cursor.lastrowid

        return Booking(
            booking_id=booking_id,
            venue_id=venue["id"],
            venue_name=venue["name"],
            customer=customer.strip(),
            purpose=purpose_name,
            price=booking_price,
            start_time=start_time,
            end_time=end_time,
        )

    def add_bookings_for_purpose(
        self,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
        price: float = 0,
    ) -> List[Booking]:
        purpose_name = purpose.strip()
        if purpose_name not in {"單月租", "雙月租"}:
            return [self.add_booking(venue_id, customer, start, end, purpose, price)]

        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        duration = end_time - start_time
        period_end = self._month_end(start_time)
        if purpose_name == "雙月租":
            period_end = self._month_end(self._next_month_start(start_time))

        slot_starts: List[datetime] = []
        cursor = start_time
        while cursor.date() <= period_end.date():
            slot_starts.append(cursor)
            cursor += timedelta(days=7)

        with self._connect() as conn:
            group_id = str(uuid.uuid4())
            venue = conn.execute("SELECT id, name FROM venues WHERE id = ?", (venue_id,)).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_row = conn.execute("SELECT 1 FROM purposes WHERE name = ?", (purpose_name,)).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            for slot_start in slot_starts:
                slot_end = slot_start + duration
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
                        slot_end.strftime(TIME_FORMAT),
                        slot_start.strftime(TIME_FORMAT),
                    ),
                ).fetchone()
                if conflict:
                    raise ValueError(
                        f"時段衝突：{venue['name']} 已有預約 "
                        f"({conflict['start_time']} - {conflict['end_time']})"
                    )

            created: List[Booking] = []
            for slot_start in slot_starts:
                slot_end = slot_start + duration
                cursor = conn.execute(
                    """
                    INSERT INTO bookings(venue_id, customer, purpose, price, start_time, end_time, rental_group_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        venue_id,
                        customer.strip(),
                        purpose_name,
                        booking_price,
                        slot_start.strftime(TIME_FORMAT),
                        slot_end.strftime(TIME_FORMAT),
                        group_id,
                    ),
                )
                created.append(
                    Booking(
                        booking_id=cursor.lastrowid,
                        venue_id=venue["id"],
                        venue_name=venue["name"],
                        customer=customer.strip(),
                        purpose=purpose_name,
                        price=booking_price,
                        start_time=slot_start,
                        end_time=slot_end,
                    )
                )

        return created

    def cancel_booking(self, booking_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, venue_id, customer, purpose, start_time, end_time, rental_group_id
                FROM bookings
                WHERE id = ?
                """,
                (booking_id,),
            ).fetchone()
            if row is None:
                return False

            if row["purpose"] in {"單月租", "雙月租"}:
                if row["rental_group_id"]:
                    cur = conn.execute(
                        "DELETE FROM bookings WHERE rental_group_id = ?",
                        (row["rental_group_id"],),
                    )
                    return cur.rowcount > 0

                start_time = datetime.strptime(row["start_time"], TIME_FORMAT)
                period_end = self._month_end(start_time)
                if row["purpose"] == "雙月租":
                    period_end = self._month_end(self._next_month_start(start_time))

                cur = conn.execute(
                    """
                    DELETE FROM bookings
                    WHERE venue_id = ?
                      AND customer = ?
                      AND purpose = ?
                      AND date(start_time) BETWEEN date(?) AND date(?)
                      AND time(start_time) = time(?)
                      AND time(end_time) = time(?)
                    """,
                    (
                        row["venue_id"],
                        row["customer"],
                        row["purpose"],
                        start_time.strftime("%Y-%m-%d"),
                        period_end.strftime("%Y-%m-%d"),
                        row["start_time"],
                        row["end_time"],
                    ),
                )
                return cur.rowcount > 0

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
        price: float = 0,
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
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
                SET venue_id = ?, customer = ?, purpose = ?, price = ?, start_time = ?, end_time = ?
                WHERE id = ?
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    booking_price,
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
            price=booking_price,
            start_time=start_time,
            end_time=end_time,
        )

    def list_bookings(self, date: Optional[str] = None) -> List[Booking]:
        query = (
            "SELECT b.id, b.venue_id, v.name AS venue_name, b.customer, b.purpose, b.price, b.start_time, b.end_time "
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
                price=float(row["price"]),
                start_time=datetime.strptime(row["start_time"], TIME_FORMAT),
                end_time=datetime.strptime(row["end_time"], TIME_FORMAT),
            )
            for row in rows
        ]

    def summarize_fees(self, start_date: str, end_date: str, customer: str = "") -> List[dict]:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD") from exc
        if end_date < start_date:
            raise ValueError("結束日期不可早於開始日期")

        customer_name = customer.strip()
        query = """
            SELECT b.customer, COUNT(*) AS booking_count, SUM(b.price) AS total_fee
            FROM bookings b
            WHERE date(b.start_time) BETWEEN date(?) AND date(?)
        """
        params: tuple = (start_date, end_date)
        if customer_name:
            query += " AND b.customer = ?"
            params = (start_date, end_date, customer_name)
        query += " GROUP BY b.customer ORDER BY total_fee DESC, b.customer"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "customer": row["customer"],
                "booking_count": int(row["booking_count"]),
                "total_fee": float(row["total_fee"] or 0),
            }
            for row in rows
        ]

    def add_extra_income(
        self,
        customer: str,
        item: str,
        amount: float,
        income_time: str,
        note: str = "",
        contact_phone: str = "",
        racket_model: str = "",
        string_tension: Optional[int] = None,
        payment_status: str = "",
        racket_status: str = "",
        pickup_date: str = "",
    ) -> ExtraIncome:
        customer_name = customer.strip()
        item_name = item.strip()
        memo = note.strip()
        phone = contact_phone.strip()
        racket = racket_model.strip()
        paid_status = payment_status.strip()
        racket_state = racket_status.strip()
        pickup = pickup_date.strip()
        if not customer_name:
            raise ValueError("姓名不可為空")
        if not item_name:
            raise ValueError("項目不可為空")

        try:
            dt = datetime.strptime(income_time.strip(), TIME_FORMAT)
        except ValueError as exc:
            raise ValueError(f"時間格式錯誤，請使用 {TIME_FORMAT}") from exc
        income_amount = self._parse_price(amount)

        tension_value: Optional[int] = None
        if string_tension not in (None, ""):
            try:
                tension_value = int(string_tension)
            except (TypeError, ValueError) as exc:
                raise ValueError("磅數格式錯誤") from exc
            if tension_value <= 0:
                raise ValueError("磅數必須為正整數")

        if item_name == "球拍":
            if not racket:
                raise ValueError("球拍項目需填寫穿線項目")
            if tension_value is None:
                raise ValueError("球拍項目需填寫磅數")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO extra_incomes(
                    customer, item, amount, note, income_time,
                    contact_phone, racket_model, string_tension, payment_status, racket_status, pickup_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_name,
                    item_name,
                    income_amount,
                    memo,
                    dt.strftime(TIME_FORMAT),
                    phone,
                    racket,
                    tension_value,
                    paid_status,
                    racket_state,
                    pickup,
                ),
            )
            income_id = cursor.lastrowid

        return ExtraIncome(
            income_id=income_id,
            customer=customer_name,
            item=item_name,
            amount=income_amount,
            note=memo,
            income_time=dt,
            contact_phone=phone,
            racket_model=racket,
            string_tension=tension_value,
            payment_status=paid_status,
            racket_status=racket_state,
            pickup_date=pickup,
        )

    def update_extra_income(
        self,
        income_id: int,
        customer: str,
        item: str,
        amount: float,
        income_time: str,
        note: str = "",
        contact_phone: str = "",
        racket_model: str = "",
        string_tension: Optional[int] = None,
        payment_status: str = "",
        racket_status: str = "",
        pickup_date: str = "",
    ) -> ExtraIncome:
        if income_id <= 0:
            raise ValueError("收入資料不存在")

        customer_name = customer.strip()
        item_name = item.strip()
        memo = note.strip()
        phone = contact_phone.strip()
        racket = racket_model.strip()
        paid_status = payment_status.strip()
        racket_state = racket_status.strip()
        pickup = pickup_date.strip()
        if not customer_name:
            raise ValueError("姓名不可為空")
        if not item_name:
            raise ValueError("項目不可為空")

        try:
            dt = datetime.strptime(income_time.strip(), TIME_FORMAT)
        except ValueError as exc:
            raise ValueError(f"時間格式錯誤，請使用 {TIME_FORMAT}") from exc
        income_amount = self._parse_price(amount)

        tension_value: Optional[int] = None
        if string_tension not in (None, ""):
            try:
                tension_value = int(string_tension)
            except (TypeError, ValueError) as exc:
                raise ValueError("磅數格式錯誤") from exc
            if tension_value <= 0:
                raise ValueError("磅數必須為正整數")

        if item_name == "球拍":
            if not racket:
                raise ValueError("球拍項目需填寫穿線項目")
            if tension_value is None:
                raise ValueError("球拍項目需填寫磅數")

        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE extra_incomes
                SET customer = ?, item = ?, amount = ?, note = ?, income_time = ?,
                    contact_phone = ?, racket_model = ?, string_tension = ?, payment_status = ?,
                    racket_status = ?, pickup_date = ?
                WHERE id = ?
                """,
                (
                    customer_name,
                    item_name,
                    income_amount,
                    memo,
                    dt.strftime(TIME_FORMAT),
                    phone,
                    racket,
                    tension_value,
                    paid_status,
                    racket_state,
                    pickup,
                    income_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("收入資料不存在")

        return ExtraIncome(
            income_id=income_id,
            customer=customer_name,
            item=item_name,
            amount=income_amount,
            note=memo,
            income_time=dt,
            contact_phone=phone,
            racket_model=racket,
            string_tension=tension_value,
            payment_status=paid_status,
            racket_status=racket_state,
            pickup_date=pickup,
        )

    def list_extra_incomes(
        self,
        start_date: str = "",
        end_date: str = "",
        customer: str = "",
    ) -> List[ExtraIncome]:
        query = (
            "SELECT id, customer, item, amount, note, income_time, "
            "contact_phone, racket_model, string_tension, payment_status, racket_status, pickup_date "
            "FROM extra_incomes WHERE 1=1"
        )
        params: List[str] = []
        if start_date:
            query += " AND date(income_time) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(income_time) <= date(?)"
            params.append(end_date)
        if customer.strip():
            query += " AND customer = ?"
            params.append(customer.strip())
        query += " ORDER BY income_time DESC, id DESC"

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [
            ExtraIncome(
                income_id=row["id"],
                customer=row["customer"],
                item=row["item"],
                amount=float(row["amount"] or 0),
                note=row["note"] or "",
                income_time=datetime.strptime(row["income_time"], TIME_FORMAT),
                contact_phone=row["contact_phone"] or "",
                racket_model=row["racket_model"] or "",
                string_tension=(int(row["string_tension"]) if row["string_tension"] is not None else None),
                payment_status=row["payment_status"] or "",
                racket_status=row["racket_status"] or "",
                pickup_date=row["pickup_date"] or "",
            )
            for row in rows
        ]

    def delete_extra_income(self, income_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM extra_incomes WHERE id = ?", (income_id,))
            return cur.rowcount > 0

    @staticmethod
    def _parse_price(price: float) -> float:
        try:
            value = float(price)
        except (TypeError, ValueError) as exc:
            raise ValueError("價錢格式錯誤") from exc
        if value < 0:
            raise ValueError("價錢不可為負數")
        return value

    @staticmethod
    def _month_end(dt: datetime) -> datetime:
        next_month = BookingManager._next_month_start(dt)
        return next_month - timedelta(days=1)

    @staticmethod
    def _next_month_start(dt: datetime) -> datetime:
        year = dt.year + 1 if dt.month == 12 else dt.year
        month = 1 if dt.month == 12 else dt.month + 1
        return datetime(year, month, 1, dt.hour, dt.minute)

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
                    price=input("價錢：").strip() or 0,
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
                    f"~{b.end_time.strftime(TIME_FORMAT)} {b.customer}/{b.purpose}/$ {b.price:.0f}"
                )
        elif choice == "3":
            booking_id = input("預約編號：").strip()
            print("取消成功" if booking_id.isdigit() and manager.cancel_booking(int(booking_id)) else "找不到編號")
        elif choice == "4":
            break


if __name__ == "__main__":
    run_cli()
