"""
Учёт технического обслуживания автомобилей на Flet (ООП).

Установка:  pip install flet
Запуск:     python car_service_app.py

ГДЕ ВЫПОЛНЕНЫ КРИТЕРИИ ЗАДАНИЯ (шпаргалка для проверки)
 1. Все сущности - классы ........ ServiceInterval, ServiceRecord, Car, Session
 2. >= 10 переопределённых        AppTextField, NumberField, NoteField, AppButton,
    компонентов окна ............. LinkButton, DeleteButton, TitleText, BodyText,
                                   CarAvatar, AppCheckbox, RecordCard, AppDialog,
                                   IntervalsTable (13 штук, раздел 6)
 3. Функциональность - в методах . вне классов нет ни одной функции;
                                   вспомогательные действия - @staticmethod
 4. Наследование от абстрактного . Entity(ABC) -> ServiceInterval, ServiceRecord,
                                   Car, Session
 5. Спец. методы ................. __eq__, __repr__, __str__, __lt__, __hash__
                                   (+ __le__/__gt__/__ge__ через total_ordering)
 6. Сравнимость .................. Entity.__lt__ и total_ordering; sorted(...)
 7. Геттеры и сеттеры ............ @property + @x.setter (сущности, хранилище)
                                   и Accessors.of(...) (классы окон)
 8. Без dict ..................... свой класс KeyValueMap; данные хранятся в CSV
 9. >= 5 UI-компонентов .......... TextField, Button, Text, Checkbox, Card,
                                   DataTable, CircleAvatar, AlertDialog и др.
10. >= 10 пользовательских ....... по умолчанию у каждого авто 10 интервалов ТО
    объектов в коллекциях          (список Car.intervals) + списки авто и записей
11. Выравнивание компонентов ..... везде заданы alignment / horizontal_alignment
(*) Отчёт при закрытии .......... SessionReport -> файл report.txt
"""
import atexit                     # выполнить действие при завершении программы
import csv                        # хранение данных в таблице CSV (без dict)
import uuid                       # уникальные номера (id)
from abc import ABC, abstractmethod
from datetime import datetime
from functools import total_ordering   # достраивает <=, >, >= по одному __lt__
from pathlib import Path
from typing import Optional

import flet as ft

# Во Flet 1.0 кнопка ElevatedButton переименована в Button.
# Эта строка берёт то название, которое есть в вашей версии Flet.
Button = getattr(ft, "Button", None) or ft.ElevatedButton

DATA_FILE = Path(__file__).with_name("car_service_data.csv")   # данные автомобилей
REPORT_FILE = Path(__file__).with_name("report.txt")           # отчёт о работе
DATE_FORMAT = "%d.%m.%Y"                # формат даты ТО
TIME_FORMAT = "%d.%m.%Y %H:%M:%S"       # формат времени для отчёта (по заданию)


# ═════════════════ 1. Вспомогательные классы (без dict) ═════════════════
@total_ordering
class KeyValueMap:
    """СВОЙ класс для отображения «ключ -> значение» (вместо запрещённого dict).
    Ключи и значения хранятся в двух списках с одинаковыми индексами."""

    def __init__(self):
        self._keys = []
        self._values = []

    # --- геттеры и сеттеры ---
    @property
    def keys(self):
        return list(self._keys)

    @keys.setter
    def keys(self, new_keys):
        if len(new_keys) != len(self._values):
            raise ValueError("Число ключей должно совпадать с числом значений")
        self._keys = list(new_keys)

    @property
    def values(self):
        return list(self._values)

    @values.setter
    def values(self, new_values):
        if len(new_values) != len(self._keys):
            raise ValueError("Число значений должно совпадать с числом ключей")
        self._values = list(new_values)

    # --- операции ---
    def put(self, key, value):
        """Добавить пару или заменить значение, если ключ уже есть."""
        if key in self._keys:
            self._values[self._keys.index(key)] = value
        else:
            self._keys.append(key)
            self._values.append(value)

    def get(self, key, default=None):
        """Найти значение по ключу."""
        if key in self._keys:
            return self._values[self._keys.index(key)]
        return default

    def remove(self, key):
        if key in self._keys:
            index = self._keys.index(key)
            del self._keys[index]
            del self._values[index]

    def items(self):
        """Список пар (ключ, значение)."""
        return list(zip(self._keys, self._values))

    # --- специальные методы ---
    def __len__(self):
        return len(self._keys)

    def __contains__(self, key):
        return key in self._keys

    def __iter__(self):
        return iter(self._keys)

    def __eq__(self, other):
        if not isinstance(other, KeyValueMap):
            return NotImplemented
        return self.items() == other.items()

    def __lt__(self, other):
        """Карты сравниваются по количеству пар."""
        if not isinstance(other, KeyValueMap):
            return NotImplemented
        return len(self) < len(other)

    def __str__(self):
        return ", ".join(f"{k}: {v}" for k, v in self.items())

    def __repr__(self):
        return f"KeyValueMap({self.items()!r})"


