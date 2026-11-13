"""LAN mock of the myJob "My Roster" page, with made-up data, for screenshots.

python3 demo/mock_roster.py [port]
  http://<this Mac's LAN IP>:<port>/EmployeeSS/MyRoster/Index                 -> first roster
  http://<this Mac's LAN IP>:<port>/EmployeeSS/MyRoster/Index?scenario=changed -> roster after changes

Use it with "MCD Shift Sync Demo" (python3 build.py --demo), never with the real shortcut:
the real one refuses pages that are not on mcdonalds.com.au.
The shift-card markup copies the real page (including the unclosed <div id="time" />),
so the parser reads it exactly as it reads myJob.
"""
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from urllib.parse import urlparse, parse_qs
import sys

STORE = 'EXAMPLE STORE VIC'
EMPLOYEE = 'Example (12345678)'
ROLES = {'PI': 'PI:Production Intermediate', 'SI': 'SI:Service Intermediate', 'MB': 'MCBR:McCafe Barista'}

# (date, start, finish, role, meal break or None)
FIRST = [
    ('2026-11-23', '12:00', '15:00', 'PI', None),
    ('2026-11-25', '16:00', '21:30', 'SI', ('18:30', '19:00')),
    ('2026-11-27', '11:00', '14:00', 'MB', None),
    ('2026-11-28', '21:00', '00:00', 'PI', None),
    ('2026-12-01', '12:00', '16:00', 'PI', None),
    ('2026-12-05', '17:00', '22:00', 'SI', None),
]
# Wed 25 moved later, Fri 27 cancelled, Thu 3 Dec added
CHANGED = [
    ('2026-11-23', '12:00', '15:00', 'PI', None),
    ('2026-11-25', '17:00', '22:30', 'SI', ('19:30', '20:00')),
    ('2026-11-28', '21:00', '00:00', 'PI', None),
    ('2026-12-01', '12:00', '16:00', 'PI', None),
    ('2026-12-03', '10:00', '14:00', 'MB', None),
    ('2026-12-05', '17:00', '22:00', 'SI', None),
]
WEEKS = ['2026-11-23', '2026-11-30']


def day(d):        # Monday 23/Nov/2026
    return d.strftime('%A %d/%b/%Y')


def stamp(d):      # 9:00 PM Saturday 28/Nov/2026
    return d.strftime('%I:%M %p ').lstrip('0') + day(d)


def card(date, start, finish, role, meal):
    s = datetime.fromisoformat(f'{date}T{start}')
    f = datetime.fromisoformat(f'{date}T{finish}')
    if f <= s:
        f += timedelta(days=1)
    hours = (f - s).seconds // 60
    meal_html = ''
    if meal:
        hours -= 30
        m1, m2 = (datetime.fromisoformat(f'{date}T{t}').strftime('%I:%M %p').lstrip('0') for t in meal)
        meal_html = (f'                                    Break time\n                <span>{m1} - {m2}</span>\n'
                     f'                                    <br />\n')
    length = f'{hours // 60}:{hours % 60:02d}hrs' + (' + 0:30hrs Break' if meal else '')
    return f'''                                <div id="time" />
                                <strong>
{day(s)}
                                </strong>
                                <br />
                                <span>{STORE}</span>
                                <br />
                                    Start
                                    <span>{stamp(s)}</span>
                                    <br />
                                    Finish
                                    <span>{stamp(f)}</span>
                                    <br />
{meal_html}                                    <span>{length}</span>
                                    <br />
                                <span>{ROLES[role]}</span>
                                <br />
                                        Intially viewed at <span>Friday 20/Nov/2026 10:35 PM</span>
                                <div class="decoration" style="margin-bottom: 15px!important;">
                                </div>
'''


def page(shifts):
    body = ''
    for monday in WEEKS:
        m = datetime.fromisoformat(monday)
        mine = [x for x in shifts if m <= datetime.fromisoformat(x[0]) < m + timedelta(days=7)]
        body += f'''                        <p>
                            <div class="container heading-style-5" style="margin-bottom: 0px; ">
                                <div style="background-color : black; color : white; font-weight: 700;">Roster period from {day(m)} to {day(m + timedelta(days=6))}</div>
                                    You have been rostered on {len(mine)} shifts this week
                                <br />
                                    <b>This weeks roster was last published on 20/Nov/2026 12:00 AM</b>
                                <br />
                                    <div class="decoration" style="margin-bottom: 15px!important;">
                                    </div>
                            </div>
                        </p>
''' + ''.join(card(*x) for x in mine)
    return f'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>myJob</title>
<style>
body{{margin:0;font:17px/1.5 -apple-system,"Helvetica Neue",Arial,sans-serif;color:#222;background:#fff;text-align:center}}
header{{background:#24272b;height:62px;display:flex;align-items:center;justify-content:center;position:relative}}
header .menu{{position:absolute;left:18px;color:#fff;font-size:26px}}
header .logo{{font:italic 800 30px/1 "Arial Rounded MT Bold",Arial,sans-serif;letter-spacing:-1px}}
.logo .my{{color:#ffbc0d}} .logo .job{{color:#e4231f}}
h1{{font-size:24px;font-weight:500;margin:26px 0 6px}} .who{{font-weight:700;margin-bottom:14px}}
.divider{{display:flex;align-items:center;gap:14px;margin:0 36px 20px;color:#222}}
.divider:before,.divider:after{{content:"";flex:1;border-top:1px solid #ddd}}
.details{{max-width:430px;margin:0 auto;padding:0 18px 40px}}
.container > div:first-child{{padding:4px 6px}}
.decoration{{border-bottom:1px solid #ddd;margin:10px 0}}
strong{{display:block;margin-top:14px}}
</style></head><body>
<header><span class="menu">&#9776;</span><span class="logo"><span class="my">my</span><span class="job">Job</span></span></header>
<h1>My Roster</h1><div class="who">{escape(EMPLOYEE)}</div>
<div class="divider">&#9719;</div>
                <div class="details">
{body}                </div>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if not url.path.startswith('/EmployeeSS/MyRoster'):
            self.send_response(302)
            self.send_header('Location', '/EmployeeSS/MyRoster/Index')
            self.end_headers()
            return
        scenario = parse_qs(url.query).get('scenario', ['first'])[0]
        data = page(CHANGED if scenario == 'changed' else FIRST).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    print(f'Mock roster on port {port}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
