#!/usr/bin/env python3
"""Заменить маски анонимизации на реалистичные русские данные в ORPO датасете."""

import json
import os
import re
import random
from typing import Dict, Set, Tuple
from pathlib import Path
import tempfile
import shutil

# Русские имена для генерации разнообразных ФИО
SURNAMES = [
    "Козлов", "Морозова", "Тихонов", "Петухова", "Журавлева", "Орлова", "Соколов",
    "Кукушкин", "Сороцкий", "Волков", "Медведев", "Лисицын", "Зайцев", "Слонов",
    "Сороцкий", "Барсуков", "Ежов", "Кротов", "Хорьков", "Норкин", "Калинин",
    "Тугаринов", "Малинов", "Смородинов", "Вишняков", "Абрикосов", "Лимонов", "Апельсинов",
    "Гречко", "Ячменев", "Ржанцев", "Пшеничный", "Овсянников", "Просов", "Кукурузников",
    "Железнов", "Медынцев", "Селезнев", "Сокольников", "Полевой", "Луговой", "Лесной",
    "Морозов", "Орлов", "Волков", "Соколов", "Львов", "Ястребков", "Кондратьев",
    "Борисов", "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Лебедев",
    "Виноградов", "Макаров", "Романов", "Новиков", "Федоров", "Викторов", "Казанцев",
    "Молоков", "Колосов", "Дубинин", "Березин", "Сосновский", "Елецкий", "Пихтин",
    "Буланин", "Кленовский", "Тополевский", "Ивовский", "Ольховский", "Кленов", "Березов",
    "Сосновцев", "Еловцев", "Пихтов", "Осинцев", "Липовцев", "Буковцев", "Кленовцев",
    "Колпаков", "Гончаров", "Шустов", "Решетников", "Крупин", "Быстров", "Медведев",
    "Сафаров", "Терентьев", "Алексеев", "Евгеньев", "Николаев", "Сергеев", "Дмитриев",
    "Константинов", "Павлов", "Васильев", "Михайлов", "Григорьев", "Ильин", "Архипов"
]

FIRST_NAMES_MALE = [
    "Андрей", "Виктор", "Сергей", "Иван", "Петр", "Павел", "Александр", "Дмитрий",
    "Николай", "Евгений", "Владимир", "Юрий", "Константин", "Валерий", "Вячеслав",
    "Алексей", "Игорь", "Ростислав", "Станислав", "Борис", "Геннадий", "Олег", "Валентин",
    "Ростан", "Арсений", "Руслан", "Кирилл", "Тимур", "Илья", "Ярослав", "Максим"
]

FIRST_NAMES_FEMALE = [
    "Елена", "Анна", "Мария", "Наталья", "Ольга", "Людмила", "Ирина", "Галина",
    "Татьяна", "Светлана", "Виктория", "Алина", "Дарья", "Юлия", "Полина", "Вера",
    "Надежда", "Любовь", "Софья", "Кристина", "Марина", "Лариса", "Валентина",
    "Оксана", "Евгения", "Эльвира", "Диана", "Жанна", "Елизавета", "Снежана"
]

PATRONYMICS_FROM_MALE = [
    "Викторович", "Сергеевич", "Иванович", "Петрович", "Павлович", "Александрович",
    "Дмитриевич", "Николаевич", "Евгеньевич", "Владимирович", "Юрьевич",
    "Константинович", "Валерьевич", "Вячеславич", "Алексеевич", "Игоревич",
    "Ростиславич", "Станиславич", "Борисович", "Геннадьевич", "Олегович",
    "Валентинович", "Арсеньевич", "Русланович", "Кириллович", "Тимурович",
    "Ильич", "Ярославич", "Максимович", "Давидович", "Михайлович"
]

PATRONYMICS_FROM_FEMALE = [
    "Викторовна", "Сергеевна", "Ивановна", "Петровна", "Павловна", "Александровна",
    "Дмитриевна", "Николаевна", "Евгеньевна", "Владимировна", "Юрьевна",
    "Константиновна", "Валерьевна", "Вячеславовна", "Алексеевна", "Игоревна",
    "Ростиславовна", "Станиславовна", "Борисовна", "Геннадьевна", "Олеговна",
    "Валентиновна", "Арсеньевна", "Русланова", "Кирилловна", "Тимуровна",
    "Ильинична", "Ярославовна", "Максимовна", "Давидовна", "Михайловна"
]