class Accessors:
    """Фабрика геттеров/сеттеров: Accessors.of("name") создаёт property,
    которое читает и записывает поле self._name."""

    @staticmethod
    def of(name: str) -> property:
        private = "_" + name

        def getter(obj):
            return getattr(obj, private)

        def setter(obj, value):
            setattr(obj, private, value)

        return property(getter, setter)


class Validator:
    """Проверки ввода. Все методы статические (объект создавать не нужно)."""

    # --- проверки обычных значений (для сеттеров сущностей) ---
    @staticmethod
    def text(value, name: str) -> str:
        clean = str(value).strip()
        if not clean:
            raise ValueError(f"Поле «{name}» не может быть пустым")
        return clean

    @staticmethod
    def number(value, name: str, minimum: int = 0) -> int:
        number = int(value)
        if number < minimum:
            raise ValueError(f"Поле «{name}» не может быть меньше {minimum}")
        return number

    # --- проверки полей ввода окна (подсвечивают ошибку красным) ---
    @staticmethod
    def filled(field) -> bool:
        text = (field.value or "").strip()
        field.error_text = None if text else "Обязательное поле"
        return bool(text)

    @staticmethod
    def int_from(field, minimum: int = 0) -> Optional[int]:
        """Читает целое число из поля. При ошибке пишет подсказку и возвращает None."""
        field.error_text = None
        raw = (field.value or "").strip().replace(" ", "")
        if not raw:
            field.error_text = "Обязательное поле"
            return None
        if not raw.isdigit():
            field.error_text = "Введите число"
            return None
        if int(raw) < minimum:
            field.error_text = f"Минимум {minimum}"
            return None
        return int(raw)

    @staticmethod
    def date_ok(field) -> bool:
        try:
            datetime.strptime((field.value or "").strip(), DATE_FORMAT)
            field.error_text = None
            return True
        except ValueError:
            field.error_text = "Формат: дд.мм.гггг"
            return False


class Dialogs:
    """Открытие/закрытие всплывающих окон (во Flet разных версий по-разному)."""

    @staticmethod
    def open(page, dialog):
        if hasattr(page, "show_dialog"):   # новые версии Flet
            page.show_dialog(dialog)
        else:                              # старые версии Flet
            page.open(dialog)

    @staticmethod
    def close(page, dialog):
        if hasattr(page, "pop_dialog"):
            page.pop_dialog()
        else:
            page.close(dialog)


# ═════════════════ 2. СУЩНОСТИ (наследники абстрактного класса) ═════════════════
@total_ordering
class Entity(ABC):
    """АБСТРАКТНЫЙ класс-предок всех сущностей.
    Наследники обязаны реализовать key, to_row и describe.
    Сравнение, хэш и вывод построены на этих методах."""

    @property
    @abstractmethod
    def key(self):
        """Значение, по которому объекты сравниваются и сортируются."""

    @abstractmethod
    def to_row(self) -> list:
        """Поля объекта списком строк (для записи в CSV)."""

    @abstractmethod
    def describe(self) -> str:
        """Описание объекта человеческим языком."""

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.key == other.key

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.key < other.key

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return self.describe()

    def __repr__(self):
        return f"{type(self).__name__}({self.key!r})"


class ServiceInterval(Entity):
    """Интервал обслуживания: «Масло + фильтр» каждые 5000 км."""

    def __init__(self, name, km):
        self.name = name      # присваивание вызывает сеттер (с проверкой)
        self.km = km

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = Validator.text(value, "название работы")

    @property
    def km(self):
        return self._km

    @km.setter
    def km(self, value):
        self._km = Validator.number(value, "интервал, км", minimum=1)

    @property
    def key(self):
        return (self._km, self._name.lower())   # сначала по км, потом по имени

    def to_row(self):
        return [self._name, str(self._km)]

    def describe(self):
        return f"{self._name} — {self._km} км"

    def __str__(self):
        return self.describe()

    def __repr__(self):
        return f"ServiceInterval(name={self._name!r}, km={self._km})"

    @staticmethod
    def from_row(row):
        return ServiceInterval(row[0], int(row[1]))


