"""
Учёт технического обслуживания автомобилей на Flet (ООП).

Установка:  pip install flet
Запуск:     python car_service_app.py
Данные хранятся в файле car_service_data.json рядом со скриптом.

КАК УСТРОЕН ЭТОТ ФАЙЛ (общая карта, читайте сверху вниз):

  1. Импорты и настройки      - подключаем нужные библиотеки
  2. МОДЕЛИ                   - классы, которые описывают ДАННЫЕ
                                (автомобиль, запись о ТО, интервал)
  3. Storage                  - класс, который СОХРАНЯЕТ и ЗАГРУЖАЕТ данные из файла
  4. Помощники                - маленькие функции, чтобы не повторять код
  5. ДИАЛОГИ                  - всплывающие окошки (добавить ТО, интервал, выбрать авто)
  6. ЭКРАНЫ                   - регистрация, история ТО, таблица интервалов
  7. App                      - главный класс, который собирает всё вместе
  8. main и запуск            - точка входа в программу

Идея ООП здесь простая: каждый кусочек программы - отдельный класс со своей
задачей. Так проще искать ошибки и добавлять новые возможности.
"""

# ───────────────────────────── 1. Импорты ─────────────────────────────
import json                      # чтобы сохранять данные в файл в формате JSON
import uuid                      # чтобы создавать уникальные номера (id) для записей
from dataclasses import dataclass, field, asdict
# dataclass - удобный способ описать класс, который просто хранит данные.
# field     - нужен, чтобы задать значение по умолчанию для списка.
# asdict    - превращает объект dataclass в обычный словарь (для сохранения в JSON).
from datetime import datetime    # работа с датами
from pathlib import Path         # удобная работа с путями к файлам
from typing import Optional      # подсказка типов: значение может быть None ("пусто")

import flet as ft                # сама библиотека для окон и кнопок (сокращённо ft)

# Во Flet 1.0 кнопка ElevatedButton переименована в Button.
# Эта строка выбирает то название, которое есть в вашей версии Flet,
# поэтому код работает и на старых, и на новых версиях.
Button = getattr(ft, "Button", None) or ft.ElevatedButton

# Файл с данными лежит рядом со скриптом.
# __file__ - это путь к текущему файлу, with_name заменяет имя файла на другое.
DATA_FILE = Path(__file__).with_name("car_service_data.json")

# Интервалы, которые автоматически получает каждый НОВЫЙ автомобиль.
# Формат: (название работы, через сколько км повторять).
# Их можно будет менять на вкладке «Интервалы ТО».
DEFAULT_INTERVALS = [
    ("Масло + фильтр", 5000),
    ("Фильтр салонный", 20000),
    ("Фильтр воздушный", 30000),
    ("Антифриз", 120000),
]


# ───────────────────────────── 2. МОДЕЛИ ─────────────────────────────
# Модель - это класс, который описывает "вещь" из реального мира.
# Декоратор @dataclass сам создаёт конструктор (__init__), так что
# ServiceInterval("Масло", 5000) работает без лишнего кода.

@dataclass
class ServiceInterval:
    """Один интервал обслуживания, например: «Масло + фильтр» каждые 5000 км."""
    name: str   # название работы
    km: int     # через сколько километров её повторять


@dataclass
class ServiceRecord:
    """Одна запись в истории: что и когда сделали с автомобилем."""
    id: str             # уникальный номер записи (нужен, чтобы найти и удалить именно её)
    date: str           # дата ТО, например "11.08.2026"
    mileage: int        # пробег на момент ТО
    works: str          # текст: какие работы сделали
    interval_km: int    # через сколько км ехать снова
    next_mileage: int   # на каком пробеге ехать снова (mileage + interval_km)
    price: str = ""     # цена (необязательное поле, по умолчанию пустая строка)
    # Список названий интервалов, которые были выполнены в этом ТО.
    # Нужен, чтобы в таблице интервалов показать "последний раз сделано на ... км".
    # default_factory=list означает: у каждой записи свой новый пустой список.
    done: list = field(default_factory=list)


