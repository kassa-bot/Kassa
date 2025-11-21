# bot_kassa_final.py
# Безопасный мультиязычный бот (RU + UZ) с админ-рассылкой и корректным выводом карты
# Требует: pip install pyTelegramBotAPI

import telebot
from telebot import types
import os
import json
import time
from datetime import datetime

# ========== НАСТРОЙКИ ==========
TOKEN = "8526368948:AAGsewidegbgnB_2YlTvCYXt5YHEX-opJrU"   # <-- Вставь свой токен локально
ADMIN_ID = 8582260752              # <-- Твой админ ID
DATA_FILE = "bot_data.json"
IMAGE_NAME = "start.jpg"           # приветственная картинка

bot = telebot.TeleBot(TOKEN)

# ========== ВСПОМОГАТЕЛИ: загрузка/сохранение ==========
def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "welcome_text_ru": "🎉 Добро пожаловать в нашу современную Telegram-кассу!\nЗдесь вы можете быстро и безопасно пополнить или вывести средства.",
            "welcome_text_uz": "🎉 Zamonaviy Telegram-kassamizga xush kelibsiz!\nBu yerda siz pulni tez va xavfsiz to‘ldirishingiz yoki yechib olishingiz mumkin.",
            "payment_info": "Инструкция для оплаты (публичный текст).",
            "requests": {},
            "users_lang": {},   # user_id -> 'ru'|'uz'
            "users": []         # список user_id для рассылок
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

def add_user(user_id):
    uid = str(user_id)
    if "users" not in data:
        data["users"] = []
    if uid not in data["users"]:
        data["users"].append(uid)
        save_data(data)

def get_user_lang(user_id):
    return data.get("users_lang", {}).get(str(user_id), None)

def set_user_lang(user_id, lang):
    if "users_lang" not in data:
        data["users_lang"] = {}
    data["users_lang"][str(user_id)] = lang
    save_data(data)

def new_request_id():
    return str(int(time.time() * 1000))

# ========== ТЕКСТЫ (локализация) ==========
TEXTS = {
    "menu": {
        "ru": ["📥 Пополнение", "📤 Вывод", "🛠 Техподдержка"],
        "uz": ["📥 To'ldirish", "📤 Pul yechish", "🛠 Texnik yordam"]
    },
    "ask_1win": {"ru": "🔎 Введите ваш 1Win ID:", "uz": "🔎 1Win ID raqamingizni kiriting:"},
    "ask_sum_deposit": {"ru": "💳 Введите сумму пополнения (не меньше 20000 UZS):", "uz": "💳 To'ldirish miqdorini kiriting (kamida 20000 UZS):"},
    "ask_sum_withdraw": {"ru": "💸 Введите сумму для вывода:", "uz": "💸 Pulni yechib olish miqdorini kiriting:"},
    "ask_code": {"ru": "🔐 Введите код подтверждения:", "uz": "🔐 Tasdiqlash kodini kiriting:"},
    "ask_card": {"ru": "💳 Введите номер вашей карты (Uzcard или Humo):", "uz": "💳 Iltimos, Uzcard yoki Humo kartangiz raqamini kiriting:"},
    "min_sum_error": {"ru": "⚠️ Минимальная сумма — 20000 UZS. Введите ещё раз:", "uz": "⚠️ Minimal summa — 20000 UZS. Qayta kiriting:"},
    "invalid_sum": {"ru": "⚠️ Введите сумму цифрами, например: 25000", "uz": "⚠️ Miqdorni raqamlar bilan kiriting, masalan: 25000"},
    "after_payment_info": {"ru": "💳 Инструкция для оплаты:\n\n{info}\n\nПосле перевода нажмите «Я оплатил»", "uz": "💳 To'lov bo'yicha yo'riqnoma:\n\n{info}\n\nTo'lovdan so'ng «Men to'ladim» tugmasini bosing"},
    "paid_button": {"ru": "Я оплатил ✅", "uz": "Men to‘ladim ✅"},
    "done_button": {"ru": "Готово ✅", "uz": "Tayyor ✅"},
    "support_text": {"ru": "🛠 Техподдержка: @tuzpay", "uz": "🛠 Texnik yordam: @tuzpay"},
    "request_sent": {"ru": "✅ Заявка отправлена администратору. Ожидайте решения.", "uz": "✅ Ariza admin ga yuborildi. Javob kuting."},
    "broadcast_prompt_photo": {"ru": "Отправьте картинку для рассылки или напишите 'Нет', чтобы отправить только текст.", "uz": "Yuborish uchun rasmni jo‘nating yoki faqat matn yuborish uchun 'Yo‘q' deb yozing."}
}

