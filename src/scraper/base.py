from abc import ABC, abstractmethod


class ScrapingStrategy(ABC):
    def __init__(self, url: str):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        self.url = url

    def set_url(self, url):
        self.url = url

    @abstractmethod
    def scrap(self) -> str:
        pass
