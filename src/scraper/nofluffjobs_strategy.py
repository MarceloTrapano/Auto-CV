import requests
import json
from bs4 import BeautifulSoup

from .base import ScrapingStrategy


class NoFluffJobsStrategy(ScrapingStrategy):
    def __init__(self, url):
        if "nofluffjobs" not in url:
            raise ValueError("Invalid url.")
        super().__init__(url)

    def set_url(self, url):
        if "nofluffjobs" not in url:
            raise ValueError("Invalid url.")
        super().set_url(url)

    def scrap(self):
        response = requests.get(self.url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        state = json.loads(soup.find("script", id="serverApp-state").string)

        posting = next(v for k, v in state.items()
                       if k.startswith("/posting/"))

        def html_to_text(html: str) -> str:
            return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)

        description = "\n\n".join([
            "Requirements:\n" +
            html_to_text(posting["requirements"]["description"]),
            "Responsibilities:\n" + "\n".join(posting["specs"]["dailyTasks"]),
            "Job description:\n" +
            html_to_text(posting["details"]["description"]),
        ])
        return description
