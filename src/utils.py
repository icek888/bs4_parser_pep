import logging
from requests import RequestException
from exceptions import ParserFindTagException


def get_response(session, url):
    """Обрабатывает запросы и перехватывает сетевые ошибки."""
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None, string=None):
    """Ищет тег в переданном объекте BeautifulSoup.
    Вызывает исключение, если тег не найден."""
    searched_tag = soup.find(tag, attrs=(attrs or {}), string=string)
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag
