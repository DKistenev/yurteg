"""Скрейпер шаблонов договоров для датасета.

Источники:
    1. dogovor-urist.ru  — основные типы договоров
    2. dogovor-blank.ru  — редкие типы (лизинг, мена, страхование, НТП...)

Скачивает DOC-файлы по категориям, каждый файл получает метку типа договора.

Запуск:
    cd /path/to/yurteg
    python dataset/scrape_contracts.py                    # оба сайта
    python dataset/scrape_contracts.py --site urist       # только dogovor-urist.ru
    python dataset/scrape_contracts.py --site blank       # только dogovor-blank.ru

Флаги:
    --output DIR      папка для файлов (по умолчанию: dataset/contracts_scraped)
    --per-category N  файлов на категорию (по умолчанию: 20)
    --site SITE       urist | blank | all (по умолчанию: all)
    --categories      показать список категорий и выйти
    --dry-run         показать что будет скачано, без скачивания
"""
import re
import sys
import json
import time
import logging
import argparse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Нужны библиотеки: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DATASET_DIR = Path(__file__).parent
DEFAULT_OUTPUT = DATASET_DIR / "contracts_scraped"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
})

POLITE_DELAY = 0.5

# ─── Категории: наша метка → (сайт, slug) ────────────────────────────────────

SITE_URIST = "https://dogovor-urist.ru"
SITE_BLANK = "https://dogovor-blank.ru"

# dogovor-urist.ru — основные типы
CATEGORIES_URIST = {
    "Договор подряда":                        "раздел-Типовой_договор_подряда",
    "Договор строительного подряда":          "раздел-Договор_строительства_строительного_подряда",
    "Договор бытового подряда":               "раздел-Договор_бытового_подряда",
    "Договор оказания услуг":                 "раздел-Договор_оказания_услуг_работ",
    "Договор аренды жилья":                   "раздел-Договор_аренды_жилого_помещения",
    "Договор аренды нежилого помещения":      "раздел-Договор_аренды_нежилых_помещений_зданий_и_сооружений",
    "Договор аренды земельного участка":      "раздел-Договор_аренды_земли_земельной_доли_участка",
    "Договор аренды имущества":               "раздел-Договор_аренды_имущества_оборудования",
    "Договор аренды транспорта":              "раздел-Договор_аренды_автомобиля_и_других_транспортных_средств",
    "Договор купли-продажи недвижимости":     "раздел-Договор_купли-продажи_недвижимости",
    "Договор купли-продажи имущества":        "раздел-Договор_купли-продажи_имущества",
    "Договор поставки":                       "раздел-Договор_поставки_товаров_продукции",
    "Трудовой договор":                       "раздел-Трудовой_договор_контракт",
    "Договор займа":                          "раздел-Договор_займа_денег",
    "Агентский договор":                      "раздел-Агентский_договор_и_соглашение",
    "Договор дарения":                        "раздел-Договор_дарения_недвижимости_и_иных_ценностей",
    "Договор перевозки":                      "раздел-Договор_перевозки_грузов_и_пассажиров",
    "Договор совместной деятельности":        "раздел-Договор_о_совместной_деятельности-2",
    "Договор уступки права":                  "раздел-Договор_об_уступке_права_требования",
    "Договор транспортной экспедиции":        "раздел-Договор_транспортного_обслуживания_и_экспедиции",
    "Брачный договор":                        "раздел-Брачный_договор_контракт",
    "Договор безвозмездного пользования":     "раздел-Договор_безвозмездного_пользования",
}

# dogovor-blank.ru — редкие типы + добить объём по частым
CATEGORIES_BLANK = {
    # Редкие типы (нет на первом сайте)
    "Договор мены":                           "Договор_мены__обмена__бартера",
    "Договор лизинга":                        "Договор_лизинга__финансовой_аренды",
    "Договор страхования":                    "Договор_страхования_имущества__здоровья__ответственности",
    "Договор хранения":                       "Договор_хранения__документы_на_хранение",
    "Договор поручения":                      "Договор_поручения__договор_комиссии",
    "Договор доверительного управления":      "Договор_доверительного_управления__траста",
    "Договор пожизненного содержания":        "Договор_пожизненного_содержания",
    "Кредитный договор":                      "Кредитный_договор__залоговый_договор",
    "Договор на выполнение НТП":              "Договор_на_создание_и_выполнение_НТП",
    "Договор проката":                        "Договор_проката__бытового_проката",
    "Банковский договор":                     "Банковский_договор__депозитный_договор",
    "Договор товарищества":                   "Договор_товарищества__совместной_деятельности",
    "Договор франчайзинга":                   "Договор_франчайзинга__концессии",
    # Добить объём по частым типам
    "Договор поставки":                       "Договор_поставки_товаров__продукции",
    "Трудовой договор":                       "Трудовой_договор__трудовой_контракт",
    "Договор купли-продажи":                  "Договор_купли-продажи__договор_контрактации",
}


