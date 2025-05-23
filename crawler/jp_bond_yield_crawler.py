from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import csv
import os
import sys
import subprocess
import re

def get_first_date_in_csv():
    try:
        with open("data/raw/jp_bond_yield.csv", "r", encoding="utf-8") as f:
            next(f)
            first_line = f.readline()
            if first_line:
                return ','.join(first_line.strip().split(',')[:2]).replace('"', '').strip()
    except Exception as e:
        print(f"Error reading first date: {str(e)}")
        return None

def clean_date_for_compare(date_str):
    return re.sub(r'\s+', ' ', date_str.replace('"', '').strip().lower())

def run_cleaner():
    subprocess.run([sys.executable, "cleaner/jp_bond_yield_cleaner.py"])

def run_visualizer():
    subprocess.run([sys.executable, "visualize/jp_bond_yield_visualizer.py"])

def crawl_jp_bond_yield():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Set user agent
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        url = "https://www.investing.com/rates-bonds/japan-5-year-bond-yield-historical-data"
        driver.get(url)
        time.sleep(5)
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(5)

        stop_date = get_first_date_in_csv()
        stop_date_cmp = clean_date_for_compare(stop_date)
        print(f"Stop crawling when reaching date: {stop_date}")

        os.makedirs('data/raw', exist_ok=True)

        try:
            existing_df = csv.reader(open("data/raw/jp_bond_yield.csv", encoding="utf-8"))
            next(existing_df)
            existing_data = list(existing_df)
        except Exception as e:
            print(f"Error reading existing data: {str(e)}")
            existing_data = []

        rows = driver.find_elements(By.CSS_SELECTOR, 'table tr')
        new_data = []

        for i in range(1, len(rows)):
            try:
                row = rows[i]
                date_td = row.find_element(By.CSS_SELECTOR, 'td.sticky.left-0 time')
                date_val_raw = date_td.get_attribute('datetime')
                date_val_cmp = clean_date_for_compare(date_val_raw)
                percent_td = row.find_elements(By.CSS_SELECTOR, 'td')[-1]
                percent_val = percent_td.text.strip()
                if date_val_cmp == stop_date_cmp:
                    print(f"Reached stop date {stop_date}, stopping crawl.")
                    break
                print(f"Found new data for {date_val_raw}: {percent_val}")
                new_data.append([date_val_raw.strip(), percent_val])
                driver.execute_script('arguments[0].scrollIntoView({block: "end"});', row)
                time.sleep(0.15)
            except Exception as e:
                print(f"Error when crawl row: {str(e)}")
                continue

        if not new_data:
            print("No new data found. Stopping process.")
            return False

        all_data = new_data + existing_data
        with open("data/raw/jp_bond_yield.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'yield'])
            writer.writerows(all_data)
        print("Data saved successfully!")
        return True

    except Exception as e:
        print(f"Error during crawling: {str(e)}")
        return False

    finally:
        driver.quit()

if __name__ == "__main__":
    success = crawl_jp_bond_yield()
    if success:
        run_cleaner()
        run_visualizer()
    sys.exit(0 if success else 1) 