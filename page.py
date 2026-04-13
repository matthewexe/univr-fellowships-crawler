import dataclasses

from bs4 import BeautifulSoup


class Page:

    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.next_link = None
        for list_item in self.soup.select_one("ul.pagination").children:
            if isinstance(list_item, str):
                continue
            link = list_item.select_one('a')
            if link is not None and 'successivo' in link.text.strip().lower():
                self.next_link = link['href']
                break

    def get_all_records(self):
        return list(map(Record.from_soup, self.soup.select('.card-record')))

    def has_next_link(self):
        return bool(self.next_link)

    def get_next_link(self):
        return self.next_link

@dataclasses.dataclass
class Record:
    link: str
    title: str
    start_date: str
    end_date: str
    is_open: bool

    @classmethod
    def from_soup(cls, soup: BeautifulSoup | str):
        if isinstance(soup, str):
            soup = BeautifulSoup(soup)

        link = soup.select_one('.card-record-title a')['href']
        title = soup.select_one('.card-record-title a').text.strip()
        start_date, end_date, *_ = soup.select_one('.card-record-dettagli').children
        is_open = 'aperto' in soup.select_one('.card-record-title .label-success').text.strip().lower()
        return Record(link, title, start_date.text.strip(), end_date.text.strip(), is_open)