def t(user_id, key):
    lang = get_user_lang(user_id) or "ru"
    return TEXTS.get(key, {}).get(lang, "")

# ========== МЕНЮ ==========
def user_menu(is_admin=False, user_id=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    lang = get_user_lang(user_id) or "ru"
    items = TEXTS["menu"][lang]
    kb.add(types.KeyboardButton(items[0]), types.KeyboardButton(items[1]))
    kb.add(types.KeyboardButton(items[2]))
    if is_admin:
        kb.add(types.KeyboardButton("🔐 Админ-панель"))
    return kb

def admin_panel_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✏ Изменить приветственный текст", "🖼 Изменить картинку")
    kb.add("💳 Изменить инструкцию оплаты", "📢 Рассылка", "⬅ Назад")
    return kb

# ========== /start ==========
@bot.message_handler(commands=["start"])
def cmd_start(m):
    chat_id = m.chat.id
    add_user(chat_id)

    # если язык не выбран — предложим
    if not get_user_lang(chat_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
               types.InlineKeyboardButton("🇺🇿 O'zbek", callback_data="setlang_uz"))
        bot.send_message(chat_id, "Выберите язык / Tilni tanlang", reply_markup=kb)
        return

    lang = get_user_lang(chat_id)
    caption = data.get("welcome_text_ru") if lang == "ru" else data.get("welcome_text_uz")
    try:
        if os.path.exists(IMAGE_NAME):
            with open(IMAGE_NAME, "rb") as ph:
                bot.send_photo(chat_id, ph, caption=caption, reply_markup=user_menu(chat_id==ADMIN_ID, chat_id))
                return
    except Exception:
        pass
    bot.send_message(chat_id, caption, reply_markup=user_menu(chat_id==ADMIN_ID, chat_id))

# ========== /lang команда ==========
@bot.message_handler(commands=["lang"])
def cmd_lang(m):
    chat_id = m.chat.id
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
           types.InlineKeyboardButton("🇺🇿 O'zbek", callback_data="setlang_uz"))
    bot.send_message(chat_id, "Выберите язык / Tilni tanlang", reply_markup=kb)

# ========== STATE ==========
user_state = {}  # chat_id -> {"flow":..., "step":..., "temp":{}}

# ===== ПОПОЛНЕНИЕ =====
def start_deposit(chat_id):
    add_user(chat_id)
    user_state[chat_id] = {"flow": "deposit", "step": "ask_1win", "temp": {}}
    bot.send_message(chat_id, t(chat_id, "ask_1win"))

def deposit_step_handler(message):
    chat_id = message.chat.id
    st = user_state.get(chat_id)
    if not st:
        return
    step = st["step"]

    if step == "ask_1win":
        st["temp"]["win_id"] = message.text.strip()
        st["step"] = "ask_sum"
        bot.send_message(chat_id, t(chat_id, "ask_sum_deposit"))
        return

    if step == "ask_sum":
        try:
            s = int(message.text.replace(" ", ""))
        except:
            bot.send_message(chat_id, t(chat_id, "invalid_sum"))
            return
        if s < 20000:
            bot.send_message(chat_id, t(chat_id, "min_sum_error"))
            return
        st["temp"]["sum"] = s
        info = data.get("payment_info", "")
        caption = t(chat_id, "after_payment_info").format(info=info)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(t(chat_id, "paid_button"), callback_data=f"paid_deposit_{chat_id}"))
        bot.send_message(chat_id, caption, reply_markup=kb)
        return

