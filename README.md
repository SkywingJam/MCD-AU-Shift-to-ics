# McDonald's AU Shift to ICS

A simple Chrome extension to export your McDonald's Australia shifts to an ICS calendar file.

## Features

- Extracts roster/shift details from the web page.
- Generates an `.ics` file compatible with major calendar apps.
    - Recommended to use cloud-based calendars (Google Calendar, Outlook) for automatic syncing across devices.

## Dependencies

- [Luxon](https://moment.github.io/luxon/): Used for robust date and time parsing and manipulation.

## How to Use

### Installation

1. Download or clone this repository.
2. Open Chrome and navigate to `chrome://extensions/`.
3. Toggle **Developer mode** on in the top right corner.
4. Click **Load unpacked** and select the extension directory.

### Usage

1. Log in to myJob/My Roster and view your roster.
2. Click 📅 button and download your shifts as an ICS file.
3. Open the downloaded file with your calendar app of choice to import the events.

### Reporting Issues

If you encounter any issues or have suggestions for improvements, please open an issue in the issue tracker of this repository.

## Permissions & Privacy

### Permissions
- **Scripting:** Required to inject the parsing script into the roster page to extract shift details.
- **Storage:** Used to store local settings or temporary data needed for generating the calendar file.
- **Host Permissions:** The extension requires access to `https://myrestaurant.mcdonalds.com.au/*` to read the roster data directly from the page.

### Privacy
- **Local Processing:** All data extraction and file generation happen locally within your browser.
- **No Data Collection:** This extension does not collect, store, or transmit your personal information or roster details to any external servers.
- **Open Source:** The code is open source and can be inspected to verify its behavior.

## Disclaimers

- **Region Lock:** This tool is intended and tested for use with McDonald's Australia only. It is not guaranteed to work for other regions.
- **Website Changes:** This extension relies on the current structure of the website. It may break if the website layout or code is updated.
- **Unofficial Software:** This project is not affiliated with, endorsed by, or connected to McDonald's.
