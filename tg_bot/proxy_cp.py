from __future__ import annotations

import time
from typing import TYPE_CHECKING
from tg_bot import utils, static_keyboards as skb, keyboards as kb, CBT
import telebot.apihelper
from Utils.cardinal_tools import build_proxy, validate_proxy, cache_proxy_dict, check_proxy
from Utils.telegram_proxy import (check_telegram_proxy, mask_telegram_proxy,
                                  normalize_telegram_proxy)
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B

if TYPE_CHECKING:
    from sigma import Cardinal
from tg_bot import keyboards as kb, CBT
from telebot.types import CallbackQuery, Message
import logging
from threading import Thread
from locales.localizer import Localizer

logger = logging.getLogger("TGBot")
localizer = Localizer()
_ = localizer.translate

def init_proxy_cp(crd: Cardinal, *args):
    tg = crd.telegram
    bot = tg.bot
    pr_dict = {}

    def check_one_proxy(proxy: str):
        try:
            proxy_url = build_proxy(*validate_proxy(proxy))
            d = {"http": proxy_url, "https": proxy_url}
            pr_dict[proxy] = check_proxy(d)
        except:
            pass

    def check_proxies():
        time.sleep(60)
        while True:
            if crd.MAIN_CFG["Proxy"].getboolean("enable") and crd.MAIN_CFG["Proxy"].getboolean("check"):
                for proxy in crd.proxy_dict.values():
                    check_one_proxy(proxy)
                time.sleep(3600)
            else:
                time.sleep(60)

    Thread(target=check_proxies, daemon=True).start()

    if not crd.MAIN_CFG["Proxy"].get("type"):
        crd.MAIN_CFG["Proxy"]["type"] = "HTTP"
        crd.save_config(crd.MAIN_CFG, "configs/_main.cfg")

    def open_proxy_list(c: CallbackQuery):

        offset = int(c.data.split(":")[1])
        text = f'\n\nПрокси: {"вкл." if crd.MAIN_CFG["Proxy"].getboolean("enable") else "выкл."}\n'               f'Проверка прокси: {"вкл." if crd.MAIN_CFG["Proxy"].getboolean("check") else "выкл."}\n'               f'Тип прокси: {crd.MAIN_CFG["Proxy"]["type"]}\n\n'               f'⚠️ <b>Изменения вступят в силу только после перезапуска бота (/restart)!</b>'
        try:
            bot.edit_message_text(f'{_("desc_proxy")}{text}', c.message.chat.id, c.message.id,
                                  reply_markup=kb.proxy(crd, offset, pr_dict))
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                logger.debug("TRACEBACK", exc_info=True)

    def act_add_proxy(c: CallbackQuery):

        offset = int(c.data.split(":")[-1])
        result = bot.send_message(c.message.chat.id, _("act_proxy"), reply_markup=skb.CLEAR_STATE_BTN())
        crd.telegram.set_state(result.chat.id, result.id, c.from_user.id, CBT.ADD_PROXY, {"offset": offset})
        bot.answer_callback_query(c.id)

    def add_proxy(m: Message):

        offset = tg.get_state(m.chat.id, m.from_user.id)["data"]["offset"]
        kb = K().add(B(_("gl_back"), callback_data=f"{CBT.PROXY}:{offset}"))
        tg.clear_state(m.chat.id, m.from_user.id, True)
        proxy = m.text
        try:
            scheme, login, password, ip, port = validate_proxy(proxy)
            if "://" not in proxy:
                scheme = "socks5" if crd.MAIN_CFG["Proxy"]["type"] == "SOCKS5" else "http"
            proxy_str = build_proxy(scheme, login, password, ip, port)
            if proxy_str in crd.proxy_dict.values():
                bot.send_message(m.chat.id, _("proxy_already_exists").format(utils.escape(proxy_str)), reply_markup=kb)
                return
            max_id = max(crd.proxy_dict.keys(), default=-1)
            crd.proxy_dict[max_id + 1] = proxy_str
            cache_proxy_dict(crd.proxy_dict)
            bot.send_message(m.chat.id, _("proxy_added").format(utils.escape(proxy_str)), reply_markup=kb)
            Thread(target=check_one_proxy, args=(proxy_str,), daemon=True).start()
        except ValueError:
            bot.send_message(m.chat.id, _("proxy_format"), reply_markup=kb)
        except:
            bot.send_message(m.chat.id, _("proxy_adding_error"), reply_markup=kb)
            logger.debug("TRACEBACK", exc_info=True)

    def choose_proxy(c: CallbackQuery):

        q, offset, proxy_id = c.data.split(":")
        offset = int(offset)
        proxy_id = int(proxy_id)
        proxy = crd.proxy_dict.get(proxy_id)
        c.data = f"{CBT.PROXY}:{offset}"
        if not proxy:
            open_proxy_list(c)
            return

        scheme, login, password, ip, port = validate_proxy(proxy)

        crd.MAIN_CFG["Proxy"].update({
            "ip": ip,
            "port": port,
            "login": login,
            "password": password,
            "type": "SOCKS5" if scheme.startswith("socks5") else "HTTP",
        })
        crd.save_config(crd.MAIN_CFG, "configs/_main.cfg")

        bot.answer_callback_query(c.id, "✅ Настройки сохранены. Перезапустите бота для применения изменений.", show_alert=True)
        open_proxy_list(c)

    def delete_proxy(c: CallbackQuery):

        q, offset, proxy_id = c.data.split(":")
        offset = int(offset)
        proxy_id = int(proxy_id)
        c.data = f"{CBT.PROXY}:{offset}"
        if proxy_id in crd.proxy_dict.keys():
            proxy = crd.proxy_dict[proxy_id]
            scheme, login, password, ip, port = validate_proxy(proxy)
            now_proxy = crd.account.proxy
            if not now_proxy or proxy not in now_proxy.values():
                del crd.proxy_dict[proxy_id]
                cache_proxy_dict(crd.proxy_dict)
                if proxy in pr_dict:
                    del pr_dict[proxy]
                logger.info(f"Прокси {proxy} удалены.")
                if str(crd.MAIN_CFG["Proxy"]["ip"]) == str(ip) and str(crd.MAIN_CFG["Proxy"]["login"]) == str(login)                        and str(crd.MAIN_CFG["Proxy"]["port"]) == str(port)                        and str(crd.MAIN_CFG["Proxy"]["password"]) == str(password):
                    for i in ("password", "port", "login", "ip"):
                        crd.MAIN_CFG["Proxy"][i] = ""
                    crd.save_config(crd.MAIN_CFG, "configs/_main.cfg")
            else:
                bot.answer_callback_query(c.id, _("proxy_undeletable"), show_alert=True)
                return

        open_proxy_list(c)

    def change_proxy_type(c: CallbackQuery):

        offset = int(c.data.split(":")[1])
        current_type = crd.MAIN_CFG["Proxy"]["type"]

        new_type = "SOCKS5" if current_type != "SOCKS5" else "HTTP"
        crd.MAIN_CFG["Proxy"]["type"] = new_type
        crd.save_config(crd.MAIN_CFG, "configs/_main.cfg")
        logger.info(f"Тип прокси изменен на {new_type}.")
        open_proxy_list(c)

    def telegram_proxy_keyboard() -> K:
        telegram_proxy = crd.MAIN_CFG["Telegram"].get("proxy", "")
        keyboard = K().row(
            B(_("tg_proxy_set"), callback_data=CBT.TELEGRAM_PROXY_SET),
            B(_("tg_proxy_test"), callback_data=CBT.TELEGRAM_PROXY_TEST),
        )
        if telegram_proxy:
            keyboard.add(B(_("tg_proxy_disable"), callback_data=CBT.TELEGRAM_PROXY_DISABLE))
        keyboard.add(B(_("gl_back"), callback_data=CBT.MAIN3))
        return keyboard

    def telegram_proxy_text() -> str:
        telegram_proxy = crd.MAIN_CFG["Telegram"].get("proxy", "")
        try:
            proxy_text = mask_telegram_proxy(telegram_proxy)
        except ValueError:
            proxy_text = _("tg_proxy_invalid_config")
        status = _("tg_proxy_enabled") if telegram_proxy else _("tg_proxy_direct")
        return _("tg_proxy_info", status, proxy_text)

    def render_telegram_proxy(chat_id: int, message_id: int | None = None):
        if message_id is None:
            bot.send_message(chat_id, telegram_proxy_text(), reply_markup=telegram_proxy_keyboard())
            return
        try:
            bot.edit_message_text(telegram_proxy_text(), chat_id, message_id,
                                  reply_markup=telegram_proxy_keyboard())
        except telebot.apihelper.ApiTelegramException as error:
            if "message is not modified" not in str(error):
                raise

    def open_telegram_proxy(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        render_telegram_proxy(c.message.chat.id, c.message.id)

    def cmd_telegram_proxy(m: Message):
        render_telegram_proxy(m.chat.id)

    def act_set_telegram_proxy(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        prompt = bot.send_message(c.message.chat.id, _("tg_proxy_enter"), reply_markup=skb.CLEAR_STATE_BTN())
        tg.set_state(c.message.chat.id, prompt.id, c.from_user.id, CBT.TELEGRAM_PROXY_SET)

    def set_telegram_proxy(m: Message):
        try:
            proxy = normalize_telegram_proxy(m.text)
        except ValueError as error:
            bot.reply_to(m, _("tg_proxy_invalid", utils.escape(str(error))))
            return

        progress = bot.reply_to(m, _("tg_proxy_checking"))
        success, details = check_telegram_proxy(proxy, crd.MAIN_CFG["Telegram"]["token"])
        if not success:
            bot.edit_message_text(_("tg_proxy_check_failed", utils.escape(details)),
                                  progress.chat.id, progress.id)
            return

        tg.clear_state(m.chat.id, m.from_user.id, True)
        crd.MAIN_CFG["Telegram"]["proxy"] = proxy
        crd.save_config(crd.MAIN_CFG, "configs/_main.cfg")
        bot.edit_message_text(_("tg_proxy_saved", utils.escape(details)), progress.chat.id, progress.id,
                              reply_markup=telegram_proxy_keyboard())
        tg.apply_telegram_proxy(proxy)

    def disable_telegram_proxy(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        crd.MAIN_CFG["Telegram"]["proxy"] = ""
        crd.save_config(crd.MAIN_CFG, "configs/_main.cfg")
        bot.edit_message_text(_("tg_proxy_disabled"), c.message.chat.id, c.message.id,
                              reply_markup=telegram_proxy_keyboard())
        tg.apply_telegram_proxy("")

    def test_telegram_proxy(c: CallbackQuery):
        telegram_proxy = crd.MAIN_CFG["Telegram"].get("proxy", "")
        if not telegram_proxy:
            bot.answer_callback_query(c.id, _("tg_proxy_not_set"), show_alert=True)
            return
        bot.answer_callback_query(c.id, _("tg_proxy_checking_short"))
        success, details = check_telegram_proxy(telegram_proxy, crd.MAIN_CFG["Telegram"]["token"])
        if success:
            bot.send_message(c.message.chat.id, _("tg_proxy_test_ok", utils.escape(details)))
        else:
            bot.send_message(c.message.chat.id, _("tg_proxy_check_failed", utils.escape(details)))

    tg.cbq_handler(open_proxy_list, lambda c: c.data.startswith(f"{CBT.PROXY}:"))
    tg.cbq_handler(act_add_proxy, lambda c: c.data.startswith(f"{CBT.ADD_PROXY}:"))
    tg.cbq_handler(choose_proxy, lambda c: c.data.startswith(f"{CBT.CHOOSE_PROXY}:"))
    tg.cbq_handler(delete_proxy, lambda c: c.data.startswith(f"{CBT.DELETE_PROXY}:"))
    tg.cbq_handler(change_proxy_type, lambda c: c.data.startswith(f"{CBT.CHANGE_PROXY_TYPE}:"))
    tg.msg_handler(add_proxy, func=lambda m: crd.telegram.check_state(m.chat.id, m.from_user.id, CBT.ADD_PROXY))
    tg.cbq_handler(open_telegram_proxy, lambda c: c.data == CBT.TELEGRAM_PROXY)
    tg.cbq_handler(act_set_telegram_proxy, lambda c: c.data == CBT.TELEGRAM_PROXY_SET)
    tg.cbq_handler(disable_telegram_proxy, lambda c: c.data == CBT.TELEGRAM_PROXY_DISABLE)
    tg.cbq_handler(test_telegram_proxy, lambda c: c.data == CBT.TELEGRAM_PROXY_TEST)
    tg.msg_handler(set_telegram_proxy,
                   func=lambda m: crd.telegram.check_state(m.chat.id, m.from_user.id,
                                                            CBT.TELEGRAM_PROXY_SET))
    tg.msg_handler(cmd_telegram_proxy, commands=["telegram_proxy"])

BIND_TO_PRE_INIT = [init_proxy_cp]
