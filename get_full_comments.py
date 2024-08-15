import json
import time
import os
import random
from typing import List, Dict, Optional
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from tqdm import tqdm

from utils import (
    print_info, print_success, print_warning, print_error,
    setup_driver, wait_for_element, extract_text, extract_info,
    extract_download_links, get_total_comments
)
from models import CommentInfo, Address, Submitter, Attachment


def scrape_comment_list(driver, url: str) -> List[Dict[str, str]]:
    driver.get(url)
    total_comments = get_total_comments(driver)
    print_info(f"Total comments to scrape: {total_comments}")

    comments = []
    scraped_count = 0

    with tqdm(total=total_comments, desc="Scraping comment list") as pbar:
        while scraped_count < total_comments:
            try:
                wait_for_element(driver, By.CSS_SELECTOR,
                                 ".card.card-type-comment")
                comment_elements = driver.find_elements(
                    By.CSS_SELECTOR, ".card.card-type-comment")

                for comment_element in comment_elements:
                    comments.append(scrape_comment_info(comment_element))
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
                print_warning(f"Timeout waiting for elements on page. Scraped {
                              scraped_count} comments so far.")
                break

    return comments


def scrape_comment_info(comment_element) -> Dict[str, str]:
    html_content = comment_element.get_attribute('outerHTML')
    soup = BeautifulSoup(html_content, 'html.parser')

    return {
        "id": extract_text(soup, "li:-soup-contains('ID')").replace("ID", "").strip(),
        "title": extract_text(soup, "h3.card-title a"),
        "url": soup.select_one("h3.card-title a")['href'],
        "agency": extract_text(soup, "li:-soup-contains('Agency')").replace("Agency", "").strip(),
        "posted_date": extract_text(soup, "li:-soup-contains('Posted')").replace("Posted", "").strip(),
    }


def scrape_comment_details(driver, url: str, max_retries: int = 3) -> Optional[CommentInfo]:
    for attempt in range(max_retries):
        try:
            driver.get(url)
            wait_for_element(driver, By.ID, "mainContent")
            time.sleep(2)  # Short wait for dynamic content to load

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            comment_id = url.split('/')[-1]

            tracking_soup = BeautifulSoup(str(soup.select_one(
                'div.card-block:-soup-contains("Tracking Number")')), 'html.parser')
            tracking_number = extract_text(tracking_soup, 'p.mb-0')

            details_soup = BeautifulSoup(
                str(soup.select_one('#tab-document-details')), 'html.parser')
            document_subtype = extract_info(details_soup, "Document Subtype")
            received_date = extract_info(details_soup, "Received Date")

            submitter_soup = BeautifulSoup(
                str(soup.select_one('#tab-submitter-info')), 'html.parser')
            submitter = Submitter(
                name=extract_info(submitter_soup, "Submitter Name"),
                organization=extract_info(submitter_soup, "Organization Name"),
                representative=extract_info(
                    submitter_soup, "Submitter's Representative"),
                address=Address(
                    line1=extract_info(submitter_soup, "Mailing Address"),
                    line2=extract_info(submitter_soup, "Mailing Address 2"),
                    city=extract_info(submitter_soup, "City"),
                    state=extract_info(submitter_soup, "State or Province"),
                    zip=extract_info(submitter_soup, "ZIP/Postal Code"),
                    country=extract_info(submitter_soup, "Country")
                )
            )

            comment_content = extract_text(soup, 'div.px-2')

            attachments = []
            for attachment_html in soup.find_all('div', class_='card-block'):
                title = extract_text(attachment_html, 'h3.h5')
                if title:
                    download_links = extract_download_links(
                        str(attachment_html))
                    attachments.append(Attachment(
                        title=title, url=download_links[0] if download_links else ""))

            return CommentInfo(
                id=comment_id,
                tracking_number=tracking_number,
                title="",  # This will be updated later
                agency="",  # This will be updated later
                # posted date will be updated later
                dates={"received": received_date, "posted": ""},
                submitter=submitter,
                content=comment_content,
                attachments=attachments,
                document_subtype=document_subtype
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

    print_info("Starting full comment scraping process...")

    try:
        with setup_driver() as driver:
            comment_list = scrape_comment_list(driver, comment_list_url)
            print_success(f"Scraped {len(comment_list)
                                     } comments from the list.")

            full_comments = []

            os.makedirs('output', exist_ok=True)
            output_file = 'output/full_comments_data.json'

            with tqdm(total=len(comment_list), desc="Scraping detailed comments") as pbar:
                for comment in comment_list:
                    comment_url = f"{base_url}{comment['url']}"
                    detailed_comment = scrape_comment_details(
                        driver, comment_url)

                    if detailed_comment:
                        # Update the CommentInfo object with list information
                        detailed_comment.title = comment['title']
                        detailed_comment.agency = comment['agency']
                        detailed_comment.dates['posted'] = comment['posted_date']

                        full_comments.append(detailed_comment.__dict__)

                        # Save progress after each successful scrape
                        with open(output_file, 'w') as f:
                            json.dump(full_comments, f, indent=2,
                                      default=lambda o: o.__dict__)

                    pbar.update(1)
                    # Random delay between requests
                    time.sleep(random.uniform(0.5, 1.5))

        print_success(f"Scraped {len(full_comments)
                                 } full comments. Data saved to {output_file}")

    except Exception as e:
        print_error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
