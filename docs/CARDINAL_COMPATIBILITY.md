# Совместимость с FunPay Cardinal

FunPay Sigma 2.15 синхронизирует публичный `FunPayAPI` и плагинный контракт с
FunPay Cardinal 0.1.17.8. Обычный плагин Cardinal можно положить в `plugins/`
без изменения его импортов и метаданных.

## Импорты

Поддерживаются оба варианта:

```python
from cardinal import Cardinal, PluginData, get_cardinal
from FunPayAPI import Account, Runner, events, exceptions, types
```

Модуль `cardinal` реэкспортирует публичное пространство `sigma`, поэтому
сохраняются и менее распространённые импорты объектов из `cardinal`.

## Метаданные и хуки

Обязательные поля плагина совпадают с Cardinal:

```python
NAME = "Example"
VERSION = "1.0.0"
DESCRIPTION = "Example plugin"
CREDITS = "author"
SETTINGS_PAGE = False
UUID = "2f1b8f3b-12c6-4b7f-9c3f-0a8e0d4a6f10"
BIND_TO_DELETE = None
```

Поддерживаются все хуки Cardinal: lifecycle, сообщения, заказы, автовыдача и
поднятие лотов. Объект третьего аргумента `BIND_TO_POST_LOTS_RAISE` является
строкой, как в Cardinal, и дополнительно поддерживает Sigma-доступ
`result.get("wait_time")` и `result["last_interval"]`.

`PluginData` содержит совместимые поля `enabled`, `pinned`, `commands` и
`delete_handler`. Методы `toggle_plugin()`, `pin_plugin()` и
`add_telegram_commands()` повторяют контракт Cardinal.

Sigma дополнительно понимает необязательные поля:

```python
MIN_VERSION = "2.13.0"
DEPENDS_ON = ["uuid-другого-плагина"]
```

## Обновлённый API

В API перенесены очередь запросов Runner, `runner_request()`,
`get_payload_data()`, `abuse_runner()`, массовое получение истории чатов,
методы просмотра покупателем, пакетное получение заказов, новый cookie-кэш и
очистка zero-width суффикса сообщений.

Sigma сохраняет собственные расширения `get_all_my_lots()` и
`get_create_lot_fields()`, необходимые редактору лотов Telegram-панели.

Из Cardinal также перенесён отдельный `[Telegram] proxy`: он применяется к
`telebot.apihelper.proxy` до создания бота, настраивается при первом запуске,
через отдельный CLI и из Telegram-панели Sigma.

Плагин выполняется с правами процесса Sigma и получает доступ к аккаунту,
конфигам и файловой системе. Устанавливайте только проверенный код.