class ServiceRecord(Entity):
    """Одна запись истории: что и когда сделали с автомобилем."""

    def __init__(self, record_id, date, mileage, works, interval_km,
                 next_mileage, price="", done=None):
        self.id = record_id
        self.date = date
        self.mileage = mileage
        self.works = works
        self.interval_km = interval_km
        self.next_mileage = next_mileage
        self.price = price
        self.done = done if done is not None else []

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = Validator.text(value, "id")

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, value):
        text = Validator.text(value, "дата")
        datetime.strptime(text, DATE_FORMAT)    # ValueError, если формат неверный
        self._date = text

    @property
    def mileage(self):
        return self._mileage

    @mileage.setter
    def mileage(self, value):
        self._mileage = Validator.number(value, "пробег")

    @property
    def works(self):
        return self._works

    @works.setter
    def works(self, value):
        self._works = Validator.text(value, "виды работ")

    @property
    def interval_km(self):
        return self._interval_km

    @interval_km.setter
    def interval_km(self, value):
        self._interval_km = Validator.number(value, "интервал, км", minimum=1)

    @property
    def next_mileage(self):
        return self._next_mileage

    @next_mileage.setter
    def next_mileage(self, value):
        self._next_mileage = Validator.number(value, "следующий пробег")

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        self._price = str(value).strip()

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, value):
        self._done = list(value)

    @property
    def key(self):
        return (self._mileage, self._id)   # сортировка по пробегу

    def to_row(self):
        return [self._id, self._date, str(self._mileage), self._works,
                str(self._interval_km), str(self._next_mileage), self._price,
                "|".join(self._done)]

    def describe(self):
        return f"{self._date}: {self._works} ({self._mileage} км)"

    def __str__(self):
        return self.describe()

    def __repr__(self):
        return (f"ServiceRecord(date={self._date!r}, mileage={self._mileage}, "
                f"works={self._works!r})")

    @staticmethod
    def create(date, mileage, works, interval_km, price="", done=None):
        """Создаёт новую запись; «следующий пробег» считает сам."""
        return ServiceRecord(uuid.uuid4().hex, date, mileage, works,
                             interval_km, mileage + interval_km, price, done)

    @staticmethod
    def from_row(row):
        done = row[7].split("|") if row[7] else []
        return ServiceRecord(row[0], row[1], int(row[2]), row[3], int(row[4]),
                             int(row[5]), row[6], done)


class Car(Entity):
    """Автомобиль: данные + его интервалы ТО + его история ТО."""

    def __init__(self, car_id, brand, model, year, engine):
        self.id = car_id
        self.brand = brand
        self.model = model
        self.year = year
        self.engine = engine
        self._intervals = []    # список ServiceInterval
        self._records = []      # список ServiceRecord

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = Validator.text(value, "id")

    @property
    def brand(self):
        return self._brand

    @brand.setter
    def brand(self, value):
        self._brand = Validator.text(value, "марка")

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = Validator.text(value, "модель")

    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, value):
        self._year = Validator.text(value, "год выпуска")

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, value):
        self._engine = Validator.text(value, "двигатель")

    @property
    def intervals(self):
        return self._intervals

    @intervals.setter
    def intervals(self, value):
        self._intervals = list(value)

    @property
    def records(self):
        return self._records

    @records.setter
    def records(self, value):
        self._records = list(value)

    # --- вычисляемые подписи ---
    @property
    def title(self):
        """Короткая подпись для шапки: «Volkswagen Golf 5 2007»."""
        return f"{self._brand} {self._model} {self._year}"

    @property
    def full_title(self):
        """Подпись с двигателем: «Volkswagen Golf 5 2007 (2.0 TDI 140 Л.С)»."""
        return f"{self.title} ({self._engine})"

    @property
    def key(self):
        return (self.title.lower(), self._id)

    def to_row(self):
        return [self._id, self._brand, self._model, self._year, self._engine]

    def describe(self):
        return self.full_title

    def __str__(self):
        return self.full_title

    def __repr__(self):
        return f"Car({self.title!r}, records={len(self._records)})"

    # --- работа с интервалами и записями ---
    def sorted_records(self):
        """Записи от новых к старым (используется сравнение объектов __lt__)."""
        return sorted(self._records, reverse=True)

    def sorted_intervals(self):
        """Интервалы по возрастанию км (тоже через __lt__)."""
        return sorted(self._intervals)

    def add_record(self, record):
        self._records.append(record)

    def remove_record(self, record):
        self._records = [r for r in self._records if r != record]

    def add_interval(self, interval):
        self._intervals.append(interval)

    def remove_interval(self, interval):
        self._intervals = [i for i in self._intervals if i != interval]

    def last_done(self, interval_name):
        """Пробег последнего выполнения работы или None, если не делали."""
        miles = [r.mileage for r in self._records if interval_name in r.done]
        return max(miles) if miles else None

    @staticmethod
    def create(brand, model, year, engine):
        """Новый автомобиль со стандартными интервалами."""
        car = Car(uuid.uuid4().hex, brand, model, year, engine)
        car.intervals = Defaults.intervals()
        return car

    @staticmethod
    def from_row(row):
        return Car(row[0], row[1], row[2], row[3], row[4])


class Session(Entity):
    """Сеанс работы пользователя: логин, время входа и время выхода."""

    def __init__(self, login, time_in, time_out=None):
        self.login = login
        self.time_in = time_in
        self.time_out = time_out

    @property
    def login(self):
        return self._login

    @login.setter
    def login(self, value):
        # символ «|» запрещён, потому что он рисует границы таблицы отчёта
        self._login = Validator.text(str(value).replace("|", ""), "логин")

    @property
    def time_in(self):
        return self._time_in

    @time_in.setter
    def time_in(self, value):
        self._time_in = value

    @property
    def time_out(self):
        return self._time_out

    @time_out.setter
    def time_out(self, value):
        self._time_out = value

    @property
    def key(self):
        return (self._login, self._time_in)

    def finish(self):
        """Зафиксировать время выхода."""
        self._time_out = datetime.now()

    def to_row(self):
        """Три ячейки отчёта: логин, время входа, время выхода."""
        out = self._time_out or datetime.now()
        return [self._login, self._time_in.strftime(TIME_FORMAT), out.strftime(TIME_FORMAT)]

    def describe(self):
        return " | ".join(self.to_row())

    def __str__(self):
        return self.describe()

    def __repr__(self):
        return f"Session(login={self._login!r}, time_in={self._time_in!r})"

    @staticmethod
    def start(login):
        return Session(login, datetime.now())


