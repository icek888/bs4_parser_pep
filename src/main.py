import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, RequestException
from tqdm import tqdm
from urllib3.util.retry import Retry

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_INDEX_URL
from exceptions import ParserFindTagException
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
        )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]

    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        results.append((version_link, h1.text.strip(), dl.text.strip()))
    return results


def latest_versions(session):
    """Парсинг версий Python и их статусов с главной страницы документации."""
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ParserFindTagException('Не найден список версий.')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]

    for a_tag in a_tags:
        link = a_tag['href']
        if not link.startswith('http'):
            link = urljoin(MAIN_DOC_URL, link)
        text = a_tag.text.strip()
        match = re.match(r'(?P<version>[\d.]+)?\s*(?P<status>.+)?', text)
        if match:
            version = match.group('version') or text
            status = match.group('status') or ''
        else:
            version = text
            status = ''
        results.append((link, version, status))
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_tag = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(main_tag, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        response = session.get(archive_url, stream=True)
        response.raise_for_status()

        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm(
            total=total_size_in_bytes, unit='iB', unit_scale=True
            )

        with open(archive_path, 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)

        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            logging.error("Ошибка при загрузке: размер файла не совпадает.")
        else:
            logging.info(f'Архив успешно загружен и сохранён: {archive_path}')

    except ChunkedEncodingError as e:
        logging.error(f'Ошибка передачи данных: {e}')
        logging.info('Попробуйте запустить программу повторно.')
    except RequestException as e:
        logging.error(f'Общая ошибка запроса: {e}')
    except Exception as e:
        logging.error(f'Неизвестная ошибка: {e}')


def pep(session):
    response = get_response(session, PEP_INDEX_URL)
    if response is None:
        logging.error('Не удалось получить страницу PEP Index.')
        return

    soup = BeautifulSoup(response.text, 'lxml')
    try:
        tables = soup.find_all('table')
        if not tables:
            logging.error('На странице не найдено таблиц.')
            return
        logging.info(f'Найдено таблиц: {len(tables)}')
    except Exception as e:
        logging.error(f'Ошибка поиска таблиц: {e}')
        return

    results = {}
    total_peps = 0

    for table_index, table in enumerate(tables, start=1):
        try:
            rows = table.find('tbody').find_all('tr')
            logging.info(
                f'Таблица {table_index}: '
                f'Найдено строк {len(rows)} (включая заголовок).'
            )
        except Exception as e:
            logging.error(f'Ошибка обработки таблицы {table_index}: {e}')
            continue

        for row in tqdm(rows, desc=f'Обработка таблицы {table_index}'):
            try:
                columns = row.find_all('td')
                if len(columns) < 2:
                    logging.warning(
                        'Пропущена строка таблицы с '
                        'недостаточным числом колонок.'
                    )
                    continue

                table_status_abbr = columns[0].text.strip()
                table_status = EXPECTED_STATUS.get(
                    table_status_abbr[0], ('Неизвестный статус',)
                )
                pep_link = urljoin(PEP_INDEX_URL, columns[1].find('a')['href'])
                logging.debug(
                    f'Таблица {table_index}: '
                    f'статус "{table_status_abbr}", ссылка {pep_link}'
                )
            except Exception as e:
                logging.error(
                    f'Ошибка извлечения данных из строки таблицы '
                    f'{table_index}: {e}'
                )
                continue

            pep_response = get_response(session, pep_link)
            if pep_response is None:
                logging.warning(
                    f'Не удалось получить страницу PEP: {pep_link}'
                    )
                continue

            try:
                pep_soup = BeautifulSoup(pep_response.text, 'lxml')
                status_dd = pep_soup.select_one('dt:contains("Status") + dd')
                page_status = (
                    status_dd.text.strip() if status_dd else 'Не найден'
                    )
                logging.debug(f'Статус из карточки PEP: {page_status}')
            except Exception as e:
                logging.error(
                    f'Ошибка извлечения статуса на странице {pep_link}: {e}'
                )
                continue

            if page_status not in table_status:
                logging.warning(
                    f'Несовпадающие статусы:\n'
                    f'{pep_link}\n'
                    f'Статус в карточке: {page_status}\n'
                    f'Ожидаемые статусы: {table_status}'
                )

            results[page_status] = results.get(page_status, 0) + 1
            total_peps += 1

    results['Total'] = total_peps
    logging.info(f'Результаты парсинга PEP: {results}')
    return [('Статус', 'Количество')] + list(results.items())


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()

    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
        logging.info('Кеш очищен.')

    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