# ─── Общие функции ────────────────────────────────────────────────────────────

def fetch(url: str) -> str | None:
    """GET-запрос с обработкой ошибок."""
    try:
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            return r.text
        logger.warning("HTTP %d: %s", r.status_code, url)
    except requests.RequestException as e:
        logger.warning("Ошибка сети: %s — %s", url, e)
    return None


def download_file(url: str, dest: Path) -> bool:
    """Скачивает файл."""
    try:
        r = SESSION.get(url, timeout=20, stream=True)
        if r.status_code != 200:
            return False
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if dest.stat().st_size < 500:
            dest.unlink()
            return False
        return True
    except Exception:
        if dest.exists():
            dest.unlink()
        return False


def _safe_dirname(name: str) -> str:
    """Безопасное имя для папки."""
    return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')


# ─── dogovor-urist.ru ─────────────────────────────────────────────────────────

def urist_get_doc_pages(slug: str) -> list[str]:
    """Список страниц документов в категории (все на одной странице)."""
    url = f"{SITE_URIST}/договоры/{slug}/"
    html = fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    doc_list = soup.find("ul", id="doc-list") or soup.find("ul", class_="doc-list2")
    if not doc_list:
        return []

    links = []
    for a in doc_list.find_all("a", href=True):
        href = a["href"]
        if "/договоры/образец-" in href:
            full = href if href.startswith("http") else SITE_URIST + href
            links.append(full)
    return list(dict.fromkeys(links))


def urist_get_download_url(page_url: str) -> str | None:
    """Прямая ссылка на .doc со страницы документа."""
    html = fetch(page_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r'/dogovora/\d+\.doc', href, re.I):
            return href if href.startswith("http") else SITE_URIST + href

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r'\.(doc|docx|pdf)$', href, re.I):
            return href if href.startswith("http") else SITE_URIST + href
    return None


# ─── dogovor-blank.ru ─────────────────────────────────────────────────────────

def blank_get_doc_pages(slug: str, max_pages: int = 5) -> list[str]:
    """Список страниц документов с пагинацией."""
    all_links = []

    for page_num in range(1, max_pages + 1):
        if page_num == 1:
            url = f"{SITE_BLANK}/шаблон/{slug}"
        else:
            url = f"{SITE_BLANK}/шаблон/{slug}/{page_num}-страница"

        html = fetch(url)
        if not html:
            break

        soup = BeautifulSoup(html, "lxml")
        lists = soup.find_all("ul", class_="spisok1")
        page_links = []
        for ul in lists:
            for a in ul.find_all("a", href=True):
                href = a["href"]
                # Ссылки на конкретные документы (не на категории и не на страницы)
                if "/шаблон/" in href and href.count("/") >= 4 and "страница" not in href:
                    full = href if href.startswith("http") else SITE_BLANK + href
                    page_links.append(full)

        if not page_links:
            break
        all_links.extend(page_links)

        # Проверяем наличие следующей страницы
        pagination = soup.find("ul", class_="pagination")
        if not pagination:
            break
        time.sleep(POLITE_DELAY)

    return list(dict.fromkeys(all_links))


def blank_get_download_url(page_url: str) -> str | None:
    """Прямая ссылка на .doc со страницы документа."""
    html = fetch(page_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    # Ищем прямую ссылку на .doc файл
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r'\.(doc|docx)$', href, re.I) and "/шаблон/" in href:
            return href if href.startswith("http") else SITE_BLANK + href

    # Fallback: любая ссылка на .doc/.pdf
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r'\.(doc|docx|pdf)$', href, re.I):
            return href if href.startswith("http") else SITE_BLANK + href
    return None


# ─── Общий скрейпер ───────────────────────────────────────────────────────────

