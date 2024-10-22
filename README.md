# BASECAMP BUDDY

## Overview

BASECAMP BUDDY is a Python-based tool designed to enhance productivity by integrating a Chrome extension with a local Flask server and a Tkinter GUI interface. This project allows users to interact with web pages directly from their browser and receive real-time feedback in a desktop interface.

## Features

- **Chrome Extension Integration:** Communicates with the Flask server through a locally hosted API.
- **Context Menu Options:** Offers actions like text translation, discussion summarization, and link extraction directly from the Chrome context menu.
- **Real-Time Updates:** Uses a Tkinter GUI to display received data in real time.
- **Flask Server:** Handles backend logic for various actions like summarization, translation, and page analysis.
- **Cross-Platform Notifications:** Provides desktop notifications through the Chrome extension when operations are completed.

## Why Use BASECAMP BUDDY?

This tool simplifies repetitive tasks by enabling:
- Quick text translation to Mandarin for selected content.
- Real-time discussion summaries to improve collaboration.
- Instant link extraction for easier navigation.
- A seamless workflow between your browser and desktop application.
- Ideal for users who frequently interact with online discussions, research documents, or need quick translations.

## How It Works

1. **Chrome Extension**:
   - Provides context menu options for selected text or the entire page.
   - Sends the selected content to the Flask server for processing.

2. **Flask Server**:
   - Handles requests sent from the Chrome extension.
   - Provides responses such as translated text, summaries, or extracted links.

3. **Tkinter GUI**:
   - Displays results in a simple, non-editable text area.
   - Updates in real-time as new responses arrive from the server.

## Getting Started

### Prerequisites

- Python 3.x installed on your system.
- Google Chrome browser.

### Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Install required Python packages:
   ```bash
   pip install flask flask-cors
   ```

3. Run the script to install the Chrome extension:
   ```bash
   python Script.py
   ```

4. Follow the instructions displayed in the terminal to load the extension into Chrome.

### Usage

- Start the Flask server and Tkinter GUI by running the main script:
  ```bash
  python Script.py
  ```

- Use the extension from the Chrome context menu for various actions:
  - **Send Plain Text**: Sends the selected text to the Tkinter GUI.
  - **Translate to Mandarin**: Translates the selected text.
  - **Summarize Page/Discussion**: Provides a summary of the content.
  - **Show All Links**: Extracts all links from the page.

## Troubleshooting

- Ensure that Chrome is in **Developer Mode** to load the unpacked extension.
- Verify that the Flask server is running on `http://127.0.0.1:5000`.
- If the GUI does not update, confirm that no exceptions are logged in the console.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Special thanks to all contributors and open-source projects that made this integration possible.
