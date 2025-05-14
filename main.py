import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto, InputMediaVideo


from MySQL_settings import get_db_connection

TOKEN = '7777122360:AAFqDFBpG66zvf95v5T8u5TRqZT386D_8r4'
ADMIN_ID = 5257065430

bot = telebot.TeleBot(TOKEN)

user_paths = {} 
user_states = {}


@bot.message_handler(commands=['start'])
def start_handler(message):
    # if message.from_user.id != ADMIN_ID:
    #     bot.send_message(message.chat.id, "Доступ запрещён.")
    #     return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🗂 Создать подкатегорию", callback_data="create_subcat"),
        InlineKeyboardButton("➕ Добавить товар", callback_data="add_item"),
        InlineKeyboardButton("💰 Вывести каталог", callback_data="catalog"),
        InlineKeyboardButton("🗑 Удаление", callback_data="delete_menu")
    )

    bot.send_message(message.chat.id, "Привет, админ! Выберите действие:", reply_markup=markup)



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещён.")
        return

    bot.answer_callback_query(call.id)

    if call.data == "create_subcat":
        create_subcategory(call.message.chat.id)
    
    elif call.data == "add_item":
        add_item(call.message.chat.id)
    
    elif call.data == "catalog":
        browse_catalog(call.message.chat.id)

    elif call.data.startswith("cat_"):
        navigate_to_category(call)
    elif call.data == "back_main_page":
        show_categories(call.message.chat.id, parent_id=None)
    elif call.data.startswith("selectcat_"):
        handle_category_selection(call)
    elif call.data.startswith("item_"):
        handle_item_selection(call)
    elif call.data.startswith("page_"):
        handle_pagination(call)
    





    
    elif call.data == "delete_menu":
        delete_menu(call)
    
    elif call.data == "delete_categories":
        navigate_delete_categories(call)

    elif call.data.startswith("delcatnav_"):
        cat_id = int(call.data.split("_")[1])
        navigate_delete_categories(call, parent_id=cat_id)

    elif call.data.startswith("deldetcat_"):
        cat_id = int(call.data.split("_")[1])
        delete_specific_category(call, cat_id)

    elif call.data.startswith("delback_"):
        current_id = int(call.data.split("_")[1])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT parent_id FROM categories WHERE id = %s", (current_id,))
        row = cursor.fetchone()
        parent_id = row[0] if row else None
        cursor.close()
        conn.close()
        navigate_delete_categories(call, parent_id=parent_id)

    elif call.data.startswith("delete_items_"):
        parent_id = call.data.split("_")[2]
        delete_items(call, parent_id)


    elif call.data.startswith("start"):
        return_to_start(call)
    elif call.data.startswith("confirm_deleteitem_"):
        confirm_deleteitem(call)

    elif call.data.startswith("confirm_deletecat_"):
        confirm_deletecat(call)



































