import os
import sys
import json
import threading
import logging
import queue
import shutil
import base64
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import atexit
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import re
from html.parser import HTMLParser

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)  # Enable CORS for the Flask app

message_queue = queue.Queue()  # Thread-safe queue for communication

# Paths and configuration
script_dir = Path(__file__).resolve().parent
extension_dir = script_dir / "chrome_extension"  # Extension directory
config_file = script_dir / "config.json"

# Embedded file contents
MANIFEST_JSON = '''
{
  "manifest_version": 3,
  "name": "BASECAMP BUDDY",
  "version": "1.0",
  "description": "Communicates with a Python Flask server",
  "permissions": ["activeTab", "scripting", "contextMenus", "notifications"],
  "host_permissions": ["http://127.0.0.1/*"],
  "background": {
    "service_worker": "background.js"
  },
  "icons": {
    "16": "icon.png",
    "32": "icon.png",
    "48": "icon.png",
    "128": "icon.png"
  }
}
'''

BACKGROUND_JS = '''
// background.js

// Create context menu items when the extension is installed
chrome.runtime.onInstalled.addListener(() => {
  // Parent menu item
  chrome.contextMenus.create({
    id: "basecampBuddy",
    title: "BASECAMP BUDDY",
    contexts: ["page", "selection"]
  });

  // Child menu items for text selection
  chrome.contextMenus.create({
    id: "sendPlainText",
    parentId: "basecampBuddy",
    title: "Send Plain Text",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "translateToMandarin",
    parentId: "basecampBuddy",
    title: "Translate to Mandarin",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "provideDiscussionSummary",
    parentId: "basecampBuddy",
    title: "Provide Discussion Summary",
    contexts: ["selection"]
  });

  // Child menu items for page context
  chrome.contextMenus.create({
    id: "summarizePage",
    parentId: "basecampBuddy",
    title: "Summarize Page",
    contexts: ["page"]
  });

  chrome.contextMenus.create({
    id: "showAllLinks",
    parentId: "basecampBuddy",
    title: "Show All Links",
    contexts: ["page"]
  });
});

// Add a click event listener for the context menu items
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (
    info.menuItemId === "sendPlainText" ||
    info.menuItemId === "translateToMandarin" ||
    info.menuItemId === "provideDiscussionSummary"
  ) {
    // Send the selected text to the Flask server
    fetch("http://127.0.0.1:5000/receive_text", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        menuItemId: info.menuItemId,
        text: info.selectionText
      })
    })
      .then(response => response.json())
      .then(data => {
        console.log("Received response:", data);
        // Use chrome.runtime.getURL to correctly reference the icon
        chrome.notifications.create({
          type: "basic",
          iconUrl: chrome.runtime.getURL('icon.png'),
          title: "BASECAMP BUDDY",
          message: data.reply
        });
      })
      .catch(error => {
        console.error("Error:", error);
        alert("Error: " + error);
      });
  } else if (
    info.menuItemId === "summarizePage" ||
    info.menuItemId === "showAllLinks"
  ) {
    // Execute a script in the page to get the content
    chrome.scripting.executeScript(
      {
        target: { tabId: tab.id },
        func: () => {
          return {
            text: document.body.innerText,
            html: document.body.innerHTML
          };
        }
      },
      (results) => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError);
          return;
        }

        const result = results[0].result;
        // Send the page content to the Flask server
        fetch("http://127.0.0.1:5000/receive_text", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            menuItemId: info.menuItemId,
            text: result.text,
            html: result.html
          })
        })
          .then(response => response.json())
          .then(data => {
            console.log("Received response:", data);
            // Use chrome.runtime.getURL to correctly reference the icon
            chrome.notifications.create({
              type: "basic",
              iconUrl: chrome.runtime.getURL('icon.png'),
              title: "BASECAMP BUDDY",
              message: data.reply
            });
          })
          .catch(error => {
            console.error("Error:", error);
            alert("Error: " + error);
          });
      }
    );
  }
});
'''

# Base64-encoded icon.png (a simple red dot image)
ICON_PNG_BASE64 = '''
iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAABF0lEQVRYhe3XwQ2AIAwF0P//6Shl
cBVN+NHKTqyohJLE1EADgY0NLLyUz4gkDBgQIECBAgQIAAAQIECAAAECBAgQIECAAAECBAgQIEDg
G4L0KxjMY6dA+eGgVQGvsA+gZAG9CV6o0TaBDpDQOk0SahQAIECAAAECBAgQIECAAAECBAgQIECA
AAECBAgQIECAQKgHYLzCEmfZcaA6XME/QBYIXAH6BPgoABAgQIECBAgAABAgQIECBAgAABAgQIEC
BAgAABAgQIECBAgAABAgQIECAAAECBAgQIECgBqC/AViN38PC/bYAAAAASUVORK5CYII=
'''

created_files = []

def cleanup():
    logging.debug("Cleaning up created files...")
    for file_path in created_files:
        try:
            if file_path.exists():
                file_path.unlink()
                logging.debug(f"Deleted: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting {file_path}: {e}")

atexit.register(cleanup)

