import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests import RequestException

from constants import EXPECTED_STATUS, PEP_INDEX_URL
from exceptions import ParserFindTagException


def get_response(session, url, encoding='utf-8'):
    """
    Обрабатывает запросы и перехватывает сетевые ошибки.
    """
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException as e:
        raise RuntimeError(f'Ошибка при загрузке страницы {url}: {e}') from e


def find_tag(soup, tag, attrs=None, string=None):
    """
    Ищет тег в переданном объекте BeautifulSoup.
    Вызывает исключение, если тег не найден.
    """
    searched_tag = soup.find(tag, attrs=(attrs or {}), string=string)
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        raise ParserFindTagException(error_msg)
    return searched_tag


def fetch_and_parse(session, url, encoding='utf-8'):
    """
    Загрузка страницы по URL и создание объекта BeautifulSoup.
    """
    try:
        response = get_response(session, url, encoding=encoding)
        return BeautifulSoup(response.text, 'lxml')
    except RuntimeError as e:
        logging.error(str(e))
        return None


def extract_rows_from_tables(soup):
    """
    Извлекает все строки из всех таблиц на странице.
    """
    tables = soup.find_all('table')
    if not tables:
        logging.error('На странице не найдено таблиц.')
        return []

    logging.info(f'Найдено таблиц: {len(tables)}')
    all_rows = []
    for table_index, table in enumerate(tables, start=1):
        try:
            rows = table.find('tbody').find_all('tr')
            logging.info(
                f'Таблица {table_index}: '
                f'Найдено строк {len(rows)}.'
            )
            all_rows.extend(rows)
        except Exception as e:
            logging.error(f'Ошибка обработки таблицы {table_index}: {e}')
    return all_rows


def parse_row(row, table_index):
    """
    Обрабатывает строку таблицы и возвращает статус и ссылку.
    """
    try:
        columns = row.find_all('td')
        if len(columns) < 2:
            logging.warning(
                f'Пропущена строка таблицы {table_index} '
                f'с недостаточным числом колонок.'
            )
            return None, None

        table_status_abbr = columns[0].text.strip()
        table_status = EXPECTED_STATUS.get(
            table_status_abbr[0], ('Неизвестный статус',)
        )
        pep_link = urljoin(PEP_INDEX_URL, columns[1].find('a')['href'])
        logging.debug(
            f'Таблица {table_index}: статус "{table_status_abbr}", '
            f'ссылка {pep_link}'
        )
        return table_status, pep_link
    except Exception as e:
        logging.error(
            f'Ошибка извлечения данных из строки таблицы {table_index}: {e}'
        )
        return None, None


def extract_status_from_pep_page(session, pep_link):
    """
    Извлекает статус PEP со страницы PEP.
    """
    pep_soup = fetch_and_parse(session, pep_link)
    if pep_soup is None:
        logging.warning(f'Не удалось загрузить страницу PEP: {pep_link}')
        return 'Не найден'

    try:
        status_dd = pep_soup.select_one('dt:contains("Status") + dd')
        return status_dd.text.strip() if status_dd else 'Не найден'
    except Exception as e:
        logging.error(f'Ошибка извлечения статуса на странице {pep_link}: {e}')
        return 'Не найден'
