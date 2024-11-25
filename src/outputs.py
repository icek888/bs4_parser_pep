import csv
import logging
from datetime import datetime

from prettytable import PrettyTable

from constants import RESULTS_DIR, BASE_DIR


def control_output(results, cli_args):
    """Обработка результатов согласно выбранному способу вывода."""
    output_options = {
        'pretty': pretty_output,
        'file': file_output,
        None: default_output
    }

    output_function = output_options.get(cli_args.output, default_output)
    output_function(results, cli_args)


def default_output(results, *_):
    """Вывод результатов в консоль по умолчанию."""
    for row in results:
        print(' '.join(map(str, row)))


def pretty_output(results, *_):
    """Вывод результатов в виде таблицы."""
    table = PrettyTable()
    table.field_names = results[0]
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    """Сохранение результатов в CSV-файл."""
    results_dir = BASE_DIR / RESULTS_DIR
    results_dir.mkdir(exist_ok=True)
    file_name = (
        f"{cli_args.mode}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        )
    file_path = results_dir / file_name

    with open(file_path, mode='w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(results)

    logging.info(f'Файл с результатами был сохранён: {file_path}')