def delete_menu(call):
    print('delete_menu')
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🗑 Удалить категорию", callback_data="delete_categories"))
    # markup.add(InlineKeyboardButton("🗑 Удалить товар", callback_data="delete_items"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="start"))
    bot.edit_message_text("Выберите, что хотите удалить:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)





def delete_categories(call):
    print('delete_categories')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    markup = InlineKeyboardMarkup()
    for cat in categories:
        markup.add(InlineKeyboardButton(f"🗑 {cat['name']}", callback_data=f"confirm_deletecat_{cat['id']}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="delete_menu"))

    try:
        bot.edit_message_text(f"Выберите категорию для удаления (всего {len(categories)}):",
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


def delete_category_recursive(cursor, cat_id):
    print('delete_category_recursive')
    # Удаляем все товары в этой категории
    cursor.execute("DELETE FROM items WHERE category_id = %s", (cat_id,))
    
    # Получаем подкатегории
    cursor.execute("SELECT id FROM categories WHERE parent_id = %s", (cat_id,))
    subcategories = cursor.fetchall()

    for subcat in subcategories:
        delete_category_recursive(cursor, subcat[0])  # Рекурсивно удаляем подкатегорию

    # Удаляем саму категорию
    cursor.execute("DELETE FROM categories WHERE id = %s", (cat_id,))





def delete_items(call, parent_id):
    print(f"parent_id: {parent_id}")
    print(type(parent_id), parent_id) 
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title FROM items WHERE category_id = %s ORDER BY id DESC LIMIT 20", (int(parent_id),))
    items = cursor.fetchall()
    cursor.close()
    conn.close()

    markup = InlineKeyboardMarkup()
    for item in items:
        markup.add(InlineKeyboardButton(f"🗑 {item['title']}", callback_data=f"confirm_deleteitem_{item['id']}"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="delete_menu"))

    bot.edit_message_text("Выберите товар для удаления:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)





def confirm_deleteitem(call):
    print('confirm_deleteitem')
    item_id = int(call.data.split("_")[-1])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    conn.commit()
    cursor.close()
    conn.close()

    bot.answer_callback_query(call.id, "Товар удалён.")
    delete_items(call)












def confirm_deletecat(call):
    print('confirm_deletecat')
    cat_id = int(call.data.split("_")[-1])
    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем категорию и всё, что в ней
    delete_category_recursive(cursor, cat_id)
    conn.commit()

    bot.answer_callback_query(call.id, "Категория и всё содержимое удалены.")
    cursor.close()
    conn.close()
    delete_categories(call)





def return_to_start(call):
    start_handler(call.message)


























def navigate_delete_categories(call, parent_id=None):
    print('navigate_delete_categories')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if parent_id:
        cursor.execute("SELECT name FROM categories WHERE id = %s", (parent_id,))
        parent = cursor.fetchone()
        title = f"🗂 Подкатегории '{parent['name']}':"
    else:
        title = "🗂 Категории для удаления:"

    if parent_id is None:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    else:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id = %s", (parent_id,))

    categories = cursor.fetchall()

    markup = InlineKeyboardMarkup()
    for cat in categories:
        markup.add(InlineKeyboardButton(f"📁 {cat['name']}", callback_data=f"delcatnav_{cat['id']}"))

    if parent_id:
        cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (parent_id,))
        has_subcats = cursor.fetchone()['COUNT(*)']
        cursor.execute("SELECT COUNT(*) FROM items WHERE category_id = %s", (parent_id,))
        has_items = cursor.fetchone()['COUNT(*)']

        if has_subcats == 0 and has_items == 0:
            markup.add(InlineKeyboardButton("🗑 Удалить эту категорию", callback_data=f"deldetcat_{parent_id}"))
        elif has_items >= 1:
            markup.add(InlineKeyboardButton("🗑 Удалить товар", callback_data=f"delete_items_{parent_id}"))

    if parent_id:
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data=f"delback_{parent_id}"))
    else:
        markup.add(InlineKeyboardButton("🔙 Назад", callback_data="delete_menu"))

    bot.edit_message_text(title, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    cursor.close()
    conn.close()











def delete_specific_category(call, cat_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (cat_id,))
    has_subcats = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM items WHERE category_id = %s", (cat_id,))
    has_items = cursor.fetchone()[0]

    if has_subcats or has_items:
        bot.answer_callback_query(call.id, "❌ Категория не пуста.", show_alert=True)
    else:
        cursor.execute("DELETE FROM categories WHERE id = %s", (cat_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Категория удалена.")

    cursor.close()
    conn.close()
    navigate_delete_categories(call, parent_id=None)
























def browse_catalog(chat_id):
    user_states[chat_id] = {"action": "view_catalog", "path": []}
    show_category_selector(chat_id, parent_id=None)




def handle_category_selection(call):
    user_id = call.message.chat.id
    if user_id not in user_states:
        return

    action_state = user_states[user_id]

    if call.data == "selectcat_back":
        if action_state["path"]:
            action_state["path"].pop()
        parent_id = action_state["path"][-1] if action_state["path"] else None
        show_category_selector(user_id, parent_id, message_id=call.message.message_id)

    elif call.data == "selectcat_done":
        path = action_state["path"]
        if not path:
            create_category(user_id)
            return
        category_id = path[-1]
        if action_state["action"] == "create_subcat":
            msg = bot.send_message(user_id, "Введите имя подкатегории:")
            bot.register_next_step_handler(msg, lambda m: save_subcategory(m, category_id, get_path_string(path)))
        elif action_state["action"] == "add_item":
            msg = bot.send_message(user_id, "Введите название товара:")
            bot.register_next_step_handler(msg, lambda m: ask_for_item_description(m, get_path_string(path), category_id))
        del user_states[user_id]

    else:
        # Пользователь выбрал категорию
        cat_id = int(call.data.split("_")[1])
        action_state["path"].append(cat_id)

        # Если действие "Просмотр каталога" — сразу показываем
        if action_state["action"] == "view_catalog":
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (cat_id,))
            subcategory_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            if subcategory_count > 0:
                show_category_selector(user_id, cat_id, message_id=call.message.message_id)
            else:
                show_items(user_id, cat_id)
                del user_states[user_id]
        else:
            # Для добавления или создания подкатегорий — продолжаем выбор
            show_category_selector(user_id, cat_id, message_id=call.message.message_id)




def get_path_string(path_ids):
    conn = get_db_connection()
    cursor = conn.cursor()
    names = []
    for cat_id in path_ids:
        cursor.execute("SELECT name FROM categories WHERE id = %s", (cat_id,))
        row = cursor.fetchone()
        if row:
            names.append(row[0])
    cursor.close()
    conn.close()
    return " > ".join(names)



# Показ категорий
def show_categories(chat_id, parent_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if parent_id is None:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    else:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id = %s", (parent_id,))

    categories = cursor.fetchall()
    markup = InlineKeyboardMarkup()

    for category in categories:
        markup.add(InlineKeyboardButton(text=category["name"], callback_data=f"cat_{category['id']}"))

    if parent_id is not None:
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="selectcat_back"))
        if user_states.get(chat_id, {}).get("action") != "view_catalog":
            markup.add(InlineKeyboardButton("✅ Выбрать эту категорию", callback_data="selectcat_done"))

    bot.send_message(chat_id, "Выберите категорию:", reply_markup=markup)

    cursor.close()
    conn.close()




def show_items(chat_id, category_id, page=0):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Получаем все товары в категории
    cursor.execute("SELECT id, title FROM items WHERE category_id = %s", (category_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()

    items_per_page = 8  # Количество товаров на странице
    total_pages = (len(items) - 1) // items_per_page + 1  # Общее число страниц
    
    # Получаем товары для текущей страницы
    start = page * items_per_page
    end = start + items_per_page
    page_items = items[start:end]

    text = f"<b>Товары в категории:</b> (Страница {page+1}/{total_pages})\n\n"
    markup = InlineKeyboardMarkup(row_width=2)  # 2 колонки кнопок

    buttons = []
    for item in page_items:
        buttons.append(InlineKeyboardButton(item['title'], callback_data=f"item_{item['id']}"))

    # Размещаем кнопки **по 4 в ряд (2 столбца × 4 строки)**
    for i in range(0, len(buttons), 2):
        if i+1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])  # Добавляем две кнопки в строку
        else:
            markup.add(buttons[i])  # Если нечетное кол-во, добавляем последнюю кнопку

    # Кнопки пагинации
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("◀ Назад", callback_data=f"page_{category_id}_{page-1}"))
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("Вперед ▶", callback_data=f"page_{category_id}_{page+1}"))

    if pagination_buttons:
        markup.row(*pagination_buttons)  # Размещаем кнопки пагинации в одной строке

    bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)




