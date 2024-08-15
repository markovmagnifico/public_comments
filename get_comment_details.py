"""Script to pull a single comment details from an NPRM on regulations.gov"""
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from utils import (
    print_info, print_success, print_warning, print_error,
    setup_driver, wait_for_element, extract_text, extract_info
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


def extract_download_links(attachment_html: str) -> List[str]:
    soup = BeautifulSoup(attachment_html, 'html.parser')
    links = soup.select('a[href]')
    return [link['href'] for link in links if 'download' in link.get('class', []) or link.find('span', string='Download')]


def scrape_comment_page(url: str) -> CommentInfo:
    with setup_driver() as driver:
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
    comment_details = CommentDetails(
        document_subtype=extract_info(details_soup, "Document Subtype"),
        received_date=extract_info(details_soup, "Received Date")
    )

    submitter_soup = BeautifulSoup(
        str(soup.select_one('#tab-submitter-info')), 'html.parser')
    submitter_info = SubmitterInfo(
        submitter_name=extract_info(submitter_soup, "Submitter Name"),
        mailing_address=extract_info(submitter_soup, "Mailing Address"),
        mailing_address_2=extract_info(submitter_soup, "Mailing Address 2"),
        city=extract_info(submitter_soup, "City"),
        country=extract_info(submitter_soup, "Country"),
        state_or_province=extract_info(submitter_soup, "State or Province"),
        zip_postal_code=extract_info(submitter_soup, "ZIP/Postal Code"),
        organization_name=extract_info(submitter_soup, "Organization Name"),
        submitter_representative=extract_info(
            submitter_soup, "Submitter's Representative")
    )

    comment_content = extract_text(soup, 'div.px-2')

    attachments = []
    for attachment_html in soup.find_all('div', class_='card-block'):
        title = extract_text(attachment_html, 'h3.h5')
        if title:
            download_links = extract_download_links(str(attachment_html))
            attachments.append(Attachment(
                title=title, download_links=download_links))

    return CommentInfo(
        comment_id=comment_id,
        tracking_number=tracking_number,
        comment_details=comment_details,
        submitter_info=submitter_info,
        comment_content=comment_content,
        attachments=attachments
    )


def main() -> None:
    url = "https://www.regulations.gov/comment/PHMSA-2011-0023-0407"
    print_info("Starting comment scraping process...")
    try:
        comment_info = scrape_comment_page(url)
        with open('comment_info_html.json', 'w') as f:
            json.dump(asdict(comment_info), f, indent=2)
        print_success(
            "Comment information HTML has been saved to comment_info_html.json")
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
