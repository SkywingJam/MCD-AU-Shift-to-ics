(function () {
    const { DateTime } = luxon;

    function parseShift() {
        let shifts = [];
        document.querySelectorAll("div#time").forEach(timeDiv => {
            let shiftId = timeDiv.querySelector("strong")?.innerText?.trim();
            // detect if shiftID contains "Today" or "Tomorrow"
            if (shiftId && (shiftId.includes("Today") || shiftId.includes("Tomorrow"))) {
                // remove "Today" or "Tomorrow" and the newline
                shiftId = shiftId.replace(/Today|Tomorrow/g, "").trim();
                // remove the newline character
                shiftId = shiftId.replace(/\n/g, "");
            }
            if (!shiftId) return;

            // Extract date from shiftId
            let dateStr = shiftId.split(" ").pop(); // Example: "31/Mar/2025"
            let shiftDate = DateTime.fromFormat(dateStr, "dd/MMM/yyyy");

            // Extract start time
            let startTag = [...timeDiv.childNodes].find(n => n.textContent.includes("Start"));
            let startStr = startTag ? startTag.nextElementSibling.innerText.trim() : null; // Example: "4:00 PM Monday 31/Mar/2025"
            let startTime = startStr ? DateTime.fromFormat(startStr, "h:mm a EEEE dd/MMM/yyyy") : null;

            // Extract end time
            let endTag = [...timeDiv.childNodes].find(n => n.textContent.includes("Finish"));
            let endStr = endTag ? endTag.nextElementSibling.innerText.trim() : null; // Example: "10:00 PM Monday 31/Mar/2025"
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

            // Extract role (e.g., PI, SI, etc.)
            let roleTag = timeDiv.querySelectorAll("span")[4+isToday];
            if (roleTag && roleTag.innerText.includes("Break")) {
                roleTag = timeDiv.querySelectorAll("span")[5+isToday];
            }
            let role = roleTag ? roleTag.innerText.trim() : "No role";

            // Append role to remarks
            remarks += `\\n${role}`;

            shifts.push({ shiftId, startTime, endTime, location, remarks });
        });
        console.log("Shifts found:", shifts);
        return shifts;
    }

    function createICS(shifts) {
        let icsContent = "BEGIN:VCALENDAR\nVERSION:2.0\n";
        let now = DateTime.now().toUTC().toFormat("yyyyMMdd'T'HHmmss'Z'");
        shifts.forEach(shift => {
            let uid = btoa(shift.shiftId); 
            icsContent += `
BEGIN:VEVENT
LAST-MODIFIED:${now}
DTSTAMP:${now}
UID:${uid}
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
                createICS(shifts);
                if (numShifts === 1) {
                    showFloatingMessage("Converted 1 shift.", true);
                }
                else {
                    showFloatingMessage(`Converted ${numShifts} shifts.`, true);
                }
            }
            else showFloatingMessage("No shifts found.", false, 2000);
        });

        document.body.appendChild(button);
    }

    function showFloatingMessage(message, isSuccess = true, duration = 1000) {
        const messageDiv = document.createElement("div");
        messageDiv.innerText = message;
        messageDiv.style.position = "fixed";
        messageDiv.style.bottom = "100px"; // Position above the button
        messageDiv.style.right = "20px";
        messageDiv.style.backgroundColor = isSuccess ? "#28a745" : "#dc3545"; // Green for success, red for error
        messageDiv.style.color = "#fff";
        messageDiv.style.padding = "10px 15px";
        messageDiv.style.borderRadius = "12.5px";
        messageDiv.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
        messageDiv.style.zIndex = "1001";
        messageDiv.style.fontSize = "14px";
        messageDiv.style.transition = "opacity 0.5s ease";
        messageDiv.style.opacity = "0";
    
        document.body.appendChild(messageDiv);
    
        // Fade-in
        setTimeout(() => {
            messageDiv.style.opacity = "1";
        }, 10);
    
        // Fade out
        setTimeout(() => {
            messageDiv.style.opacity = "0"; // Start fade-out
            setTimeout(() => {
                document.body.removeChild(messageDiv);
            }, 500);
        }, duration);
    }

    // Add the hover button when the script runs
    addHoverButton();
})();