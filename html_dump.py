from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from utils import print_info, print_success, print_warning
import time
from typing import Optional

from utils import setup_driver


def scrape_page(url: str, driver: webdriver.Chrome) -> Optional[str]:
    print_info(f"Scraping URL: {url}")
    try:
        driver.get(url)
        time.sleep(5)
        return driver.page_source
    except Exception as e:
        print_warning(f"Error fetching the URL: {e}")
        return None


def save_to_file(content: str, filename: str) -> None:
    print_warning(f"Saving content to {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print_success("Content saved successfully!")


def main() -> None:
    url = "https://www.regulations.gov/document/PHMSA-2011-0023-0118/comment"
    output_file = "result.html"

    with setup_driver() as driver:
        content = scrape_page(url, driver)

    if content:
        save_to_file(content, output_file)


if __name__ == "__main__":
    main()
