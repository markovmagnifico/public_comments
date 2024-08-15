from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import re
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
        print_warning(
            "Couldn't find the results count. The page might not have loaded properly.")
        return 0


def scrape_comment_info_from_list(driver, comment_element):
    try:
        html_content = comment_element.get_attribute('outerHTML')
    except StaleElementReferenceException:
        print_warning(
            "Stale element reference encountered. Re-locating the comment element.")
        comment_element = driver.find_element(
            By.XPATH, comment_element.get_xpath())  # Re-find the element
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


def extract_text(soup, selector):
    element = soup.select_one(selector)
    return element.text.strip() if element else None


def extract_download_links(attachment_html):
    soup = BeautifulSoup(attachment_html, 'html.parser')
    links = soup.select('a[href]')
    return [link['href'] for link in links if 'download' in link.get('class', []) or link.find('span', string='Download')]


def scrape_detailed_comment_info(driver, url):
    base_url = "https://www.regulations.gov"
    full_url = base_url + url.strip()

    print_info(f"Fetching detailed comment info: {full_url}")
    driver.get(full_url)

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

    return {
        'comment_id': comment_id,
        'tracking_number': tracking_number,
        'comment_details': comment_details,
        'submitter_info': submitter_info,
        'comment_content': comment_content,
        'attachments': attachments
    }


def scrape_all_comments(url):
    driver = setup_driver()
    driver.get(url)

    total_comments = get_total_comments(driver)
    print_info(f"Total comments to scrape: {total_comments}")

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
                    list_info = scrape_comment_info_from_list(
                        driver, comment_element)
                    detailed_info = scrape_detailed_comment_info(
                        driver, list_info['url'])

                    combined_info = {**list_info, **detailed_info}
                    combined_info['posted_date'] = list_info['posted_date']

                    comments.append(combined_info)
                    scraped_count += 1
                    pbar.update(1)

                    if scraped_count >= total_comments:
                        break

                if scraped_count < total_comments:
                    next_button = wait_for_element(
                        driver, By.CSS_SELECTOR, "button[aria-label='Go to next page']")
                    next_button.click()
                    time.sleep(2)
            except TimeoutException:
                print_warning(f"Timeout waiting for elements on page. Scraped {
                              scraped_count} comments so far.")
                break

    driver.quit()
    return comments


def main():
    url = "https://www.regulations.gov/document/PHMSA-2011-0023-0118/comment"
    print_info("Starting comprehensive comment scraping process...")
    comments = scrape_all_comments(url)

    with open('all_comments_detailed.json', 'w') as f:
        json.dump(comments, f, indent=2)

    print_success(f"Scraped {len(
        comments)} comments with detailed information. Data saved to all_comments_detailed.json")


if __name__ == "__main__":
    main()
