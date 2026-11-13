"""Build "MCD Shift Sync.shortcut": one shortcut that reads the myJob roster page and adds / updates / removes shifts.

python3 build.py           -> MCD Shift Sync.shortcut       (signed with `shortcuts sign`, macOS only)
python3 build.py --debug   -> MCD Shift Sync Test.shortcut  (notification at each stage)
python3 build.py --demo    -> MCD Shift Sync Demo.shortcut  (for the mock roster page in demo/)
Never runs the shortcut and never touches Calendar.
"""
from pathlib import Path
import plistlib
import subprocess
import uuid

import sys
ROOT = Path(__file__).parent
DEBUG = '--debug' in sys.argv          # test build: a notification at each stage, to find where a run stops
# Demo build, for screenshots with demo/mock_roster.py: accepts any website and tags shifts with DEMOID:
# instead of UID:, so the demo and the real shortcut never touch each other's events.
DEMO = '--demo' in sys.argv
NAME = 'MCD Shift Sync Test' if DEBUG else 'MCD Shift Sync Demo' if DEMO else 'MCD Shift Sync'
UID_PREFIX = 'DEMOID:' if DEMO else 'UID:'
JS = (ROOT / 'parser.js').read_text()
if DEMO:
    for a, b in [('!/mcdonalds\\.com\\.au$/i.test(location.hostname) || ', ''),
                 ('var uid = "UID:" + btoa', 'var uid = "DEMOID:" + btoa')]:
        assert a in JS, a
        JS = JS.replace(a, b)
DEFAULT_CALENDAR = '工作'   # calendar pre-selected in the import question; everyone picks their own
UID_SLOTS = 21   # must match UID_SLOTS in parser.js: up to 3 weeks, one shift a day
OBJ = '￼'

actions = []
groups = []          # stack of (grouping id, identifier)
repeat_level = 0     # nesting depth of "repeat each"


def uid():
    return str(uuid.uuid4()).upper()


# ---------- value helpers ----------
class Ref:
    """A variable reference: named variable, action output, repeat item, shortcut input."""
    def __init__(self, value, keys=(), as_date=False):
        self.value, self.keys, self.as_date = value, keys, as_date

    def __getitem__(self, key):
        return Ref(self.value, self.keys + (key,), self.as_date)

    def date(self):
        return Ref(self.value, self.keys, True)

    def raw(self):
        v = dict(self.value)
        agg = [{'Type': 'WFDictionaryValueVariableAggrandizement', 'DictionaryKey': k} for k in self.keys]
        if self.as_date:
            agg.append({'Type': 'WFCoercionVariableAggrandizement', 'CoercionItemClass': 'WFDateContentItem'})
        if agg:
            v['Aggrandizements'] = agg
        return v


def var(name):
    return Ref({'Type': 'Variable', 'VariableName': name})


def repeat_item():
    return var('Repeat Item' + (f' {repeat_level}' if repeat_level > 1 else ''))


def repeat_index():
    return var('Repeat Index' + (f' {repeat_level}' if repeat_level > 1 else ''))


SHORTCUT_INPUT = Ref({'Type': 'ExtensionInput'})


def att(ref):
    return {'Value': ref.raw(), 'WFSerializationType': 'WFTextTokenAttachment'}


def tokens(*parts):
    """Text with embedded variables: tokens('Added ', ref, '\\n')."""
    s, attachments = '', {}
    for p in parts:
        if isinstance(p, Ref):
            attachments[f'{{{len(s.encode("utf-16-le")) // 2}, 1}}'] = p.raw()
            s += OBJ
        else:
            s += p
    return {'Value': {'string': s, 'attachmentsByRange': attachments}, 'WFSerializationType': 'WFTextTokenString'}


# ---------- action helpers ----------
def act(identifier, params=None, output=None):
    p = dict(params or {})
    p['UUID'] = u = uid()
    actions.append({'WFWorkflowActionIdentifier': 'is.workflow.actions.' + identifier, 'WFWorkflowActionParameters': p})
    return Ref({'Type': 'ActionOutput', 'OutputUUID': u, 'OutputName': output}) if output else None


