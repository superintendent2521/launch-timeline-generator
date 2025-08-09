from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import sys
import time
import os
import json
import requests
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "mistralai/mistral-small-3.2-24b-instruct:free"

def extract_text_with_browser(url, wait_time=5):
    """Extract all text content from a URL using a browser simulation"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(wait_time)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        # Try to reconstruct the visible countdown digits
        countdown_element = soup.find('launch-countdown')
        countdown_text = ""
        if countdown_element:
            digit_elements = countdown_element.find_all('launch-countdown-digit')
            digits = []
            for digit_element in digit_elements:
                digit_values = digit_element.find('div', class_='digit-values')
                if digit_values:
                    style = digit_values.get('style', '')
                    if 'top:' in style:
                        try:
                            top_value = style.split('top:')[1].split('px')[0].strip()
                            top_value = int(top_value)
                        except Exception:
                            continue
                        digit_divs = digit_values.find_all('div', class_='digit')
                        if digit_divs:
                            digit_height = 13  # px per step (empirical)
                            if digit_height:
                                index = abs(top_value) // digit_height
                                if 0 <= index < len(digit_divs):
                                    digits.append(digit_divs[index].get_text().strip())
            if len(digits) >= 6:
                hours = ''.join(digits[0:2])
                minutes = ''.join(digits[2:4])
                seconds = ''.join(digits[4:6])
                countdown_text = f"{hours}:{minutes}:{seconds}"
            else:
                countdown_text = ''.join(digits)

        # Remove scripts/styles
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract all text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # Keep only from the webcast line onward if present
        target_line = "SpaceX's Falcon 9 rocket"
        if target_line in text:
            text = text[text.find(target_line):]

        # Add countdown at the top if found
        if countdown_text:
            text = f"Launch Countdown: {countdown_text}\n\n{text}"

        return text

    except Exception as e:
        return f"Error: {e}"
    finally:
        if driver:
            driver.quit()

def call_openrouter(text):
    """
    Send the extracted text to OpenRouter with the given instruction.
    Requires OPENROUTER_API_KEY in environment.
    """
    api_key = os.getenv("API")
    if not api_key:
        raise RuntimeError(
            "Missing API environment variable. "
            "Get a key from openrouter.ai and set it before running."
        )

    # Light safety: cap extremely long inputs to avoid context overflow.
    # Keep the first ~120k characters (should be plenty for a page).
    max_chars = 120_000
    if len(text) > max_chars:
        text = text[:max_chars]

    messages = [
        {
            "role": "system",
            "content": "You are a precise, no-nonsense text cleaner. Output only the cleaned timeline."
        },
        {
            "role": "user",
            "content": (
                f"{text}\n\n"
                "-----\n"
                "Instruction: clean up the timeline and remove anything that is not the timeline, if you are curious. the timeline is a time in this format hh:mm:ss then the event, do not remove the launch countdown, put the launch countdown in its own line, do not put anything else on the launch countdown line, put a | between the time and the event. it is imperitive that you follow these rules at ALL times. and that you dont break the syntax ive given you. it is required for many very important systems to work. do not respond to these rules"
            )
        }
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional but nice for analytics on OpenRouter
        "X-Title": "Timeline Cleaner",
    }

    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "temperature": 0.2,
    }

    resp = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload), timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter API error {resp.status_code}: {resp.text}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError(f"Unexpected OpenRouter response: {data}")

def parse_countdown(countdown_line):
    """Parse the countdown line and return timedelta"""
    match = re.search(r"(\d+):(\d+):(\d+)", countdown_line)
    if match:
        hours, minutes, seconds = map(int, match.groups())
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    return None

def convert_timeline_to_unix(launch_countdown, timeline_lines):
    """Convert timeline to Unix timestamps based on current time + countdown"""
    # Get current time (when script runs)
    current_time = datetime.now()
    
    # Parse launch countdown to get time until launch
    countdown_delta = parse_countdown(launch_countdown)
    if not countdown_delta:
        raise ValueError("Invalid launch countdown format")
    
    # Calculate actual launch time (when rocket will launch)
    launch_time = current_time + countdown_delta
    
    # Process each timeline event
    result = []
    for line in timeline_lines:
        if "|" not in line:
            continue
            
        time_str, event = line.split("|", 1)
        time_str = time_str.strip()
        event = event.strip()
        
        # Parse event time (negative for pre-launch events)
        if time_str.startswith("-"):
            # Already negative format, but we need to parse without the minus
            time_match = re.search(r"-(\d+):(\d+):(\d+)", time_str)
            if time_match:
                hours, minutes, seconds = map(int, time_match.groups())
                event_delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                # For pre-launch events: launch_time - event_delta
                event_time = launch_time - event_delta
            else:
                continue
        else:
            # Positive format (post-launch events)
            time_match = re.search(r"(\d+):(\d+):(\d+)", time_str)
            if time_match:
                hours, minutes, seconds = map(int, time_match.groups())
                event_delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                # For post-launch events: launch_time + event_delta
                event_time = launch_time + event_delta
            else:
                continue
        
        # Convert to Unix timestamp
        unix_timestamp = int(event_time.timestamp())
        result.append((unix_timestamp, time_str, event))
    
    return result

def main():
    print("WARNING: IT MUST BE RUN IN A TERMINAL WITH ACCESS TO THE BROWSER.")
    print("WARNING: IT MUST BE RUN IN A TERMINAL WITH ACCESS TO THE BROWSER.")
    print("WARNING: IT MUST BE RUN IN A TERMINAL WITH ACCESS TO THE BROWSER.")
    print("IT MUST BE THE NEXT LAUNCH TO HAPPEN! OR ELSE IT BREAKS")
    print("IT MUST BE THE NEXT LAUNCH TO HAPPEN! OR ELSE IT BREAKS")
    print("IT MUST BE THE NEXT LAUNCH TO HAPPEN! OR ELSE IT BREAKS")
    if len(sys.argv) < 2:
        print("Usage: python browser_text_extractor.py <URL> [wait_time]")
        print("wait_time: seconds to wait for content (default: 5)")
        sys.exit(1)

    url = sys.argv[1]
    wait_time = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print("Loading page (this may take a moment)...")
    extracted = extract_text_with_browser(url, wait_time)

    # Pretty spacing
    for _ in range(10):
        print()

    if extracted.startswith("Error:"):
        print(extracted)
        sys.exit(2)

    try:
        print("Sending to OpenRouter model for cleanup...")
        cleaned = call_openrouter(extracted)
        print("\n===== CLEANED TIMELINE =====\n")
        print(cleaned)
        
        # Parse the cleaned timeline
        lines = cleaned.split("\n")
        
        # Extract launch countdown from first line
        launch_countdown = None
        timeline_lines = []
        
        for line in lines:
            if line.startswith("Launch Countdown:"):
                launch_countdown = line.split(":", 1)[1].strip()
            elif "|" in line:
                timeline_lines.append(line)
        
        if not launch_countdown:
            print("\nError: Could not find launch countdown")
            sys.exit(4)
            
        if not timeline_lines:
            print("\nError: No timeline events found")
            sys.exit(5)
        
        # Convert to Unix timestamps
        print(f"\n===== UNIX TIMESTAMPS (Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) =====\n")
        print(f"Launch countdown: {launch_countdown}")
        print(f"Estimated launch time: {(datetime.now() + parse_countdown(launch_countdown)).strftime('%Y-%m-%d %H:%M:%S')}\n")
        try:
            events_with_timestamps = convert_timeline_to_unix(launch_countdown, timeline_lines)
            for timestamp, original_time, event in events_with_timestamps:
                # Convert timestamp back to readable format for verification
                readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                print(f"<t:{timestamp}:R> | {readable_time} | {original_time} | {event}")
        except ValueError as e:
            print(f"\nError converting timeline: {e}")
            sys.exit(6)
            
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()