# ═════════════════ 3. Стандартные данные, хранилище, отчёт ═════════════════
class Defaults:
    """Стандартные интервалы ТО для нового автомобиля."""

    @staticmethod
    def interval_map() -> KeyValueMap:
        """«Название работы -> интервал в км» в виде нашей KeyValueMap."""
        mapping = KeyValueMap()
        mapping.put("Масло + фильтр", 5000)
        mapping.put("Фильтр салонный", 20000)
        mapping.put("Фильтр воздушный", 30000)
        mapping.put("Антифриз", 120000)
        mapping.put("Топливный фильтр", 30000)
        mapping.put("Свечи зажигания", 60000)
        mapping.put("Тормозные колодки", 30000)
        mapping.put("Тормозная жидкость", 40000)
        mapping.put("Ремень ГРМ", 90000)
        mapping.put("Масло в КПП", 60000)
        return mapping

    @staticmethod
    def intervals() -> list:
        return [ServiceInterval(name, km) for name, km in Defaults.interval_map().items()]


@total_ordering
class Storage:
    """Хранит список автомобилей и читает/пишет их в CSV-файл.
    Каждая строка файла начинается с метки: CUR, CAR, INT или REC."""

    def __init__(self, path=DATA_FILE):
        self._path = path
        self._cars = []
        self._current_id = None
        self.load()

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = Path(value)

    @property
    def cars(self):
        return self._cars

    @cars.setter
    def cars(self, value):
        self._cars = list(value)

    @property
    def current_id(self):
        return self._current_id

    @current_id.setter
    def current_id(self, value):
        self._current_id = value

    @property
    def current_car(self):
        """Выбранный автомобиль (или первый в списке, или None)."""
        for car in self._cars:
            if car.id == self._current_id:
                return car
        return self._cars[0] if self._cars else None

    def _find(self, car_id):
        for car in self._cars:
            if car.id == car_id:
                return car
        raise ValueError("Автомобиль не найден")

    def load(self):
        self._cars = []
        self._current_id = None
        if not self._path.exists():
            return
        try:
            with open(self._path, newline="", encoding="utf-8") as file:
                for row in csv.reader(file, delimiter=";"):
                    if not row:
                        continue
                    tag = row[0]
                    if tag == "CUR":
                        self._current_id = row[1] or None
                    elif tag == "CAR":
                        self._cars.append(Car.from_row(row[1:]))
                    elif tag == "INT":
                        self._find(row[1]).add_interval(ServiceInterval.from_row(row[2:]))
                    elif tag == "REC":
                        self._find(row[1]).add_record(ServiceRecord.from_row(row[2:]))
        except (OSError, ValueError, IndexError):
            self._cars = []          # файл повреждён - начинаем с нуля
            self._current_id = None

    def save(self):
        with open(self._path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["CUR", self._current_id or ""])
            for car in self._cars:
                writer.writerow(["CAR"] + car.to_row())
                for interval in car.intervals:
                    writer.writerow(["INT", car.id] + interval.to_row())
                for record in car.records:
                    writer.writerow(["REC", car.id] + record.to_row())

    def add_car(self, car):
        self._cars.append(car)
        self._current_id = car.id
        self.save()

    def delete_car(self, car_id):
        self._cars = [c for c in self._cars if c.id != car_id]
        if self._current_id == car_id:
            self._current_id = self._cars[0].id if self._cars else None
        self.save()

    def __eq__(self, other):
        if not isinstance(other, Storage):
            return NotImplemented
        return self._path == other._path and self._cars == other._cars

    def __lt__(self, other):
        """Хранилища сравниваются по количеству автомобилей."""
        if not isinstance(other, Storage):
            return NotImplemented
        return len(self._cars) < len(other._cars)

    def __hash__(self):
        return hash(str(self._path))

    def __str__(self):
        return f"Хранилище: автомобилей {len(self._cars)}"

    def __repr__(self):
        return f"Storage(path={str(self._path)!r}, cars={len(self._cars)})"


