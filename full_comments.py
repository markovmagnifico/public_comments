from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import json
import re
import time
from bs4 import BeautifulSoup


def setup_driver():
    print("Setting up Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def wait_for_element(driver, by, value, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def get_total_comments(driver):
    try:
        results_element = wait_for_element(
            driver, By.CSS_SELECTOR, ".pagination-container p")
        results_text = results_element.text
        match = re.search(r'of (\d+) results', results_text)
        return int(match.group(1)) if match else 0
    except TimeoutException:
        print("Couldn't find the results count. The page might not have loaded properly.")
        return 0


def scrape_comment_info(comment_element):
    html_content = comment_element.get_attribute('outerHTML')
    soup = BeautifulSoup(html_content, 'html.parser')

    title = soup.select_one("h3.card-title a").text.strip()
    url = soup.select_one("h3.card-title a")['href']
    agency = soup.select_one(
        "li:-soup-contains('Agency')").text.replace("Agency", "").strip()
    posted_date = soup.select_one(
        "li:-soup-contains('Posted')").text.replace("Posted", "").strip()
    comment_id = soup.select_one(
        "li:-soup-contains('ID')").text.replace("ID", "").strip()

    return {
        "title": title,
        "url": url,
        "agency": agency,
        "posted_date": posted_date,
        "id": comment_id,
    }


def scrape_comments(url):
    driver = setup_driver()
    driver.get(url)

    total_comments = get_total_comments(driver)
    print(f"Total comments to scrape: {total_comments}")

    comments = []
    scraped_count = 0

    with tqdm(total=total_comments, desc="Scraping comments") as pbar:
        while scraped_count < total_comments:
            try:
                wait_for_element(driver, By.CSS_SELECTOR,
                                 ".card.card-type-comment")

                comment_elements = driver.find_elements(
                    By.CSS_SELECTOR, ".card.card-type-comment")

                for comment_element in comment_elements:
                    comment_info = scrape_comment_info(comment_element)
                    comments.append(comment_info)
                    scraped_count += 1
                    pbar.update(1)

                    if scraped_count >= total_comments:
                        break

                if scraped_count < total_comments:
                    next_button = wait_for_element(
                        driver, By.CSS_SELECTOR, "button[aria-label='Go to next page']")
                    next_button.click()
                    time.sleep(2)  # Wait for the page to load
            except TimeoutException:
                print(f"Timeout waiting for elements on page. Scraped {
                      scraped_count} comments so far.")
                break

    driver.quit()
    return comments


def main():
    url = "https://www.regulations.gov/document/PHMSA-2011-0023-0118/comment"
    comments = scrape_comments(url)

    with open('comments.json', 'w') as f:
        json.dump(comments, f, indent=2)

    print(f"Scraped {len(comments)} comments. Data saved to comments.json")


if __name__ == "__main__":
    main()
