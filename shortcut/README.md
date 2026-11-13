# MCD Shift Sync: source

The shortcut is generated from code, so changes can be reviewed and rebuilt, not hand-edited in the Shortcuts app.

| File | What it is |
|---|---|
| `parser.js` | Runs on the myJob **My Roster** page (via *Run JavaScript on Web Page*) and returns the shifts as JSON. |
| `build.py` | Builds the shortcut's actions around `parser.js` and signs the file. |
| `demo/mock_roster.py` | A mock My Roster page with made-up data, served on your local network, used for testing and screenshots. |

## Build

Requires macOS (uses the `shortcuts sign` command).

```sh
python3 build.py           # MCD Shift Sync.shortcut
python3 build.py --debug   # MCD Shift Sync Test.shortcut: a notification at each stage, to see where a run stops
python3 build.py --demo    # MCD Shift Sync Demo.shortcut: for the mock page, see below
```

Open the `.shortcut` file on an iPhone to install it. Choose the calendar when asked.

Reinstalling gives every action a new internal ID, so iOS asks for the "Allow" permissions again.

## How it works

1. `parser.js` reads every roster week shown on the page, plus each shift's start, finish, store, role and meal break. Each shift's ID is `UID:` followed by the Base64 of its date heading, so events from the old extension are recognised.
2. If the number of shifts read doesn't match "You have been rostered on N shifts", it stops before touching the calendar.
3. For each shift it looks for an `MCD` event whose notes contain that UID. If none is found, it adds one. Otherwise it updates the first match and removes any extra copies.
4. In a single *Find Calendar Events* it looks for `MCD` events in the weeks shown whose notes contain `UID:` but **none** of the shift UIDs on the page. Those are cancelled shifts, and they're removed. The page's UIDs are passed in as `slot1`…`slot21`, with spare slots filled by a placeholder. This replaced an earlier per-event *Match Text* loop, which silently stopped the run when started from the iPhone share sheet.
5. It shows a summary alert.

Things learned the hard way:

- Calendar IDs differ between devices. The calendar is asked for at import instead of being written into the file.
- *Show Result* and long text-processing loops aren't reliable in the share sheet. *Show Alert* is.

## Testing with the mock page

```sh
python3 build.py --demo
python3 demo/mock_roster.py 8787
```

Then on an iPhone on the same Wi-Fi, open in **Safari**:

- `http://<your Mac's IP>:8787/EmployeeSS/MyRoster/Index`: the first roster
- `http://<your Mac's IP>:8787/EmployeeSS/MyRoster/Index?scenario=changed`: Wednesday moved later, Friday cancelled, a new Thursday shift

Run **MCD Shift Sync Demo** from the share sheet. Use a separate calendar such as "Demo", so it's easy to delete afterwards.

The demo build tags shifts with `DEMOID:` instead of `UID:`, so the demo and the real shortcut never touch each other's events.

If your Mac's firewall blocks the server, run it with a Python that's allowed to accept incoming connections (e.g. `/usr/bin/python3`).