# ===== ВЫВОД (исправлено: спрашиваем карту вместо контакта) =====
def start_withdraw(chat_id):
    add_user(chat_id)
    user_state[chat_id] = {"flow": "withdraw", "step": "ask_1win", "temp": {}}
    bot.send_message(chat_id, t(chat_id, "ask_1win"))

def withdraw_step_handler(message):
    chat_id = message.chat.id
    st = user_state.get(chat_id)
    if not st:
        return
    step = st["step"]

    if step == "ask_1win":
        st["temp"]["win_id"] = message.text.strip()
        st["step"] = "ask_sum"
        bot.send_message(chat_id, t(chat_id, "ask_sum_withdraw"))
        return

    if step == "ask_sum":
        try:
            s = int(message.text.replace(" ", ""))
        except:
            bot.send_message(chat_id, t(chat_id, "invalid_sum"))
            return
        st["temp"]["sum"] = s
        st["step"] = "ask_code"
        bot.send_message(chat_id, t(chat_id, "ask_code"))
        return

    if step == "ask_code":
        st["temp"]["code"] = message.text.strip()
        st["step"] = "ask_card"   # <-- теперь спрашиваем карту
        bot.send_message(chat_id, t(chat_id, "ask_card"))
        return

    if step == "ask_card":
        st["temp"]["card_number"] = message.text.strip()
        # готово
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(t(chat_id, "done_button"), callback_data=f"done_withdraw_{chat_id}"))
        if get_user_lang(chat_id) == "ru":
            bot.send_message(chat_id, "Проверьте данные и нажмите 'Готово', чтобы отправить заявку админу.", reply_markup=kb)
        else:
            bot.send_message(chat_id, "Ma'lumotlarni tekshiring va 'Tayyor' tugmasini bosing.", reply_markup=kb)
        return

# ========== КНОПКИ (reply) ==========
@bot.message_handler(func=lambda m: (m.text or "") in TEXTS["menu"]["ru"] + TEXTS["menu"]["uz"])
def on_menu_buttons(m):
    txt = (m.text or "").strip()
    # пополнение
    if txt == TEXTS["menu"]["ru"][0] or txt == TEXTS["menu"]["uz"][0]:
        start_deposit(m.chat.id)
        return
    # вывод
    if txt == TEXTS["menu"]["ru"][1] or txt == TEXTS["menu"]["uz"][1]:
        start_withdraw(m.chat.id)
        return
    # техподдержка
    if txt == TEXTS["menu"]["ru"][2] or txt == TEXTS["menu"]["uz"][2]:
        bot.send_message(m.chat.id, t(m.chat.id, "support_text"))
        return

@bot.message_handler(func=lambda m: m.text == "🔐 Админ-панель")
def on_admin_panel(m):
    if m.chat.id != ADMIN_ID:
        bot.send_message(m.chat.id, "У вас нет доступа.")
        return
    bot.send_message(m.chat.id, "Админ-панель:", reply_markup=admin_panel_keyboard())