CITIES = ["Москва", "Санкт-Петербург", "Екатеринбург", "Казань", "Новосибирск", "Пермь", "Сочи", "Новороссийск"]

ORGANIZATIONS = [
    "ООО «ТехСолюшнс»", "АО «Финанс-Групп»", "ООО «ДевЛаб»", "ИП Смирнов А.А.",
    "ООО «АвтоДилер»", "АО «БанкСервис»", "ООО «ЛогистХаб»",  "АО «КонсалтПро»",
    "ООО «МаркетПро»", "АО «СервисМастер»", "ООО «ДизайнЛаб»", "ИП Иванов И.И.",
]

class MaskReplacer:
    """Заменяет маски анонимизации на реалистичные данные."""

    def __init__(self):
        # Генерируем предварительно много уникальных значений
        self.fio_pool = self._generate_fio_pool(200)
        self.phone_pool = self._generate_phone_pool(100)
        self.email_pool = self._generate_email_pool(100)
        self.inn_pool = self._generate_inn_pool(100)
        self.ogrn_pool = self._generate_ogrn_pool(50)
        self.address_pool = self._generate_address_pool(80)
        self.passport_pool = self._generate_passport_pool(100)
        self.snils_pool = self._generate_snils_pool(100)
        self.account_pool = self._generate_account_pool(100)
        self.sum_pool = self._generate_sum_pool(80)
        self.date_pool = self._generate_date_pool(100)
        self.city_pool = CITIES
        self.organization_pool = ORGANIZATIONS

        # Индексы для циклирования
        self.fio_idx = 0
        self.phone_idx = 0
        self.email_idx = 0
        self.inn_idx = 0
        self.ogrn_idx = 0
        self.address_idx = 0
        self.passport_idx = 0
        self.snils_idx = 0
        self.account_idx = 0
        self.sum_idx = 0
        self.date_idx = 0
        self.city_idx = 0
        self.org_idx = 0

        # Для кэширования замен в одном примере
        self.current_replacements: Dict[str, str] = {}

    def _generate_fio_pool(self, count: int) -> list:
        """Генерируем 200+ разных ФИО."""
        fios = []
        for _ in range(count):
            surname = random.choice(SURNAMES)
            is_male = random.choice([True, False])

            if is_male:
                first_name = random.choice(FIRST_NAMES_MALE)
                patronymic = random.choice(PATRONYMICS_FROM_MALE)
            else:
                first_name = random.choice(FIRST_NAMES_FEMALE)
                patronymic = random.choice(PATRONYMICS_FROM_FEMALE)
                if surname.endswith("в"):
                    surname = surname[:-1] + "ва"
                elif surname.endswith("ов"):
                    surname = surname[:-2] + "ова"
                elif surname.endswith("ий"):
                    surname = surname[:-2] + "ая"
                elif surname.endswith("ой"):
                    surname = surname[:-2] + "ая"

            fios.append(f"{surname} {first_name} {patronymic}")

        return fios

    def _generate_phone_pool(self, count: int) -> list:
        """Генерируем реалистичные телефоны."""
        phones = []
        codes = ["495", "498", "499", "812", "903", "905", "916", "917"]

        for _ in range(count):
            code = random.choice(codes)
            middle = random.randint(100, 999)
            last = random.randint(10, 99)
            phones.append(f"+7 ({code}) {middle}-{last:02d}-{random.randint(0, 99):02d}")

        return phones

    def _generate_email_pool(self, count: int) -> list:
        """Генерируем реалистичные email адреса."""
        emails = []
        domains = ["company.ru", "mail.ru", "gmail.com", "yandex.ru", "example.ru", "corp.ru"]
        prefixes = ["info", "support", "admin", "manager", "analyst", "developer", "ivanov", "petrov", "sidorov"]

        for i in range(count):
            prefix = random.choice(prefixes)
            if i % 3 == 0:
                email = f"{prefix}@{random.choice(domains)}"
            else:
                email = f"{prefix}{random.randint(1, 9999)}@{random.choice(domains)}"
            emails.append(email)

        return emails

    def _generate_inn_pool(self, count: int) -> list:
        """Генерируем ИНН (10-12 цифр)."""
        inns = []
        for _ in range(count):
            length = random.choice([10, 12])
            inn = ''.join([str(random.randint(0, 9)) for _ in range(length)])
            inns.append(inn)
        return inns

    def _generate_ogrn_pool(self, count: int) -> list:
        """Генерируем ОГРН (13 цифр)."""
        ogrns = []
        for _ in range(count):
            ogrn = ''.join([str(random.randint(0, 9)) for _ in range(13)])
            ogrns.append(ogrn)
        return ogrns

    def _generate_address_pool(self, count: int) -> list:
        """Генерируем реалистичные адреса."""
        addresses = []
        cities = ["Москва", "Санкт-Петербург", "Екатеринбург", "Казань", "Новосибирск", "Пермь"]
        streets = ["Ленина", "Пушкина", "Толстого", "Чехова", "Горького", "Советская", "Комсомольская", "Первомайная"]

        for _ in range(count):
            city = random.choice(cities)
            street = random.choice(streets)
            house = random.randint(1, 200)
            office = random.randint(100, 999)
            addresses.append(f"г. {city}, ул. {street}, д. {house}, оф. {office}")

        return addresses

    def _generate_passport_pool(self, count: int) -> list:
        """Генерируем номера паспортов."""
        passports = []
        for _ in range(count):
            series = f"{random.randint(1000, 9999)}"
            number = f"{random.randint(100000, 999999)}"
            passports.append(f"серия {series} номер {number}")

        return passports

    def _generate_snils_pool(self, count: int) -> list:
        """Генерируем СНИЛС."""
        snils = []
        for _ in range(count):
            part1 = random.randint(100, 999)
            part2 = random.randint(100, 999)
            part3 = random.randint(100, 999)
            check = random.randint(0, 99)
            snils.append(f"{part1:03d}-{part2:03d}-{part3:03d}-{check:02d}")

        return snils

    def _generate_account_pool(self, count: int) -> list:
        """Генерируем расчётные счета."""
        accounts = []
        for _ in range(count):
            account = ''.join([str(random.randint(0, 9)) for _ in range(20)])
            accounts.append(account)

        return accounts

    def _generate_sum_pool(self, count: int) -> list:
        """Генерируем суммы денег в рублях."""
        amounts = []
        for _ in range(count):
            base = random.randint(1, 999)
            power = random.randint(3, 6)
            amount = base * (10 ** power)
            amounts.append(f"{amount:,}".replace(",", " ") + " руб.")
        return amounts

    def _generate_date_pool(self, count: int) -> list:
        """Генерируем даты."""
        dates = []
        for _ in range(count):
            year = random.randint(2022, 2026)
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            dates.append(f"{year:04d}-{month:02d}-{day:02d}")
        return dates

    def _get_next_value(self, mask_type: str) -> str:
        """Получить следующее значение из пула."""
        if mask_type == "ФИО":
            val = self.fio_pool[self.fio_idx % len(self.fio_pool)]
            self.fio_idx += 1
            return val
        elif mask_type == "ТЕЛЕФОН":
            val = self.phone_pool[self.phone_idx % len(self.phone_pool)]
            self.phone_idx += 1
            return val
        elif mask_type == "EMAIL":
            val = self.email_pool[self.email_idx % len(self.email_pool)]
            self.email_idx += 1
            return val
        elif mask_type == "ИНН":
            val = self.inn_pool[self.inn_idx % len(self.inn_pool)]
            self.inn_idx += 1
            return val
        elif mask_type == "ОГРН":
            val = self.ogrn_pool[self.ogrn_idx % len(self.ogrn_pool)]
            self.ogrn_idx += 1
            return val
        elif mask_type == "АДРЕС":
            val = self.address_pool[self.address_idx % len(self.address_pool)]
            self.address_idx += 1
            return val
        elif mask_type == "ПАСПОРТ":
            val = self.passport_pool[self.passport_idx % len(self.passport_pool)]
            self.passport_idx += 1
            return val
        elif mask_type == "СНИЛС":
            val = self.snils_pool[self.snils_idx % len(self.snils_pool)]
            self.snils_idx += 1
            return val
        elif mask_type in ["СЧЁТ", "РАСЧЁТНЫЙ_СЧЁТ"]:
            val = self.account_pool[self.account_idx % len(self.account_pool)]
            self.account_idx += 1
            return val
        elif mask_type == "СУММА":
            val = self.sum_pool[self.sum_idx % len(self.sum_pool)]
            self.sum_idx += 1
            return val
        elif mask_type == "ДАТА":
            val = self.date_pool[self.date_idx % len(self.date_pool)]
            self.date_idx += 1
            return val
        elif mask_type == "ГОРОД":
            val = self.city_pool[self.city_idx % len(self.city_pool)]
            self.city_idx += 1
            return val
        elif mask_type == "ОРГАНИЗАЦИЯ":
            val = self.organization_pool[self.org_idx % len(self.organization_pool)]
            self.org_idx += 1
            return val
        else:
            return f"[{mask_type}]"

    def _replace_masks_in_text(self, text: str) -> str:
        """Заменить маски в тексте, кэшируя замены внутри одного примера."""
        pattern = r"\[([А-Я_]+)(?:_\d+)?\]"

        def replace_func(match):
            mask_full = match.group(1)
            mask_type = re.sub(r"_\d+$", "", mask_full)

            if mask_type not in self.current_replacements:
                self.current_replacements[mask_type] = self._get_next_value(mask_type)

            return self.current_replacements[mask_type]

        return re.sub(pattern, replace_func, text)

    def process_example(self, example: dict) -> dict:
        """Обработать один пример, заменив маски."""
        self.current_replacements = {}

        for i, msg in enumerate(example.get("prompt", [])):
            if msg["role"] == "system":
                if "Маски анонимизации" in msg["content"]:
                    msg["content"] = re.sub(
                        r"Маски анонимизации \(\[[^\]]+\]\) — используй как есть\.\n?",
                        "",
                        msg["content"]
                    )
            elif msg["role"] == "user":
                msg["content"] = self._replace_masks_in_text(msg["content"])
            elif msg["role"] == "assistant":
                msg["content"] = self._replace_masks_in_text(msg["content"])

        if example.get("chosen"):
            for msg in example["chosen"]:
                if msg["role"] == "assistant":
                    msg["content"] = self._replace_masks_in_text(msg["content"])

        if example.get("rejected"):
            for msg in example["rejected"]:
                if msg["role"] == "assistant":
                    msg["content"] = self._replace_masks_in_text(msg["content"])

        return example


