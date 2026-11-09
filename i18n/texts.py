"""Тексты интерфейса на трёх языках. Подстановки — через str.format()."""
from __future__ import annotations

RU: dict[str, str] = {
    # --- главное меню
    "btn_create": "🚚 Создать поставку",
    "btn_calc": "💰 Рассчитать стоимость",
    "btn_track": "📦 Отследить груз",
    "btn_my": "📋 Мои поставки",
    "btn_ai": "🤖 AI-помощник",
    "btn_about": "ℹ️ О проекте",
    "btn_home": "🏠 Главное меню",
    "btn_cancel": "✖️ Отменить",
    "btn_confirm": "✅ Подтвердить заявку",
    "btn_send_contact": "📱 Отправить мой номер",
    "btn_language": "🌐 Сменить язык",
    "input_placeholder": "Выберите раздел",
    # --- общие
    "welcome": (
        "<b>Qadam Logistics</b> — цифровой логистический сервис для бизнеса\n\n"
        "Сәлем, {name}! 👋\n\n"
        "В одном чате вы можете:\n"
        "• оформить грузоперевозку за пару минут;\n"
        "• получить предварительный расчёт стоимости с подробной разбивкой;\n"
        "• отслеживать этапы доставки и получать уведомления;\n"
        "• описать груз своими словами — AI-помощник заполнит заявку.\n\n"
        "Основной коридор: 🇰🇿 Шымкент ⇄ 🇺🇿 Ташкент"
    ),
    "choose_language": "🌐 Выберите язык интерфейса\nТілді таңдаңыз · Choose your language",
    "language_saved": "✅ Язык интерфейса: Русский",
    "main_menu": "<b>Главное меню</b>\nВыберите раздел на клавиатуре ниже 👇",
    "about": (
        "ℹ️ <b>О проекте Qadam Logistics</b>\n\n"
        "<b>Проблема.</b> Малому бизнесу сложно организовать международную перевозку: цены, сроки и "
        "статус груза разбросаны между перевозчиками, экспедиторами и таможенными брокерами.\n\n"
        "<b>Решение.</b> Один Telegram-бот, где можно оформить заявку, сразу увидеть прозрачный расчёт "
        "стоимости и следить за каждым этапом доставки — с уведомлениями.\n\n"
        "<b>Для кого:</b> магазины, интернет-магазины, импортёры и экспортёры, небольшие производства.\n\n"
        "<b>Как это работает</b>\n"
        "1. Вы оформляете заявку или описываете груз AI-помощнику.\n"
        "2. Система считает стоимость по тарифам маршрута.\n"
        "3. Менеджер подтверждает заявку и обновляет статусы.\n"
        "4. Вы получаете уведомление о каждом этапе.\n\n"
        "<i>MVP для хакатона Digital Economy &amp; Future Tech. Тарифы — демонстрационные.</i>"
    ),
    "help": (
        "<b>Команды</b>\n"
        "/start — начать заново\n/menu — главное меню\n/cancel — отменить текущее действие\n"
        "/track — отследить груз\n/language — сменить язык\n/help — помощь"
    ),
    "unknown": "Не понял сообщение 🤔\nВыберите раздел в меню ниже или отправьте /menu.",
    "error_generic": "⚠️ Что-то пошло не так. Попробуйте ещё раз или вернитесь в /menu.",
    "action_cancelled": "Действие отменено.",
    "callback_expired": "Эта кнопка устарела",
    "access_denied": "⛔ Нет доступа.",
    "not_specified": "—",
    "unit_kg": "кг",
    "unit_m3": "м³",
    "unit_pcs": "шт.",
    "unit_km": "км",
    # --- справочники
    "cat_clothing": "Одежда",
    "cat_electronics": "Электроника",
    "cat_food": "Продукты",
    "cat_construction": "Стройматериалы",
    "cat_furniture": "Мебель",
    "cat_other": "Другое",
    "tr_road": "Автомобильный",
    "tr_rail": "Железнодорожный",
    "status_created": "Заявка создана",
    "status_pending": "Ожидает подтверждения",
    "status_confirmed": "Подтверждена",
    "status_preparing": "Подготовка груза",
    "status_picked_up": "Груз принят перевозчиком",
    "status_in_transit": "В пути",
    "status_at_customs": "Прибыл на таможенное оформление",
    "status_customs_cleared": "Таможенное оформление завершено",
    "status_arrived": "Прибыл в город назначения",
    "status_delivered": "Доставлен",
    "status_cancelled": "Отменён",
    # --- поля
    "f_number": "Номер",
    "f_origin": "Откуда",
    "f_destination": "Куда",
    "f_route": "Маршрут",
    "f_distance": "Расстояние",
    "f_category": "Груз",
    "f_weight": "Вес",
    "f_volume": "Объём",
    "f_packages": "Упаковок",
    "f_transport": "Транспорт",
    "f_date": "Дата отправки",
    "f_phone": "Телефон",
    "f_price": "Предварительная стоимость",
    "f_status": "Статус",
    "f_created": "Создана",
    "f_updated": "Обновлена",
    # --- оформление поставки
    "sh_header": "🚚 <b>Новая поставка</b> · шаг {step}/10",
    "ask_origin": "Выберите <b>город отправления</b>:",
    "ask_destination": "Выберите <b>город назначения</b>:",
    "ask_category": "Выберите <b>категорию груза</b>:",
    "ask_weight": "Укажите <b>вес груза</b> в килограммах.\nНапример: <code>150</code> или <code>1250.5</code>",
    "ask_volume": (
        "Укажите <b>объём груза</b> в кубических метрах (м³).\nНапример: <code>1.2</code>\n\n"
        "💡 Объём коробки = длина × ширина × высота в метрах."
    ),
    "ask_packages": "Укажите <b>количество упаковок</b> — коробок, мест или паллет.\nНапример: <code>10</code>",
    "ask_transport": "Выберите <b>тип транспорта</b>:",
    "ask_date": "Выберите <b>желаемую дату отправки</b> или введите её в формате <code>ДД.ММ.ГГГГ</code>:",
    "ask_phone": (
        "Укажите <b>контактный телефон</b> — менеджер свяжется для уточнения деталей.\n"
        "Нажмите кнопку «📱 Отправить мой номер» или введите номер, например <code>+7 701 123 45 67</code>."
    ),
    "phone_saved": "📱 Номер сохранён: {phone}",
    "sh_summary_title": "📋 <b>Проверьте заявку</b>",
    "sh_confirm_hint": "Если всё верно — подтвердите заявку. Её получит менеджер Qadam Logistics.",
    "sh_created": (
        "✅ <b>Заявка оформлена!</b>\n\n"
        "Номер поставки: <code>{tracking}</code>\n"
        "Статус: ⏳ Ожидает подтверждения\n\n"
        "Менеджер проверит заявку и подтвердит её. Об изменении статуса придёт уведомление в этот чат."
    ),
    "sh_already_processed": "Эта заявка уже обработана.",
    "sh_cancelled": "Оформление заявки отменено. Данные не сохранены.",
    "no_routes": "Сейчас нет доступных маршрутов. Попробуйте позже.",
    "no_destinations": "Из этого города пока нет маршрутов. Выберите другой город.",
    "no_transport": "Для этого маршрута сейчас нет активных тарифов. Выберите другой маршрут.",
    "route_unavailable": "Выбранный маршрут недоступен. Выберите города заново.",
    "date_today": "Сегодня",
    "date_tomorrow": "Завтра",
    "date_in_days": "Через {n} дн.",
    # --- ошибки ввода
    "err_number": "Введите число, например <code>150</code>.",
    "err_positive": "Значение должно быть больше нуля.",
    "err_weight_max": "Максимальный вес в MVP — {max} кг. Для крупных партий свяжитесь с менеджером.",
    "err_volume_min": "Слишком маленький объём. Минимум — 0.001 м³.",
    "err_volume_max": "Максимальный объём в MVP — {max} м³.",
    "err_packages": "Количество упаковок — целое число от 1 до 10 000.",
    "err_date_format": "Не удалось распознать дату. Формат: <code>ДД.ММ.ГГГГ</code>, например <code>25.11.2026</code>.",
    "err_date_past": "Дата не может быть в прошлом.",
    "err_date_far": "Дата должна быть не позднее чем через {days} дней.",
    "err_phone": (
        "Некорректный номер. Введите его в международном формате, например "
        "<code>+77011234567</code> или <code>+998901234567</code>."
    ),
    "err_use_buttons": "Пожалуйста, выберите вариант кнопкой выше.",
    # --- цена
    "price_title": "💰 <b>Предварительная оценка</b>",
    "price_base": "Базовая стоимость маршрута",
    "price_weight": "По весу: {weight} кг × {rate}",
    "price_volume": "По объёму: {volume} м³ × {rate}",
    "price_applied": "◀ учитывается",
    "price_additional": "Доп. расходы по тарифу",
    "price_total": "Итого",
    "price_rule": "<i>Учитывается большее из двух: стоимость по весу или по объёму.</i>",
    "price_disclaimer": (
        "<i>⚠️ Предварительная оценка по демонстрационным ТЕСТОВЫМ тарифам. "
        "Не является подтверждённым предложением перевозчика — итоговую стоимость сообщит менеджер.</i>"
    ),
    # --- калькулятор
    "calc_header": "💰 <b>Расчёт стоимости</b> · шаг {step}/4",
    "calc_result_title": "💰 <b>Предварительный расчёт</b>",
    "calc_best": "Выгоднее: {transport}",
    "btn_order_with": "🚚 Оформить: {transport}",
    "btn_new_calc": "🔁 Новый расчёт",
    # --- отслеживание
    "ask_tracking": (
        "📦 <b>Отслеживание груза</b>\n\n"
        "Введите номер поставки, например <code>QDM-261106-7KX4P</code>,\n"
        "или откройте её в разделе «📋 Мои поставки»."
    ),
    "tracking_invalid": "Номер выглядит так: <code>QDM-261106-7KX4P</code>. Проверьте и введите ещё раз.",
    "tracking_not_found": "Поставка <code>{tracking}</code> не найдена среди ваших поставок.",
    "card_title": "📦 <b>Поставка {tracking}</b>",
    "timeline_title": "<b>Этапы доставки</b>",
    "history_title": "🕓 <b>История статусов · {tracking}</b>",
    "history_empty": "История пока пуста.",
    "btn_open_shipment": "📦 Открыть поставку",
    "btn_history": "🕓 История",
    "btn_refresh": "🔄 Обновить",
    "btn_cancel_shipment": "❌ Отменить заявку",
    "btn_yes_cancel": "Да, отменить",
    "btn_no": "Нет",
    "btn_back_list": "⬅️ К списку",
    "btn_back_card": "⬅️ К поставке",
    "sh_cancel_confirm": "Отменить заявку <code>{tracking}</code>? Это действие необратимо.",
    "sh_cancelled_by_user": "Заявка <code>{tracking}</code> отменена.",
    "sh_cannot_cancel": "Заявку уже нельзя отменить самостоятельно — она в работе. Свяжитесь с менеджером.",
    "notify_status": "🔔 <b>Обновление статуса</b>\n\nПоставка <code>{tracking}</code>\n{route}\n\n{old} → <b>{new}</b>",
    "notify_comment": "💬 {comment}",
    # --- мои поставки
    "my_title": "📋 <b>Мои поставки</b> · всего: {count}\nВыберите поставку, чтобы открыть подробности.",
    "my_empty": "У вас пока нет поставок.\nНажмите «🚚 Создать поставку», чтобы оформить первую заявку.",
    # --- AI-помощник
    "ai_intro": (
        "🤖 <b>AI-помощник Qadam</b>\n\n"
        "Опишите груз своими словами — я заполню заявку. Например:\n"
        "<i>«Мне нужно отправить 150 кг одежды из Шымкента в Ташкент, примерно 10 коробок»</i>\n\n"
        "Также отвечу на вопросы о работе сервиса и этапах доставки.\n\n{mode}"
    ),
    "ai_mode_ai": "Режим: Gemini AI ✨",
    "ai_mode_fallback": "Режим: базовый (без ИИ) — распознаю типовые фразы.",
    "ai_extracted_title": "🧾 <b>Распознанная заявка</b>",
    "ai_extracted_hint": (
        "Проверьте данные. Недостающие поля бот спросит при оформлении.\n"
        "Стоимость считает система по тарифам, заявку подтверждает менеджер."
    ),
    "btn_ai_fill": "✅ Продолжить оформление",
    "btn_ai_calc": "💰 Рассчитать стоимость",
    "btn_ai_manual": "✏️ Заполнить вручную",
    "ai_fallback_extracted": "AI сейчас недоступен — данные распознаны в базовом режиме.",
    "ai_cooldown": "Подождите пару секунд перед следующим сообщением.",
    "ai_too_long": "Сообщение слишком длинное — сократите до {max} символов.",
    "ai_need_text": "Отправьте, пожалуйста, текстовое сообщение.",
    "ai_session_expired": "Данные распознавания устарели. Опишите груз ещё раз.",
    "faq_price": (
        "Стоимость рассчитывает система по тарифам маршрута: базовая ставка + большее из (вес × цена за кг) "
        "и (объём × цена за м³) + доп. расходы. Нажмите «💰 Рассчитать стоимость» — расчёт займёт минуту."
    ),
    "faq_tracking": (
        "Статус поставки смотрите в разделе «📦 Отследить груз» по номеру вида QDM-261106-7KX4P "
        "или в «📋 Мои поставки». При каждом изменении статуса бот пришлёт уведомление."
    ),
    "faq_customs": (
        "Для международных маршрутов (например, Шымкент → Ташкент) есть этапы «Прибыл на таможенное "
        "оформление» и «Таможенное оформление завершено». Детали по документам уточнит менеджер."
    ),
    "faq_docs": (
        "Обычно нужны: инвойс, упаковочный лист и документы на товар. Точный список зависит от категории "
        "груза — менеджер уточнит его после подтверждения заявки."
    ),
    "faq_create": (
        "Нажмите «🚚 Создать поставку» и пройдите 10 шагов: маршрут, груз, вес, объём, упаковки, транспорт, "
        "дата и телефон. Или просто опишите груз мне одним сообщением."
    ),
    "faq_time": (
        "Сроки зависят от маршрута, транспорта и таможни. Ориентировочную дату сообщит менеджер после "
        "подтверждения, а этапы доставки видны в разделе «📦 Отследить груз»."
    ),
    "faq_default": (
        "Я помогаю оформить перевозку и разобраться с этапами доставки. Опишите груз, например: "
        "«200 кг электроники из Ташкента в Шымкент, 5 коробок» — и я подготовлю заявку."
    ),
}