@dataclass
class Car:
    """Автомобиль: его данные + его интервалы + его история ТО."""
    id: str
    brand: str      # марка, например Volkswagen
    model: str      # модель, например Golf 5
    year: str       # год выпуска
    engine: str     # двигатель, например 2.0 TDI 140 Л.С
    intervals: list = field(default_factory=list)   # список ServiceInterval
    records: list = field(default_factory=list)     # список ServiceRecord

    # @property делает так, что title можно читать как обычное поле: car.title
    # (без скобок), хотя на самом деле это маленькая функция.
    @property
    def title(self) -> str:
        """Короткая подпись для шапки: «Volkswagen Golf 5 2007»."""
        return f"{self.brand} {self.model} {self.year}"

    @property
    def full_title(self) -> str:
        """Полная подпись с двигателем: «Volkswagen Golf 5 2007 (2.0 TDI 140 Л.С)»."""
        return f"{self.title} ({self.engine})" if self.engine else self.title

    # @staticmethod - функция, которая принадлежит классу, но не требует
    # существующего объекта. Вызывается так: Car.create(...)
    @staticmethod
    def create(brand, model, year, engine) -> "Car":
        """Создаёт НОВЫЙ автомобиль и сразу даёт ему стандартные интервалы."""
        return Car(
            id=uuid.uuid4().hex,   # случайный уникальный идентификатор
            brand=brand, model=model, year=year, engine=engine,
            intervals=[ServiceInterval(n, k) for n, k in DEFAULT_INTERVALS],
        )

    @staticmethod
    def from_dict(d: dict) -> "Car":
        """Собирает автомобиль обратно из словаря (так мы читаем JSON-файл)."""
        return Car(
            id=d["id"], brand=d["brand"], model=d["model"], year=d["year"],
            engine=d.get("engine", ""),
            # **i "распаковывает" словарь в аргументы: ServiceInterval(name=..., km=...)
            intervals=[ServiceInterval(**i) for i in d.get("intervals", [])],
            records=[ServiceRecord(**r) for r in d.get("records", [])],
        )

    def last_done(self, interval_name: str) -> Optional[int]:
        """Возвращает пробег, на котором эту работу делали ПОСЛЕДНИЙ раз.
        Если её ни разу не делали - возвращает None (то есть «пусто»)."""
        miles = [r.mileage for r in self.records if interval_name in r.done]
        return max(miles) if miles else None


# ───────────────────────── 3. Хранилище данных ─────────────────────────
class Storage:
    """Отвечает только за одно: хранить список автомобилей
    и читать/писать их в файл. Больше этот класс ничего не знает."""

    def __init__(self, path: Path = DATA_FILE):
        self.path = path                       # где лежит файл
        self.cars: list[Car] = []              # все автомобили пользователя
        self.current_id: Optional[str] = None  # id автомобиля, выбранного сейчас
        self.load()                            # сразу при создании читаем файл

    @property
    def current_car(self) -> Optional[Car]:
        """Текущий (выбранный) автомобиль. Если ничего не выбрано - первый в списке."""
        for c in self.cars:
            if c.id == self.current_id:
                return c
        return self.cars[0] if self.cars else None

    def load(self):
        """Читает данные из файла. Если файла нет или он повреждён - начинаем с нуля."""
        if not self.path.exists():
            return  # файла ещё нет (первый запуск) - ничего не делаем
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.cars = [Car.from_dict(c) for c in data.get("cars", [])]
            self.current_id = data.get("current_id")
        except (json.JSONDecodeError, KeyError, TypeError):
            # Файл битый - не падаем с ошибкой, просто начинаем с пустого списка
            self.cars = []

    def save(self):
        """Записывает все данные в файл. Вызываем после КАЖДОГО изменения."""
        data = {"current_id": self.current_id, "cars": [asdict(c) for c in self.cars]}
        # ensure_ascii=False - чтобы русские буквы в файле были читаемыми
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_car(self, car: Car):
        """Добавляет автомобиль, делает его текущим и сохраняет."""
        self.cars.append(car)
        self.current_id = car.id
        self.save()

    def delete_car(self, car_id: str):
        """Удаляет автомобиль по id."""
        # Оставляем в списке все автомобили, кроме удаляемого
        self.cars = [c for c in self.cars if c.id != car_id]
        if self.current_id == car_id:
            # Удалили текущий - выбираем первый оставшийся (или None, если пусто)
            self.current_id = self.cars[0].id if self.cars else None
        self.save()