def set_var(name, ref):
    act('setvariable', {'WFInput': att(ref), 'WFVariableName': name})
    return var(name)


def append_var(name, ref):
    act('appendvariable', {'WFInput': att(ref), 'WFVariableName': name})


def text(*parts):
    return act('gettext', {'WFTextActionText': tokens(*parts)}, 'Text')


def if_(ref, condition, **extra):
    g = uid()
    groups.append((g, 'conditional'))
    act('conditional', {'WFInput': {'Type': 'Variable', 'Variable': att(ref)}, 'WFCondition': condition,
                        'WFControlFlowMode': 0, 'GroupingIdentifier': g, **extra})


def else_():
    act('conditional', {'WFControlFlowMode': 1, 'GroupingIdentifier': groups[-1][0]})


def end_if():
    g, kind = groups.pop()
    assert kind == 'conditional'
    act('conditional', {'WFControlFlowMode': 2, 'GroupingIdentifier': g})


def repeat_each(ref):
    global repeat_level
    g = uid()
    groups.append((g, 'repeat.each'))
    act('repeat.each', {'WFInput': att(ref), 'WFControlFlowMode': 0, 'GroupingIdentifier': g})
    repeat_level += 1


def end_repeat():
    global repeat_level
    g, kind = groups.pop()
    assert kind == 'repeat.each'
    repeat_level -= 1
    act('repeat.each', {'WFControlFlowMode': 2, 'GroupingIdentifier': g})


def find_mcd_events(range_start, range_end, notes_contains, notes_excludes=()):
    """Find Calendar Events: title is MCD, start date in range, notes contain X (and none of the excludes).
    Searches all calendars, no limit."""
    templates = [
        {'Property': 'Title', 'Operator': 4, 'Values': {'String': 'MCD'}, 'Removable': True},
        {'Property': 'Start Date', 'Operator': 1003, 'Removable': False, 'Bounded': True,
         'Values': {'Date': att(range_start), 'AnotherDate': att(range_end)}},
        {'Property': 'Notes', 'Operator': 99, 'Removable': True,
         'Values': {'String': tokens(notes_contains) if isinstance(notes_contains, Ref) else notes_contains}},
    ] + [{'Property': 'Notes', 'Operator': 999, 'Removable': True, 'Values': {'String': tokens(x)}}
         for x in notes_excludes]
    return act('filter.calendarevents', {
        'WFContentItemFilter': {'Value': {'WFActionParameterFilterPrefix': 1, 'WFContentPredicateBoundedDate': True,
                                          'WFActionParameterFilterTemplates': templates},
                                'WFSerializationType': 'WFContentPredicateTableTemplate'},
        'WFContentItemLimitEnabled': False}, 'Calendar Events')


def event_detail(event, prop, output):
    return act('properties.calendarevents', {'WFInput': att(event), 'WFContentItemPropertyName': prop}, output)


SETTER_KEYS = {'Start Date': 'WFCalendarEventContentItemStartDate', 'End Date': 'WFCalendarEventContentItemEndDate',
               'Location': 'WFCalendarEventContentItemLocation', 'Notes': 'WFCalendarEventContentItemNotes'}


def edit_event(event, prop, value):
    act('setters.calendarevents', {'WFInput': att(event), 'WFContentItemPropertyName': prop, 'Mode': 'Set',
                                   SETTER_KEYS[prop]: tokens(value)})


def alert(title, *message):
    act('alert', {'WFAlertActionTitle': title, 'WFAlertActionMessage': tokens(*message),
                  'WFAlertActionCancelButtonShown': False})


def notify(*message):
    if DEBUG:
        act('notification', {'WFNotificationActionTitle': 'MCD Shift Sync test', 'WFNotificationActionBody': tokens(*message),
                             'WFNotificationActionSound': False})


def count(ref):
    return act('count', {'Input': att(ref), 'WFCountType': 'Items'}, 'Count')