EN: dict[str, str] = {
    "btn_create": "🚚 Create shipment",
    "btn_calc": "💰 Calculate cost",
    "btn_track": "📦 Track cargo",
    "btn_my": "📋 My shipments",
    "btn_ai": "🤖 AI assistant",
    "btn_about": "ℹ️ About",
    "btn_home": "🏠 Main menu",
    "btn_cancel": "✖️ Cancel",
    "btn_confirm": "✅ Confirm request",
    "btn_send_contact": "📱 Share my number",
    "btn_language": "🌐 Change language",
    "input_placeholder": "Choose a section",
    "welcome": (
        "<b>Qadam Logistics</b> — a digital logistics service for business\n\n"
        "Hello, {name}! 👋\n\n"
        "In one chat you can:\n"
        "• book a cargo shipment in a couple of minutes;\n"
        "• get a preliminary cost estimate with a detailed breakdown;\n"
        "• track delivery stages and receive notifications;\n"
        "• describe your cargo in plain words — the AI assistant fills in the form.\n\n"
        "Main corridor: 🇰🇿 Shymkent ⇄ 🇺🇿 Tashkent"
    ),
    "choose_language": "🌐 Choose your language\nВыберите язык · Тілді таңдаңыз",
    "language_saved": "✅ Interface language: English",
    "main_menu": "<b>Main menu</b>\nChoose a section on the keyboard below 👇",
    "about": (
        "ℹ️ <b>About Qadam Logistics</b>\n\n"
        "<b>Problem.</b> Small businesses struggle to arrange international shipping: prices, timing and cargo "
        "status are scattered across carriers, forwarders and customs brokers.\n\n"
        "<b>Solution.</b> One Telegram bot to book a shipment, instantly see a transparent cost estimate and "
        "follow every delivery stage — with notifications.\n\n"
        "<b>For:</b> shops, online stores, importers and exporters, small manufacturers.\n\n"
        "<b>How it works</b>\n"
        "1. You create a request or describe the cargo to the AI assistant.\n"
        "2. The system calculates the cost from route tariffs.\n"
        "3. An operator confirms the request and updates statuses.\n"
        "4. You are notified about every stage.\n\n"
        "<i>MVP for the Digital Economy &amp; Future Tech hackathon. Tariffs are for demo only.</i>"
    ),
    "help": (
        "<b>Commands</b>\n"
        "/start — start over\n/menu — main menu\n/cancel — cancel current action\n"
        "/track — track cargo\n/language — change language\n/help — help"
    ),
    "unknown": "I didn't get that 🤔\nChoose a section in the menu below or send /menu.",
    "error_generic": "⚠️ Something went wrong. Please try again or go back to /menu.",
    "action_cancelled": "Action cancelled.",
    "callback_expired": "This button is outdated",
    "access_denied": "⛔ Access denied.",
    "not_specified": "—",
    "unit_kg": "kg",
    "unit_m3": "m³",
    "unit_pcs": "pcs",
    "unit_km": "km",
    "cat_clothing": "Clothing",
    "cat_electronics": "Electronics",
    "cat_food": "Food products",
    "cat_construction": "Building materials",
    "cat_furniture": "Furniture",
    "cat_other": "Other",
    "tr_road": "Road",
    "tr_rail": "Rail",
    "status_created": "Request created",
    "status_pending": "Awaiting confirmation",
    "status_confirmed": "Confirmed",
    "status_preparing": "Cargo preparation",
    "status_picked_up": "Accepted by carrier",
    "status_in_transit": "In transit",
    "status_at_customs": "Arrived at customs",
    "status_customs_cleared": "Customs cleared",
    "status_arrived": "Arrived in destination city",
    "status_delivered": "Delivered",
    "status_cancelled": "Cancelled",
    "f_number": "Number",
    "f_origin": "From",
    "f_destination": "To",
    "f_route": "Route",
    "f_distance": "Distance",
    "f_category": "Cargo",
    "f_weight": "Weight",
    "f_volume": "Volume",
    "f_packages": "Packages",
    "f_transport": "Transport",
    "f_date": "Shipping date",
    "f_phone": "Phone",
    "f_price": "Preliminary cost",
    "f_status": "Status",
    "f_created": "Created",
    "f_updated": "Updated",
    "sh_header": "🚚 <b>New shipment</b> · step {step}/10",
    "ask_origin": "Choose the <b>origin city</b>:",
    "ask_destination": "Choose the <b>destination city</b>:",
    "ask_category": "Choose the <b>cargo category</b>:",
    "ask_weight": "Enter the <b>cargo weight</b> in kilograms.\nFor example: <code>150</code> or <code>1250.5</code>",
    "ask_volume": (
        "Enter the <b>cargo volume</b> in cubic metres (m³).\nFor example: <code>1.2</code>\n\n"
        "💡 Box volume = length × width × height in metres."
    ),
    "ask_packages": "Enter the <b>number of packages</b> — boxes, pieces or pallets.\nFor example: <code>10</code>",
    "ask_transport": "Choose the <b>transport type</b>:",
    "ask_date": "Choose the <b>preferred shipping date</b> or type it as <code>DD.MM.YYYY</code>:",
    "ask_phone": (
        "Enter a <b>contact phone number</b> — an operator will call to clarify details.\n"
        "Press «📱 Share my number» or type it, e.g. <code>+7 701 123 45 67</code>."
    ),
    "phone_saved": "📱 Number saved: {phone}",
    "sh_summary_title": "📋 <b>Review your request</b>",
    "sh_confirm_hint": "If everything is correct, confirm the request. A Qadam Logistics operator will receive it.",
    "sh_created": (
        "✅ <b>Request submitted!</b>\n\n"
        "Shipment number: <code>{tracking}</code>\n"
        "Status: ⏳ Awaiting confirmation\n\n"
        "An operator will review and confirm it. You will be notified here about every status change."
    ),
    "sh_already_processed": "This request has already been processed.",
    "sh_cancelled": "Request cancelled. No data was saved.",
    "no_routes": "No routes are available right now. Please try later.",
    "no_destinations": "There are no routes from this city yet. Choose another city.",
    "no_transport": "This route has no active tariffs right now. Choose another route.",
    "route_unavailable": "The selected route is unavailable. Please choose the cities again.",
    "date_today": "Today",
    "date_tomorrow": "Tomorrow",
    "date_in_days": "In {n} days",
    "err_number": "Enter a number, e.g. <code>150</code>.",
    "err_positive": "The value must be greater than zero.",
    "err_weight_max": "Maximum weight in the MVP is {max} kg. For larger lots contact an operator.",
    "err_volume_min": "The volume is too small. Minimum is 0.001 m³.",
    "err_volume_max": "Maximum volume in the MVP is {max} m³.",
    "err_packages": "Number of packages must be a whole number from 1 to 10,000.",
    "err_date_format": "Could not read the date. Format: <code>DD.MM.YYYY</code>, e.g. <code>25.11.2026</code>.",
    "err_date_past": "The date cannot be in the past.",
    "err_date_far": "The date must be within {days} days.",
    "err_phone": (
        "Invalid number. Use the international format, e.g. "
        "<code>+77011234567</code> or <code>+998901234567</code>."
    ),
    "err_use_buttons": "Please choose an option using the buttons above.",
    "price_title": "💰 <b>Preliminary estimate</b>",
    "price_base": "Route base price",
    "price_weight": "By weight: {weight} kg × {rate}",
    "price_volume": "By volume: {volume} m³ × {rate}",
    "price_applied": "◀ applied",
    "price_additional": "Additional tariff costs",
    "price_total": "Total",
    "price_rule": "<i>The larger of the two is applied: cost by weight or cost by volume.</i>",
    "price_disclaimer": (
        "<i>⚠️ Preliminary estimate based on demo TEST tariffs. "
        "This is not a confirmed carrier offer — the operator will provide the final price.</i>"
    ),
    "calc_header": "💰 <b>Cost calculation</b> · step {step}/4",
    "calc_result_title": "💰 <b>Preliminary calculation</b>",
    "calc_best": "Best price: {transport}",
    "btn_order_with": "🚚 Book: {transport}",
    "btn_new_calc": "🔁 New calculation",
    "ask_tracking": (
        "📦 <b>Cargo tracking</b>\n\n"
        "Enter the shipment number, e.g. <code>QDM-261106-7KX4P</code>,\n"
        "or open it in «📋 My shipments»."
    ),
    "tracking_invalid": "The number looks like <code>QDM-261106-7KX4P</code>. Please check and try again.",
    "tracking_not_found": "Shipment <code>{tracking}</code> was not found among your shipments.",
    "card_title": "📦 <b>Shipment {tracking}</b>",
    "timeline_title": "<b>Delivery stages</b>",
    "history_title": "🕓 <b>Status history · {tracking}</b>",
    "history_empty": "No history yet.",
    "btn_open_shipment": "📦 Open shipment",
    "btn_history": "🕓 History",
    "btn_refresh": "🔄 Refresh",
    "btn_cancel_shipment": "❌ Cancel request",
    "btn_yes_cancel": "Yes, cancel",
    "btn_no": "No",
    "btn_back_list": "⬅️ Back to list",
    "btn_back_card": "⬅️ Back to shipment",
    "sh_cancel_confirm": "Cancel request <code>{tracking}</code>? This cannot be undone.",
    "sh_cancelled_by_user": "Request <code>{tracking}</code> has been cancelled.",
    "sh_cannot_cancel": "This request is already in progress and cannot be cancelled here. Please contact an operator.",
    "notify_status": "🔔 <b>Status update</b>\n\nShipment <code>{tracking}</code>\n{route}\n\n{old} → <b>{new}</b>",
    "notify_comment": "💬 {comment}",
    "my_title": "📋 <b>My shipments</b> · total: {count}\nSelect a shipment to see details.",
    "my_empty": "You have no shipments yet.\nPress «🚚 Create shipment» to book your first one.",
    "ai_intro": (
        "🤖 <b>Qadam AI assistant</b>\n\n"
        "Describe your cargo in plain words and I'll fill in the request. For example:\n"
        "<i>“I need to send 150 kg of clothes from Shymkent to Tashkent, about 10 boxes”</i>\n\n"
        "I can also answer questions about the service and delivery stages.\n\n{mode}"
    ),
    "ai_mode_ai": "Mode: Gemini AI ✨",
    "ai_mode_fallback": "Mode: basic (no AI) — I recognise common phrases.",
    "ai_extracted_title": "🧾 <b>Recognised request</b>",
    "ai_extracted_hint": (
        "Please check the data. The bot will ask for missing fields during booking.\n"
        "The cost is calculated by the system from tariffs; an operator confirms the request."
    ),
    "btn_ai_fill": "✅ Continue booking",
    "btn_ai_calc": "💰 Calculate cost",
    "btn_ai_manual": "✏️ Fill in manually",
    "ai_fallback_extracted": "AI is unavailable right now — the data was recognised in basic mode.",
    "ai_cooldown": "Please wait a couple of seconds before the next message.",
    "ai_too_long": "The message is too long — please shorten it to {max} characters.",
    "ai_need_text": "Please send a text message.",
    "ai_session_expired": "The recognised data has expired. Please describe the cargo again.",
    "faq_price": (
        "The system calculates the cost from route tariffs: base rate + the larger of (weight × price per kg) "
        "and (volume × price per m³) + additional costs. Press «💰 Calculate cost» — it takes a minute."
    ),
    "faq_tracking": (
        "Check the status in «📦 Track cargo» using a number like QDM-261106-7KX4P, or in «📋 My shipments». "
        "The bot notifies you about every status change."
    ),
    "faq_customs": (
        "International routes (e.g. Shymkent → Tashkent) include the stages “Arrived at customs” and "
        "“Customs cleared”. The operator will advise on documents."
    ),
    "faq_docs": (
        "Usually you need an invoice, a packing list and product documents. The exact list depends on the cargo "
        "category — the operator will confirm it after the request is approved."
    ),
    "faq_create": (
        "Press «🚚 Create shipment» and complete 10 steps: route, cargo, weight, volume, packages, transport, "
        "date and phone. Or just describe the cargo to me in one message."
    ),
    "faq_time": (
        "Timing depends on the route, transport and customs. The operator will give an estimated date after "
        "confirmation, and the stages are visible in «📦 Track cargo»."
    ),
    "faq_default": (
        "I help you book shipments and understand delivery stages. Describe your cargo, e.g. "
        "“200 kg of electronics from Tashkent to Shymkent, 5 boxes”, and I'll prepare the request."
    ),
}