# ───────────────────── 4. Помощники для диалогов ─────────────────────
# Во Flet разных версий окошки открываются по-разному.
# Эти две функции скрывают разницу, чтобы остальной код был одинаковым.

def open_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """Показывает всплывающее окно."""
    if hasattr(page, "show_dialog"):   # новые версии Flet
        page.show_dialog(dlg)
    else:                              # более старые версии Flet
        page.open(dlg)


def close_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """Закрывает всплывающее окно."""
    if hasattr(page, "pop_dialog"):
        page.pop_dialog()
    else:
        page.close(dlg)


def parse_int(field_: ft.TextField, required: bool = True) -> Optional[int]:
    """Читает целое число из текстового поля.
    Если ввод неправильный - подсвечивает поле красным с текстом ошибки
    и возвращает None. Если всё хорошо - возвращает число."""
    field_.error_text = None  # сначала убираем старую ошибку
    # strip() убирает пробелы по краям, replace убирает пробелы внутри ("282 406" -> "282406")
    raw = (field_.value or "").strip().replace(" ", "")
    if not raw:
        if required:
            field_.error_text = "Обязательное поле"
        return None
    if not raw.isdigit():       # isdigit() - True, если в строке только цифры
        field_.error_text = "Введите число"
        return None
    return int(raw)


# ───────────────────────── 5. ДИАЛОГИ (всплывающие окна) ─────────────────────────

class RecordDialog:
    """Окно «Новая запись о ТО»: дата, пробег, работы, интервал, цена."""

    def __init__(self, app: "App"):
        self.app = app                       # ссылка на главное приложение
        car = app.store.current_car          # запись добавляем текущему автомобилю
        self.car = car

        # --- Поля ввода. ft.TextField - это строка, в которую пользователь печатает ---
        # value="..." - значение по умолчанию (сегодняшняя дата в формате дд.мм.гггг)
        self.date = ft.TextField(label="Дата (дд.мм.гггг)", value=datetime.now().strftime("%d.%m.%Y"))
        # on_change - функция, которая вызывается КАЖДЫЙ раз, когда пользователь меняет текст.
        # Мы используем это, чтобы сразу пересчитывать «следующий пробег».
        self.mileage = ft.TextField(label="Пробег, км", keyboard_type=ft.KeyboardType.NUMBER,
                                    on_change=self._update_next)
        self.works = ft.TextField(label="Виды работ", multiline=True, min_lines=2, max_lines=4)
        self.interval = ft.TextField(label="Приехать через, км", value="5000",
                                     keyboard_type=ft.KeyboardType.NUMBER, on_change=self._update_next)
        # Надпись, которая сама обновляется: «Следующее ТО на пробеге: 287406 км»
        self.next_text = ft.Text("Следующее ТО на пробеге: —", weight=ft.FontWeight.BOLD)
        self.price = ft.TextField(label="Цена за обслуживание")

        # --- Галочки: по одной на каждый интервал автомобиля ---
        # data=i прячет внутри галочки сам объект интервала, чтобы потом его достать.
        self.checks = [
            ft.Checkbox(label=f"{i.name} ({i.km} км)", data=i, on_change=self._on_check)
            for i in car.intervals
        ]

        # --- Само окно. AlertDialog = всплывающее окно с заголовком, содержимым и кнопками ---
        self.dialog = ft.AlertDialog(
            modal=True,                      # True - нельзя кликнуть мимо окна, пока оно открыто
            title=ft.Text("Новая запись о ТО"),
            content=ft.Container(
                width=460,
                content=ft.Column(           # Column = элементы друг под другом
                    [self.date, self.mileage,
                     ft.Text("Выполненные работы из интервалов:", size=12),
                     ft.Column(self.checks, spacing=0),
                     self.works, self.interval, self.next_text, self.price],
                    tight=True,              # не растягивать колонку больше нужного
                    scroll=ft.ScrollMode.AUTO,   # если не влезает - появится прокрутка
                    spacing=10,
                ),
            ),
            # actions - кнопки внизу окна
            actions=[ft.TextButton("Отмена", on_click=self._cancel),
                     Button("Сохранить", on_click=self._save)],
        )

    def show(self):
        """Открыть окно."""
        open_dialog(self.app.page, self.dialog)

    def _on_check(self, e):
        """Вызывается, когда пользователь ставит/снимает галочку у работы.
        Автоматически заполняет поля «Виды работ» и «Приехать через»."""
        # Собираем интервалы, у которых галочка стоит (c.value == True)
        chosen = [c.data for c in self.checks if c.value]
        if chosen:
            # Названия соединяем через « + »: «Масло + фильтр + Фильтр салонный»
            self.works.value = " + ".join(i.name for i in chosen)
            # Берём САМЫЙ КОРОТКИЙ интервал, чтобы не пропустить ближайшее ТО
            self.interval.value = str(min(i.km for i in chosen))
        else:
            self.works.value = ""
        self._update_next()

    def _update_next(self, e=None):
        """Пересчитывает надпись «Следующее ТО на пробеге» = пробег + интервал."""
        m = (self.mileage.value or "").strip()
        k = (self.interval.value or "").strip()
        if m.isdigit() and k.isdigit():
            self.next_text.value = f"Следующее ТО на пробеге: {int(m) + int(k)} км"
        else:
            self.next_text.value = "Следующее ТО на пробеге: —"
        # page.update() - важная команда: она перерисовывает окно с новыми значениями.
        # Без неё изменения в коде не появятся на экране.
        self.app.page.update()

    def _cancel(self, e):
        """Кнопка «Отмена»: просто закрываем окно."""
        close_dialog(self.app.page, self.dialog)

    def _save(self, e):
        """Кнопка «Сохранить»: проверяем ввод и добавляем запись."""
        ok = True  # флаг: все ли поля заполнены правильно

        # Проверяем дату: strptime выдаст ошибку ValueError, если формат неверный
        try:
            datetime.strptime(self.date.value.strip(), "%d.%m.%Y")
            self.date.error_text = None
        except ValueError:
            self.date.error_text = "Формат: дд.мм.гггг"
            ok = False

        mileage = parse_int(self.mileage)
        interval = parse_int(self.interval)
        if mileage is None or interval is None:
            ok = False
        if not (self.works.value or "").strip():
            self.works.error_text = "Укажите виды работ"
            ok = False
        else:
            self.works.error_text = None

        if not ok:
            self.app.page.update()   # показать красные подсказки об ошибках
            return                   # и НЕ сохранять

        # Всё верно - создаём запись
        record = ServiceRecord(
            id=uuid.uuid4().hex,
            date=self.date.value.strip(),
            mileage=mileage,
            works=self.works.value.strip(),
            interval_km=interval,
            next_mileage=mileage + interval,
            price=(self.price.value or "").strip(),
            # Запоминаем названия отмеченных галочек - пригодится для таблицы интервалов
            done=[c.data.name for c in self.checks if c.value],
        )
        self.car.records.append(record)   # добавляем в историю автомобиля
        self.app.store.save()             # записываем в файл
        close_dialog(self.app.page, self.dialog)
        self.app.refresh()                # перерисовываем экран, чтобы запись появилась


class IntervalDialog:
    """Окно «Новый интервал»: название работы и через сколько км её делать."""

    def __init__(self, app: "App"):
        self.app = app
        self.name = ft.TextField(label="Название работы")
        self.km = ft.TextField(label="Интервал, км", keyboard_type=ft.KeyboardType.NUMBER)
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Новый интервал"),
            content=ft.Column([self.name, self.km], tight=True, width=360),
            actions=[
                # lambda e: ... - короткая безымянная функция, удобна для простых действий
                ft.TextButton("Отмена", on_click=lambda e: close_dialog(app.page, self.dialog)),
                Button("Добавить", on_click=self._save),
            ],
        )

    def show(self):
        open_dialog(self.app.page, self.dialog)

    def _save(self, e):
        """Проверяем поля и добавляем интервал текущему автомобилю."""
        km = parse_int(self.km)
        if not (self.name.value or "").strip():
            self.name.error_text = "Обязательное поле"
            self.app.page.update()
            return
        self.name.error_text = None
        if km is None:
            self.app.page.update()
            return
        self.app.store.current_car.intervals.append(ServiceInterval(self.name.value.strip(), km))
        self.app.store.save()
        close_dialog(self.app.page, self.dialog)
        self.app.refresh()