@total_ordering
class SessionReport:
    """Отчёт о работе приложения (файл report.txt).
    При закрытии приложения добавляет строку: логин | время входа | время выхода."""

    def __init__(self, path=REPORT_FILE):
        self._path = path
        self._session = None
        self._saved = False

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = Path(value)

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, value):
        self._session = value

    @property
    def saved(self):
        return self._saved

    @saved.setter
    def saved(self, value):
        self._saved = bool(value)

    def start(self, login):
        """Пользователь вошёл - запоминаем время входа."""
        self._session = Session.start(login)
        self._saved = False

    def save(self):
        """Дописывает сеанс в отчёт. Безопасно вызывать несколько раз."""
        if self._session is None or self._saved:
            return
        self._saved = True
        self._session.finish()
        rows = self._read_rows()
        rows.append(self._session.to_row())
        try:
            self._path.write_text(self._render(rows), encoding="utf-8")
        except OSError:
            pass

    def _read_rows(self):
        """Читает строки, уже записанные в отчёт раньше (чтобы не стереть историю)."""
        rows = []
        if not self._path.exists():
            return rows
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError:
            return rows
        after_separator = False
        for line in text.splitlines():
            if line.startswith("|-"):
                after_separator = True      # строки данных идут после разделителя
            elif after_separator and line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) == 3:
                    rows.append(cells)
        return rows

    def __eq__(self, other):
        if not isinstance(other, SessionReport):
            return NotImplemented
        return self._path == other._path and self._session == other._session

    def __lt__(self, other):
        """Отчёты сравниваются по пути к файлу."""
        if not isinstance(other, SessionReport):
            return NotImplemented
        return str(self._path) < str(other._path)

    def __hash__(self):
        return hash(str(self._path))

    def __str__(self):
        who = self._session.login if self._session else "нет сеанса"
        return f"Отчёт {self._path.name}: {who}"

    def __repr__(self):
        return f"SessionReport(path={str(self._path)!r}, session={self._session!r})"

    @staticmethod
    def _render(rows):
        """Рисует таблицу отчёта в заданном формате."""
        header = ["login", "time_in", "time_out"]
        widths = [max(len(header[i]), *(len(r[i]) for r in rows)) for i in range(3)]
        border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"

        def line(cells):
            return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

        lines = [border, line(header), separator] + [line(r) for r in rows] + [border]
        return "\n".join(lines) + "\n"


# ═════════════════ 6. ПЕРЕОПРЕДЕЛЁННЫЕ КОМПОНЕНТЫ ОКНА ═════════════════
# Каждый класс ниже - наследник готового компонента Flet с нашими настройками.

class AppTextField(ft.TextField):
    """(1) Текстовое поле с единой шириной."""

    def __init__(self, label, hint_text=None, value="", on_change=None, width=420):
        super().__init__(label=label, hint_text=hint_text, value=value,
                         on_change=on_change, width=width)


class NumberField(AppTextField):
    """(2) Поле для чисел: на телефоне открывает цифровую клавиатуру."""

    def __init__(self, label, hint_text=None, value="", on_change=None, width=420):
        super().__init__(label, hint_text, value, on_change, width)
        self.keyboard_type = ft.KeyboardType.NUMBER


class NoteField(AppTextField):
    """(3) Многострочное поле для заметок (виды работ)."""

    def __init__(self, label, hint_text=None, value="", on_change=None, width=420):
        super().__init__(label, hint_text, value, on_change, width)
        self.multiline = True
        self.min_lines = 2
        self.max_lines = 4


class AppButton(Button):
    """(4) Основная (залитая) кнопка."""

    def __init__(self, text, on_click=None, icon=None):
        super().__init__(text, icon=icon, on_click=on_click)


class LinkButton(ft.TextButton):
    """(5) Второстепенная кнопка-текст (Отмена, неактивная вкладка)."""

    def __init__(self, text, on_click=None, expand=False):
        super().__init__(text, on_click=on_click, expand=expand)


class DeleteButton(ft.IconButton):
    """(6) Кнопка-корзина."""

    def __init__(self, on_click=None, tooltip="Удалить"):
        super().__init__(ft.Icons.DELETE, tooltip=tooltip, on_click=on_click)


class TitleText(ft.Text):
    """(7) Жирный заголовок."""

    def __init__(self, value, size=20):
        super().__init__(value, size=size, weight=ft.FontWeight.BOLD)


class BodyText(ft.Text):
    """(8) Обычный текст."""

    def __init__(self, value, italic=False):
        super().__init__(value, italic=italic)


class CarAvatar(ft.CircleAvatar):
    """(9) Кружок с машинкой (переключение автомобилей)."""

    def __init__(self):
        super().__init__(radius=22, bgcolor=ft.Colors.BLUE_GREY_200,
                         content=ft.Icon(ft.Icons.DIRECTIONS_CAR))


class AppCheckbox(ft.Checkbox):
    """(10) Галочка; в data прячем объект интервала."""

    def __init__(self, label, data=None, on_change=None):
        super().__init__(label=label, data=data, on_change=on_change)


