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

def extract_text_with_browser(url, wait_time=5):
    """Extract all text content from a URL using a browser simulation"""
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        # Automatically download and setup ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to the URL
        driver.get(url)
        
        # Wait for page to load
        time.sleep(wait_time)
        
        # Wait for body to be present
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass  # Continue even if wait condition fails
        
        # Get page source after JavaScript execution
        html_content = driver.page_source
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract countdown text by parsing the digit positions
        countdown_element = soup.find('launch-countdown')
        countdown_text = ""
        
        if countdown_element:
            # Find all launch-countdown-digit elements
            digit_elements = countdown_element.find_all('launch-countdown-digit')
            digits = []
            
            for digit_element in digit_elements:
                # Get the digit container
                digit_values = digit_element.find('div', class_='digit-values')
                if digit_values:
                    # Get the top position to determine which digit is visible
                    style = digit_values.get('style', '')
                    if 'top:' in style:
                        # Extract the top value
                        top_value = style.split('top:')[1].split('px')[0].strip()
                        top_value = int(top_value)
                        
                        # Get all digit elements
                        digit_divs = digit_values.find_all('div', class_='digit')
                        if digit_divs:
                            # Calculate which digit is visible based on top position
                            # Each digit is approximately 13px high (based on the -13px, -26px pattern)
                            digit_height = 13
                            if digit_height != 0:
                                # Calculate index: negative top values mean scrolling up
                                index = abs(top_value) // digit_height
                                if 0 <= index < len(digit_divs):
                                    digits.append(digit_divs[index].get_text().strip())
            
            # Format the countdown string (HH:MM:SS format)
            if len(digits) >= 6:
                hours = ''.join(digits[0:2])
                minutes = ''.join(digits[2:4])
                seconds = ''.join(digits[4:6])
                countdown_text = f"{hours}:{minutes}:{seconds}"
            else:
                countdown_text = ''.join(digits)
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract all text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Remove all text before the specified line
        target_line = "A live webcast of this mission will begin about 15 minutes prior to liftoff"
        if target_line in text:
            text = text[text.find(target_line):]
        
        # Add countdown digits text at the beginning if found
        if countdown_text:
            text = f"Launch Countdown: {countdown_text}\n\n{text}"
        
        return text
        
    except Exception as e:
        return f"Error: {e}"
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python browser_text_extractor.py <URL> [wait_time]")
        print("wait_time: seconds to wait for content (default: 5)")
        sys.exit(1)
    
    url = sys.argv[1]
    wait_time = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    print("Loading page (this may take a moment)...")
    text_content = extract_text_with_browser(url, wait_time)
    # This prints 10 empty lines by looping 10 times and calling print() each time, pretty prints it
    for i in range(10):
        print()
    print(text_content)