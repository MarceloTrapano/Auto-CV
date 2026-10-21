import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from base import ScrapingStrategy


class LinkedinStrategy(ScrapingStrategy):
    def __init__(self, url):
        if "linkedin" not in url:
            raise ValueError("Invalid url.")
        super().__init__(url)

    def set_url(self, url):
        if "linkedin" not in url:
            raise ValueError("Invalid url.")
        super().set_url(url)

    def scrap(self) -> str:
        response = requests.get(self.url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        node = soup.select_one("div.show-more-less-html__markup")
        if not node:
            job_id = parse_qs(urlparse(self.url).query).get(
                "currentJobId", [None])[0]
            if job_id is None:
                raise ValueError(
                    "Invalid url, url should follow schema: https://www.linkedin.com/jobs/view/job_id/")
            self.url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            response = requests.get(self.url, headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")
            node = soup.select_one("div.show-more-less-html__markup")
        return node.get_text(separator="\n", strip=True)