# ---------- the shortcut ----------
act('comment', {'WFCommentActionText':
    'MCD Shift Sync\n'
    'How to use: open My Roster in Safari, tap Share, then tap MCD Shift Sync.\n\n'
    '• New shifts on your roster are added to your calendar.\n'
    '• Shifts already in your calendar are kept up to date. Extra copies are removed.\n'
    '• Shifts that are no longer on your roster are removed (only for the weeks shown on the page). '
    'Your iPhone will ask before anything is deleted.\n\n'
    'To use a different calendar, change "Calendar" in the "Add New Event" action below.'})

js_result = act('runjavascriptonwebpage', {'WFInput': att(SHORTCUT_INPUT), 'WFJavaScript': JS}, 'JavaScript Result')
data = set_var('Roster', act('detect.dictionary', {'WFInput': att(js_result)}, 'Dictionary'))

status = text(data['status'])
if_(status, 5, WFConditionalActionString='ok')                       # is not "ok"
alert("Couldn't sync your roster", data['error'])
act('exit')
end_if()
if DEBUG:
    alert('Test mode: step 0', 'Found ', data['shiftCount'], ' shifts on the page. If you can see this, pop-ups work.')

# 1. Each shift on the page: add it, or update the copy already in the calendar
repeat_each(data['shifts'])
shift = set_var('Shift', repeat_item())
matches = set_var('Matching Events', find_mcd_events(data['rangeStart'].date(), data['rangeEnd'].date(), shift['uid']))
if_(matches, 101)                                                     # does not have any value
new_event = act('addnewevent', {
    'WFCalendarItemTitle': 'MCD',
    'WFCalendarItemStartDate': tokens(shift['start']),
    'WFCalendarItemEndDate': tokens(shift['end']),
    'WFCalendarItemLocation': tokens(shift['location']),
    'WFCalendarItemNotes': tokens(shift['notes']),
    'WFCalendarItemAllDay': False,
    'ShowWhenRun': False,
    'WFCalendarDescriptor': {'Title': DEFAULT_CALENDAR, 'IsAllCalendar': False},
}, 'New Event')
ADD_EVENT_INDEX = len(actions) - 1
append_var('Added', new_event)
append_var('Changes', text('+ Added ', shift['label']))
else_()
keep = set_var('Existing Event', act('getitemfromlist', {'WFInput': att(matches), 'WFItemSpecifier': 'First Item'}, 'Item from List'))
old_end = event_detail(keep, 'End Date', 'End Date')
# Change start or end first depending on direction, so the event never ends before it starts
if_(shift['start'].date(), 0, WFDate=att(old_end))                 # new start is before old end
edit_event(keep, 'Start Date', shift['start'])
edit_event(keep, 'End Date', shift['end'])
else_()
edit_event(keep, 'End Date', shift['end'])
edit_event(keep, 'Start Date', shift['start'])
end_if()
edit_event(keep, 'Location', shift['location'])
edit_event(keep, 'Notes', shift['notes'])
append_var('Up To Date', keep)
repeat_each(matches)
if_(repeat_index(), 2, WFNumberValue=1)                               # 2nd match onwards = extra copy
append_var('To Remove', repeat_item())
append_var('Changes', text('− Removed an extra copy of ', shift['label']))
end_if()
end_repeat()
end_if()
end_repeat()
if DEBUG: notify('Step 1 done. Added ', count(var('Added')), ', already in calendar ', count(var('Up To Date')), ', extra copies ', count(var('To Remove')))

# 2. MCD shifts in the weeks shown that are no longer on the page.
#    Filtered by the Find action itself (notes contain none of the page's UIDs).
#    Looping over events with Match Text silently stops the run in the iPhone share sheet.
cancelled = find_mcd_events(data['rangeStart'].date(), data['rangeEnd'].date(), UID_PREFIX,
                            [data['slot%d' % i] for i in range(1, UID_SLOTS + 1)])