def handle_pagination(call):
    _, category_id, page = call.data.split("_")
    category_id = int(category_id)
    page = int(page)

    # Удаляем старое сообщение и отправляем обновленное
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_items(call.message.chat.id, category_id, page)







# Словарь для хранения `message_id` медиа-сообщений
media_messages = {}



def handle_item_selection(call):
    item_id = int(call.data.split("_")[1])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT title, description FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()

    from telebot.types import InputMediaPhoto, InputMediaVideo

    if item:
        title = item["title"]
        description = item["description"]
        photo_path1 = r'C:\mylife\Git_project\filteg_tg\3txJdpHYuuk.jpg'
        video_path = r'C:\mylife\Git_project\filteg_tg\Администратор_ Windows PowerShell 2025-02-21 18-06-27.mp4'
        photo_path2 = r'C:\mylife\Git_project\filteg_tg\1663986735_10-phonoteka-org-p-oboi-na-telefon-v-stile-fonk-krasivo-11.png'
        media = []

        try:
            with open(video_path, 'rb') as video_file:
                video_data = video_file.read()
                media.append(InputMediaVideo(video_data, caption=f"<b>{title}</b>\n\n{description}", parse_mode='HTML'))
            
            with open(photo_path1, 'rb') as photo_file:
                photo_data = photo_file.read()
                media.append(InputMediaPhoto(photo_data))
            
            with open(photo_path2, 'rb') as photo_file:
                photo_data = photo_file.read()
                media.append(InputMediaPhoto(photo_data))

            # Удаляем все предыдущие сообщения медиа-группы
            if call.message.chat.id in media_messages:
                for msg_id in media_messages[call.message.chat.id]:
                    bot.delete_message(call.message.chat.id, msg_id)

            # Отправляем новую медиа-группу
            sent_messages = bot.send_media_group(call.message.chat.id, media)

            # Запоминаем `message_id` всех отправленных сообщений
            media_messages[call.message.chat.id] = [msg.message_id for msg in sent_messages]

        except FileNotFoundError:
            bot.send_message(call.message.chat.id, "Ошибка: один из файлов не найден.")

    else:
        bot.send_message(call.message.chat.id, "Товар не найден.")