def scrape_site(
    categories: dict[str, str],
    get_pages_fn,
    get_url_fn,
    site_name: str,
    output_dir: Path,
    per_category: int,
    existing: set,
    dry_run: bool,
) -> list[dict]:
    """Скрейпит один сайт."""
    manifest = []
    total = 0

    for label, slug in categories.items():
        cat_dir = output_dir / _safe_dirname(label)
        cat_dir.mkdir(exist_ok=True)

        # Считаем уже скачанные файлы в папке
        existing_count = len(list(cat_dir.glob("*.*")))

        logger.info("[%s] [%s] Загружаю список...", site_name, label)
        doc_pages = get_pages_fn(slug)
        logger.info("  Найдено документов: %d", len(doc_pages))
        time.sleep(POLITE_DELAY)

        downloaded = 0
        for page_url in doc_pages:
            if downloaded >= per_category:
                break
            if page_url in existing:
                continue

            if dry_run:
                logger.info("  [dry-run] %s", page_url)
                downloaded += 1
                continue

            file_url = get_url_fn(page_url)
            time.sleep(POLITE_DELAY)
            if not file_url:
                continue

            ext = ".doc"
            m = re.search(r'\.(doc|docx|pdf)$', file_url, re.I)
            if m:
                ext = "." + m.group(1).lower()

            num = existing_count + downloaded + 1
            filename = f"{_safe_dirname(label)}_{num:03d}{ext}"
            dest = cat_dir / filename

            if download_file(file_url, dest):
                downloaded += 1
                total += 1
                manifest.append({
                    "file": str(dest.relative_to(output_dir)),
                    "label": label,
                    "source": site_name,
                    "source_url": page_url,
                    "file_url": file_url,
                })
                logger.info("  [%d/%d] %s", downloaded, per_category, filename)
                time.sleep(POLITE_DELAY)

        logger.info("  Скачано: %d", downloaded)

    logger.info("[%s] Итого новых: %d", site_name, total)
    return manifest


def scrape(output_dir: Path, per_category: int, sites: str, dry_run: bool = False):
    """Основная функция."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    # Загрузить существующий манифест
    existing = set()
    all_items = []
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                all_items = json.load(f)
            for item in all_items:
                existing.add(item.get("source_url", ""))
            logger.info("Уже скачано: %d файлов", len(existing))
        except (json.JSONDecodeError, KeyError):
            pass

    new_items = []

    if sites in ("urist", "all"):
        items = scrape_site(
            CATEGORIES_URIST, urist_get_doc_pages, urist_get_download_url,
            "dogovor-urist.ru", output_dir, per_category, existing, dry_run,
        )
        new_items.extend(items)

    if sites in ("blank", "all"):
        items = scrape_site(
            CATEGORIES_BLANK, blank_get_doc_pages, blank_get_download_url,
            "dogovor-blank.ru", output_dir, per_category, existing, dry_run,
        )
        new_items.extend(items)

    # Сохранить манифест
    if not dry_run and new_items:
        all_items.extend(new_items)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)

    logger.info("─" * 40)
    logger.info("Скачано новых:  %d", len(new_items))
    logger.info("Всего в манифесте: %d", len(all_items) + (len(new_items) if dry_run else 0))
    logger.info("Папка: %s", output_dir)
    logger.info("─" * 40)


def main():
    parser = argparse.ArgumentParser(description="Скрейпер шаблонов договоров")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Папка для файлов (по умолчанию: {DEFAULT_OUTPUT.name})")
    parser.add_argument("--per-category", type=int, default=20,
                        help="Файлов на категорию (по умолчанию: 20)")
    parser.add_argument("--site", choices=["urist", "blank", "all"], default="all",
                        help="Какой сайт скрейпить (по умолчанию: all)")
    parser.add_argument("--categories", action="store_true",
                        help="Показать список категорий и выйти")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показать что будет скачано, без скачивания")
    args = parser.parse_args()

    if args.categories:
        if args.site in ("urist", "all"):
            print(f"\ndogovor-urist.ru ({len(CATEGORIES_URIST)} категорий):")
            for label in CATEGORIES_URIST:
                print(f"  {label}")
        if args.site in ("blank", "all"):
            print(f"\ndogovor-blank.ru ({len(CATEGORIES_BLANK)} категорий):")
            for label in CATEGORIES_BLANK:
                print(f"  {label}")
        return

    scrape(args.output, args.per_category, args.site, args.dry_run)


if __name__ == "__main__":
    main()