if DEBUG: notify('Step 2: ', count(cancelled), ' shift(s) in your calendar are no longer on the roster')
repeat_each(cancelled)
append_var('To Remove', repeat_item())
start = event_detail(repeat_item(), 'Start Date', 'Start Date')
when = act('format.date', {'WFDate': tokens(start), 'WFDateFormatStyle': 'Custom', 'WFDateFormat': 'dd/MM HH:mm'},
           'Formatted Date')
append_var('Changes', text('− Removed ', when, ' (no longer on your roster)'))
end_repeat()

# 3. Remove (iOS asks the user to confirm)
if DEBUG: notify('Step 3: about to remove ', count(var('To Remove')), ' event(s)')
if_(var('To Remove'), 100)
act('removeevents', {'WFInputEvents': att(var('To Remove')), 'WFCalendarIncludeFutureEvents': False})
end_if()

if DEBUG: notify('Step 4: done removing, showing the summary next')
if_(var('Changes'), 101)
set_var('Changes', text("Everything's already up to date. Nothing needed changing."))
end_if()
added = set_var('Added Count', count(var('Added')))
kept = set_var('Up To Date Count', count(var('Up To Date')))
removed = set_var('Removed Count', count(var('To Remove')))
alert('Roster synced',
      data['shiftCount'], ' shift(s) on your roster.\n\n',
      'Added: ', added, '\n',
      'Already in calendar: ', kept, '\n',
      'Removed: ', removed, '\n\n',
      var('Changes'))

assert not groups and repeat_level == 0

workflow = {
    'WFWorkflowName': NAME,
    'WFWorkflowActions': actions,
    'WFWorkflowClientVersion': '3612.0.2.9',
    'WFWorkflowMinimumClientVersion': 1113,
    'WFWorkflowMinimumClientVersionString': '1113',
    'WFWorkflowIcon': {'WFWorkflowIconStartColor': 4282601983, 'WFWorkflowIconGlyphNumber': 59681},
    'WFWorkflowTypes': ['ActionExtension'],
    'WFWorkflowInputContentItemClasses': ['WFSafariWebPageContentItem'],
    'WFWorkflowOutputContentItemClasses': [],
    'WFWorkflowHasOutputFallback': False,
    'WFWorkflowHasShortcutInputVariables': True,
    'WFWorkflowNoInputBehavior': {'Name': 'WFWorkflowNoInputBehaviorShowError',
                                  'Parameters': {'Error': 'Open My Roster in Safari, tap Share, then tap MCD Shift Sync.'}},
    # Ask for the calendar on import, so each iPhone resolves its own calendar ID.
    # (Calendar IDs differ between devices; a hard-coded one silently breaks Add New Event.)
    'WFWorkflowImportQuestions': [{'ActionIndex': ADD_EVENT_INDEX, 'Category': 'Parameter',
                                   'ParameterKey': 'WFCalendarDescriptor', 'Text': 'Which calendar should your shifts be added to?',
                                   'DefaultValue': {'Title': DEFAULT_CALENDAR, 'IsAllCalendar': False}}],
}

unsigned = ROOT / f'{NAME}.unsigned.shortcut'   # `shortcuts sign` only accepts the .shortcut extension
signed = ROOT / f'{NAME}.shortcut'
with open(unsigned, 'wb') as f:
    plistlib.dump(workflow, f, fmt=plistlib.FMT_BINARY)
signed.unlink(missing_ok=True)
for attempt in range(3):   # `shortcuts sign` sometimes fails the first time; retrying works
    r = subprocess.run(['shortcuts', 'sign', '--mode', 'anyone', '--input', str(unsigned), '--output', str(signed)],
                       capture_output=True, text=True)
    if r.returncode == 0 and signed.exists():
        break
else:
    raise SystemExit('shortcuts sign failed:\n' + '\n'.join(l for l in r.stderr.splitlines() if 'Unrecognized' not in l))
print(f'{len(actions)} actions -> {signed.name} ({signed.stat().st_size} bytes)')
