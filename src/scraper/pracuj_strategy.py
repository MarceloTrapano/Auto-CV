import requests
import json
from bs4 import BeautifulSoup

from .base import ScrapingStrategy


class PracujStrategy(ScrapingStrategy):
    def __init__(self, url):
        if "pracuj" not in url:
            raise ValueError("Invalid url.")
        super().__init__(url)

    def set_url(self, url):
        if "pracuj" not in url:
            raise ValueError("Invalid url.")
        super().set_url(url)

    def scrap(self):
        response = requests.get(self.url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")

        data = json.loads(soup.find("script", id="__NEXT_DATA__").string)
        queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
        offer = next(q["state"]["data"]
                     for q in queries if q["queryKey"][0] == "jobOffer")

        description = "\n".join(
            line
            for section in offer["textSections"]
            for line in section["textElements"]
        )
        return description
