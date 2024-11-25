import logging
import re
from urllib.parse import urljoin

import requests_cache
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, RequestException
from tqdm import tqdm
from urllib3.util.retry import Retry

from configs import configure_argument_parser, configure_logging
from constants import MAIN_DOC_URL, PEP_INDEX_URL, DOWNLOADS_DIR, BASE_DIR
from exceptions import ParserFindTagException
from outputs import control_output
from utils import (
    find_tag,
    extract_rows_from_tables,
    extract_status_from_pep_page,
    parse_row,
    fetch_and_parse
)


def whats_new(session):
    """Парсинг раздела What's New."""
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = fetch_and_parse(session, whats_new_url)
    if soup is None:
        return

    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li',
                                              attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]

    for section in tqdm(sections_by_python, desc='Парсинг нововведений'):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        soup = fetch_and_parse(session, version_link)
        if soup is None:
            logging.warning(f'Пропущена итерация для ссылки: {version_link}')
            continue
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        results.append((version_link, h1.text.strip(), dl.text.strip()))
    return results


def latest_versions(session):
    """Парсинг версий Python и их статусов с главной страницы документации."""
    soup = fetch_and_parse(session, MAIN_DOC_URL)
    if soup is None:
        return

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
    """Загрузка PDF документации."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = fetch_and_parse(session, downloads_url)
    if soup is None:
        return

    main_tag = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(main_tag, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / DOWNLOADS_DIR
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
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB',
                            unit_scale=True)

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
    """Парсинг всех таблиц PEP и подсчет статусов."""
    soup = fetch_and_parse(session, PEP_INDEX_URL)
    if soup is None:
        return

    rows = extract_rows_from_tables(soup)
    if not rows:
        return

    results = {}
    total_peps = 0
    warnings = []

    for row in tqdm(rows, desc='Обработка строк таблиц'):
        table_status, pep_link = parse_row(row, table_index=0)
        if not pep_link:
            continue

        page_status = extract_status_from_pep_page(session, pep_link)

        if page_status not in table_status:
            warnings.append(
                'Несовпадающие статусы:\n'
                f'{pep_link}\n'
                f'Статус в карточке: {page_status}\n'
                f'Ожидаемые статусы: {table_status}'
            )

        results[page_status] = results.get(page_status, 0) + 1
        total_peps += 1

    results['Total'] = total_peps
    logging.info(f'Результаты парсинга PEP: {results}')

    for warning in warnings:
        logging.warning(warning)

    return [('Статус', 'Количество')] + list(results.items())


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    """Главная функция запуска парсера."""
    try:
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
    except Exception as e:
        logging.exception(
            f'Критическая ошибка во время выполнения программы: {e}'
            )


if __name__ == '__main__':
    main()
