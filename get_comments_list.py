from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from bs4 import BeautifulSoup
from tqdm import tqdm
import json
import time
import os
from typing import List, Dict

from utils import (
    print_info, print_success, print_warning, print_error,
    setup_driver, wait_for_element, extract_text, get_total_comments
)


def scrape_comment_info(comment_element: WebElement) -> Dict[str, str]:
    html_content = comment_element.get_attribute('outerHTML')
    soup = BeautifulSoup(html_content, 'html.parser')

    return {
        "id": extract_text(soup, "li:-soup-contains('ID')").replace("ID", "").strip(),
        "title": extract_text(soup, "h3.card-title a"),
        "url": soup.select_one("h3.card-title a")['href'],
        "agency": extract_text(soup, "li:-soup-contains('Agency')").replace("Agency", "").strip(),
        "posted_date": extract_text(soup, "li:-soup-contains('Posted')").replace("Posted", "").strip(),
    }


def scrape_comments(url: str) -> List[Dict[str, str]]:
    with setup_driver() as driver:
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


def main() -> None:
    url = "https://www.regulations.gov/document/PHMSA-2011-0023-0118/comment"
    try:
        comments = scrape_comments(url)

        os.makedirs('output', exist_ok=True)
        output_file = 'output/comments_list.json'
        with open(output_file, 'w') as f:
            json.dump(comments, f, indent=2)

        print_success(
            f"Scraped {len(comments)} comments. Data saved to {output_file}")
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