class CarPickerDialog:
    """Окно «Мои автомобили». Открывается по клику на кружок в правом верхнем углу."""

    def __init__(self, app: "App"):
        self.app = app
        rows = []   # сюда соберём строки: по одной на каждый автомобиль
        for car in app.store.cars:
            rows.append(ft.Row([   # Row = элементы в одну строку, слева направо
                # Кнопка с названием авто. expand=True - занять всё свободное место.
                # c=car "запоминает" именно этот автомобиль для этой кнопки
                # (без этого все кнопки указывали бы на последний автомобиль).
                ft.TextButton(car.full_title, expand=True, on_click=lambda e, c=car: self._select(c)),
                ft.IconButton(ft.Icons.DELETE, tooltip="Удалить автомобиль",
                              on_click=lambda e, c=car: self._delete(c)),
            ]))
        self.dialog = ft.AlertDialog(
            title=ft.Text("Мои автомобили"),
            content=ft.Column(rows, tight=True, width=420, scroll=ft.ScrollMode.AUTO),
            actions=[Button("Добавить автомобиль", icon=ft.Icons.ADD, on_click=self._add),
                     ft.TextButton("Закрыть", on_click=lambda e: close_dialog(app.page, self.dialog))],
        )

    def show(self):
        open_dialog(self.app.page, self.dialog)

    def _select(self, car: Car):
        """Переключиться на выбранный автомобиль."""
        self.app.store.current_id = car.id
        self.app.store.save()
        close_dialog(self.app.page, self.dialog)
        self.app.render()   # перерисовать весь экран уже для нового автомобиля

    def _delete(self, car: Car):
        """Удалить автомобиль."""
        self.app.store.delete_car(car.id)
        close_dialog(self.app.page, self.dialog)
        self.app.render()

    def _add(self, e):
        """Открыть форму регистрации нового автомобиля."""
        close_dialog(self.app.page, self.dialog)
        self.app.render(registration=True)


# ───────────────────────── 6. ЭКРАНЫ ─────────────────────────
# Каждый экран - отдельный класс. Внутри он собирает свои элементы
# и хранит их в self.control. Главное приложение потом просто
# вставляет этот control на страницу.

class RegistrationView:
    """Экран регистрации автомобиля."""

    def __init__(self, app: "App", cancelable: bool):
        # cancelable=True значит: у нас уже есть автомобили, поэтому
        # можно нажать «Отмена» и вернуться. На самом первом запуске отмены нет.
        self.app = app
        # hint_text - серая подсказка-пример внутри пустого поля
        self.brand = ft.TextField(label="Марка", hint_text="Volkswagen")
        self.model = ft.TextField(label="Модель", hint_text="Golf 5")
        self.year = ft.TextField(label="Год выпуска", hint_text="2007", keyboard_type=ft.KeyboardType.NUMBER)
        self.engine = ft.TextField(label="Двигатель", hint_text="2.0 TDI 140 Л.С")

        buttons = [Button("Зарегистрировать", on_click=self._save)]
        if cancelable:
            # insert(0, ...) - вставить кнопку «Отмена» в начало списка (слева)
            buttons.insert(0, ft.TextButton("Отмена", on_click=lambda e: app.render()))

        # self.control - то, что будет показано на экране
        self.control = ft.Column(
            [ft.Text("Регистрация автомобиля", size=24, weight=ft.FontWeight.BOLD),
             self.brand, self.model, self.year, self.engine,
             ft.Row(buttons, alignment=ft.MainAxisAlignment.END)],
            width=420, spacing=14,
        )

    def _save(self, e):
        """Кнопка «Зарегистрировать»: проверяем, что всё заполнено, и создаём авто."""
        ok = True
        for f in (self.brand, self.model, self.year, self.engine):
            if not (f.value or "").strip():
                f.error_text = "Обязательное поле"
                ok = False
            else:
                f.error_text = None
        if not ok:
            self.app.page.update()
            return
        car = Car.create(self.brand.value.strip(), self.model.value.strip(),
                         self.year.value.strip(), self.engine.value.strip())
        self.app.store.add_car(car)
        self.app.tab = "history"   # после регистрации показываем вкладку «История ТО»
        self.app.render()


