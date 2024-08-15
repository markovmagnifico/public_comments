from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from colorama import init, Fore
from tqdm import tqdm
import time

# Initialize colorama
init(autoreset=True)


def setup_driver():
    print(Fore.YELLOW + "Setting up Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def scrape_page(url, driver):
    print(Fore.CYAN + f"Scraping URL: {url}")

    try:
        driver.get(url)
        # Wait for the page to load (adjust the sleep time if needed)
        time.sleep(5)
        page_source = driver.page_source
    except Exception as e:
        print(Fore.RED + f"Error fetching the URL: {e}")
        return None

    return page_source


def save_to_file(content, filename):
    print(Fore.YELLOW + f"Saving content to {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(Fore.GREEN + "Content saved successfully!")


def main():
    url = "https://www.regulations.gov/document/PHMSA-2011-0023-0118/comment"
    output_file = "result.html"

    driver = setup_driver()
    content = scrape_page(url, driver)
    driver.quit()

    if content:
        save_to_file(content, output_file)


if __name__ == "__main__":
    main()
