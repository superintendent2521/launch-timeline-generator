from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

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
    
    # Print the HTML content
    print("HTML content:")
    print(driver.page_source)
    print("\n" + "="*50 + "\n")
    
    # Find all td elements with class 'timeline-time'
    time_elements = driver.find_elements(By.CSS_SELECTOR, 'td.timeline-time')
    
    # List to store all extracted numbers
    all_numbers = []

    # Iterate through each time element
    for element in time_elements:
        # Get text content
        text = element.text.strip()
        # Extract numbers including negative and decimal numbers
        numbers = re.findall(r'-?\d+\.?\d*', text)
        # Add numbers to the main list
        all_numbers.extend(numbers)

    # Print all extracted numbers
    print("Extracted numbers:")
    for number in all_numbers:
        print(number)
        
except Exception as e:
    print(f"An error occurred: {e}")
    
finally:
    try:
        driver.quit()
    except:
        pass