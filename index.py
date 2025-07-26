from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
from datetime import datetime, timedelta

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in background
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# URL of the page
url = "https://www.spacex.com/launches/sl-17-2"

try:
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Load the page
    driver.get(url)
    
    # Wait for the content to load
    time.sleep(5)
    
    # Find all rows in the timeline table
    timeline_rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
    
    # List to store time-event pairs
    timeline_events = []

    # Iterate through each row
    for row in timeline_rows:
        try:
            # Find time cell (first td)
            time_cell = row.find_element(By.CSS_SELECTOR, 'td.timeline-time')
            time_text = time_cell.text.strip()
            
            # Find event cell (second td)
            event_cell = row.find_element(By.CSS_SELECTOR, 'td.timeline-description')
            event_text = event_cell.text.strip()
            
            # Only add non-empty entries
            if time_text and event_text:
                timeline_events.append({
                    'time': time_text,
                    'event': event_text
                })
        except:
            # Skip rows that don't have the expected structure
            continue

    # Print all extracted time-event pairs with Discord timestamps
    print("Launch Timeline with Discord Timestamps:")
    print("="*50)
    
    # For demonstration, we'll use current time as the reference point
    # In a real scenario, you'd use the actual launch time
    reference_time = datetime.utcnow()
    
    for item in timeline_events:
        # Parse the time (format: HH:MM:SS)
        time_parts = item['time'].split(':')
        if len(time_parts) == 3:
            hours, minutes, seconds = map(int, time_parts)
            # Convert to timedelta (assuming times are before launch)
            time_delta = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            # Calculate actual timestamp (reference - countdown)
            event_time = reference_time - time_delta
            # Create Discord timestamp
            discord_timestamp = f"<t:{int(event_time.timestamp())}:f>"
            
            print(f"Time: {item['time']} ({discord_timestamp})")
            print(f"Event: {item['event']}")
            print("-" * 30)
        
except Exception as e:
    print(f"An error occurred: {e}")
    
finally:
    try:
        driver.quit()
    except:
        pass