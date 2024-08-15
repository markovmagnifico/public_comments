import random
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import time
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from bs4 import BeautifulSoup
from tqdm import tqdm

from utils import (
    print_info, print_success, print_warning, print_error,
    setup_driver, extract_text, extract_info
)


@dataclass
class CommentDetails:
    document_subtype: str
    received_date: str


@dataclass
class SubmitterInfo:
    submitter_name: str
    mailing_address: str
    mailing_address_2: Optional[str]
    city: str
    country: str
    state_or_province: str
    zip_postal_code: str
    organization_name: Optional[str]
    submitter_representative: Optional[str]


@dataclass
class Attachment:
    title: str
    download_links: List[str]


@dataclass
class CommentInfo:
    comment_id: str
    tracking_number: str
    comment_details: CommentDetails
    submitter_info: SubmitterInfo
    comment_content: str
    attachments: List[Attachment]
    title: str
    agency: str
    posted_date: str


# ... (Keep all the dataclass definitions as before)


def get_total_comments(driver: webdriver.Chrome) -> int:
    try:
        results_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".pagination-container p"))
        )
        results_text = results_element.text
        match = re.search(r'of (\d+) results', results_text)
        return int(match.group(1)) if match else 0
    except TimeoutException:
        print_warning(
            "Couldn't find the results count. The page might not have loaded properly.")
        return 0


def scrape_comment_list(driver: webdriver.Chrome, url: str) -> List[Dict[str, str]]:
    driver.get(url)
    total_comments = get_total_comments(driver)
    print_info(f"Total comments to scrape: {total_comments}")

    comments = []
    scraped_count = 0

    with tqdm(total=total_comments, desc="Scraping comment list") as pbar:
        while scraped_count < total_comments:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, ".card.card-type-comment"))
                )
                comment_elements = driver.find_elements(
                    By.CSS_SELECTOR, ".card.card-type-comment")

                for comment_element in comment_elements:
                    comments.append(scrape_comment_info(comment_element))
                    scraped_count += 1
                    pbar.update(1)

                    if scraped_count >= total_comments:
                        break

                if scraped_count < total_comments:
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "button[aria-label='Go to next page']"))
                    )
                    next_button.click()
                    time.sleep(2)  # Short wait for page load
            except TimeoutException:
                print_warning(f"Timeout waiting for elements on page. Scraped {
                              scraped_count} comments so far.")
                break

    return comments


def scrape_comment_info(comment_element: WebElement) -> Dict[str, str]:
    html_content = comment_element.get_attribute('outerHTML')
    soup = BeautifulSoup(html_content, 'html.parser')

    return {
        "title": extract_text(soup, "h3.card-title a"),
        "url": soup.select_one("h3.card-title a")['href'],
        "agency": extract_text(soup, "li:-soup-contains('Agency')").replace("Agency", "").strip(),
        "posted_date": extract_text(soup, "li:-soup-contains('Posted')").replace("Posted", "").strip(),
        "id": extract_text(soup, "li:-soup-contains('ID')").replace("ID", "").strip(),
    }


def extract_download_links(attachment_html: str) -> List[str]:
    soup = BeautifulSoup(attachment_html, 'html.parser')
    links = soup.select('a[href]')
    return [link['href'] for link in links if 'download' in link.get('class', []) or link.find('span', string='Download')]


def scrape_comment_details(driver: webdriver.Chrome, url: str, max_retries: int = 3) -> Optional[CommentInfo]:
    for attempt in range(max_retries):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "mainContent"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            comment_id = url.split('/')[-1]

            tracking_soup = BeautifulSoup(str(soup.select_one(
                'div.card-block:-soup-contains("Tracking Number")')), 'html.parser')
            tracking_number = extract_text(tracking_soup, 'p.mb-0')

            details_soup = BeautifulSoup(
                str(soup.select_one('#tab-document-details')), 'html.parser')
            comment_details = CommentDetails(
                document_subtype=extract_info(
                    details_soup, "Document Subtype"),
                received_date=extract_info(details_soup, "Received Date")
            )

            submitter_soup = BeautifulSoup(
                str(soup.select_one('#tab-submitter-info')), 'html.parser')
            submitter_info = SubmitterInfo(
                submitter_name=extract_info(submitter_soup, "Submitter Name"),
                mailing_address=extract_info(
                    submitter_soup, "Mailing Address"),
                mailing_address_2=extract_info(
                    submitter_soup, "Mailing Address 2"),
                city=extract_info(submitter_soup, "City"),
                country=extract_info(submitter_soup, "Country"),
                state_or_province=extract_info(
                    submitter_soup, "State or Province"),
                zip_postal_code=extract_info(
                    submitter_soup, "ZIP/Postal Code"),
                organization_name=extract_info(
                    submitter_soup, "Organization Name"),
                submitter_representative=extract_info(
                    submitter_soup, "Submitter's Representative")
            )

            comment_content = extract_text(soup, 'div.px-2')

            attachments = []
            for attachment_html in soup.find_all('div', class_='card-block'):
                title = extract_text(attachment_html, 'h3.h5')
                if title:
                    download_links = extract_download_links(
                        str(attachment_html))
                    attachments.append(Attachment(
                        title=title, download_links=download_links))

            return CommentInfo(
                comment_id=comment_id,
                tracking_number=tracking_number,
                comment_details=comment_details,
                submitter_info=submitter_info,
                comment_content=comment_content,
                attachments=attachments,
                title="",  # These fields will be populated later
                agency="",
                posted_date=""
            )
        except (TimeoutException, WebDriverException) as e:
            print_warning(f"Error scraping {url} (attempt {
                          attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                # Random delay between retries
                time.sleep(random.uniform(1, 3))
            else:
                print_error(f"Failed to scrape {url} after {
                            max_retries} attempts")
                return None


def main():
    base_url = "https://www.regulations.gov"
    comment_list_url = f"{base_url}/document/PHMSA-2011-0023-0118/comment"

    print_info("Starting comment scraping process...")

    try:
        with setup_driver() as driver:
            comment_list = scrape_comment_list(driver, comment_list_url)
            print_success(f"Scraped {len(comment_list)
                                     } comments from the list.")

            full_comments = []

            # Load previously scraped comments if the file exists
            try:
                with open('full_comments_data.json', 'r') as f:
                    full_comments = json.load(f)
                print_info(f"Loaded {len(full_comments)
                                     } previously scraped comments.")
            except FileNotFoundError:
                pass

            # Find the index of the last scraped comment
            last_scraped_index = next((i for i, c in enumerate(
                comment_list) if c['id'] not in [fc['comment_id'] for fc in full_comments]), 0)

            with tqdm(total=len(comment_list), initial=last_scraped_index, desc="Scraping detailed comments") as pbar:
                for comment in comment_list[last_scraped_index:]:
                    comment_url = f"{base_url}{comment['url']}"
                    detailed_comment = scrape_comment_details(
                        driver, comment_url)

                    if detailed_comment:
                        # Combine list and detailed information
                        detailed_comment.title = comment['title']
                        detailed_comment.agency = comment['agency']
                        detailed_comment.posted_date = comment['posted_date']

                        full_comments.append(asdict(detailed_comment))

                        # Save progress after each successful scrape
                        with open('full_comments_data.json', 'w') as f:
                            json.dump(full_comments, f, indent=2)

                    pbar.update(1)
                    # Random delay between requests
                    time.sleep(random.uniform(0.5, 1.5))

        print_success(f"Scraped {
                      len(full_comments)} full comments. Data saved to full_comments_data.json")

    except Exception as e:
        print_error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
