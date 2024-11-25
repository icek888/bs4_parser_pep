import logging
import csv
from datetime import datetime
from prettytable import PrettyTable
from constants import BASE_DIR


def control_output(results, cli_args):
    output = cli_args.output
    if output == 'pretty':
        pretty_output(results)
    elif output == 'file':
        file_output(results, cli_args)
    else:
        default_output(results)


def default_output(results):
    for row in results:
        print(' '.join(map(str, row)))


def pretty_output(results):
    table = PrettyTable()
    table.field_names = results[0]
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)
    file_name = (
        f"{cli_args.mode}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        )
    file_path = results_dir / file_name
    with open(file_path, mode='w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(results)
    logging.info(f'Файл с результатами был сохранён: {file_path}')