class HistoryView:
    """Вкладка «История ТО»: записи в виде карточек-заметок."""

    def __init__(self, app: "App"):
        self.app = app
        # Колонка, в которую мы будем складывать карточки.
        # expand=True - занять всё свободное место, scroll - прокрутка при большом числе записей.
        self.cards = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        self.control = ft.Column(
            [ft.Row([Button("Добавить ТО", icon=ft.Icons.ADD,
                                       on_click=lambda e: RecordDialog(app).show())]),
             self.cards],
            expand=True, spacing=12,
        )

    def refresh(self):
        """Заново заполняет список карточек из данных текущего автомобиля."""
        car = self.app.store.current_car
        self.cards.controls.clear()   # сначала очищаем старые карточки
        if not car.records:
            self.cards.controls.append(ft.Text("Записей о ТО пока нет. Нажмите «Добавить ТО».", italic=True))
            return
        # sorted(..., reverse=True) - сортируем по пробегу от большего к меньшему,
        # поэтому самые свежие записи оказываются сверху
        for r in sorted(car.records, key=lambda x: x.mileage, reverse=True):
            self.cards.controls.append(self._card(car, r))

    def _card(self, car: Car, r: ServiceRecord) -> ft.Card:
        """Собирает ОДНУ карточку для ОДНОЙ записи о ТО."""
        lines = [
            ft.Text(f"Дата {r.date}  ·  Пробег {r.mileage} км", weight=ft.FontWeight.BOLD, size=16),
            ft.Text(f"Виды работ: {r.works}"),
            ft.Text(f"Приехать через {r.interval_km} км  →  на пробеге {r.next_mileage} км"),
        ]
        if r.price:   # строку с ценой добавляем, только если цена указана
            lines.append(ft.Text(f"Цена: {r.price}"))
        return ft.Card(content=ft.Container(
            padding=14,
            content=ft.Row([
                ft.Column(lines, spacing=4, expand=True),   # текст слева
                ft.IconButton(ft.Icons.DELETE, tooltip="Удалить запись",   # корзина справа
                              on_click=lambda e: self._delete(car, r)),
            ], vertical_alignment=ft.CrossAxisAlignment.START),
        ))

    def _delete(self, car: Car, r: ServiceRecord):
        """Удаляет запись: оставляем все записи, кроме той, у которой совпал id."""
        car.records = [x for x in car.records if x.id != r.id]
        self.app.store.save()
        self.app.refresh()


class IntervalsView:
    """Вкладка «Интервалы ТО»: таблица со всеми интервалами автомобиля."""

    def __init__(self, app: "App"):
        self.app = app
        # DataTable - готовая таблица. Здесь задаём только заголовки колонок,
        # а строки (rows) заполним позже в refresh().
        self.table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("Работа")),
                     ft.DataColumn(ft.Text("Интервал, км"), numeric=True),
                     ft.DataColumn(ft.Text("Последний раз, км"), numeric=True),
                     ft.DataColumn(ft.Text("Следующий раз, км"), numeric=True),
                     ft.DataColumn(ft.Text(""))],   # пустой заголовок для колонки с корзинкой
            rows=[],
        )
        self.control = ft.Column(
            [ft.Row([Button("Добавить интервал", icon=ft.Icons.ADD,
                                       on_click=lambda e: IntervalDialog(app).show())]),
             ft.Column([self.table], scroll=ft.ScrollMode.AUTO, expand=True)],
            expand=True, spacing=12,
        )

    def refresh(self):
        """Заново строит строки таблицы из интервалов текущего автомобиля."""
        car = self.app.store.current_car
        rows = []
        for i in car.intervals:
            last = car.last_done(i.name)   # когда эту работу делали в последний раз
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(i.name)),
                ft.DataCell(ft.Text(str(i.km))),
                # Если работу ещё ни разу не делали, показываем прочерк «—»
                ft.DataCell(ft.Text(str(last) if last is not None else "—")),
                # Следующий раз = последний пробег + интервал
                ft.DataCell(ft.Text(str(last + i.km) if last is not None else "—")),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE, tooltip="Удалить",
                                          on_click=lambda e, it=i: self._delete(car, it))),
            ]))
        self.table.rows = rows

    def _delete(self, car: Car, interval: ServiceInterval):
        """Удаляет интервал из списка."""
        car.intervals = [x for x in car.intervals if x is not interval]
        self.app.store.save()
        self.app.refresh()


