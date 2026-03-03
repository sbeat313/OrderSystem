from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse

from booking_manager import Booking, BookingManager, TIME_FORMAT

manager = BookingManager()
manager_lock = Lock()


def booking_to_dict(booking: Booking) -> dict:
    return {
        "booking_id": booking.booking_id,
        "venue": booking.venue,
        "customer": booking.customer,
        "start_time": booking.start_time.strftime(TIME_FORMAT),
        "end_time": booking.end_time.strftime(TIME_FORMAT),
    }


HTML_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>場地預定管理</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; color: #1f2937; }
    h1 { margin-bottom: 8px; }
    .wrap { display: grid; grid-template-columns: 340px 1fr; gap: 20px; }
    .panel { border: 1px solid #d1d5db; border-radius: 8px; padding: 14px; }
    label { display: block; margin: 8px 0 4px; font-weight: 600; }
    input, button { width: 100%; padding: 8px; box-sizing: border-box; }
    button { margin-top: 10px; background: #2563eb; color: white; border: 0; border-radius: 6px; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .msg { margin-top: 10px; min-height: 20px; font-size: 14px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { border: 1px solid #e5e7eb; vertical-align: top; padding: 6px; height: 110px; }
    th { background: #f3f4f6; }
    .day-num { font-weight: 700; margin-bottom: 4px; }
    .event { font-size: 12px; background: #eff6ff; border-left: 3px solid #2563eb; margin: 2px 0; padding: 2px 4px; border-radius: 3px; }
    .toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
    .toolbar input { width: auto; }
  </style>
</head>
<body>
  <h1>場地預定管理（Web）</h1>
  <div class="wrap">
    <div class="panel">
      <h3>新增預約</h3>
      <label>場地名稱</label>
      <input id="venue" placeholder="例如：A館" />

      <label>預約人</label>
      <input id="customer" placeholder="例如：王小明" />

      <label>開始時間</label>
      <input id="start" type="datetime-local" />

      <label>結束時間</label>
      <input id="end" type="datetime-local" />

      <button id="add-btn">新增預約</button>
      <div class="msg" id="msg"></div>
    </div>

    <div class="panel">
      <div class="toolbar">
        <label for="month">月份：</label>
        <input id="month" type="month" />
      </div>
      <table id="calendar"></table>
    </div>
  </div>

<script>
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

function toServerFormat(v) {
  return v.replace("T", " ");
}

function parseServerDate(s) {
  return new Date(s.replace(" ", "T") + ":00");
}

async function fetchBookings() {
  const resp = await fetch('/api/bookings');
  return await resp.json();
}

function renderCalendar(bookings) {
  const monthInput = document.getElementById('month');
  const [year, month] = monthInput.value.split('-').map(Number);
  const firstDay = new Date(year, month - 1, 1);
  const lastDate = new Date(year, month, 0).getDate();
  const startWeekday = firstDay.getDay();

  const byDay = {};
  for (const b of bookings) {
    const start = parseServerDate(b.start_time);
    if (start.getFullYear() === year && start.getMonth() === month - 1) {
      const d = start.getDate();
      if (!byDay[d]) byDay[d] = [];
      byDay[d].push(b);
    }
  }

  const cal = document.getElementById('calendar');
  cal.innerHTML = '';

  const head = document.createElement('tr');
  for (const w of WEEKDAYS) {
    const th = document.createElement('th');
    th.textContent = w;
    head.appendChild(th);
  }
  cal.appendChild(head);

  let day = 1;
  for (let row = 0; row < 6; row++) {
    const tr = document.createElement('tr');
    for (let col = 0; col < 7; col++) {
      const td = document.createElement('td');
      if ((row === 0 && col < startWeekday) || day > lastDate) {
        tr.appendChild(td);
        continue;
      }

      const num = document.createElement('div');
      num.className = 'day-num';
      num.textContent = day;
      td.appendChild(num);

      const events = (byDay[day] || []).sort((a, b) => a.start_time.localeCompare(b.start_time));
      for (const e of events) {
        const div = document.createElement('div');
        div.className = 'event';
        div.textContent = `${e.start_time.slice(11)}-${e.end_time.slice(11)} ${e.venue} (${e.customer})`;
        td.appendChild(div);
      }

      day += 1;
      tr.appendChild(td);
    }
    cal.appendChild(tr);
    if (day > lastDate) break;
  }
}

async function reload() {
  const bookings = await fetchBookings();
  renderCalendar(bookings);
}

document.getElementById('add-btn').addEventListener('click', async () => {
  const msg = document.getElementById('msg');
  msg.textContent = '';

  const payload = {
    venue: document.getElementById('venue').value.trim(),
    customer: document.getElementById('customer').value.trim(),
    start: toServerFormat(document.getElementById('start').value),
    end: toServerFormat(document.getElementById('end').value),
  };

  const resp = await fetch('/api/bookings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await resp.json();
  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '新增失敗';
    return;
  }

  msg.style.color = '#16a34a';
  msg.textContent = `新增成功，編號 #${data.booking_id}`;
  await reload();
});

document.getElementById('month').addEventListener('change', reload);

(function init() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  document.getElementById('month').value = `${now.getFullYear()}-${month}`;
  reload();
})();
</script>
</body>
</html>
"""


class BookingWebHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(HTML_PAGE)
            return

        if parsed.path == "/api/bookings":
            with manager_lock:
                bookings = [booking_to_dict(b) for b in manager.list_bookings()]
            self._send_json(bookings)
            return

        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/bookings":
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
            for field in ["venue", "customer", "start", "end"]:
                if not str(payload.get(field, "")).strip():
                    raise ValueError(f"缺少必要欄位：{field}")

            with manager_lock:
                booking = manager.add_booking(
                    venue=payload["venue"],
                    customer=payload["customer"],
                    start=payload["start"],
                    end=payload["end"],
                )
            self._send_json(booking_to_dict(booking), status=HTTPStatus.CREATED)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)


def run_web_app(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), BookingWebHandler)
    print(f"伺服器已啟動：http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_web_app()