# ========== CALLBACKS (язык, я оплатил, готово, админ) ==========
@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    data_call = c.data
    caller = c.from_user

    # язык
    if data_call == "setlang_ru":
        set_user_lang(c.message.chat.id, "ru")
        add_user(c.message.chat.id)
        bot.answer_callback_query(c.id, "Язык — Русский")
        caption = data.get("welcome_text_ru", "")
        try:
            if os.path.exists(IMAGE_NAME):
                with open(IMAGE_NAME, "rb") as ph:
                    bot.send_photo(c.message.chat.id, ph, caption=caption, reply_markup=user_menu(c.message.chat.id==ADMIN_ID, c.message.chat.id))
                    return
        except:
            pass
        bot.send_message(c.message.chat.id, caption, reply_markup=user_menu(c.message.chat.id==ADMIN_ID, c.message.chat.id))
        return

    if data_call == "setlang_uz":
        set_user_lang(c.message.chat.id, "uz")
        add_user(c.message.chat.id)
        bot.answer_callback_query(c.id, "Til — O'zbekcha")
        caption = data.get("welcome_text_uz", "")
        try:
            if os.path.exists(IMAGE_NAME):
                with open(IMAGE_NAME, "rb") as ph:
                    bot.send_photo(c.message.chat.id, ph, caption=caption, reply_markup=user_menu(c.message.chat.id==ADMIN_ID, c.message.chat.id))
                    return
        except:
            pass
        bot.send_message(c.message.chat.id, caption, reply_markup=user_menu(c.message.chat.id==ADMIN_ID, c.message.chat.id))
        return

    # пополнение: Я оплатил
    if data_call.startswith("paid_deposit_"):
        try:
            user_chat = int(data_call.split("_")[-1])
        except:
            bot.answer_callback_query(c.id, "Ошибка данных.")
            return
        st = user_state.get(user_chat)
        if not st or st.get("flow") != "deposit":
            bot.answer_callback_query(c.id, "Данные заявки не найдены или истекли.")
            return
        req_id = new_request_id()
        req = {
            "type": "deposit",
            "user_id": user_chat,
            "username": caller.username or "",
            "win_id": st["temp"].get("win_id"),
            "sum": st["temp"].get("sum"),
            "contact": None,
            "time": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        data["requests"][req_id] = req
        save_data(data)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{req_id}"),
                   types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{req_id}"))
        bot.send_message(ADMIN_ID,
                         f"📥 *НОВОЕ ПОПОЛНЕНИЕ*\n\n1Win ID: `{req['win_id']}`\nСумма: `{req['sum']}` UZS\nКлиент: @{req['username']} (ID: {req['user_id']})\nВремя (UTC): {req['time']}",
                         parse_mode="Markdown", reply_markup=markup)
        bot.send_message(user_chat, t(user_chat, "request_sent"))
        user_state.pop(user_chat, None)
        bot.answer_callback_query(c.id, "Заявка отправлена админу.")
        return

    # вывод: Готово
    if data_call.startswith("done_withdraw_"):
        try:
            user_chat = int(data_call.split("_")[-1])
        except:
            bot.answer_callback_query(c.id, "Ошибка данных.")
            return
        st = user_state.get(user_chat)
        if not st or st.get("flow") != "withdraw":
            bot.answer_callback_query(c.id, "Данные заявки не найдены или истекли.")
            return
        req_id = new_request_id()
        req = {
            "type": "withdraw",
            "user_id": user_chat,
            "username": caller.username or "",
            "win_id": st["temp"].get("win_id"),
            "sum": st["temp"].get("sum"),
            "code": st["temp"].get("code"),
            "card_number": st["temp"].get("card_number"),
            "time": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        data["requests"][req_id] = req
        save_data(data)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{req_id}"),
                   types.InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{req_id}"))
        bot.send_message(ADMIN_ID,
                         f"📤 *НОВЫЙ ВЫВОД*\n\n1Win ID: `{req['win_id']}`\nСумма: `{req['sum']}` UZS\nКод: `{req['code']}`\nКарта: `{req['card_number']}`\nКлиент: @{req['username']} (ID: {req['user_id']})\nВремя (UTC): {req['time']}",
                         parse_mode="Markdown", reply_markup=markup)
        bot.send_message(user_chat, t(user_chat, "request_sent"))
        user_state.pop(user_chat, None)
        bot.answer_callback_query(c.id, "Заявка отправлена админу.")
        return

    # админ: подтвердить/отменить
    if data_call.startswith("confirm_") or data_call.startswith("cancel_"):
        if caller.id != ADMIN_ID:
            bot.answer_callback_query(c.id, "У вас нет доступа.")
            return
        action, req_id = data_call.split("_", 1)
        req = data["requests"].get(req_id)
        if not req:
            bot.answer_callback_query(c.id, "Заявка не найдена.")
            return
        if req.get("status") != "pending":
            bot.answer_callback_query(c.id, "Заявка уже обработана.")
            return
        if action == "confirm":
            req["status"] = "confirmed"
            req["admin_time"] = datetime.utcnow().isoformat()
            save_data(data)
            try:
                bot.send_message(req["user_id"], "✔️ Ваша заявка подтверждена администратором.")
            except:
                pass
            bot.send_message(ADMIN_ID, f"Заявка {req_id} подтверждена.")
            bot.answer_callback_query(c.id, "Подтверждено.")
            return
        else:
            req["status"] = "cancelled"
            req["admin_time"] = datetime.utcnow().isoformat()
            save_data(data)
            try:
                bot.send_message(req["user_id"], "❌ Ваша заявка отменена администратором.")
            except:
                pass
            bot.send_message(ADMIN_ID, f"Заявка {req_id} отменена.")
            bot.answer_callback_query(c.id, "Отменено.")
            return

    bot.answer_callback_query(c.id, "Неизвестное действие.")

# ========== ROUTING TEXTS & ADMIN FLOWS (включая рассылку) ==========
@bot.message_handler(func=lambda m: True)
def all_texts(m):
    chat_id = m.chat.id
    txt = (m.text or "").strip()

    # маршрутизация состояний
    st = user_state.get(chat_id)
    if st:
        if st["flow"] == "deposit":
            deposit_step_handler(m)
            return
        if st["flow"] == "withdraw":
            withdraw_step_handler(m)
            return
        if st["flow"] == "broadcast" and chat_id == ADMIN_ID:
            # handled via admin_broadcast functions
            return

    # админ - изменение приветственных текстов (RU || UZ)
    if txt == "✏ Изменить приветственный текст" and chat_id == ADMIN_ID:
        bot.send_message(chat_id, "Отправьте новый приветственный текст в формате: RU текст || UZ текст")
        bot.register_next_step_handler(m, save_welcome_both)
        return
    if txt == "💳 Изменить инструкцию оплаты" and chat_id == ADMIN_ID:
        bot.send_message(chat_id, "Отправьте новую публичную инструкцию оплаты:")
        bot.register_next_step_handler(m, save_payment_info)
        return
    if txt == "🖼 Изменить картинку" and chat_id == ADMIN_ID:
        bot.send_message(chat_id, "Отправьте новую картинку (фото) для приветствия:")
        bot.register_next_step_handler(m, save_image)
        return
    if txt == "📢 Рассылка" and chat_id == ADMIN_ID:
        bot.send_message(chat_id, "📢 Введите текст рассылки (он будет отправлен ВСЕМ пользователям):")
        bot.register_next_step_handler(m, admin_broadcast_text)
        return
    if txt == "⬅ Назад":
        bot.send_message(chat_id, "Возврат в меню", reply_markup=user_menu(chat_id==ADMIN_ID, chat_id))
        return

    # если пользователь нажал одну из локализованных кнопок (обработать снова)
    if txt in TEXTS["menu"]["ru"] + TEXTS["menu"]["uz"]:
        if txt == TEXTS["menu"]["ru"][0] or txt == TEXTS["menu"]["uz"][0]:
            start_deposit(chat_id)
            return
        if txt == TEXTS["menu"]["ru"][1] or txt == TEXTS["menu"]["uz"][1]:
            start_withdraw(chat_id)
            return
        if txt == TEXTS["menu"]["ru"][2] or txt == TEXTS["menu"]["uz"][2]:
            bot.send_message(chat_id, t(chat_id, "support_text"))
            return

    # если язык не установлен — предложим выбор
    if not get_user_lang(chat_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
               types.InlineKeyboardButton("🇺🇿 O'zbek", callback_data="setlang_uz"))
        bot.send_message(chat_id, "Выберите язык / Tilni tanlang", reply_markup=kb)
        return

    # иначе показываем меню
    bot.send_message(chat_id, "Выберите действие:", reply_markup=user_menu(chat_id==ADMIN_ID, chat_id))

# ========== ADMIN: сохранения ==========
def save_welcome_both(m):
    if m.chat.id != ADMIN_ID:
        return
    text = m.text or ""
    parts = text.split("||")
    if len(parts) >= 2:
        ru = parts[0].strip()
        uz = parts[1].strip()
        data["welcome_text_ru"] = ru
        data["welcome_text_uz"] = uz
        save_data(data)
        bot.send_message(m.chat.id, "✅ Приветственные тексты обновлены (RU/UZ).", reply_markup=user_menu(True, m.chat.id))
    else:
        bot.send_message(m.chat.id, "Ошибка формата. Отправьте: RU текст || UZ текст")

def save_payment_info(m):
    if m.chat.id != ADMIN_ID:
        return
    data["payment_info"] = m.text or ""
    save_data(data)
    bot.send_message(m.chat.id, "✅ Инструкция оплаты обновлена.", reply_markup=user_menu(True, m.chat.id))

def save_image(m):
    if m.chat.id != ADMIN_ID:
        return
    if not m.photo:
        bot.send_message(m.chat.id, "Это не фото. Попробуйте ещё раз.")
        return
    file_info = bot.get_file(m.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)
    with open(IMAGE_NAME, "wb") as f:
        f.write(downloaded)
    bot.send_message(m.chat.id, "✅ Картинка приветствия обновлена.", reply_markup=user_menu(True, m.chat.id))

# ========== ADMIN: рассылка (текст -> фото? -> рассылка) ==========
def admin_broadcast_text(m):
    if m.chat.id != ADMIN_ID:
        return
    text = m.text or ""
    user_state[ADMIN_ID] = {"flow": "broadcast", "step": "ask_photo", "temp": {"text": text}}
    bot.send_message(ADMIN_ID, t(ADMIN_ID, "broadcast_prompt_photo"))
    bot.register_next_step_handler(m, admin_broadcast_photo)

def admin_broadcast_photo(m):
    if m.chat.id != ADMIN_ID:
        return
    st = user_state.get(ADMIN_ID)
    if not st or st.get("flow") != "broadcast":
        bot.send_message(ADMIN_ID, "Ошибка состояния. Начните рассылку заново.")
        return
    if m.text and m.text.strip().lower() in ("нет", "yo'q", "yoq", "no"):
        # отправляем только текст
        text = st["temp"].get("text", "")
        bot.send_message(ADMIN_ID, "Запускаю рассылку текстом всем пользователям...")
        send_broadcast_to_all(text=text, photo_path=None)
        user_state.pop(ADMIN_ID, None)
        return
    if m.photo:
        file_info = bot.get_file(m.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        temp_img = f"broadcast_{int(time.time())}.jpg"
        with open(temp_img, "wb") as f:
            f.write(downloaded)
        text = st["temp"].get("text", "")
        bot.send_message(ADMIN_ID, "Запускаю рассылку с картинкой всем пользователям...")
        send_broadcast_to_all(text=text, photo_path=temp_img)
        try:
            os.remove(temp_img)
        except:
            pass
        user_state.pop(ADMIN_ID, None)
        return
    bot.send_message(ADMIN_ID, "Отправьте картинку или 'Нет'.")

def send_broadcast_to_all(text, photo_path=None):
    users = data.get("users", [])
    sent = 0
    failed = 0
    for uid in users:
        try:
            uid_int = int(uid)
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, "rb") as ph:
                    bot.send_photo(uid_int, ph, caption=text)
            else:
                bot.send_message(uid_int, text)
            sent += 1
            time.sleep(0.05)
        except Exception:
            failed += 1
            continue
    bot.send_message(ADMIN_ID, f"Рассылка завершена. Отправлено: {sent}. Ошибок: {failed}.")

# ========== RUN ==========
if __name__ == "__main__":
    print("Bot (final) started...")
    bot.infinity_polling(skip_pending=True)