# ───────────────────────── 7. Главный класс приложения ─────────────────────────
class App:
    """Главный класс. Он ничего не рисует сам, а только
    собирает вместе хранилище, шапку, вкладки и экраны."""

    def __init__(self, page: ft.Page):
        # page - это окно приложения. Во Flet на него "кладут" все элементы.
        self.page = page
        self.store = Storage()       # загружаем сохранённые автомобили
        self.tab = "history"         # какая вкладка открыта: "history" или "intervals"
        self.history = HistoryView(self)     # экран истории ТО
        self.intervals = IntervalsView(self) # экран интервалов

        # Настройки окна
        page.title = "Учёт ТО автомобиля"
        page.padding = 20
        try:
            page.window.width = 1000
            page.window.height = 700
        except AttributeError:
            pass   # в очень старых версиях Flet этих настроек нет - просто пропускаем
        self.render()   # рисуем экран в первый раз

    # --- отрисовка ---
    def render(self, registration: bool = False):
        """Полностью перерисовывает окно.
        Если автомобилей нет (или нас попросили) - показываем регистрацию,
        иначе показываем шапку + выбранную вкладку."""
        self.page.clean()   # удаляем всё, что было на странице
        if registration or not self.store.cars:
            view = RegistrationView(self, cancelable=bool(self.store.cars))
            # Row с выравниванием по центру, чтобы форма была посередине
            self.page.add(ft.Row([view.control], alignment=ft.MainAxisAlignment.CENTER))
        else:
            # Добавляем на страницу: шапка, линия-разделитель, содержимое вкладки
            self.page.add(self._header(), ft.Divider(), self._body())
            self._refresh_active()   # наполняем вкладку актуальными данными
        self.page.update()   # показать результат на экране

    def refresh(self):
        """Короткое имя для «перерисовать всё». Вызываем после любых изменений данных."""
        self.render()

    def _refresh_active(self):
        """Обновляет данные только той вкладки, которая сейчас открыта."""
        (self.history if self.tab == "history" else self.intervals).refresh()

    def _body(self) -> ft.Control:
        """Возвращает содержимое активной вкладки."""
        return (self.history if self.tab == "history" else self.intervals).control

    def _header(self) -> ft.Row:
        """Шапка: слева - вкладки, справа - название автомобиля и кружок."""
        car = self.store.current_car
        # Кружок. CircleAvatar сам по себе не умеет реагировать на клик,
        # поэтому оборачиваем его в Container, у которого есть on_click.
        avatar = ft.Container(
            on_click=lambda e: CarPickerDialog(self).show(),   # клик -> окно выбора авто
            tooltip="Сменить автомобиль",
            content=ft.CircleAvatar(
                radius=22, bgcolor=ft.Colors.BLUE_GREY_200,
                content=ft.Icon(ft.Icons.DIRECTIONS_CAR),
            ),
        )
        return ft.Row(
            [self._tabs(),   # левая часть
             ft.Row([ft.Text(car.title, size=18, weight=ft.FontWeight.BOLD), avatar], spacing=12)],  # правая часть
            # SPACE_BETWEEN: первый элемент прижат влево, второй - вправо
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def _tabs(self) -> ft.Row:
        """Две кнопки-вкладки. Активная вкладка выглядит как заливная кнопка,
        неактивная - как обычный текст."""
        def make(label, key):
            cls = Button if self.tab == key else ft.TextButton
            return cls(label, on_click=lambda e: self._switch(key))
        return ft.Row([make("История ТО", "history"), make("Интервалы ТО", "intervals")])

    def _switch(self, key: str):
        """Переключение вкладки: запоминаем выбор и перерисовываем."""
        self.tab = key
        self.render()


# ───────────────────────── 8. Точка входа ─────────────────────────
def main(page: ft.Page):
    """Flet сам вызывает эту функцию при запуске и передаёт ей окно (page)."""
    App(page)


# Эта проверка означает: «запускать приложение только если файл запущен напрямую»
# (а не импортирован из другого файла).
if __name__ == "__main__":
    # В новых версиях Flet запуск делается через ft.run, в старых - через ft.app
    (ft.run if hasattr(ft, "run") else ft.app)(main)