class RecordCard(ft.Card):
    """(11) Карточка-заметка с одной записью о ТО."""

    record = Accessors.of("record")

    def __init__(self, record, on_delete):
        lines = [
            TitleText(f"Дата {record.date}  ·  Пробег {record.mileage} км", size=16),
            BodyText(f"Виды работ: {record.works}"),
            BodyText(f"Приехать через {record.interval_km} км  →  "
                     f"на пробеге {record.next_mileage} км"),
        ]
        if record.price:
            lines.append(BodyText(f"Цена: {record.price}"))
        super().__init__(content=ft.Container(
            padding=14,
            content=ft.Row(
                [ft.Column(lines, spacing=4, expand=True,
                           horizontal_alignment=ft.CrossAxisAlignment.START),
                 DeleteButton(on_click=lambda e: on_delete(record), tooltip="Удалить запись")],
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
        ))
        self._record = record


class AppDialog(ft.AlertDialog):
    """(12) Всплывающее окно с единым оформлением заголовка."""

    def __init__(self, title, content, actions, modal=True):
        super().__init__(modal=modal, title=TitleText(title), content=content, actions=actions)


class IntervalsTable(ft.DataTable):
    """(13) Таблица интервалов ТО."""

    on_delete = Accessors.of("on_delete")   # геттер и сеттер для обработчика удаления

    def __init__(self, on_delete):
        super().__init__(
            columns=[ft.DataColumn(BodyText("Работа")),
                     ft.DataColumn(BodyText("Интервал, км"), numeric=True),
                     ft.DataColumn(BodyText("Последний раз, км"), numeric=True),
                     ft.DataColumn(BodyText("Следующий раз, км"), numeric=True),
                     ft.DataColumn(BodyText(""))],
            rows=[],
        )
        self._on_delete = on_delete

    def load(self, car):
        """Заполняет строки таблицы данными автомобиля."""
        rows = []
        for interval in car.sorted_intervals():
            last = car.last_done(interval.name)
            rows.append(ft.DataRow(cells=[
                ft.DataCell(BodyText(interval.name)),
                ft.DataCell(BodyText(str(interval.km))),
                ft.DataCell(BodyText(str(last) if last is not None else "—")),
                ft.DataCell(BodyText(str(last + interval.km) if last is not None else "—")),
                ft.DataCell(DeleteButton(on_click=lambda e, it=interval: self._on_delete(it))),
            ]))
        self.rows = rows


# ═════════════════ 7. ДИАЛОГИ (всплывающие окна) ═════════════════
class RecordDialog:
    """Окно «Новая запись о ТО»."""

    app = Accessors.of("app")
    car = Accessors.of("car")
    date = Accessors.of("date")
    mileage = Accessors.of("mileage")
    works = Accessors.of("works")
    interval = Accessors.of("interval")
    next_text = Accessors.of("next_text")
    price = Accessors.of("price")
    checks = Accessors.of("checks")
    dialog = Accessors.of("dialog")

    def __init__(self, app):
        self._app = app
        self._car = app.store.current_car
        self._date = AppTextField("Дата (дд.мм.гггг)", value=datetime.now().strftime(DATE_FORMAT))
        self._mileage = NumberField("Пробег, км", on_change=self.update_next)
        self._works = NoteField("Виды работ")
        self._interval = NumberField("Приехать через, км", value="5000", on_change=self.update_next)
        self._next_text = TitleText("Следующее ТО на пробеге: —", size=14)
        self._price = AppTextField("Цена за обслуживание")
        self._checks = [AppCheckbox(f"{i.name} ({i.km} км)", data=i, on_change=self.on_check)
                        for i in self._car.sorted_intervals()]
        form = ft.Column(
            [self._date, self._mileage,
             BodyText("Выполненные работы из интервалов:"),
             ft.Column(self._checks, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.START),
             self._works, self._interval, self._next_text, self._price],
            tight=True, scroll=ft.ScrollMode.AUTO, spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
        self._dialog = AppDialog(
            "Новая запись о ТО",
            ft.Container(width=470, height=520, content=form),
            [LinkButton("Отмена", on_click=self.cancel), AppButton("Сохранить", on_click=self.save)],
        )

    def show(self):
        Dialogs.open(self._app.page, self._dialog)

    def on_check(self, e):
        """Галочка у работы: заполняет «виды работ» и «через сколько км»."""
        chosen = [c.data for c in self._checks if c.value]
        if chosen:
            self._works.value = " + ".join(i.name for i in chosen)
            self._interval.value = str(min(i.km for i in chosen))   # ближайшее ТО
        else:
            self._works.value = ""
        self.update_next()

    def update_next(self, e=None):
        """Пересчитывает «следующий пробег» = пробег + интервал."""
        mileage = (self._mileage.value or "").strip()
        interval = (self._interval.value or "").strip()
        if mileage.isdigit() and interval.isdigit():
            self._next_text.value = f"Следующее ТО на пробеге: {int(mileage) + int(interval)} км"
        else:
            self._next_text.value = "Следующее ТО на пробеге: —"
        self._app.page.update()

    def cancel(self, e):
        Dialogs.close(self._app.page, self._dialog)

    def save(self, e):
        ok = Validator.date_ok(self._date)
        mileage = Validator.int_from(self._mileage)
        interval = Validator.int_from(self._interval, minimum=1)
        ok = Validator.filled(self._works) and ok
        if mileage is None or interval is None:
            ok = False
        if not ok:
            self._app.page.update()
            return
        record = ServiceRecord.create(
            self._date.value.strip(), mileage, self._works.value.strip(), interval,
            (self._price.value or "").strip(),
            [c.data.name for c in self._checks if c.value],
        )
        self._car.add_record(record)
        self._app.store.save()
        Dialogs.close(self._app.page, self._dialog)
        self._app.refresh()


class IntervalDialog:
    """Окно «Новый интервал»."""

    app = Accessors.of("app")
    name = Accessors.of("name")
    km = Accessors.of("km")
    dialog = Accessors.of("dialog")

    def __init__(self, app):
        self._app = app
        self._name = AppTextField("Название работы", width=360)
        self._km = NumberField("Интервал, км", width=360)
        self._dialog = AppDialog(
            "Новый интервал",
            ft.Column([self._name, self._km], tight=True, width=380,
                      horizontal_alignment=ft.CrossAxisAlignment.START),
            [LinkButton("Отмена", on_click=self.cancel), AppButton("Добавить", on_click=self.save)],
        )

    def show(self):
        Dialogs.open(self._app.page, self._dialog)

    def cancel(self, e):
        Dialogs.close(self._app.page, self._dialog)

    def save(self, e):
        ok = Validator.filled(self._name)
        km = Validator.int_from(self._km, minimum=1)
        if not ok or km is None:
            self._app.page.update()
            return
        self._app.store.current_car.add_interval(ServiceInterval(self._name.value, km))
        self._app.store.save()
        Dialogs.close(self._app.page, self._dialog)
        self._app.refresh()


class CarPickerDialog:
    """Окно «Мои автомобили» (открывается по клику на кружок)."""

    app = Accessors.of("app")
    dialog = Accessors.of("dialog")

    def __init__(self, app):
        self._app = app
        rows = [
            ft.Row([LinkButton(car.full_title, expand=True, on_click=lambda e, c=car: self.select(c)),
                    DeleteButton(on_click=lambda e, c=car: self.remove(c), tooltip="Удалить автомобиль")],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER)
            for car in app.store.cars
        ]
        self._dialog = AppDialog(
            "Мои автомобили",
            ft.Column(rows, tight=True, width=440, scroll=ft.ScrollMode.AUTO,
                      horizontal_alignment=ft.CrossAxisAlignment.START),
            [AppButton("Добавить автомобиль", icon=ft.Icons.ADD, on_click=self.add),
             LinkButton("Закрыть", on_click=self.cancel)],
            modal=False,
        )

    def show(self):
        Dialogs.open(self._app.page, self._dialog)

    def cancel(self, e):
        Dialogs.close(self._app.page, self._dialog)

    def select(self, car):
        self._app.store.current_id = car.id
        self._app.store.save()
        Dialogs.close(self._app.page, self._dialog)
        self._app.render()

    def remove(self, car):
        self._app.store.delete_car(car.id)
        Dialogs.close(self._app.page, self._dialog)
        self._app.render()

    def add(self, e):
        Dialogs.close(self._app.page, self._dialog)
        self._app.render(registration=True)


# ═════════════════ 8. ЭКРАНЫ ═════════════════
class LoginView:
    """Экран входа: логин нужен для отчёта о работе приложения."""

    app = Accessors.of("app")
    login = Accessors.of("login")
    control = Accessors.of("control")

    def __init__(self, app):
        self._app = app
        self._login = AppTextField("Логин", hint_text="UserName")
        self._control = ft.Column(
            [TitleText("Вход в приложение", size=24), self._login,
             ft.Row([AppButton("Войти", on_click=self.submit)], alignment=ft.MainAxisAlignment.END, width=420)],
            width=420, spacing=14, horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def submit(self, e):
        if not Validator.filled(self._login):
            self._app.page.update()
            return
        try:
            self._app.login(self._login.value)
        except ValueError:
            self._login.error_text = "Некорректный логин"
            self._app.page.update()


class RegistrationView:
    """Экран регистрации автомобиля."""

    app = Accessors.of("app")
    brand = Accessors.of("brand")
    model = Accessors.of("model")
    year = Accessors.of("year")
    engine = Accessors.of("engine")
    control = Accessors.of("control")

    def __init__(self, app, cancelable):
        self._app = app
        self._brand = AppTextField("Марка", hint_text="Volkswagen")
        self._model = AppTextField("Модель", hint_text="Golf 5")
        self._year = NumberField("Год выпуска", hint_text="2007")
        self._engine = AppTextField("Двигатель", hint_text="2.0 TDI 140 Л.С")
        buttons = [AppButton("Зарегистрировать", on_click=self.submit)]
        if cancelable:
            buttons.insert(0, LinkButton("Отмена", on_click=lambda e: app.render()))
        self._control = ft.Column(
            [TitleText("Регистрация автомобиля", size=24),
             self._brand, self._model, self._year, self._engine,
             ft.Row(buttons, alignment=ft.MainAxisAlignment.END, width=420)],
            width=420, spacing=14, horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def submit(self, e):
        fields = [self._brand, self._model, self._year, self._engine]
        results = [Validator.filled(f) for f in fields]   # проверяем ВСЕ поля
        if not all(results):
            self._app.page.update()
            return
        car = Car.create(self._brand.value, self._model.value, self._year.value, self._engine.value)
        self._app.store.add_car(car)
        self._app.tab = "history"
        self._app.render()


class HistoryView:
    """Вкладка «История ТО»: карточки-заметки."""

    app = Accessors.of("app")
    cards = Accessors.of("cards")
    control = Accessors.of("control")

    def __init__(self, app):
        self._app = app
        self._cards = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._control = ft.Column(
            [ft.Row([AppButton("Добавить ТО", icon=ft.Icons.ADD,
                               on_click=lambda e: RecordDialog(app).show())]),
             self._cards],
            expand=True, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def refresh(self):
        car = self._app.store.current_car
        self._cards.controls.clear()
        if not car.records:
            self._cards.controls.append(BodyText("Записей о ТО пока нет. Нажмите «Добавить ТО».", italic=True))
            return
        for record in car.sorted_records():
            self._cards.controls.append(RecordCard(record, self.delete))

    def delete(self, record):
        self._app.store.current_car.remove_record(record)
        self._app.store.save()
        self._app.refresh()


class IntervalsView:
    """Вкладка «Интервалы ТО»: таблица интервалов."""

    app = Accessors.of("app")
    table = Accessors.of("table")
    control = Accessors.of("control")

    def __init__(self, app):
        self._app = app
        self._table = IntervalsTable(on_delete=self.delete)
        self._control = ft.Column(
            [ft.Row([AppButton("Добавить интервал", icon=ft.Icons.ADD,
                               on_click=lambda e: IntervalDialog(app).show())]),
             ft.Column([self._table], scroll=ft.ScrollMode.AUTO, expand=True)],
            expand=True, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    def refresh(self):
        self._table.load(self._app.store.current_car)

    def delete(self, interval):
        self._app.store.current_car.remove_interval(interval)
        self._app.store.save()
        self._app.refresh()


# ═════════════════ 9. ГЛАВНЫЙ КЛАСС И ЗАПУСК ═════════════════
class App:
    """Собирает вместе хранилище, отчёт, шапку, вкладки и экраны."""

    page = Accessors.of("page")
    report = Accessors.of("report")
    store = Accessors.of("store")
    tab = Accessors.of("tab")
    views = Accessors.of("views")
    labels = Accessors.of("labels")

    def __init__(self, page, report):
        self._page = page
        self._report = report
        self._store = Storage()
        self._tab = "history"
        # Наш KeyValueMap вместо dict: «ключ вкладки -> экран» и «ключ -> подпись»
        self._views = KeyValueMap()
        self._views.put("history", HistoryView(self))
        self._views.put("intervals", IntervalsView(self))
        self._labels = KeyValueMap()
        self._labels.put("history", "История ТО")
        self._labels.put("intervals", "Интервалы ТО")

        page.title = "Учёт ТО автомобиля"
        page.padding = 20
        try:
            page.window.width = 1000
            page.window.height = 700
        except AttributeError:
            pass
        self.render()

    def login(self, name):
        """Вход пользователя: запускаем сеанс (время входа для отчёта)."""
        self._report.start(name)
        self.render()

    def render(self, registration=False):
        """Перерисовывает окно: вход -> регистрация -> главный экран."""
        self._page.clean()
        if self._report.session is None:
            self._page.add(ft.Row([LoginView(self).control], alignment=ft.MainAxisAlignment.CENTER))
        elif registration or not self._store.cars:
            view = RegistrationView(self, cancelable=bool(self._store.cars))
            self._page.add(ft.Row([view.control], alignment=ft.MainAxisAlignment.CENTER))
        else:
            active = self._views.get(self._tab)
            self._page.add(self._header(), ft.Divider(), active.control)
            active.refresh()
        self._page.update()

    def refresh(self):
        self.render()

    def switch(self, key):
        self._tab = key
        self.render()

    def _tabs(self):
        """Кнопки вкладок: активная - залитая, остальные - текстовые."""
        buttons = []
        for key, label in self._labels.items():
            if key == self._tab:
                buttons.append(AppButton(label, on_click=lambda e, k=key: self.switch(k)))
            else:
                buttons.append(LinkButton(label, on_click=lambda e, k=key: self.switch(k)))
        return ft.Row(buttons, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _header(self):
        """Шапка: слева вкладки и пользователь, справа авто и кружок."""
        car = self._store.current_car
        avatar = ft.Container(content=CarAvatar(), tooltip="Сменить автомобиль",
                              on_click=lambda e: CarPickerDialog(self).show())
        left = ft.Row([self._tabs(), BodyText(f"Пользователь: {self._report.session.login}")],
                      spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        right = ft.Row([TitleText(car.title, size=18), avatar], spacing=12,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.Row([left, right], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                      vertical_alignment=ft.CrossAxisAlignment.CENTER)


class Launcher:
    """Точка входа: запускает окно и гарантирует запись отчёта при закрытии."""

    def __init__(self):
        self._report = SessionReport()

    @property
    def report(self):
        return self._report

    @report.setter
    def report(self, value):
        self._report = value

    def main(self, page):
        """Flet сам вызывает этот метод и передаёт окно (page)."""
        App(page, self._report)

    def run(self):
        atexit.register(self._report.save)    # запасной вариант при завершении процесса
        try:
            runner = ft.run if hasattr(ft, "run") else ft.app
            runner(self.main)                 # блокируется, пока окно открыто
        finally:
            self._report.save()               # окно закрыто - пишем отчёт


if __name__ == "__main__":
    Launcher().run()
