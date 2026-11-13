// MCD Shift Sync: reads the shifts from the myJob "My Roster" page.
// Shift IDs (UID) are the same as the original MCD Shift Parser (Base64 of the date heading),
// so events added by older versions are recognised and updated instead of duplicated.
(function () {
  var UID_SLOTS = 21; // must match build.py; used to find calendar shifts that are no longer on the page
  var EMPTY_SLOT = "#MCD-EMPTY-SLOT#";
  var DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var MONTHS = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11 };

  function fail(message) { var e = new Error(message); e.friendly = true; throw e; }
  function clean(text) { return String(text || "").replace(/ /g, " ").replace(/\s+/g, " ").trim(); }

  // "09/Nov/2026" (weekday optional) -> local midnight
  function parseDay(text) {
    var m = clean(text).match(/(\d{1,2})\/([A-Za-z]{3})\/(\d{4})/);
    if (!m || MONTHS[m[2].toLowerCase()] === undefined) return null;
    return new Date(+m[3], MONTHS[m[2].toLowerCase()], +m[1]);
  }
  // "12:00 PM Monday 09/Nov/2026" -> local time
  function parseDateTime(text) {
    var m = clean(text).match(/(\d{1,2}):(\d{2})\s*(AM|PM)\s+[A-Za-z]+\s+(\d{1,2})\/([A-Za-z]{3})\/(\d{4})/i);
    if (!m || MONTHS[m[5].toLowerCase()] === undefined) return null;
    var hour = (+m[1] % 12) + (m[3].toUpperCase() === "PM" ? 12 : 0);
    return new Date(+m[6], MONTHS[m[5].toLowerCase()], +m[4], hour, +m[2], 0);
  }
  function addDays(date, days) { return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function hm(d) { return pad(d.getHours()) + ":" + pad(d.getMinutes()); }
  function ownTime(timeDiv, label) {
    var node = Array.prototype.find.call(timeDiv.childNodes, function (n) {
      return n.nodeType === 3 && new RegExp("\\b" + label + "\\b").test(n.textContent);
    });
    return node && node.nextElementSibling ? node.nextElementSibling.innerText : "";
  }

  var output;
  try {
    if (!/mcdonalds\.com\.au$/i.test(location.hostname) || !/MyRoster/i.test(location.pathname)) {
      fail("This only works on your myJob roster. Open My Roster in Safari, then try again from the Share menu.");
    }
    var pageText = clean(document.body.innerText);

    // 1. Roster weeks shown, and how many shifts each week says it has
    var periodRe = /Roster period from\s+(?:[A-Za-z]+\s+)?(\d{1,2}\/[A-Za-z]{3}\/\d{4})\s+to\s+(?:[A-Za-z]+\s+)?(\d{1,2}\/[A-Za-z]{3}\/\d{4})(.*?)(?=Roster period from|$)/gi;
    var periods = [], match;
    while ((match = periodRe.exec(pageText))) {
      var count = match[3].match(/rostered on\s+(\d+)\s+shifts?/i);
      periods.push({ first: parseDay(match[1]), last: parseDay(match[2]), declared: count ? +count[1] : null });
    }
    if (!periods.length) fail("Couldn't find your roster on this page. Wait for the page to finish loading, then try again.");
    periods.forEach(function (p) {
      if (!p.first || !p.last) fail("Couldn't read the roster dates. Reload the page and try again.");
      if (p.declared === null) fail("The roster page doesn't look fully loaded. Reload the page and try again.");
    });
    var rangeStart = periods.reduce(function (a, p) { return p.first < a ? p.first : a; }, periods[0].first);
    var rangeEndDay = periods.reduce(function (a, p) { return p.last > a ? p.last : a; }, periods[0].last);
    var rangeEnd = new Date(addDays(rangeEndDay, 1).getTime() - 1000);

    // 2. Shift cards (read the same way as the original parser)
    var shifts = [], seen = {};
    document.querySelectorAll("div#time").forEach(function (timeDiv) {
      var header = timeDiv.querySelector("strong");
      var shiftId = header ? header.innerText.trim() : "";
      if (/Today|Tomorrow/.test(shiftId)) shiftId = shiftId.replace(/Today|Tomorrow/g, "").trim().replace(/\n/g, "");
      if (!shiftId) return;

      var start = parseDateTime(ownTime(timeDiv, "Start"));
      var end = parseDateTime(ownTime(timeDiv, "Finish"));
      if (!start || !end) fail("Couldn't read the start or finish time for " + shiftId + ". Reload the page and try again.");
      if (end <= start) end = new Date(end.getTime() + 86400000); // finishes after midnight

      var spans = timeDiv.querySelectorAll("span");
      var offset = spans[0] && /Today|Tomorrow/.test(spans[0].innerText) ? 1 : 0;
      var place = spans[offset] ? spans[offset].innerText.trim() : "No location";
      var breakTag = spans[3 + offset];
      var remarks = "Break: " + (breakTag && /AM|PM/.test(breakTag.innerText) ? breakTag.innerText.trim() : "No meal break");
      var roleTag = spans[4 + offset];
      if (roleTag && /Break/.test(roleTag.innerText)) roleTag = spans[5 + offset];
      var role = (roleTag && roleTag.innerText.trim()) || "No role";

      var uid = "UID:" + btoa(unescape(encodeURIComponent(shiftId)));
      if (seen[uid]) fail(shiftId + " shows up twice on the page. Reload the page and try again.");
      seen[uid] = true;
      if (start < rangeStart || start > rangeEnd) fail(shiftId + " isn't inside the roster weeks shown. Reload the page and try again.");

      shifts.push({
        uid: uid,
        start: start.toISOString(),
        end: end.toISOString(),
        location: place,
        notes: remarks + "\n" + role + "\n" + uid,
        label: DAYS[start.getDay()] + " " + pad(start.getDate()) + "/" + pad(start.getMonth() + 1) + " " + hm(start) + "–" + hm(end)
      });
    });

    // 3. Safety check: never touch the calendar if the page was only partly read
    var declared = periods.reduce(function (s, p) { return s + p.declared; }, 0);
    if (shifts.length !== declared) {
      fail("Your roster says " + declared + " shift(s), but only " + shifts.length + " could be read. "
        + "Your calendar was not changed. Reload the page and try again.");
    }

    if (shifts.length > UID_SLOTS) fail("There are " + shifts.length + " shifts on this page, more than this shortcut can handle ("
      + UID_SLOTS + "). Your calendar was not changed.");

    output = {
      status: "ok",
      error: "",
      shifts: shifts,
      shiftCount: shifts.length,
      weekCount: periods.length,
      rangeStart: rangeStart.toISOString(),
      rangeEnd: rangeEnd.toISOString()
    };
    for (var i = 1; i <= UID_SLOTS; i++) output["slot" + i] = shifts[i - 1] ? shifts[i - 1].uid : EMPTY_SLOT;
  } catch (error) {
    output = { status: "error", error: error && error.friendly ? error.message
      : "Something went wrong while reading your roster. Reload the page and try again. (" + String(error && error.message || error) + ")" };
  }
  completion(JSON.stringify(output));
})();