#Назад
def navigate_to_category(call):
    cat_id = int(call.data.split("_")[1])
    path = user_paths.get(call.message.chat.id, [])
    path.append(cat_id)
    user_paths[call.message.chat.id] = path

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (cat_id,))
    subcategory_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    bot.delete_message(call.message.chat.id, call.message.message_id)
    if subcategory_count > 0:
        show_categories(call.message.chat.id, cat_id)
    else:
        show_items(call.message.chat.id, cat_id)




# Создать Категории
def create_category(chat_id):
    msg = bot.send_message(chat_id, "Введите название новой категории:")
    bot.register_next_step_handler(msg, process_category_name)


def process_category_name(message):
    name = message.text.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM categories WHERE name = %s AND parent_id IS NULL", (name,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Категория уже существует.")
    else:
        cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
        conn.commit()
        bot.send_message(message.chat.id, f"Категория '{name}' создана.")
    cursor.close()
    conn.close()



#Создать Подкатегории
def create_subcategory(chat_id):
    user_states[chat_id] = {"action": "create_subcat", "path": []}
    show_category_selector(chat_id, parent_id=None)


def add_item(chat_id):
    user_states[chat_id] = {"action": "add_item", "path": []}
    show_category_selector(chat_id, parent_id=None)


def show_category_selector(chat_id, parent_id, message_id=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if parent_id is None:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    else:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id = %s", (parent_id,))

    categories = cursor.fetchall()
    markup = InlineKeyboardMarkup()

    for cat in categories:
        markup.add(InlineKeyboardButton(cat['name'], callback_data=f"selectcat_{cat['id']}"))
        
    
    if parent_id is not None:
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="selectcat_back"))
    if user_states.get(chat_id, {}).get("action") != "view_catalog":
        markup.add(InlineKeyboardButton("✅ Выбрать эту категорию", callback_data="selectcat_done"))

    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="start"))

    if message_id:
        bot.edit_message_text("Выберите категорию:", chat_id=chat_id, message_id=message_id, reply_markup=markup)
    
    else:
        bot.send_message(chat_id, "Выберите категорию:", reply_markup=markup)

    cursor.close()
    conn.close()



def save_subcategory(message, parent_id, path):
    name = message.text.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM categories WHERE name = %s AND parent_id = %s", (name, parent_id))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Такая подкатегория уже существует.")
    else:
        cursor.execute("INSERT INTO categories (name, parent_id) VALUES (%s, %s)", (name, parent_id))
        conn.commit()
        bot.send_message(message.chat.id, f"Подкатегория '{name}' добавлена в '{path}'.")
    cursor.close()
    conn.close()




# Добавление товара
def ask_for_item_description(message, path, category_id):
    title = message.text.strip()
    msg = bot.send_message(message.chat.id, "Введите описание товара:")
    bot.register_next_step_handler(msg, lambda m: ask_for_item_photo(m, path, category_id, title))


def ask_for_item_photo(message, path, category_id, title):
    description = message.text.strip()
    msg = bot.send_message(message.chat.id, "Отправьте фото товара или напишите 'пропустить':")
    bot.register_next_step_handler(msg, lambda m: ask_for_item_video(m, path, category_id, title, description))


def ask_for_item_video(message, path, category_id, title, description):
    photo_id = None
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
    elif message.text.lower() != 'пропустить':
        bot.send_message(message.chat.id, "Пожалуйста, отправьте фото или напишите 'пропустить'")
        return
    msg = bot.send_message(message.chat.id, "Отправьте видео товара или напишите 'пропустить':")
    bot.register_next_step_handler(msg, lambda m: save_item(m, path, category_id, title, description, photo_id))


def save_item(message, path, category_id, title, description, photo_id):
    video_id = None
    if message.content_type == 'video':
        video_id = message.video.file_id
    elif message.text.lower() != 'пропустить':
        bot.send_message(message.chat.id, "Пожалуйста, отправьте видео или напишите 'пропустить'")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (title, description, photo_id, video_id, category_id) VALUES (%s, %s, %s, %s, %s)",
        (title, description, photo_id, video_id, category_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    bot.send_message(message.chat.id, f"Товар '{title}' успешно добавлен в {path} > {title}.")


bot.polling()