def write_file(path, content, binary=False):
    try:
        if binary:
            with open(path, 'wb') as f:
                f.write(content)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        created_files.append(Path(path))
        logging.debug(f"File written successfully: {path}")
    except Exception as e:
        logging.error(f"Error writing to {path}: {e}")
        raise

def create_extension_files(extension_dir):
    write_file(extension_dir / "manifest.json", MANIFEST_JSON.strip())
    write_file(extension_dir / "background.js", BACKGROUND_JS.strip())
    # Decode the base64-encoded icon and write it to the extension directory
    icon_data = base64.b64decode(ICON_PNG_BASE64)
    write_file(extension_dir / "icon.png", icon_data, binary=True)
    logging.info("Extension files created successfully")

def install_extension():
    extension_dir.mkdir(parents=True, exist_ok=True)
    print("Creating extension files...")
    logging.debug("Creating extension files...")
    create_extension_files(extension_dir)
    print(f"Extension files created in: {extension_dir}")

    print("\nInstructions to load the extension in Chrome:")
    print("1. Open Google Chrome")
    print("2. Go to chrome://extensions/")
    print("3. Enable 'Developer mode' in the top right corner")
    print("4. Click 'Load unpacked' and select the following directory:")
    print(f"   {extension_dir}")

    input("\nPress Enter when you've loaded the extension...")

    # Update configuration file
    config = {'extension_installed': True}
    with open(config_file, 'w') as f:
        json.dump(config, f)
    logging.debug("Updated configuration file indicating extension is installed.")

# Flask route and function definitions
@app.route('/receive_text', methods=['POST'])
def receive_text():
    data = request.get_json()
    menu_item_id = data.get('menuItemId', '')
    text = data.get('text', '')
    html = data.get('html', '')
    logging.debug(f"Received menu item: {menu_item_id}")
    logging.debug(f"Received text from extension: {text[:100]}")  # Log only first 100 chars
    # Process based on menu item
    if menu_item_id == 'summarizePage' or menu_item_id == 'provideDiscussionSummary':
        # Implement summarization logic
        summary = summarize_text(text)
        message_queue.put(summary)
        response_message = 'Summary provided'
    elif menu_item_id == 'showAllLinks':
        # Extract links from html
        links = extract_links(html)
        message_queue.put(links)
        response_message = 'Links extracted'
    elif menu_item_id == 'sendPlainText':
        # Send the text as-is to the GUI
        message_queue.put(text)
        response_message = 'Text received by Flask server'
    elif menu_item_id == 'translateToMandarin':
        # Simulate translation (since we cannot actually translate here)
        translated_text = translate_to_mandarin(text)
        message_queue.put(translated_text)
        response_message = 'Text translated to Mandarin'
    else:
        # Default case
        message_queue.put(text)
        response_message = 'Text received by Flask server'
    response = {'reply': response_message}
    return jsonify(response)

def summarize_text(text):
    # Simple summarization: return the first 3 sentences
    sentences = re.split(r'(?<=[.!?]) +', text)
    summary = ' '.join(sentences[:3])
    return summary

def translate_to_mandarin(text):
    # Placeholder function for translation
    # In real implementation, you'd integrate with a translation API
    translated = "[Translated to Mandarin]: " + text
    return translated

class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for (attr, value) in attrs:
                if attr == 'href':
                    self.links.append(value)
def extract_links(html):
    parser = LinkExtractor()
    parser.feed(html)
    links_text = '\n'.join(parser.links)
    return links_text

def run_flask_app():
    app.run(host='127.0.0.1', port=5000)

# GUI class
class TextDisplayGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BASECAMP BUDDY")
        # Use ScrolledText widget to handle large amounts of text
        self.text_widget = ScrolledText(self.root, wrap=tk.WORD, width=60, height=20)
        self.text_widget.pack(padx=10, pady=10)
        # Disable editing
        self.text_widget.config(state=tk.DISABLED)
        # Start checking the queue
        self.check_queue()
        # Start the Tkinter mainloop in the main thread
        self.root.mainloop()

    def check_queue(self):
        try:
            # Try to get a message from the queue without blocking
            text = message_queue.get_nowait()
            self.update_text(text)
        except queue.Empty:
            pass
        # Schedule the check_queue method to run again after 100ms
        self.root.after(100, self.check_queue)

    def update_text(self, new_text):
        # Enable editing
        self.text_widget.config(state=tk.NORMAL)
        # Clear existing text
        self.text_widget.delete(1.0, tk.END)
        # Insert new text
        self.text_widget.insert(tk.END, new_text)
        # Disable editing
        self.text_widget.config(state=tk.DISABLED)
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)

def main():
    try:
        # Always install the extension files
        install_extension()

        print("\nStarting Flask server...")
        # Start the Flask server in a separate thread
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        flask_thread.start()

        print("Flask server is running on http://127.0.0.1:5000")
        print("You can now interact with the extension.")

        # Start the Tkinter GUI in the main thread
        gui = TextDisplayGUI()

    except Exception as e:
        logging.exception("Error in main")
        print(f"An error occurred. Please check the log file for details.")
        print(f"Error details: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
