from __future__ import annotations

import json
import os
import secrets
import struct
import zlib
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any, Dict, List, Union
from urllib.parse import parse_qs, urlparse

from booking_manager import Booking, BookingManager, TIME_FORMAT

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

manager = BookingManager()
manager_lock = Lock()


def booking_to_dict(booking: Booking) -> dict:
    return {
        "booking_id": booking.booking_id,
        "venue_id": booking.venue_id,
        "venue_name": booking.venue_name,
        "customer": booking.customer,
        "purpose": booking.purpose,
        "start_time": booking.start_time.strftime(TIME_FORMAT),
        "end_time": booking.end_time.strftime(TIME_FORMAT),
    }


def _to_ascii(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii")


def _start_of_week(date_str: str) -> datetime:
    day = datetime.strptime(date_str, "%Y-%m-%d")
    return day - timedelta(days=(day.weekday()))


def _build_biweekly_export_data(base_date: str) -> dict:
    start = _start_of_week(base_date)
    days = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]
    hours = list(range(8, 22))
    venues = manager.list_venues()

    daily = {}
    for day in days:
        daily[day] = manager.list_bookings(date=day)

    return {"days": days, "hours": hours, "venues": venues, "daily": daily}


def _cell_text(bookings: list, venue_id: int, hour: int, role: str) -> str:
    for b in bookings:
        if b.venue_id != venue_id:
            continue
        if b.start_time.hour <= hour < b.end_time.hour:
            if role == "admin":
                return f"{b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}"
            return "RESERVED"
    return ""


def _bitmap_for_char(ch: str) -> list:
    font = {
        "0": ["111", "101", "101", "101", "111"],
        "1": ["010", "110", "010", "010", "111"],
        "2": ["111", "001", "111", "100", "111"],
        "3": ["111", "001", "111", "001", "111"],
        "4": ["101", "101", "111", "001", "001"],
        "5": ["111", "100", "111", "001", "111"],
        "6": ["111", "100", "111", "101", "111"],
        "7": ["111", "001", "001", "001", "001"],
        "8": ["111", "101", "111", "101", "111"],
        "9": ["111", "101", "111", "001", "111"],
        "-": ["000", "000", "111", "000", "000"],
        ":": ["0", "1", "0", "1", "0"],
        "V": ["101", "101", "101", "101", "010"],
        "R": ["110", "101", "110", "101", "101"],
        "E": ["111", "100", "110", "100", "111"],
        "S": ["111", "100", "111", "001", "111"],
        "D": ["110", "101", "101", "101", "110"],
        " ": ["0", "0", "0", "0", "0"],
        "?": ["111", "001", "010", "000", "010"],
    }
    return font.get(ch, font["?"])


def _draw_text(pixels: bytearray, width: int, height: int, x: int, y: int, text: str) -> None:
    color = (30, 41, 59)
    cursor_x = x
    for ch in _to_ascii(text.upper()):
        bitmap = _bitmap_for_char(ch)
        for row, bits in enumerate(bitmap):
            for col, bit in enumerate(bits):
                if bit != "1":
                    continue
                px = cursor_x + col
                py = y + row
                if 0 <= px < width and 0 <= py < height:
                    idx = (py * width + px) * 3
                    pixels[idx:idx + 3] = bytes(color)
        cursor_x += len(bitmap[0]) + 1


def _draw_rect(pixels: bytearray, width: int, height: int, x: int, y: int, w: int, h: int, color: tuple) -> None:
    for yy in range(max(0, y), min(height, y + h)):
        for xx in range(max(0, x), min(width, x + w)):
            idx = (yy * width + xx) * 3
            pixels[idx:idx + 3] = bytes(color)


