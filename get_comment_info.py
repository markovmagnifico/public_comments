from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import time
import os
from typing import List

from utils import (
    print_info, print_success, print_warning, print_error,
    setup_driver, wait_for_element, extract_text, extract_info,
    extract_download_links
)
from models import CommentInfo, Address, Submitter, Attachment


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
            download_links = extract_download_links(str(attachment_html))
            attachments.append(Attachment(
                title=title, url=download_links[0] if download_links else ""))

    return CommentInfo(
        id=comment_id,
        tracking_number=tracking_number,
        title=extract_text(soup, "h1.document-title"),
        agency=extract_text(soup, "div.agency-name"),
        dates={"received": received_date, "posted": extract_info(
            details_soup, "Posted Date")},
        submitter=submitter,
        content=comment_content,
        attachments=attachments,
        document_subtype=document_subtype
    )


def main() -> None:
    url = "https://www.regulations.gov/comment/PHMSA-2011-0023-0407"
    print_info("Starting comment scraping process...")
    try:
        comment_info = scrape_comment_page(url)

        os.makedirs('output', exist_ok=True)
        output_file = 'output/single_comment_info.json'
        with open(output_file, 'w') as f:
            json.dump(comment_info.__dict__, f, indent=2,
                      default=lambda o: o.__dict__)

        print_success(f"Comment information has been saved to {output_file}")
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
