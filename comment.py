from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
from colorama import init, Fore, Style

init(autoreset=True)


def print_info(message):
    print(f"{Fore.CYAN}{message}{Style.RESET_ALL}")


def print_success(message):
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")


def print_warning(message):
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")


def setup_driver():
    print_info("Setting up Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def wait_for_element(driver, by, value, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def extract_text(soup, selector):
    element = soup.select_one(selector)
    return element.text.strip() if element else None


def extract_download_links(attachment_html):
    soup = BeautifulSoup(attachment_html, 'html.parser')
    links = soup.select('a[href]')
    return [link['href'] for link in links if 'download' in link.get('class', []) or link.find('span', string='Download')]


def scrape_comment_page(url):
    driver = setup_driver()
    print_info(f"Fetching page: {url}")
    driver.get(url)

    wait_for_element(driver, By.ID, "mainContent")
    print_warning("Waiting for page to load completely...")
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    comment_id = url.split('/')[-1]

    tracking_soup = BeautifulSoup(str(soup.select_one(
        'div.card-block:-soup-contains("Tracking Number")')), 'html.parser')
    tracking_number = extract_text(tracking_soup, 'p.mb-0')

    details_soup = BeautifulSoup(
        str(soup.select_one('#tab-document-details')), 'html.parser')
    comment_details = {
        'Document Subtype': extract_text(details_soup, 'li:-soup-contains("Document Subtype") p.mb-0'),
        'Received Date': extract_text(details_soup, 'li:-soup-contains("Received Date") p.mb-0')
    }

    submitter_soup = BeautifulSoup(
        str(soup.select_one('#tab-submitter-info')), 'html.parser')
    submitter_info = {
        'Submitter Name': extract_text(submitter_soup, 'li:-soup-contains("Submitter Name") p.mb-0'),
        'Mailing Address': extract_text(submitter_soup, 'li:-soup-contains("Mailing Address") p.mb-0'),
        'Mailing Address 2': extract_text(submitter_soup, 'li:-soup-contains("Mailing Address 2") p.mb-0'),
        'City': extract_text(submitter_soup, 'li:-soup-contains("City") p.mb-0'),
        'Country': extract_text(submitter_soup, 'li:-soup-contains("Country") p.mb-0'),
        'State or Province': extract_text(submitter_soup, 'li:-soup-contains("State or Province") p.mb-0'),
        'ZIP/Postal Code': extract_text(submitter_soup, 'li:-soup-contains("ZIP/Postal Code") p.mb-0'),
        'Organization Name': extract_text(submitter_soup, 'li:-soup-contains("Organization Name") p.mb-0'),
        "Submitter's Representative": extract_text(submitter_soup, 'li:-soup-contains("Submitter\'s Representative") p.mb-0')
    }

    comment_content = extract_text(soup, 'div.px-2')

    attachments = []
    for attachment_html in soup.find_all('div', class_='card-block'):
        title = extract_text(attachment_html, 'h3.h5')
        if title:
            download_links = extract_download_links(str(attachment_html))
            attachments.append({
                'title': title,
                'download_links': download_links
            })

    comment_info = {
        'comment_id': comment_id,
        'tracking_number': tracking_number,
        'comment_details': comment_details,
        'submitter_info': submitter_info,
        'comment_content': comment_content,
        'attachments': attachments
    }

    driver.quit()
    return comment_info


def main():
    url = "https://www.regulations.gov/comment/PHMSA-2011-0023-0407"
    print_info("Starting comment scraping process...")
    comment_info = scrape_comment_page(url)

    with open('comment_info_html.json', 'w') as f:
        json.dump(comment_info, f, indent=2)

    print_success(
        "Comment information HTML has been saved to comment_info_html.json")


if __name__ == "__main__":
    main()