def process_file(input_path: str, output_path: str):
    """Обработать файл и заменить маски."""
    replacer = MaskReplacer()
    total_examples = 0
    examples_with_masks = 0
    total_masks_replaced = 0

    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.jsonl') as tmpfile:
        tmpname = tmpfile.name

        with open(input_path, "r", encoding="utf-8") as infile:
            for line in infile:
                total_examples += 1
                example = json.loads(line)

                before_str = json.dumps(example, ensure_ascii=False)
                example = replacer.process_example(example)
                after_str = json.dumps(example, ensure_ascii=False)

                if before_str != after_str and replacer.current_replacements:
                    examples_with_masks += 1
                    total_masks_replaced += len(replacer.current_replacements)

                tmpfile.write(json.dumps(example, ensure_ascii=False) + "\n")

        shutil.move(tmpname, output_path)

    return total_examples, examples_with_masks, total_masks_replaced


def main():
    """Главная функция."""
    base_path = os.path.expanduser("~/Downloads/Личное/ЮР тэг/yurteg/dataset/training")

    files_to_process = [
        ("v3_orpo_train.jsonl", 1086),
        ("v3_orpo_val.jsonl", 141)
    ]

    total_stats = {"total": 0, "with_masks": 0, "replaced": 0}

    for filename, expected_count in files_to_process:
        input_path = os.path.join(base_path, filename)
        output_path = input_path

        print(f"\nОбработка {filename}...")
        total, with_masks, replaced = process_file(input_path, output_path)

        print(f"  Всего примеров: {total} (ожидалось: {expected_count})")
        print(f"  Примеров с масками: {with_masks}")
        print(f"  Масок заменено: {replaced}")

        total_stats["total"] += total
        total_stats["with_masks"] += with_masks
        total_stats["replaced"] += replaced

    print("\n" + "="*60)
    print("ФИНАЛЬНАЯ СТАТИСТИКА")
    print("="*60)
    print(f"Обработано файлов: 2")
    print(f"Обработано примеров: {total_stats['total']}")
    print(f"Примеров содержали маски: {total_stats['with_masks']}")
    print(f"Масок заменено: {total_stats['replaced']}")
    print("="*60)


if __name__ == "__main__":
    main()