KK: dict[str, str] = {
    "btn_create": "🚚 Жөнелтім құру",
    "btn_calc": "💰 Құнын есептеу",
    "btn_track": "📦 Жүкті бақылау",
    "btn_my": "📋 Менің жөнелтімдерім",
    "btn_ai": "🤖 AI-көмекші",
    "btn_about": "ℹ️ Жоба туралы",
    "btn_home": "🏠 Басты мәзір",
    "btn_cancel": "✖️ Бас тарту",
    "btn_confirm": "✅ Өтінімді растау",
    "btn_send_contact": "📱 Нөмірімді жіберу",
    "btn_language": "🌐 Тілді ауыстыру",
    "input_placeholder": "Бөлімді таңдаңыз",
    "welcome": (
        "<b>Qadam Logistics</b> — бизнеске арналған цифрлық логистикалық сервис\n\n"
        "Сәлеметсіз бе, {name}! 👋\n\n"
        "Бір чатта сіз:\n"
        "• жүк тасымалын бірнеше минутта рәсімдей аласыз;\n"
        "• толық бөлінісімен алдын ала құн есебін аласыз;\n"
        "• жеткізу кезеңдерін бақылап, хабарламалар аласыз;\n"
        "• жүкті өз сөзіңізбен сипаттасаңыз — AI-көмекші өтінімді толтырады.\n\n"
        "Негізгі дәліз: 🇰🇿 Шымкент ⇄ 🇺🇿 Ташкент"
    ),
    "choose_language": "🌐 Интерфейс тілін таңдаңыз\nВыберите язык · Choose your language",
    "language_saved": "✅ Интерфейс тілі: Қазақша",
    "main_menu": "<b>Басты мәзір</b>\nТөмендегі пернетақтадан бөлімді таңдаңыз 👇",
    "about": (
        "ℹ️ <b>Qadam Logistics жобасы туралы</b>\n\n"
        "<b>Мәселе.</b> Шағын бизнеске халықаралық тасымалды ұйымдастыру қиын: баға, мерзім және жүк "
        "мәртебесі туралы ақпарат тасымалдаушылар, экспедиторлар мен кеден брокерлері арасында шашыраңқы.\n\n"
        "<b>Шешім.</b> Бір Telegram-бот: өтінім рәсімдеу, құнның ашық есебін бірден көру және жеткізудің "
        "әр кезеңін хабарламалармен бақылау.\n\n"
        "<b>Кімге арналған:</b> дүкендер, интернет-дүкендер, импорттаушылар мен экспорттаушылар, шағын өндірістер.\n\n"
        "<b>Қалай жұмыс істейді</b>\n"
        "1. Сіз өтінім рәсімдейсіз немесе жүкті AI-көмекшіге сипаттайсыз.\n"
        "2. Жүйе бағыт тарифтері бойынша құнды есептейді.\n"
        "3. Менеджер өтінімді растап, мәртебелерді жаңартады.\n"
        "4. Әр кезең туралы хабарлама аласыз.\n\n"
        "<i>Digital Economy &amp; Future Tech хакатонына арналған MVP. Тарифтер — демонстрациялық.</i>"
    ),
    "help": (
        "<b>Командалар</b>\n"
        "/start — қайта бастау\n/menu — басты мәзір\n/cancel — ағымдағы әрекеттен бас тарту\n"
        "/track — жүкті бақылау\n/language — тілді ауыстыру\n/help — көмек"
    ),
    "unknown": "Хабарламаны түсінбедім 🤔\nТөмендегі мәзірден бөлімді таңдаңыз немесе /menu жіберіңіз.",
    "error_generic": "⚠️ Қате орын алды. Қайталап көріңіз немесе /menu бөліміне оралыңыз.",
    "action_cancelled": "Әрекеттен бас тартылды.",
    "callback_expired": "Бұл батырма ескірген",
    "access_denied": "⛔ Қолжетімділік жоқ.",
    "not_specified": "—",
    "unit_kg": "кг",
    "unit_m3": "м³",
    "unit_pcs": "дана",
    "unit_km": "км",
    "cat_clothing": "Киім",
    "cat_electronics": "Электроника",
    "cat_food": "Азық-түлік",
    "cat_construction": "Құрылыс материалдары",
    "cat_furniture": "Жиһаз",
    "cat_other": "Басқа",
    "tr_road": "Автокөлік",
    "tr_rail": "Темір жол",
    "status_created": "Өтінім құрылды",
    "status_pending": "Растауды күтуде",
    "status_confirmed": "Расталды",
    "status_preparing": "Жүкті дайындау",
    "status_picked_up": "Жүкті тасымалдаушы қабылдады",
    "status_in_transit": "Жолда",
    "status_at_customs": "Кедендік рәсімдеуге келді",
    "status_customs_cleared": "Кедендік рәсімдеу аяқталды",
    "status_arrived": "Межелі қалаға келді",
    "status_delivered": "Жеткізілді",
    "status_cancelled": "Жойылды",
    "f_number": "Нөмірі",
    "f_origin": "Қайдан",
    "f_destination": "Қайда",
    "f_route": "Бағыт",
    "f_distance": "Қашықтық",
    "f_category": "Жүк",
    "f_weight": "Салмағы",
    "f_volume": "Көлемі",
    "f_packages": "Қаптама саны",
    "f_transport": "Көлік",
    "f_date": "Жөнелту күні",
    "f_phone": "Телефон",
    "f_price": "Алдын ала құны",
    "f_status": "Мәртебесі",
    "f_created": "Құрылған",
    "f_updated": "Жаңартылған",
    "sh_header": "🚚 <b>Жаңа жөнелтім</b> · {step}/10-қадам",
    "ask_origin": "<b>Жөнелту қаласын</b> таңдаңыз:",
    "ask_destination": "<b>Межелі қаланы</b> таңдаңыз:",
    "ask_category": "<b>Жүк санатын</b> таңдаңыз:",
    "ask_weight": "<b>Жүк салмағын</b> килограммен көрсетіңіз.\nМысалы: <code>150</code> немесе <code>1250.5</code>",
    "ask_volume": (
        "<b>Жүк көлемін</b> текше метрмен (м³) көрсетіңіз.\nМысалы: <code>1.2</code>\n\n"
        "💡 Қорап көлемі = ұзындығы × ені × биіктігі (метрмен)."
    ),
    "ask_packages": "<b>Қаптама санын</b> көрсетіңіз — қорап, орын немесе паллет.\nМысалы: <code>10</code>",
    "ask_transport": "<b>Көлік түрін</b> таңдаңыз:",
    "ask_date": "<b>Жөнелтудің қалаған күнін</b> таңдаңыз немесе <code>КК.АА.ЖЖЖЖ</code> пішімінде енгізіңіз:",
    "ask_phone": (
        "<b>Байланыс телефонын</b> көрсетіңіз — менеджер мәліметтерді нақтылау үшін хабарласады.\n"
        "«📱 Нөмірімді жіберу» батырмасын басыңыз немесе нөмірді енгізіңіз, мысалы <code>+7 701 123 45 67</code>."
    ),
    "phone_saved": "📱 Нөмір сақталды: {phone}",
    "sh_summary_title": "📋 <b>Өтінімді тексеріңіз</b>",
    "sh_confirm_hint": "Бәрі дұрыс болса — өтінімді растаңыз. Оны Qadam Logistics менеджері алады.",
    "sh_created": (
        "✅ <b>Өтінім рәсімделді!</b>\n\n"
        "Жөнелтім нөмірі: <code>{tracking}</code>\n"
        "Мәртебесі: ⏳ Растауды күтуде\n\n"
        "Менеджер өтінімді тексеріп, растайды. Мәртебе өзгергенде осы чатқа хабарлама келеді."
    ),
    "sh_already_processed": "Бұл өтінім өңделіп қойған.",
    "sh_cancelled": "Өтінімді рәсімдеуден бас тартылды. Деректер сақталмады.",
    "no_routes": "Қазір қолжетімді бағыттар жоқ. Кейінірек қайталап көріңіз.",
    "no_destinations": "Бұл қаладан әзірге бағыттар жоқ. Басқа қаланы таңдаңыз.",
    "no_transport": "Бұл бағыт үшін қазір белсенді тарифтер жоқ. Басқа бағытты таңдаңыз.",
    "route_unavailable": "Таңдалған бағыт қолжетімсіз. Қалаларды қайта таңдаңыз.",
    "date_today": "Бүгін",
    "date_tomorrow": "Ертең",
    "date_in_days": "{n} күннен соң",
    "err_number": "Санды енгізіңіз, мысалы <code>150</code>.",
    "err_positive": "Мән нөлден үлкен болуы керек.",
    "err_weight_max": "MVP-дегі ең жоғары салмақ — {max} кг. Ірі партиялар үшін менеджерге хабарласыңыз.",
    "err_volume_min": "Көлем тым аз. Ең азы — 0.001 м³.",
    "err_volume_max": "MVP-дегі ең жоғары көлем — {max} м³.",
    "err_packages": "Қаптама саны — 1-ден 10 000-ға дейінгі бүтін сан.",
    "err_date_format": "Күнді тану мүмкін болмады. Пішімі: <code>КК.АА.ЖЖЖЖ</code>, мысалы <code>25.11.2026</code>.",
    "err_date_past": "Күн өткен уақытта болмауы керек.",
    "err_date_far": "Күн {days} күннен кешіктірілмеуі керек.",
    "err_phone": (
        "Нөмір қате. Халықаралық пішімде енгізіңіз, мысалы "
        "<code>+77011234567</code> немесе <code>+998901234567</code>."
    ),
    "err_use_buttons": "Жоғарыдағы батырмалар арқылы нұсқаны таңдаңыз.",
    "price_title": "💰 <b>Алдын ала бағалау</b>",
    "price_base": "Бағыттың базалық құны",
    "price_weight": "Салмақ бойынша: {weight} кг × {rate}",
    "price_volume": "Көлем бойынша: {volume} м³ × {rate}",
    "price_applied": "◀ есепке алынады",
    "price_additional": "Тариф бойынша қосымша шығындар",
    "price_total": "Барлығы",
    "price_rule": "<i>Екеуінің үлкені есепке алынады: салмақ бойынша немесе көлем бойынша құн.</i>",
    "price_disclaimer": (
        "<i>⚠️ Демонстрациялық ТЕСТІЛІК тарифтер бойынша алдын ала бағалау. "
        "Тасымалдаушының расталған ұсынысы емес — түпкілікті құнды менеджер хабарлайды.</i>"
    ),
    "calc_header": "💰 <b>Құнды есептеу</b> · {step}/4-қадам",
    "calc_result_title": "💰 <b>Алдын ала есеп</b>",
    "calc_best": "Тиімдісі: {transport}",
    "btn_order_with": "🚚 Рәсімдеу: {transport}",
    "btn_new_calc": "🔁 Жаңа есеп",
    "ask_tracking": (
        "📦 <b>Жүкті бақылау</b>\n\n"
        "Жөнелтім нөмірін енгізіңіз, мысалы <code>QDM-261106-7KX4P</code>,\n"
        "немесе оны «📋 Менің жөнелтімдерім» бөлімінен ашыңыз."
    ),
    "tracking_invalid": "Нөмір осылай көрінеді: <code>QDM-261106-7KX4P</code>. Тексеріп, қайта енгізіңіз.",
    "tracking_not_found": "<code>{tracking}</code> жөнелтімі сіздің жөнелтімдеріңіздің арасынан табылмады.",
    "card_title": "📦 <b>Жөнелтім {tracking}</b>",
    "timeline_title": "<b>Жеткізу кезеңдері</b>",
    "history_title": "🕓 <b>Мәртебелер тарихы · {tracking}</b>",
    "history_empty": "Тарих әзірге бос.",
    "btn_open_shipment": "📦 Жөнелтімді ашу",
    "btn_history": "🕓 Тарих",
    "btn_refresh": "🔄 Жаңарту",
    "btn_cancel_shipment": "❌ Өтінімнен бас тарту",
    "btn_yes_cancel": "Иә, бас тарту",
    "btn_no": "Жоқ",
    "btn_back_list": "⬅️ Тізімге",
    "btn_back_card": "⬅️ Жөнелтімге",
    "sh_cancel_confirm": "<code>{tracking}</code> өтінімінен бас тартасыз ба? Бұл әрекетті қайтару мүмкін емес.",
    "sh_cancelled_by_user": "<code>{tracking}</code> өтінімінен бас тартылды.",
    "sh_cannot_cancel": "Өтінім жұмыста — одан өзіңіз бас тарта алмайсыз. Менеджерге хабарласыңыз.",
    "notify_status": "🔔 <b>Мәртебе жаңартылды</b>\n\nЖөнелтім <code>{tracking}</code>\n{route}\n\n{old} → <b>{new}</b>",
    "notify_comment": "💬 {comment}",
    "my_title": "📋 <b>Менің жөнелтімдерім</b> · барлығы: {count}\nТолық ақпарат үшін жөнелтімді таңдаңыз.",
    "my_empty": "Сізде әзірге жөнелтімдер жоқ.\nАлғашқы өтінімді рәсімдеу үшін «🚚 Жөнелтім құру» батырмасын басыңыз.",
    "ai_intro": (
        "🤖 <b>Qadam AI-көмекшісі</b>\n\n"
        "Жүкті өз сөзіңізбен сипаттаңыз — мен өтінімді толтырамын. Мысалы:\n"
        "<i>«Шымкенттен Ташкентке 150 кг киім жіберу керек, шамамен 10 қорап»</i>\n\n"
        "Сондай-ақ сервис жұмысы мен жеткізу кезеңдері туралы сұрақтарға жауап беремін.\n\n{mode}"
    ),
    "ai_mode_ai": "Режим: Gemini AI ✨",
    "ai_mode_fallback": "Режим: базалық (ЖИ-сіз) — үлгілік сөйлемдерді танимын.",
    "ai_extracted_title": "🧾 <b>Танылған өтінім</b>",
    "ai_extracted_hint": (
        "Деректерді тексеріңіз. Жетіспейтін өрістерді бот рәсімдеу кезінде сұрайды.\n"
        "Құнды жүйе тарифтер бойынша есептейді, өтінімді менеджер растайды."
    ),
    "btn_ai_fill": "✅ Рәсімдеуді жалғастыру",
    "btn_ai_calc": "💰 Құнын есептеу",
    "btn_ai_manual": "✏️ Қолмен толтыру",
    "ai_fallback_extracted": "AI қазір қолжетімсіз — деректер базалық режимде танылды.",
    "ai_cooldown": "Келесі хабарламаға дейін бірнеше секунд күтіңіз.",
    "ai_too_long": "Хабарлама тым ұзын — {max} таңбаға дейін қысқартыңыз.",
    "ai_need_text": "Мәтіндік хабарлама жіберіңіз.",
    "ai_session_expired": "Тану деректері ескірді. Жүкті қайта сипаттаңыз.",
    "faq_price": (
        "Құнды жүйе бағыт тарифтері бойынша есептейді: базалық мөлшерлеме + (салмақ × 1 кг бағасы) мен "
        "(көлем × 1 м³ бағасы) үлкені + қосымша шығындар. «💰 Құнын есептеу» батырмасын басыңыз."
    ),
    "faq_tracking": (
        "Жөнелтім мәртебесін «📦 Жүкті бақылау» бөлімінде QDM-261106-7KX4P тәрізді нөмір бойынша немесе "
        "«📋 Менің жөнелтімдерім» бөлімінде қараңыз. Мәртебе өзгерген сайын бот хабарлама жібереді."
    ),
    "faq_customs": (
        "Халықаралық бағыттарда (мысалы, Шымкент → Ташкент) «Кедендік рәсімдеуге келді» және «Кедендік "
        "рәсімдеу аяқталды» кезеңдері бар. Құжаттар бойынша менеджер кеңес береді."
    ),
    "faq_docs": (
        "Әдетте инвойс, қаптама парағы және тауарға құжаттар қажет. Нақты тізім жүк санатына байланысты — "
        "өтінім расталғаннан кейін менеджер нақтылайды."
    ),
    "faq_create": (
        "«🚚 Жөнелтім құру» батырмасын басып, 10 қадамнан өтіңіз: бағыт, жүк, салмақ, көлем, қаптама, "
        "көлік, күн және телефон. Немесе жүкті маған бір хабарламамен сипаттаңыз."
    ),
    "faq_time": (
        "Мерзім бағытқа, көлікке және кеденге байланысты. Болжамды күнді менеджер растаудан кейін хабарлайды, "
        "ал кезеңдер «📦 Жүкті бақылау» бөлімінде көрінеді."
    ),
    "faq_default": (
        "Мен тасымалды рәсімдеуге және жеткізу кезеңдерін түсінуге көмектесемін. Жүкті сипаттаңыз, мысалы: "
        "«Ташкенттен Шымкентке 200 кг электроника, 5 қорап» — мен өтінім дайындаймын."
    ),
}

TEXTS: dict[str, dict[str, str]] = {"ru": RU, "kk": KK, "en": EN}
