from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
from typing import List, Optional
import re

init(autoreset=True)


def print_colored(color: str, message: str) -> None:
    print(f"{color}{message}{Style.RESET_ALL}")


def print_info(msg: str) -> None:
    print_colored(Fore.CYAN, msg)


def print_success(msg: str) -> None:
    print_colored(Fore.GREEN, msg)


def print_warning(msg: str) -> None:
    print_colored(Fore.YELLOW, msg)


def print_error(msg: str) -> None:
    print_colored(Fore.RED, msg)


def setup_driver() -> webdriver.Chrome:
    print_info("Setting up Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service()
    return webdriver.Chrome(service=service, options=chrome_options)


def wait_for_element(driver: webdriver.Chrome, by: By, value: str, timeout: int = 20) -> WebElement:
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def extract_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    element = soup.select_one(selector)
    return element.text.strip() if element else None


def extract_info(soup: BeautifulSoup, field: str) -> Optional[str]:
    return extract_text(soup, f'li:-soup-contains("{field}") p.mb-0')


def extract_download_links(attachment_html: str) -> List[str]:
    soup = BeautifulSoup(attachment_html, 'html.parser')
    links = soup.select('a[href]')
    return [link['href'] for link in links if 'download' in link.get('class', []) or link.find('span', string='Download')]


def get_total_comments(driver: webdriver.Chrome) -> int:
    try:
        results_element = wait_for_element(
            driver, By.CSS_SELECTOR, ".pagination-container p")
        results_text = results_element.text
        match = re.search(r'of (\d+) results', results_text)
        return int(match.group(1)) if match else 0
    except TimeoutException:
        print_warning(
            "Couldn't find the results count. The page might not have loaded properly.")
        return 0
