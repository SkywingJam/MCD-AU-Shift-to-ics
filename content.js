(function () {
    const { DateTime } = luxon;

    function parseShift() {
        let shifts = [];
        document.querySelectorAll("div#time").forEach(timeDiv => {
            let shiftId = timeDiv.querySelector("strong")?.innerText?.trim();
            
            // Detect if shiftID contains "Today" or "Tomorrow"
            if (shiftId && (shiftId.includes("Today") || shiftId.includes("Tomorrow"))) {
                shiftId = shiftId.replace(/Today|Tomorrow/g, "").trim();
                shiftId = shiftId.replace(/\n/g, "");
            }
            if (!shiftId) return;

            // Extract date from shiftId
            let dateStr = shiftId.split(" ").pop(); 
            let shiftDate = DateTime.fromFormat(dateStr, "dd/MMM/yyyy");

            // Extract start time
            let startTag = [...timeDiv.childNodes].find(n => n.textContent.includes("Start"));
            let startStr = startTag ? startTag.nextElementSibling.innerText.trim() : null; 
            let startTime = startStr ? DateTime.fromFormat(startStr, "h:mm a EEEE dd/MMM/yyyy") : null;

            // Extract end time
            let endTag = [...timeDiv.childNodes].find(n => n.textContent.includes("Finish"));
            let endStr = endTag ? endTag.nextElementSibling.innerText.trim() : null; 
            let endTime = endStr ? DateTime.fromFormat(endStr, "h:mm a EEEE dd/MMM/yyyy") : null;

            if (!startTime || !endTime) return;

            // Extract location
            let locationTag = timeDiv.querySelectorAll("span")[0];
            let isToday = 0;
            if (locationTag && (locationTag.innerText.includes("Today") || locationTag.innerText.includes("Tomorrow"))) {
                isToday = 1;
                locationTag = timeDiv.querySelectorAll("span")[0+isToday];
            }
            let location = locationTag ? locationTag.innerText.trim() : "No location";

            // Extract remarks
            let breakTag = timeDiv.querySelectorAll("span")[3+isToday];
            let remarks = "";
            if (breakTag && (breakTag.innerText.includes("AM") || breakTag.innerText.includes("PM"))) {
                remarks = `Break: ${breakTag.innerText.trim()}`;
            } else {
                remarks = `Break: No meal break`;
            }

            // Extract role
            let roleTag = timeDiv.querySelectorAll("span")[4+isToday];
            if (roleTag && roleTag.innerText.includes("Break")) {
                roleTag = timeDiv.querySelectorAll("span")[5+isToday];
            }
            let role = roleTag ? roleTag.innerText.trim() : "No role";

            // Append role and UID to remarks with a single newline
            let uid = "UID:" + btoa(unescape(encodeURIComponent(shiftId)));
            remarks += `\\n${role}\\n${uid}`;

            shifts.push({ shiftId, startTime, endTime, location, remarks, uid });
        });
        
        console.log("Shifts found:", shifts);
        return shifts;
    }

    function createICS(shifts) {
        let icsContent = "BEGIN:VCALENDAR\nVERSION:2.0\n";
        let now = DateTime.now().toUTC().toFormat("yyyyMMdd'T'HHmmss'Z'");
        
        shifts.forEach(shift => {
            icsContent += `
BEGIN:VEVENT
LAST-MODIFIED:${now}
DTSTAMP:${now}
UID:${shift.uid}
SUMMARY:MCD
DTSTART:${shift.startTime.toUTC().toFormat("yyyyMMdd'T'HHmmss'Z'")}
DTEND:${shift.endTime.toUTC().toFormat("yyyyMMdd'T'HHmmss'Z'")}
LOCATION:${shift.location}
DESCRIPTION:${shift.remarks}
END:VEVENT\n`;
        });
        icsContent += "END:VCALENDAR";

        let blob = new Blob([icsContent], { type: "text/calendar" });
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "MCD_Shifts_" + DateTime.now().toFormat("yyyyMMddHHmmss") + ".ics";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    function triggerShortcut(shifts) {
        let shortcutPayload = shifts.map(shift => {
            // Convert literal '\n' into actual newlines for Apple Calendar
            let formattedNotes = shift.remarks.replace(/\\n/g, '\n');

            return {
                title: "MCD",
                start: shift.startTime.toISO(), 
                end: shift.endTime.toISO(),
                location: shift.location,
                notes: formattedNotes,
                uid: shift.uid
            };
        });

        let jsonString = JSON.stringify(shortcutPayload);
        let encodedJSON = encodeURIComponent(jsonString);
        
        // Construct the URL to trigger the iOS Shortcut
        let shortcutName = encodeURIComponent("MCD Shift Backend");
        let shortcutURL = `shortcuts://run-shortcut?name=${shortcutName}&input=text&text=${encodedJSON}`;
        
        window.location.href = shortcutURL;
    }

    function addHoverButton() {
        const button = document.createElement("button");
        button.innerText = "🗓️";
        button.style.fontSize = "36px";
        button.style.position = "fixed";
        button.style.bottom = "20px";
        button.style.right = "20px";
        button.style.zIndex = "1000";
        button.style.padding = "10px 15px";
        button.style.backgroundColor = "#212429";
        button.style.transition = "background-color 0.3s ease";
        button.onmouseover = () => {
            button.style.backgroundColor = "#343a40";
        };
        button.onmouseout = () => {
            button.style.backgroundColor = "#212429";
        };
        button.style.color = "#fff";
        button.style.border = "none";
        button.style.borderRadius = "12.5px";
        button.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
        button.style.cursor = "pointer";

        button.addEventListener("click", () => {
            let shifts = parseShift();
            let numShifts = shifts.length;
            
            if (numShifts > 0) {
                // Change to createICS(shifts) if you want to swap back to local file downloads
                triggerShortcut(shifts);
                
                if (numShifts === 1) {
                    showFloatingMessage("Converted 1 shift.", true);
                } else {
                    showFloatingMessage(`Converted ${numShifts} shifts.`, true);
                }
            } else {
                showFloatingMessage("No shifts found.", false, 2000);
            }
        });

        document.body.appendChild(button);
    }

    function showFloatingMessage(message, isSuccess = true, duration = 1000) {
        const messageDiv = document.createElement("div");
        messageDiv.innerText = message;
        messageDiv.style.position = "fixed";
        messageDiv.style.bottom = "100px"; 
        messageDiv.style.right = "20px";
        messageDiv.style.backgroundColor = isSuccess ? "#28a745" : "#dc3545"; 
        messageDiv.style.color = "#fff";
        messageDiv.style.padding = "10px 15px";
        messageDiv.style.borderRadius = "12.5px";
        messageDiv.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
        messageDiv.style.zIndex = "1001";
        messageDiv.style.fontSize = "14px";
        messageDiv.style.transition = "opacity 0.5s ease";
        messageDiv.style.opacity = "0";
    
        document.body.appendChild(messageDiv);
    
        setTimeout(() => {
            messageDiv.style.opacity = "1";
        }, 10);
    
        setTimeout(() => {
            messageDiv.style.opacity = "0"; 
            setTimeout(() => {
                document.body.removeChild(messageDiv);
            }, 500);
        }, duration);
    }

    addHoverButton();
})();