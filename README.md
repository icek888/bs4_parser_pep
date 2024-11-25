# 📄 Парсер документации PEP

## Описание проекта

Этот проект представляет собой парсер документации PEP (Python Enhancement Proposals). Основная задача парсера — сбор и анализ данных с официального сайта PEP, включая информацию о текущих статусах, списке версий Python и других данных.

### Основные функции:
- 🔍 Сбор данных о статусах всех PEP.
- 📋 Получение списка версий Python и их статусов.
- 📥 Загрузка архива документации Python.
- 📊 Генерация и сохранение результатов в читаемом формате (таблица, CSV).

## 🛠 Стек технологий

- **Python 3.9+** — язык программирования.
- **[BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)** — парсинг HTML.
- **[Requests](https://requests.readthedocs.io/en/latest/)** — HTTP-запросы.
- **[tqdm](https://tqdm.github.io/)** — индикатор прогресса.
- **[pytest](https://docs.pytest.org/en/latest/)** — модуль тестирования.

## Установка

### Клонирование репозитория
```bash
git clone <URL вашего репозитория>
cd <имя папки проекта>
```
### Создание виртуального окружения
```bash
python -m venv venv
source venv/bin/activate  # Для Linux и MacOS
venv\\Scripts\\activate     # Для Windows
```
### Установка зависимостей
```bash
pip install -r requirements.txt
```
## 🚀 Возможности парсера

Парсер запускается с помощью аргументов командной строки, которые указывают режим работы.

### Аргументы:
- **`mode`** (обязательный аргумент) — режим работы парсера:
  - `whats-new` — парсит нововведения в Python, доступные в документации.
  - `latest-versions` — выводит список всех версий Python и их текущих статусов.
  - `download` — скачивает архив документации Python в формате PDF.
  - `pep` — анализирует статус всех PEP и сравнивает данные из таблицы и карточек.
- **`-c`/`--clear-cache`** (опционально) — очищает кеш перед выполнением парсинга.
- **`-o`/`--output`** (опционально) — указывает способ вывода данных:
  - `pretty` — вывод в виде таблицы.
  - `file` — сохранение результатов в файл CSV.
  - (по умолчанию) — вывод в консоль в простом формате.

### Примеры запуска

#### Парсинг статусов PEP
```bash
python main.py pep
```
# Парсинг нововведений в Python
```bash
python main.py whats-new
```
# Скачивание архива документации
```bash
python main.py download
```
# Получение списка версий Python
```bash
python main.py latest-versions
```
# Указание формата вывода (пример для режима PEP)
```bash
python main.py pep -o pretty
python main.py pep -o file
```
🧑‍💻 Автор
Разработчик: Карлен Абелян
📧 Email: abelyankarlen@gmail.com
🌐 GitHub: [icek888](https://github.com/icek888)