def _make_png_export(base_date: str, role: str) -> bytes:
    data = _build_biweekly_export_data(base_date)
    venues = data["venues"]
    days = data["days"]
    hours = data["hours"]
    daily = data["daily"]

    cell_w = 92
    row_h = 14
    cols = 2 + len(venues)
    rows = 1 + len(days) * len(hours)
    width = cols * cell_w
    height = rows * row_h

    pixels = bytearray([255] * (width * height * 3))

    for c in range(cols + 1):
        x = c * cell_w
        _draw_rect(pixels, width, height, x, 0, 1, height, (148, 163, 184))
    for r in range(rows + 1):
        y = r * row_h
        _draw_rect(pixels, width, height, 0, y, width, 1, (148, 163, 184))

    _draw_text(pixels, width, height, 4, 4, "DATE")
    _draw_text(pixels, width, height, cell_w + 4, 4, "TIME")
    for i, v in enumerate(venues):
        _draw_text(pixels, width, height, (i + 2) * cell_w + 4, 4, f"V{v.venue_id}")

    row = 1
    for day in days:
        for hour in hours:
            if hour == hours[0]:
                _draw_text(pixels, width, height, 4, row * row_h + 4, day[5:])
            _draw_text(pixels, width, height, cell_w + 4, row * row_h + 4, f"{hour:02d}-{hour+1:02d}")
            for i, v in enumerate(venues):
                text = _cell_text(daily[day], v.venue_id, hour, role)
                if text:
                    _draw_text(pixels, width, height, (i + 2) * cell_w + 4, row * row_h + 4, text[:12])
            row += 1

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * width * 3:(y + 1) * width * 3])
    compressed = zlib.compress(bytes(raw), level=9)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack("!I", len(payload)) + tag + payload + struct.pack("!I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def _make_pdf_export(base_date: str, role: str) -> bytes:
    data = _build_biweekly_export_data(base_date)
    venues = data["venues"]
    days = data["days"]
    hours = data["hours"]
    daily = data["daily"]

    lines = [f"Biweekly Booking Export ({base_date}) role={role}"]
    for day in days:
        lines.append(f"Date: {day}")
        for hour in hours:
            row = [f"{hour:02d}-{hour+1:02d}"]
            for v in venues:
                txt = _cell_text(daily[day], v.venue_id, hour, role)
                row.append(f"V{v.venue_id}:{txt or '-'}")
            lines.append(" | ".join(row))

    text_lines = [_to_ascii(line).replace("(", "[").replace(")", "]") for line in lines[:85]]
    content = "BT\n/F1 8 Tf\n36 800 Td\n10 TL\n" + "\n".join([f"({ln}) Tj T*" for ln in text_lines]) + "\nET"
    content_bytes = content.encode("latin-1", "replace")

    objs = []
    objs.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objs.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objs.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n")
    objs.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objs.append(f"5 0 obj << /Length {len(content_bytes)} >> stream\n".encode() + content_bytes + b"\nendstream endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
    return bytes(pdf)


HTML_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>場地預約管理</title>
<style>
:root { --border:#d1d5db; --primary:#2563eb; --bg:#f3f6fb; --panel:#ffffff; }
*{ box-sizing:border-box; }
body { font-family: "Noto Sans TC", Arial, sans-serif; margin: 0; background: linear-gradient(160deg,#eef2ff,#f8fafc); color: #111827; }
.container { width: 100%; max-width: 100vw; margin: 0 auto; padding: 14px; }
.title { margin: 0 0 10px; font-size: 28px; letter-spacing: .5px; }
.panel { border: 1px solid var(--border); border-radius: 14px; padding: 14px; background: var(--panel); box-shadow: 0 6px 20px rgba(15,23,42,.06); }
label { display: block; margin-top: 0; font-weight: 700; color: #1f2937; font-size: 14px; }
input, select, button { width: 100%; padding: 10px; margin-top: 6px; border-radius: 8px; border: 1px solid #cbd5e1; }
button { background: var(--primary); color: white; border: none; font-weight: 700; cursor: pointer; }
button:hover { filter: brightness(.96); }
.note { margin-top: 8px; min-height: 20px; font-size: 14px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin-bottom: 10px; }
.toolbar .field { min-width: 150px; }
.toolbar input,.toolbar select { width: auto; min-width: 160px; }
.chip { width:auto; padding:7px 12px; border-radius:999px; border:1px solid #cbd5e1; background:#eef2ff; color:#1e3a8a; font-weight:700; }
.chip.active { background:#1d4ed8; color:#fff; }
.grid-wrap { overflow: auto; max-height: calc(100vh - 260px); }
table { border-collapse: collapse; width: 100%; background: #fff; }
th, td { border: 1px solid #0f172a; text-align: center; font-size: 12px; padding: 4px; min-width: 48px; }
th { background: #f8fafc; height: 30px; position: sticky; top: 0; z-index: 1; }
td.venue { min-width: 76px; font-weight: 700; background: #fff; position: sticky; left: 0; z-index: 1; }
td.slot-time { min-width: 64px; font-weight: 600; background: #f8fafc; }
td.slot { height: 48px; background: #f8fafc; }
td.slot.booked-admin { background: #dcfce7; }
td.slot.booked-user { background: #0ea5e9; color: #fff; }
.badge { display:inline-block; padding:2px 6px; border-radius:999px; font-size:11px; font-weight:700; background:#e2e8f0; }
.small { font-size: 11px; line-height: 1.2; white-space: pre-line; }
.helper { margin: 6px 0 0; font-size: 12px; color: #475569; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.55); display: none; align-items: center; justify-content: center; z-index: 20; }
.modal { width: min(640px, 92vw); background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #cbd5e1; }
.modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.modal-actions { display: flex; gap: 8px; margin-top: 12px; }
.btn-secondary { background: #e2e8f0; color: #111827; }
</style>
</head>
<body>
<div class="container">
  <h2 class="title">暖西羽球館預約系統</h2>
  <div class="panel">
    <div class="toolbar">
      <div class="field">
        <label>日期</label>
        <input id="date" type="date" />
      </div>
      <div class="field">
        <label>顯示模式</label>
        <select id="view-mode">
          <option value="daily">每日</option>
          <option value="weekly">每週</option>
          <option value="biweekly" selected>雙週</option>
        </select>
      </div>
      <button class="chip" id="user-view">使用者檢視</button>
      <button class="chip" id="admin-view">管理員檢視</button>
      <button class="chip" id="options-link" style="display:none;" onclick="location.href='/options'">場地/用途設定</button>
      <button class="chip" id="open-add-modal" style="display:none;">新增預約</button>
      <button class="chip" id="export-png">匯出2週 PNG</button>
      <button class="chip" id="export-pdf">匯出2週 PDF</button>
      <span id="auth-state" class="badge">目前：使用者</span>
    </div>
    <div id="msg" class="note"></div>
    <div class="grid-wrap">
      <table id="grid"></table>
    </div>
  </div>
</div>

<div id="booking-modal" class="modal-backdrop">
  <div class="modal">
    <h3 style="margin-top:0;">新增預約（管理員）</h3>
    <div class="modal-grid">
      <div><label>場地</label><select id="venue"></select></div>
      <div><label>預約人</label><input id="customer" placeholder="例如：江江" /></div>
      <div><label>用途</label><select id="purpose"></select></div>
      <div><label>開始時間</label><input id="start" type="datetime-local" /></div>
      <div><label>結束時間</label><input id="end" type="datetime-local" /></div>
    </div>
    <div class="modal-actions">
      <button id="add-btn">送出預約</button>
      <button id="close-add-modal" class="btn-secondary">取消</button>
    </div>
    <p class="helper">※ 只有通過管理員驗證後可新增預約。</p>
  </div>
</div>

<script>
const START_HOUR = 8;
const END_HOUR = 22;
let currentRole = 'user';
let isAdmin = false;
let venues = [];
let purposes = [];
let bookingsCache = {};

function toServerDateTime(v) { return v.replace('T', ' '); }
function toDateObj(s) { return new Date(s.replace(' ', 'T') + ':00'); }
function fmtDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
function weekStart(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  const diff = (d.getDay() + 6) % 7; // monday start
  d.setDate(d.getDate() - diff);
  return d;
}

async function loadVenues() {
  const resp = await fetch('/api/venues');
  venues = await resp.json();
  const select = document.getElementById('venue');
  select.innerHTML = venues.map(v => `<option value="${v.venue_id}">${v.name}</option>`).join('');
}

async function loadPurposes() {
  const resp = await fetch('/api/purposes');
  purposes = await resp.json();
  const select = document.getElementById('purpose');
  select.innerHTML = purposes.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
}

async function loadBookings(date, force = false) {
  if (!force && bookingsCache[date]) return bookingsCache[date];
  const resp = await fetch(`/api/bookings?date=${date}`);
  const data = await resp.json();
  bookingsCache[date] = data;
  return data;
}

async function loadRangeBookings(baseDate, days) {
  const start = weekStart(baseDate);
  const dates = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    dates.push(fmtDate(d));
  }

  const lists = await Promise.all(dates.map(d => loadBookings(d)));
  const data = {};
  dates.forEach((d, idx) => {
    data[d] = lists[idx];
  });
  return data;
}

function bookingForSlot(venueId, slotHour, bookings) {
  return bookings.find(b => {
    if (b.venue_id !== venueId) return false;
    const start = toDateObj(b.start_time).getHours();
    const end = toDateObj(b.end_time).getHours();
    return slotHour >= start && slotHour < end;
  });
}

function setAuthBadge() {
  document.getElementById('auth-state').textContent = isAdmin ? '目前：管理員' : '目前：使用者';
  document.getElementById('admin-view').classList.toggle('active', currentRole === 'admin');
  document.getElementById('user-view').classList.toggle('active', currentRole === 'user');
  document.getElementById('options-link').style.display = isAdmin ? 'inline-block' : 'none';
  document.getElementById('open-add-modal').style.display = isAdmin ? 'inline-block' : 'none';
}

function renderDaily(bookings) {
  const grid = document.getElementById('grid');
  let html = '<tr><th>場地\\時段</th>';
  for (let h = START_HOUR; h < END_HOUR; h++) html += `<th>${String(h).padStart(2, '0')}-${String(h+1).padStart(2, '0')}</th>`;
  html += '</tr>';

  for (const venue of venues) {
    html += `<tr><td class="venue">${venue.name}</td>`;
    for (let h = START_HOUR; h < END_HOUR; h++) {
      const b = bookingForSlot(venue.venue_id, h, bookings);
      let cls = 'slot';
      let text = '';
      if (b) {
        if (currentRole === 'admin') {
          cls += ' booked-admin';
          text = `${b.start_time.slice(11,16)}-${b.end_time.slice(11,16)}\n${b.customer}\n${b.purpose || ''}`;
        } else {
          cls += ' booked-user';
          text = '已預約';
        }
      }
      html += `<td class="${cls}"><div class="small">${text}</div></td>`;
    }
    html += '</tr>';
  }
  grid.innerHTML = html;
}

function renderWeekly(weekData, baseDate, days = 7) {
  const grid = document.getElementById('grid');
  const start = weekStart(baseDate);
  const dates = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    dates.push(fmtDate(d));
  }

  let html = '<tr><th>日期</th><th>時段</th>';
  for (const venue of venues) html += `<th>${venue.name}</th>`;
  html += '</tr>';

  for (const day of dates) {
    for (let h = START_HOUR; h < END_HOUR; h++) {
      html += '<tr>';
      if (h === START_HOUR) {
        html += `<td class="venue" rowspan="${END_HOUR - START_HOUR}">${day}<br>${['一','二','三','四','五','六','日'][((new Date(day+'T00:00:00').getDay()+6)%7)]}</td>`;
      }
      html += `<td class="slot-time">${String(h).padStart(2, '0')}-${String(h+1).padStart(2, '0')}</td>`;

      const bookings = weekData[day] || [];
      for (const venue of venues) {
        const b = bookingForSlot(venue.venue_id, h, bookings);
        let cls = 'slot';
        let cell = '';
        if (b) {
          cls += currentRole === 'admin' ? ' booked-admin' : ' booked-user';
          cell = currentRole === 'admin'
            ? `${b.start_time.slice(11,16)}-${b.end_time.slice(11,16)}\n${b.customer}\n${b.purpose || ''}`
            : '已預約';
        }
        html += `<td class="${cls}"><div class="small">${cell}</div></td>`;
      }
      html += '</tr>';
    }
  }

  grid.innerHTML = html;
}

async function refresh() {
  const date = document.getElementById('date').value;
  const mode = document.getElementById('view-mode').value;
  if (mode === 'daily') {
    renderDaily(await loadBookings(date));
  } else if (mode === 'weekly') {
    renderWeekly(await loadRangeBookings(date, 7), date, 7);
  } else {
    renderWeekly(await loadRangeBookings(date, 14), date, 14);
  }
}

async function requestAdmin() {
  const password = prompt('請輸入管理員密碼：');
  if (password === null) return;
  const resp = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!resp.ok) {
    alert('密碼錯誤，無法切換管理員檢視');
    return;
  }
  isAdmin = true;
  currentRole = 'admin';
  setAuthBadge();
  refresh();
}

function switchToUser() {
  currentRole = 'user';
  setAuthBadge();
  closeBookingModal();
  refresh();
}

function openBookingModal() {
  if (!isAdmin) return;
  document.getElementById('booking-modal').style.display = 'flex';
}

function closeBookingModal() {
  document.getElementById('booking-modal').style.display = 'none';
}

document.getElementById('admin-view').addEventListener('click', async () => {
  if (!isAdmin) await requestAdmin();
  else {
    currentRole = 'admin';
    setAuthBadge();
    refresh();
  }
});

document.getElementById('user-view').addEventListener('click', switchToUser);
document.getElementById('date').addEventListener('change', refresh);
document.getElementById('view-mode').addEventListener('change', refresh);
document.getElementById('open-add-modal').addEventListener('click', openBookingModal);
document.getElementById('close-add-modal').addEventListener('click', closeBookingModal);
document.getElementById('export-png').addEventListener('click', () => {
  const date = document.getElementById('date').value;
  window.open(`/api/export?format=png&date=${date}&role=${currentRole}`, '_blank');
});
document.getElementById('export-pdf').addEventListener('click', () => {
  const date = document.getElementById('date').value;
  window.open(`/api/export?format=pdf&date=${date}&role=${currentRole}`, '_blank');
});

document.getElementById('add-btn').addEventListener('click', async () => {
  const msg = document.getElementById('msg');
  if (!isAdmin) {
    msg.style.color = '#dc2626';
    msg.textContent = '請先切換為管理員並通過密碼驗證';
    return;
  }

  const payload = {
    venue_id: Number(document.getElementById('venue').value),
    customer: document.getElementById('customer').value.trim(),
    purpose: document.getElementById('purpose').value.trim(),
    start: toServerDateTime(document.getElementById('start').value),
    end: toServerDateTime(document.getElementById('end').value),
  };

  const resp = await fetch('/api/bookings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await resp.json();

  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '新增失敗';
    return;
  }
  msg.style.color = '#16a34a';
  msg.textContent = `新增成功 #${data.booking_id}`;
  bookingsCache = {};
  closeBookingModal();
  refresh();
});

(async function init() {
  const now = new Date();
  document.getElementById('date').value = now.toISOString().slice(0, 10);
  await loadVenues();
  await loadPurposes();
  setAuthBadge();
  await refresh();
})();
</script>
</body>
</html>
"""

OPTIONS_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>場地與用途設定</title>
<style>
body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }
.wrap { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel { background:#fff; border:1px solid #d1d5db; border-radius: 12px; padding: 14px; }
h1 { margin-top: 0; }
input, button { padding:8px; }
button { cursor:pointer; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { border:1px solid #cbd5e1; padding:8px; text-align:left; }
.actions button { margin-right: 6px; }
.top { max-width:1100px; margin:0 auto 12px; display:flex; gap:8px; align-items:center; }
</style>
</head>
<body>
<div class="top">
  <h1 style="margin:0;">場地 / 用途 管理</h1>
  <button onclick="location.href='/'">回預約頁</button>
</div>
<div class="wrap">
  <div class="panel">
    <h3>場地管理</h3>
    <input id="new-venue" placeholder="新增場地名稱" />
    <button onclick="createVenue()">新增場地</button>
    <table id="venue-table"></table>
  </div>
  <div class="panel">
    <h3>用途管理</h3>
    <input id="new-purpose" placeholder="新增用途名稱" />
    <button onclick="createPurpose()">新增用途</button>
    <table id="purpose-table"></table>
  </div>
</div>
<script>
let adminPassword = '';

async function login() {
  const pw = prompt('請輸入管理員密碼：');
  if (pw === null) return false;
  const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})});
  if (!resp.ok) { alert('密碼錯誤'); return false; }
  adminPassword = pw;
  return true;
}

async function ensureLogin() {
  if (adminPassword) return true;
  return await login();
}

async function api(method, path, payload = {}) {
  const ok = await ensureLogin();
  if (!ok) throw new Error('need login');
  payload.admin_password = adminPassword;
  const resp = await fetch(path, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || '操作失敗');
  return data;
}

async function refresh() {
  const venues = await (await fetch('/api/venues')).json();
  const purposes = await (await fetch('/api/purposes')).json();

  const vt = document.getElementById('venue-table');
  vt.innerHTML = '<tr><th>ID</th><th>名稱</th><th>操作</th></tr>' + venues.map(v =>
    `<tr><td>${v.venue_id}</td><td><input value="${v.name}" id="venue-${v.venue_id}"/></td><td class="actions"><button onclick="updateVenue(${v.venue_id})">儲存</button><button onclick="deleteVenue(${v.venue_id})">刪除</button></td></tr>`
  ).join('');

  const pt = document.getElementById('purpose-table');
  pt.innerHTML = '<tr><th>ID</th><th>名稱</th><th>操作</th></tr>' + purposes.map(p =>
    `<tr><td>${p.purpose_id}</td><td><input value="${p.name}" id="purpose-${p.purpose_id}"/></td><td class="actions"><button onclick="updatePurpose(${p.purpose_id})">儲存</button><button onclick="deletePurpose(${p.purpose_id})">刪除</button></td></tr>`
  ).join('');
}

async function createVenue() {
  try { await api('POST', '/api/venues', {name: document.getElementById('new-venue').value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function updateVenue(id) {
  try { await api('PUT', '/api/venues', {venue_id: id, name: document.getElementById(`venue-${id}`).value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function deleteVenue(id) {
  if (!confirm('確定刪除場地？')) return;
  try { await api('DELETE', '/api/venues', {venue_id: id}); await refresh(); }
  catch (e) { alert(e.message); }
}

async function createPurpose() {
  try { await api('POST', '/api/purposes', {name: document.getElementById('new-purpose').value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function updatePurpose(id) {
  try { await api('PUT', '/api/purposes', {purpose_id: id, name: document.getElementById(`purpose-${id}`).value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function deletePurpose(id) {
  if (!confirm('確定刪除用途？')) return;
  try { await api('DELETE', '/api/purposes', {purpose_id: id}); await refresh(); }
  catch (e) { alert(e.message); }
}

refresh();
</script>
</body>
</html>
"""


class BookingWebHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Union[Dict[str, Any], List[Any]], status: int = HTTPStatus.OK) -> None:
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
        if parsed.path == "/options":
            self._send_html(OPTIONS_PAGE)
            return
        if parsed.path == "/api/venues":
            with manager_lock:
                venues = [v.__dict__ for v in manager.list_venues()]
            self._send_json(venues)
            return
        if parsed.path == "/api/purposes":
            with manager_lock:
                purposes = [p.__dict__ for p in manager.list_purposes()]
            self._send_json(purposes)
            return
        if parsed.path == "/api/bookings":
            date = parse_qs(parsed.query).get("date", [""])[0]
            if date:
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    self._send_json({"error": "日期格式錯誤，請使用 YYYY-MM-DD"}, status=HTTPStatus.BAD_REQUEST)
                    return
            with manager_lock:
                bookings = [booking_to_dict(b) for b in manager.list_bookings(date=date or None)]
            self._send_json(bookings)
            return
        if parsed.path == "/api/export":
            query = parse_qs(parsed.query)
            date = query.get("date", [datetime.now().strftime("%Y-%m-%d")])[0]
            role = query.get("role", ["user"])[0]
            fmt = query.get("format", ["png"])[0]
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                self._send_json({"error": "日期格式錯誤，請使用 YYYY-MM-DD"}, status=HTTPStatus.BAD_REQUEST)
                return
            with manager_lock:
                if fmt == "pdf":
                    payload = _make_pdf_export(base_date=date, role=role)
                    content_type = "application/pdf"
                    filename = f"booking-2weeks-{date}.pdf"
                else:
                    payload = _make_png_export(base_date=date, role=role)
                    content_type = "image/png"
                    filename = f"booking-2weeks-{date}.png"

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(payload)
            return
        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/admin/login":
            password = str(payload.get("password", ""))
            if secrets.compare_digest(password, ADMIN_PASSWORD):
                self._send_json({"ok": True})
            else:
                self._send_json({"error": "密碼錯誤"}, status=HTTPStatus.UNAUTHORIZED)
            return

        if parsed.path in ["/api/venues", "/api/purposes"]:
            try:
                self._check_admin_password(payload)
                name = str(payload.get("name", "")).strip()
                with manager_lock:
                    if parsed.path == "/api/venues":
                        item = manager.add_venue(name)
                        self._send_json(item.__dict__, status=HTTPStatus.CREATED)
                    else:
                        item = manager.add_purpose(name)
                        self._send_json(item.__dict__, status=HTTPStatus.CREATED)
                return
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

        if parsed.path != "/api/bookings":
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            for field in ["venue_id", "customer", "start", "end"]:
                if not str(payload.get(field, "")).strip():
                    raise ValueError(f"缺少必要欄位：{field}")
            with manager_lock:
                booking = manager.add_booking(
                    venue_id=int(payload["venue_id"]),
                    customer=payload["customer"],
                    purpose=payload.get("purpose", ""),
                    start=payload["start"],
                    end=payload["end"],
                )
            self._send_json(booking_to_dict(booking), status=HTTPStatus.CREATED)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
            self._check_admin_password(payload)
            with manager_lock:
                if parsed.path == "/api/venues":
                    item = manager.update_venue(int(payload.get("venue_id", 0)), str(payload.get("name", "")))
                elif parsed.path == "/api/purposes":
                    item = manager.update_purpose(int(payload.get("purpose_id", 0)), str(payload.get("name", "")))
                else:
                    self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
                    return
            self._send_json(item.__dict__)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc) or "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
            self._check_admin_password(payload)
            with manager_lock:
                if parsed.path == "/api/venues":
                    ok = manager.delete_venue(int(payload.get("venue_id", 0)))
                elif parsed.path == "/api/purposes":
                    ok = manager.delete_purpose(int(payload.get("purpose_id", 0)))
                else:
                    self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
                    return
            if not ok:
                self._send_json({"error": "資料不存在"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc) or "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)

    @staticmethod
    def _check_admin_password(payload: Dict[str, Any]) -> None:
        password = str(payload.get("admin_password", ""))
        if not secrets.compare_digest(password, ADMIN_PASSWORD):
            raise ValueError("管理員密碼錯誤")


def run_web_app(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), BookingWebHandler)
    print(f"伺服器已啟動：http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_web_app()
