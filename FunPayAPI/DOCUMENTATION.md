# 📚 FunPayAPI — Полная документация

> **Версия документации:** 1.2.0 (Sigma 2.15)
> **Язык:** Русский  
> **Проект:** FunPay Sigma

---

## 📋 Оглавление

1. [Введение](#-введение)
2. [Установка и настройка](#-установка-и-настройка)
3. [Структура пакета](#-структура-пакета)
4. [Класс Account](#-класс-account)
   - [Инициализация](#инициализация)
   - [Методы работы с аккаунтом](#методы-работы-с-аккаунтом)
   - [Методы работы с чатами](#методы-работы-с-чатами)
   - [Методы работы с заказами](#методы-работы-с-заказами)
   - [Методы работы с лотами](#методы-работы-с-лотами)
   - [Методы работы с категориями](#методы-работы-с-категориями)
   - [Методы финансов](#методы-финансов)
5. [Типы данных (types)](#-типы-данных-types)
6. [Перечисления (enums)](#-перечисления-enums)
7. [Исключения (exceptions)](#-исключения-exceptions)
8. [Модуль Runner (Updater)](#-модуль-runner-updater)
9. [События (Events)](#-события-events)
10. [Утилиты (utils)](#-утилиты-utils)
11. [Примеры использования](#-примеры-использования)

---

## 🚀 Введение

**FunPayAPI** — это Python-библиотека для взаимодействия с маркетплейсом FunPay. Библиотека предоставляет удобный интерфейс для:

- ✅ Авторизации и управления аккаунтом
- ✅ Отправки и получения сообщений в чатах
- ✅ Управления лотами и категориями
- ✅ Обработки заказов и продаж
- ✅ Получения событий в реальном времени (новые сообщения, заказы и т.д.)
- ✅ Работы с отзывами
- ✅ Вывода средств

---

## ⚙️ Установка и настройка

### Зависимости

```bash
pip install requests beautifulsoup4 lxml
```

### Импорт библиотеки

```python
import FunPayAPI

# Или отдельные модули
from FunPayAPI import Account, Runner, events, types
from FunPayAPI.common import exceptions, enums, utils
```

---

## 📁 Структура пакета

```
FunPayAPI/
├── __init__.py          # Точка входа, экспорт основных классов
├── account.py           # Класс Account — основной класс для работы с API
├── types.py             # Все типы данных (классы-модели)
├── common/
│   ├── __init__.py
│   ├── enums.py         # Перечисления (EventTypes, MessageTypes, etc.)
│   ├── exceptions.py    # Кастомные исключения
│   └── utils.py         # Вспомогательные функции и регулярные выражения
└── updater/
    ├── __init__.py
    ├── runner.py        # Класс Runner для получения событий
    └── events.py        # Классы событий
```

---

## 👤 Класс Account

**Класс `Account`** — основной класс для управления аккаунтом FunPay.

### Инициализация

```python
from FunPayAPI import Account

account = Account(
    golden_key="ваш_golden_key",           # Обязательно: токен аккаунта
    user_agent="ваш_user_agent",           # Опционально: User-Agent браузера
    requests_timeout=10,                    # Опционально: таймаут запросов (сек)
    proxy={"http": "...", "https": "..."},  # Опционально: прокси
    locale="ru"                             # Опционально: локаль ("ru", "en", "uk")
)

# Получение данных аккаунта (ОБЯЗАТЕЛЬНО перед использованием!)
account.get()
```

#### Параметры инициализации

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `golden_key` | `str` | ✅ Да | Токен авторизации (cookie `golden_key`) |
| `user_agent` | `str \| None` | ❌ Нет | User-Agent для запросов |
| `requests_timeout` | `int \| float` | ❌ Нет | Таймаут для HTTP-запросов (по умолчанию: 10) |
| `proxy` | `dict \| None` | ❌ Нет | Словарь с настройками прокси |
| `locale` | `"ru" \| "en" \| "uk" \| None` | ❌ Нет | Локаль интерфейса FunPay |

---

### Методы работы с аккаунтом

#### `get(update_phpsessid: bool = True) -> Account`

Получает / обновляет данные об аккаунте. **Необходимо вызывать каждые 40-60 минут** для обновления `phpsessid`.

```python
account = account.get()

# Атрибуты после инициализации:
print(account.id)           # ID пользователя
print(account.username)     # Никнейм
print(account.currency)     # Валюта аккаунта (Currency enum)
print(account.csrf_token)   # CSRF-токен
print(account.phpsessid)    # PHP Session ID
```

#### `is_initiated() -> bool`

Проверяет, был ли аккаунт инициализирован методом `get()`.

```python
if account.is_initiated:
    print("Аккаунт готов к работе")
```

#### `logout() -> None`

Выход из аккаунта (сброс `golden_key`).

```python
account.logout()
```

#### `locale` (property)

Получение/установка текущей локали.

```python
print(account.locale)  # "ru"
account.locale = "en"
```

---

### Методы работы с чатами

#### `get_chat(chat_id: int, with_history: bool = True) -> types.Chat`

Получает информацию о личном чате.

```python
chat = account.get_chat(123456, with_history=True)
print(chat.name)               # Имя собеседника
print(chat.messages)           # Список последних 100 сообщений
print(chat.looking_link)       # Ссылка "Покупатель смотрит"
```

#### `get_chat_history(chat_id: int | str, ...) -> list[types.Message]`

Получает историю указанного чата (до 100 последних сообщений).

```python
messages = account.get_chat_history(
    chat_id=123456,
    last_message_id=99999999999,  # ID последнего сообщения для пагинации
    interlocutor_username="User", # Имя собеседника (опционально)
    from_id=0                     # Получать сообщения начиная с этого ID
)

for msg in messages:
    print(f"{msg.author}: {msg.text}")
```

#### `get_chats_histories(chats_data: dict) -> dict`

Получает историю сообщений сразу нескольких чатов.

```python
# {chat_id: username или None}
chats_data = {123456: "User1", 789012: None}
histories = account.get_chats_histories(chats_data)

for chat_id, messages in histories.items():
    print(f"Чат {chat_id}: {len(messages)} сообщений")
```

#### `send_message(chat_id, text, ...) -> types.Message`

Отправляет сообщение в чат.

```python
message = account.send_message(
    chat_id=123456,                    # ID чата
    text="Привет!",                    # Текст сообщения (опционально)
    image_id=None,                     # ID изображения (опционально)
    interlocutor_id=None,              # ID собеседника (опционально)
    add_to_ignore_list=True,           # Добавить в список игнора Runner'а
    update_last_saved_message=False,   # Обновить ID последнего сообщения
    leave_as_unread=False              # Оставить непрочитанным
)

print(f"Сообщение отправлено: ID {message.id}")
```

#### `send_image(chat_id, image, ...) -> types.Message`

Отправляет изображение в чат (только для личных чатов).

```python
message = account.send_image(
    chat_id=123456,
    image="path/to/image.png"  # Путь к файлу или IO[bytes]
)
```

#### `upload_image(image, type_="chat") -> int`

Выгружает изображение на сервер FunPay.

```python
image_id = account.upload_image("path/to/image.png", type_="chat")
# type_: "chat" или "offer"
```

#### `request_chats() -> list[types.ChatShortcut]`

Запрашивает список чатов.

```python
chats = account.request_chats()
for chat in chats:
    print(f"{chat.name}: {chat.last_message_text}")
```

#### `add_chats(chats: list[types.ChatShortcut])`

Сохраняет чаты во внутреннее хранилище.

#### `get_chats(update: bool = False) -> dict`

Возвращает словарь сохраненных чатов.

```python
chats = account.get_chats(update=True)  # С обновлением
for chat_id, chat in chats.items():
    print(f"ID: {chat_id}, Имя: {chat.name}")
```

#### `get_chat_by_name(name: str, make_request: bool = False)`

Ищет чат по имени собеседника.

```python
chat = account.get_chat_by_name("Username", make_request=True)
```

#### `get_chat_by_id(chat_id: int, make_request: bool = False)`

Ищет чат по ID.

```python
chat = account.get_chat_by_id(123456)
```

---

### Методы работы с заказами

#### `get_order(order_id: str) -> types.Order`

Получает полную информацию о заказе.

```python
order = account.get_order("ABC12345")

print(order.id)              # ID заказа
print(order.status)          # Статус (OrderStatuses enum)
print(order.buyer_username)  # Имя покупателя
print(order.seller_username) # Имя продавца
print(order.sum)             # Сумма заказа
print(order.currency)        # Валюта
print(order.amount)          # Количество товара
print(order.lot_params)      # Параметры лота [(название, значение), ...]
print(order.buyer_params)    # Параметры покупателя {название: значение}
print(order.review)          # Отзыв (Review или None)
print(order.order_secrets)   # Товары (секреты заказа)
```

#### `get_order_shortcut(order_id: str) -> types.OrderShortcut`

Получает краткую информацию о заказе (только для продаж).

```python
order = account.get_order_shortcut("ABC12345")
print(order.description)
```

#### `get_sales(...) -> tuple[list[types.OrderShortcut], str | None]`

Получает список заказов (продаж).

```python
orders, next_cursor = account.get_sales(
    start_from=None,           # Курсор для пагинации
    include_paid=True,         # Включать оплаченные
    include_closed=True,       # Включать закрытые
    include_refunded=True,     # Включать возвращенные
    include_unpaid=True,       # Включать неоплаченные
    state=None,                # "closed", "paid", "refunded"
    game=None,                 # ID игры
    section=None,              # Секция
    server=None,               # ID сервера
    side=None,                 # Сторона
    locale="ru"
)

for order in orders:
    print(f"#{order.id} - {order.description} - {order.price} {order.currency}")
```

#### `refund(order_id: str) -> None`

Оформляет возврат средств за заказ.

```python
account.refund("ABC12345")
```

---

### Методы работы с отзывами

#### `send_review(order_id: str, text: str, rating: int = 5) -> str`

Отправляет или редактирует отзыв.

```python
html = account.send_review(
    order_id="ABC12345",
    text="Отличный продавец!",
    rating=5  # От 1 до 5 звезд
)
```

#### `delete_review(order_id: str) -> str`

Удаляет отзыв или ответ на отзыв.

```python
account.delete_review("ABC12345")
```

---

### Методы работы с лотами

#### `get_lot_page(lot_id: int) -> types.LotPage | None`

Возвращает страницу лота.

```python
page = account.get_lot_page(12345678)
if page:
    print(page.short_description)
    print(page.full_description)
    print(page.image_urls)
    print(page.seller_username)
```

#### `get_lot_fields(lot_id: int) -> types.LotFields`

Получает все поля лота для редактирования.

```python
fields = account.get_lot_fields(12345678)
fields.edit_fields({"price": "100"})
account.save_lot(fields)
```

#### `get_chip_fields(subcategory_id: int) -> types.ChipFields`

Получает поля лота игровой валюты.

#### `save_offer(offer_fields: LotFields | ChipFields)`

Сохраняет лот на FunPay.

```python
fields = account.get_lot_fields(12345678)
fields.edit_fields({"price": "150", "active": "on"})
account.save_offer(fields)
```

#### `save_lot(lot_fields: types.LotFields)`

Алиас для `save_offer` для стандартных лотов.

#### `save_chip(chip_fields: types.ChipFields)`

Алиас для `save_offer` для лотов валюты.

#### `delete_lot(lot_id: int)`

Удаляет лот.

```python
account.delete_lot(12345678)
```

#### `get_my_subcategory_lots(subcategory_id: int) -> list[types.MyLotShortcut]`

Получает список своих лотов в подкатегории.

```python
lots = account.get_my_subcategory_lots(123)
for lot in lots:
    print(f"Лот #{lot.id}: {lot.description} - {lot.price}")
```

#### `get_subcategory_public_lots(subcategory_type, subcategory_id) -> list[types.LotShortcut]`

Получает список всех публичных лотов в подкатегории.

```python
from FunPayAPI.common.enums import SubCategoryTypes

lots = account.get_subcategory_public_lots(
    SubCategoryTypes.COMMON,
    subcategory_id=123
)
```

#### `raise_lots(category_id, subcategories=None, exclude=None) -> bool`

Поднимает все лоты категории.

```python
account.raise_lots(
    category_id=123,
    subcategories=[456, 789],  # Опционально: конкретные подкатегории
    exclude=[111]              # Опционально: исключить подкатегории
)
```

#### `get_raise_modal(category_id: int) -> dict`

Получает modal-форму для поднятия лотов.

---

### Методы работы с категориями

#### `categories` (property)

Возвращает все категории (игры) FunPay.

```python
for category in account.categories:
    print(f"{category.id}: {category.name}")
```

#### `get_category(category_id: int) -> types.Category | None`

Возвращает категорию по ID.

```python
category = account.get_category(123)
if category:
    print(category.name)
    for sub in category.get_subcategories():
        print(f"  - {sub.name}")
```

#### `get_sorted_categories() -> dict[int, types.Category]`

Возвращает категории в виде словаря `{ID: Category}`.

#### `subcategories` (property)

Возвращает все подкатегории FunPay.

#### `get_subcategory(subcategory_type, subcategory_id) -> types.SubCategory | None`

Возвращает подкатегорию.

```python
from FunPayAPI.common.enums import SubCategoryTypes

subcategory = account.get_subcategory(SubCategoryTypes.COMMON, 123)
```

#### `get_sorted_subcategories() -> dict`

Возвращает подкатегории в виде словаря `{type: {id: SubCategory}}`.

---

### Методы финансов

#### `get_balance(lot_id: int) -> types.Balance`

Получает информацию о балансе.

```python
balance = account.get_balance(12345)
print(f"RUB: {balance.total_rub} (доступно: {balance.available_rub})")
print(f"USD: {balance.total_usd} (доступно: {balance.available_usd})")
print(f"EUR: {balance.total_eur} (доступно: {balance.available_eur})")
```

#### `withdraw(currency, wallet, amount, address) -> float`

Выводит средства с аккаунта.

```python
from FunPayAPI.common.enums import Currency, Wallet

result = account.withdraw(
    currency=Currency.RUB,
    wallet=Wallet.CARD_RUB,
    amount=1000,
    address="1234567890123456"  # Номер карты
)
print(f"Выведено: {result}")
```

#### `get_exchange_rate(currency: Currency) -> tuple[float, Currency]`

Получает курс обмена валют.

```python
from FunPayAPI.common.enums import Currency

rate, account_currency = account.get_exchange_rate(Currency.USD)
print(f"Курс USD: {rate}")
```

#### `calc(subcategory_type, subcategory_id, ...) -> types.CalcResult`

Рассчитывает комиссию раздела.

```python
result = account.calc(
    subcategory_type=SubCategoryTypes.COMMON,
    subcategory_id=123,
    price=1000
)
print(f"Комиссия: {result.commission_percent}%")
```

---

### Методы работы с пользователями

#### `get_user(user_id: int) -> types.UserProfile`

Парсит страницу пользователя.

```python
user = account.get_user(12345)
print(user.username)
print(user.online)
print(user.banned)
print(user.profile_photo)

# Лоты пользователя
for lot in user.get_lots():
    print(f"  {lot.description}: {lot.price}")
```

---

## 📦 Типы данных (types)

### ChatShortcut

Виджет чата со страницы чатов.

```python
class ChatShortcut:
    id: int                    # ID чата
    name: str                  # Имя собеседника
    last_message_text: str     # Текст последнего сообщения
    node_msg_id: int           # ID сообщения (node)
    user_msg_id: int           # ID сообщения (user)
    unread: bool               # Есть непрочитанные?
    html: str                  # HTML код
    last_message_type: MessageTypes  # Тип последнего сообщения
```

### Chat

Личный чат.

```python
class Chat:
    id: int                    # ID чата
    name: str                  # Имя собеседника
    looking_link: str | None   # Ссылка "Покупатель смотрит"
    looking_text: str | None   # Текст "Покупатель смотрит"
    html: str                  # HTML код
    messages: list[Message]    # Последние 100 сообщений
```

### Message

Отдельное сообщение.

```python
class Message:
    id: int                    # ID сообщения
    text: str | None           # Текст сообщения
    chat_id: int | str         # ID чата
    chat_name: str | None      # Название чата
    interlocutor_id: int | None  # ID собеседника
    author: str | None         # Автор сообщения
    author_id: int             # ID автора
    html: str                  # HTML код
    image_link: str | None     # Ссылка на изображение
    image_name: str | None     # Имя изображения
    type: MessageTypes         # Тип сообщения
    badge_text: str | None     # Текст бейджа
```

### OrderShortcut

Краткая информация о заказе.

```python
class OrderShortcut:
    id: str                    # ID заказа
    description: str           # Описание
    price: float               # Цена
    currency: Currency         # Валюта
    buyer_username: str        # Имя покупателя
    buyer_id: int              # ID покупателя
    chat_id: int | str         # ID чата
    status: OrderStatuses      # Статус заказа
    date: datetime             # Дата заказа
    subcategory_name: str      # Название подкатегории
    subcategory: SubCategory | None
    html: str
```

### Order

Полная информация о заказе.

```python
class Order:
    id: str                    # ID заказа
    status: OrderStatuses      # Статус заказа
    subcategory: SubCategory | None
    lot_params: list[tuple[str, str]]  # Параметры лота
    buyer_params: dict[str, str]       # Параметры покупателя
    short_description: str | None
    full_description: str | None
    amount: int                # Количество
    sum: float                 # Сумма
    currency: Currency         # Валюта
    buyer_id: int
    buyer_username: str
    seller_id: int
    seller_username: str
    chat_id: str | int
    html: str
    review: Review | None      # Отзыв
    order_secrets: list[str]   # Товары (секреты)
```

### Category

Категория (игра).

```python
class Category:
    id: int                    # ID категории
    name: str                  # Название
    position: int              # Позиция в списке
    
    # Методы:
    add_subcategory(subcategory)
    get_subcategory(type, id) -> SubCategory | None
    get_subcategories() -> list[SubCategory]
    get_sorted_subcategories() -> dict
```

### SubCategory

Подкатегория.

```python
class SubCategory:
    id: int                    # ID подкатегории
    name: str                  # Название
    type: SubCategoryTypes     # Тип (COMMON или CURRENCY)
    category: Category         # Родительская категория
    position: int              # Позиция
    public_link: str           # Публичная ссылка
    private_link: str          # Приватная ссылка (для редактирования)
```

### LotShortcut

Виджет лота.

```python
class LotShortcut:
    id: int | str              # ID лота
    server: str | None         # Сервер
    side: str | None           # Сторона
    description: str | None    # Описание
    amount: int | None         # Количество
    price: float               # Цена
    currency: Currency         # Валюта
    subcategory: SubCategory | None
    seller: SellerShortcut | None
    auto: bool                 # Автовыдача
    promo: bool | None         # Промо
    attributes: dict | None    # Атрибуты
    html: str
    public_link: str           # Ссылка на лот
```

### MyLotShortcut

Виджет своего лота (со страницы редактирования).

```python
class MyLotShortcut:
    id: int | str
    server: str | None
    side: str | None
    description: str | None
    amount: int | None
    price: float
    currency: Currency
    subcategory: SubCategory | None
    auto: bool                 # Автовыдача
    active: bool               # Активен ли лот
    html: str
    public_link: str
```

### LotFields

Поля лота для редактирования.

```python
class LotFields:
    lot_id: int               # ID лота
    subcategory: SubCategory | None
    currency: Currency
    
    # Свойства для редактирования:
    active: bool              # Активен
    description: str          # Описание
    price: str                # Цена
    amount: str               # Количество
    secrets: str              # Товары (автовыдача)
    images: list[int]         # ID изображений
    
    # Методы:
    fields() -> dict          # Получить все поля
    edit_fields(fields: dict) # Редактировать поля
    set_fields(fields: dict)  # Установить все поля
    renew_fields() -> LotFields
```

### LotPage

Страница лота.

```python
class LotPage:
    lot_id: int
    subcategory: SubCategory | None
    short_description: str | None
    full_description: str | None
    image_urls: list[str]
    seller_id: int
    seller_username: str
    seller_url: str            # (property)
```

### UserProfile

Профиль пользователя.

```python
class UserProfile:
    id: int
    username: str
    profile_photo: str
    online: bool
    banned: bool
    html: str
    
    # Методы:
    get_lot(lot_id) -> LotShortcut | None
    get_lots() -> list[LotShortcut]
    get_sorted_lots(mode) -> dict
    update_lot(lot)
    add_lot(lot)
    get_common_lots() -> list[LotShortcut]
    get_currency_lots() -> list[LotShortcut]
```

### Review

Отзыв на заказ.

```python
class Review:
    stars: int | None         # Количество звезд
    text: str | None          # Текст отзыва
    reply: str | None         # Ответ на отзыв
    anonymous: bool           # Анонимный отзыв
    hidden: bool              # Скрытый отзыв
    html: str
    order_id: str | None
    author: str | None
    author_id: int | None
    by_bot: bool              # Оставлен ботом
    reply_by_bot: bool        # Ответ оставлен ботом
```

### Balance

Информация о балансе.

```python
class Balance:
    total_rub: float          # Общий баланс в рублях
    available_rub: float      # Доступный баланс в рублях
    total_usd: float          # Общий баланс в долларах
    available_usd: float      # Доступный баланс в долларах
    total_eur: float          # Общий баланс в евро
    available_eur: float      # Доступный баланс в евро
```

### SellerShortcut

Краткая информация о продавце.

```python
class SellerShortcut:
    id: int
    username: str
    online: bool
    stars: int | None
    reviews: int
    html: str
    link: str                 # (property) Ссылка на профиль
```

### BuyerViewing

Информация "Покупатель смотрит".

```python
class BuyerViewing:
    buyer_id: int
    link: str | None          # Ссылка на лот
    text: str | None          # Текстовое описание
    tag: str | None           # Тег события
    html: str | None
```

### PaymentMethod

Платежный метод.

```python
class PaymentMethod:
    name: str | None
    price: float              # Цена с комиссией
    currency: Currency
    position: int | None
```

### CalcResult

Результат расчета комиссии.

```python
class CalcResult:
    subcategory_type: SubCategoryTypes
    subcategory_id: int
    methods: list[PaymentMethod]
    price: float
    min_price_with_commission: float | None
    min_price_currency: Currency
    account_currency: Currency
    
    # Методы:
    get_coefficient(currency) -> float
    commission_coefficient() -> float   # (property)
    commission_percent() -> float       # (property)
```

---

## 🔢 Перечисления (enums)

### EventTypes

Типы событий Runner'а.

```python
class EventTypes(Enum):
    INITIAL_CHAT = 0          # Чат обнаружен при первом запросе
    CHATS_LIST_CHANGED = 1    # Список чатов изменился
    LAST_CHAT_MESSAGE_CHANGED = 2  # Последнее сообщение изменилось
    NEW_MESSAGE = 3           # Новое сообщение
    INITIAL_ORDER = 4         # Заказ обнаружен при первом запросе
    ORDERS_LIST_CHANGED = 5   # Список заказов изменился
    NEW_ORDER = 6             # Новый заказ
    ORDER_STATUS_CHANGED = 7  # Статус заказа изменился
```

### MessageTypes

Типы сообщений.

```python
class MessageTypes(Enum):
    NON_SYSTEM = 0            # Обычное сообщение
    ORDER_PURCHASED = 1       # Покупатель оплатил заказ
    ORDER_CONFIRMED = 2       # Покупатель подтвердил выполнение
    NEW_FEEDBACK = 3          # Новый отзыв
    FEEDBACK_CHANGED = 4      # Отзыв изменен
    FEEDBACK_DELETED = 5      # Отзыв удален
    NEW_FEEDBACK_ANSWER = 6   # Новый ответ на отзыв
    FEEDBACK_ANSWER_CHANGED = 7   # Ответ изменен
    FEEDBACK_ANSWER_DELETED = 8   # Ответ удален
    ORDER_REOPENED = 9        # Заказ открыт повторно
    REFUND = 10               # Возврат средств
    PARTIAL_REFUND = 11       # Частичный возврат
    ORDER_CONFIRMED_BY_ADMIN = 12  # Подтвержден администратором
    DISCORD = 13              # Discord ссылка
    DEAR_VENDORS = 14         # Предупреждение продавцам
    REFUND_BY_ADMIN = 15      # Возврат администратором
```

### OrderStatuses

Статусы заказов.

```python
class OrderStatuses(Enum):
    PAID = 0                  # Оплачен
    CLOSED = 1                # Закрыт
    REFUNDED = 2              # Возврат
```

### SubCategoryTypes

Типы подкатегорий.

```python
class SubCategoryTypes(Enum):
    COMMON = 0                # Стандартные лоты
    CURRENCY = 1              # Игровая валюта (нельзя поднимать)
```

### Currency

Валюты баланса.

```python
class Currency(Enum):
    USD = 0                   # Доллар ($)
    RUB = 1                   # Рубль (₽)
    EUR = 2                   # Евро (€)
    UNKNOWN = 3               # Неизвестная валюта (¤)
    
    # Методы:
    __str__() -> str          # Символ валюты
    code() -> str             # Код валюты ("usd", "rub", "eur")
```

### Wallet

Кошельки для вывода.

```python
class Wallet(Enum):
    QIWI = 0                  # Qiwi кошелек
    BINANCE = 1               # Binance Pay
    TRC = 2                   # USDT TRC20
    CARD_RUB = 3              # Рублевая карта
    CARD_USD = 4              # Долларовая карта
    CARD_EUR = 5              # Евро карта
    WEBMONEY = 6              # WebMoney WMZ
    YOUMONEY = 7              # ЮMoney
```

---

## ⚠️ Исключения (exceptions)

### AccountNotInitiatedError

Аккаунт не инициализирован методом `get()`.

```python
try:
    account.send_message(123, "test")
except exceptions.AccountNotInitiatedError:
    print("Сначала вызовите account.get()!")
```

### RequestFailedError

Статус код ответа != 200.

```python
class RequestFailedError(Exception):
    status_code: int          # Код статуса
    url: str                  # URL запроса
    response_text: str        # Текст ответа
    request_headers: dict     # Заголовки запроса
    request_body: Any         # Тело запроса
```

### UnauthorizedError

Ошибка авторизации (невалидный `golden_key`).

### MessageNotDeliveredError

Ошибка отправки сообщения.

```python
class MessageNotDeliveredError(RequestFailedError):
    error_message: str | None  # Сообщение об ошибке
    chat_id: int              # ID чата
```

### ImageUploadError

Ошибка загрузки изображения.

### RaiseError

Ошибка при поднятии лотов.

```python
class RaiseError(RequestFailedError):
    category: types.Category   # Категория
    error_message: str | None  # Сообщение об ошибке
    wait_time: int | None      # Время ожидания (секунды)
```

### WithdrawError

Ошибка вывода средств.

### FeedbackEditingError

Ошибка при работе с отзывами.

### LotParsingError

Ошибка парсинга лота.

### LotSavingError

Ошибка сохранения лота.

```python
class LotSavingError(RequestFailedError):
    error_message: str | None
    lot_id: int
    errors: dict[str, str]    # Ошибки по полям
```

### RefundError

Ошибка возврата средств.

---

## 🔄 Модуль Runner (Updater)

**Runner** — класс для получения новых событий FunPay в реальном времени.

### Инициализация

```python
from FunPayAPI import Account, Runner

account = Account("golden_key").get()
runner = Runner(
    account=account,
    disable_message_requests=False,   # Отключить запросы о сообщениях
    disabled_order_requests=False     # Отключить запросы о заказах
)
```

### Методы

#### `listen(requests_delay=6.0, ignore_exceptions=True) -> Generator`

Бесконечно получает события.

```python
for event in runner.listen(requests_delay=6.0):
    if isinstance(event, events.NewMessageEvent):
        print(f"Новое сообщение: {event.message.text}")
    elif isinstance(event, events.NewOrderEvent):
        print(f"Новый заказ: #{event.order.id}")
```

#### `get_updates() -> dict`

Делает один запрос на получение обновлений.

#### `parse_updates(updates: dict) -> list[Event]`

Парсит ответ и создает события.

```python
updates = runner.get_updates()
events_list = runner.parse_updates(updates)
```

#### `update_last_message(chat_id, message_id, message_text)`

Обновляет сохраненный ID последнего сообщения чата.

#### `mark_as_by_bot(chat_id, message_id)`

Помечает сообщение как отправленное ботом.

---

## 📡 События (Events)

Все события наследуются от `BaseEvent`:

```python
class BaseEvent:
    runner_tag: str           # Тег Runner'а
    type: EventTypes          # Тип события
    time: float               # Время события
```

### InitialChatEvent

Чат обнаружен при первом запросе Runner'а.

```python
class InitialChatEvent(BaseEvent):
    chat: types.ChatShortcut
```

### ChatsListChangedEvent

Список чатов изменился.

```python
class ChatsListChangedEvent(BaseEvent):
    pass  # TODO: добавить список чатов
```

### LastChatMessageChangedEvent

Последнее сообщение в чате изменилось.

```python
class LastChatMessageChangedEvent(BaseEvent):
    chat: types.ChatShortcut
```

### NewMessageEvent

Новое сообщение в истории чата.

```python
class NewMessageEvent(BaseEvent):
    message: types.Message
    stack: MessageEventsStack  # Стек событий
```

### MessageEventsStack

Стек событий новых сообщений от одного пользователя.

```python
class MessageEventsStack:
    def add_events(self, messages: list[NewMessageEvent])
    def get_stack(self) -> list[NewMessageEvent]
    def id(self) -> str
```

### InitialOrderEvent

Заказ обнаружен при первом запросе Runner'а.

```python
class InitialOrderEvent(BaseEvent):
    order: types.OrderShortcut
```

### OrdersListChangedEvent

Список заказов изменился.

```python
class OrdersListChangedEvent(BaseEvent):
    purchases: int            # Незавершенные покупки
    sales: int                # Незавершенные продажи
```

### NewOrderEvent

Новый заказ.

```python
class NewOrderEvent(BaseEvent):
    order: types.OrderShortcut
```

### OrderStatusChangedEvent

Статус заказа изменился.

```python
class OrderStatusChangedEvent(BaseEvent):
    order: types.OrderShortcut
```

---

## 🛠️ Утилиты (utils)

### RegularExpressions (Singleton)

Класс с регулярными выражениями для парсинга системных сообщений.

```python
from FunPayAPI.common.utils import RegularExpressions

regex = RegularExpressions()

# Примеры регулярных выражений:
regex.ORDER_PURCHASED       # Заказ оплачен
regex.ORDER_CONFIRMED       # Заказ подтвержден
regex.NEW_FEEDBACK          # Новый отзыв
regex.FEEDBACK_CHANGED      # Отзыв изменен
regex.REFUND                # Возврат средств
regex.DISCORD               # Discord ссылка
# ... и другие
```

### Функции

#### `random_tag() -> str`

Генерирует случайный тег для запроса.

```python
from FunPayAPI.common.utils import random_tag
tag = random_tag()  # Например: "xK7mP9qR"
```

#### `parse_wait_time(response: str) -> int`

Парсит время ожидания до следующего поднятия лотов.

```python
wait_seconds = parse_wait_time(response_text)
```

#### `parse_currency(s: str) -> Currency`

Парсит символ валюты в enum.

```python
from FunPayAPI.common.utils import parse_currency
currency = parse_currency("₽")  # Currency.RUB
```

### Константа MONTHS

Словарь для парсинга названий месяцев:

```python
from FunPayAPI.common.utils import MONTHS
# {"января": 1, "февраля": 2, ..., "January": 1, "February": 2, ...}
```

---

## 💡 Примеры использования

### Простой бот-автоответчик

```python
from FunPayAPI import Account, Runner, events

# Инициализация
account = Account("your_golden_key").get()
runner = Runner(account)

print(f"Бот запущен как {account.username}")

# Обработка событий
for event in runner.listen(requests_delay=6.0):
    if isinstance(event, events.NewMessageEvent):
        msg = event.message
        
        # Игнорируем свои сообщения
        if msg.author_id == account.id:
            continue
        
        # Отвечаем на приветствие
        if "привет" in msg.text.lower():
            account.send_message(
                chat_id=msg.chat_id,
                text=f"Привет, {msg.author}! Чем могу помочь?"
            )
```

### Автовыдача товара

```python
from FunPayAPI import Account, Runner, events
from FunPayAPI.common.enums import MessageTypes

account = Account("your_golden_key").get()
runner = Runner(account)

for event in runner.listen():
    if isinstance(event, events.NewMessageEvent):
        msg = event.message
        
        # Проверяем, что это сообщение о покупке
        if msg.type == MessageTypes.ORDER_PURCHASED:
            # Извлекаем ID заказа из текста
            # Текст: "Покупатель X оплатил заказ #ABC12345..."
            order_id = extract_order_id(msg.text)  # ваша функция
            
            # Получаем заказ
            order = account.get_order(order_id)
            
            # Отправляем товар
            if order.order_secrets:
                secrets = "\n".join(order.order_secrets)
                account.send_message(
                    chat_id=msg.chat_id,
                    text=f"Ваш товар:\n{secrets}\n\nСпасибо за покупку!"
                )
```

### Мониторинг продаж

```python
from FunPayAPI import Account, Runner, events

account = Account("your_golden_key").get()
runner = Runner(account)

for event in runner.listen():
    if isinstance(event, events.NewOrderEvent):
        order = event.order
        print(f"[НОВЫЙ ЗАКАЗ] #{order.id}")
        print(f"  Покупатель: {order.buyer_username}")
        print(f"  Товар: {order.description}")
        print(f"  Сумма: {order.price} {order.currency}")
        
    elif isinstance(event, events.OrderStatusChangedEvent):
        order = event.order
        print(f"[СТАТУС ИЗМЕНЕН] #{order.id} -> {order.status.name}")
```

### Поднятие лотов по расписанию

```python
import time
from FunPayAPI import Account
from FunPayAPI.common.exceptions import RaiseError

account = Account("your_golden_key").get()

# Поднимаем лоты каждые 4 часа
while True:
    for category in account.categories:
        try:
            account.raise_lots(category.id)
            print(f"✅ Лоты категории '{category.name}' подняты")
        except RaiseError as e:
            print(f"⏳ {category.name}: нужно подождать {e.wait_time} сек")
        
        time.sleep(1)  # Пауза между категориями
    
    time.sleep(4 * 60 * 60)  # Ждем 4 часа
```

### Редактирование лота

```python
from FunPayAPI import Account

account = Account("your_golden_key").get()

# Получаем поля лота
fields = account.get_lot_fields(12345678)

# Редактируем
fields.active = True           # Активировать лот
fields.price = "150"           # Новая цена
fields.description = "Новое описание лота"
fields.secrets = "secret1\nsecret2\nsecret3"  # Товары

# Сохраняем
fields.renew_fields()  # Обновляем внутренний словарь полей
account.save_lot(fields)

print("Лот обновлен!")
```

---

## 📝 Заметки

### Панель Telegram и обновлённые сценарии Sigma

При включённом Telegram-боте доступны операционные команды:

```text
/dashboard       сводный статус Sigma и FunPay
/sales           последние продажи и ссылки на заказы
/lot_health      состояние лотов и покрытия автовыдачей
/notification_digest  состояние уведомлений и очередей
```

Для каждого сценария есть короткие алиасы: `/status`, `/orders`, `/lot_status`
и `/digest`. Эти команды используют кэш профиля, а обновление лотов и продаж
выполняется только по явному действию пользователя. Новая Telegram-кнопка
копирования ID заказа использует `copy_text`, если его поддерживает установленная
версия `pytelegrambotapi`; иначе применяется безопасный callback-alert.

Новые callback-значения используют namespace `sigma.*` и не меняют старые
числовые значения, поэтому сохранённые клавиатуры и плагины Cardinal остаются
совместимыми.

### Важные моменты

1. **Обязательно вызывайте `account.get()`** перед использованием любых методов Account.

2. **Обновляйте сессию каждые 40-60 минут** — вызывайте `account.get()` периодически для обновления `phpsessid`.

3. **Не делайте слишком частые запросы** — используйте задержки между запросами (рекомендуется 5-10 секунд).

4. **Обрабатывайте исключения** — FunPay может возвращать ошибки при высокой нагрузке.

5. **Используйте прокси** при необходимости для обхода блокировок.

### Где взять golden_key?

1. Авторизуйтесь на FunPay
2. Откройте DevTools (F12)
3. Перейдите во вкладку "Application" → "Cookies"
4. Найдите cookie `golden_key`

---

## 📄 Лицензия

Данная библиотека распространяется как часть проекта FunPay Sigma.

---

*Документация создана для FunPay Sigma*
