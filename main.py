import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputMediaPhoto, InputMediaVideo
from load_products import safe_from_xlsx

from MySQL_settings import get_db_connection

TOKEN = '7724774409:AAF09GhDB7tHZlpnB3NSqraDBZjl4J7SV44'
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
        add_item_func(call.message.chat.id)
    
    elif call.data == "catalog":
        browse_catalog(call.message.chat.id)

    elif call.data.startswith("selectcat_"):
        handle_category_selection(call)
    
    elif call.data.startswith("item_"):
        handle_item_selection(call)
    
    elif call.data.startswith("page_"):
        handle_pagination(call)
    

    
    elif call.data == "delete_menu": # ??????
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
        delback_(call)

    elif call.data.startswith("delete_items_"):
        parent_id = call.data.split("_")[2]
        delete_items(call, parent_id)


    elif call.data.startswith("start"):
        return_to_start(call)
    elif call.data.startswith("confirm_deleteitem_"):
        deleteitem_confirm(call)


    elif call.data.startswith("load_xlsx_"):
        parent_id = call.data.split("_")[2]
        management_load_xlsx(parent_id)

def delete_menu(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🗑 Удалить категорию", callback_data="delete_categories"))
    markup.add(InlineKeyboardButton("🔙 На главную", callback_data="start"))
    bot.edit_message_text("Выберите, что хотите удалить:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)




def delback_(call):
    user_id = call.from_user.id
    current_id = int(call.data.split("_")[1])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT parent_id FROM categories WHERE id = %s", (current_id,))
    row = cursor.fetchone()
    parent_id = row[0] if row else None
    cursor.close()
    conn.close()

    action_state = user_states.get(user_id, {})
    path = action_state.get("path", [])
    if path and path[-1] == current_id:
        path.pop()  
    user_states[user_id] = {"path": path}

    navigate_delete_categories(call, parent_id=parent_id)



def delete_items(call, parent_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title FROM items WHERE category_id = %s ORDER BY id DESC LIMIT 20", (int(parent_id),))

    items = cursor.fetchall()
    cursor.close()
    conn.close()

    markup = InlineKeyboardMarkup()
    for item in items:
        markup.add(InlineKeyboardButton(f"🗑 {item['title']}", callback_data=f"confirm_deleteitem_{item['id']}"))
    
    back_callback = f"delback_{parent_id}" if parent_id else "delete_menu"
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_callback))
    markup.add(InlineKeyboardButton("🔙 На главную", callback_data="start"))
    bot.edit_message_text("Выберите товар для удаления:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)



def deleteitem_confirm(call):
    item_id = int(call.data.split("_")[-1])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT category_id FROM items WHERE id = %s", (item_id,))
    row = cursor.fetchone()
    parent_id = row['category_id'] if row else None

    if parent_id is not None:
        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Товар удалён.")
        delete_items(call, parent_id)
    else:
        bot.answer_callback_query(call.id, "Ошибка: товар не найден.", show_alert=True)

    cursor.close()
    conn.close()



def return_to_start(call):
    start_handler(call.message)





def navigate_delete_categories(call, parent_id=None):
    user_id = call.from_user.id
    update_user_path(user_id, parent_id)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    path = user_states[user_id].get("path", [])
    title = build_title(cursor, parent_id, path)
    categories = get_categories(cursor, parent_id)
    markup = del_build_category_markup(cursor, categories, parent_id)

    bot.edit_message_text(title, chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)

    cursor.close()
    conn.close()


def update_user_path(user_id, parent_id):
    action_state = user_states.get(user_id, {})
    path = action_state.get("path", [])
    if parent_id:
        if not path or path[-1] != parent_id:
            path.append(parent_id)
    else:
        path = []
    user_states[user_id] = {"path": path}



def build_title(cursor, parent_id, path):
    if parent_id:
        path_str = get_path_string(path)
        return f"🗂 Подкатегории '{path_str}':"
    else:
        return "🗂 Категории для удаления:"



def get_categories(cursor, parent_id):
    if parent_id is None:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    else:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id = %s", (parent_id,))
    return cursor.fetchall()


def del_build_category_markup(cursor, categories, parent_id):
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

    back_callback = f"delback_{parent_id}" if parent_id else "delete_menu"
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_callback))
    markup.add(InlineKeyboardButton("🔙 На главную", callback_data="start"))
    return markup



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
        user_states[user_id] = {"action": "view_catalog", "path": []}


    action_state = user_states[user_id]
    action = call.data
    
    if action == "selectcat_back":
        handle_back_action(user_id, action_state, call.message.message_id)

    elif action == "selectcat_done":
        handle_done_action(user_id, action_state)

    elif action.startswith("selectcat_"):
        print(action)
        cat_id = int(action.split("_")[1])
        handle_category_click(user_id, action_state, cat_id, call.message.message_id)



def handle_back_action(user_id, action_state, message_id):
    if action_state["path"]:
        action_state["path"].pop()
    parent_id = action_state["path"][-1] if action_state["path"] else None
    show_category_selector(user_id, parent_id, message_id=message_id)



def handle_done_action(user_id, action_state):
    path = action_state["path"]
    if not path:
        create_category(user_id)
        return

    category_id = path[-1]
    action = action_state["action"]
    path_str = get_path_string(path)

    if action == "create_subcat":
        msg = bot.send_message(user_id, "Введите имя подкатегории:")
        bot.register_next_step_handler(msg, lambda m: save_subcategory(m, category_id, path_str))

    elif action == "add_item":
        msg = bot.send_message(user_id, "Введите название товара:")
        bot.register_next_step_handler(msg, lambda m: ask_for_item_description(m, path_str, category_id))
    
    if user_states[user_id]["path"]:
        user_states[user_id]["path"].pop() 



def handle_category_click(user_id, action_state, cat_id, message_id):
    action_state["path"].append(cat_id)
    action = action_state["action"]

    if action == "view_catalog":
        if has_subcategories(cat_id):
            show_category_selector(user_id, cat_id, message_id=message_id)
        else:
            show_items(user_id, cat_id)
            if user_states[user_id]["path"]:
                user_states[user_id]["path"].pop()

            show_category_selector(user_id, cat_id, message_id=message_id)
    else:   
        show_category_selector(user_id, cat_id, message_id=message_id)







# show_category -----------------------------------------------------------------------------------------------------------------------------

def show_category_selector(chat_id, parent_id, message_id=None):
    ensure_user_state(chat_id)
    show_update_user_path(chat_id, parent_id)
    categories = fetch_categories(parent_id)
    markup = build_category_markup(chat_id, categories, parent_id)
    send_or_edit_category_message(chat_id, message_id, markup, parent_id)


def ensure_user_state(chat_id):
    if chat_id not in user_states:
        user_states[chat_id] = {"action": None, "path": []}


def show_update_user_path(chat_id, parent_id):
    if parent_id is not None:
        path = user_states[chat_id]["path"]
        if not path or path[-1] != parent_id:
            path.append(parent_id)


def fetch_categories(parent_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if parent_id is None:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS NULL")
    else:
        cursor.execute("SELECT id, name FROM categories WHERE parent_id = %s", (parent_id,))
    
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return categories


def build_category_markup(chat_id, categories, parent_id):
    markup = InlineKeyboardMarkup()

    for cat in categories:
        markup.add(InlineKeyboardButton(f"📁 {cat['name']}", callback_data=f"selectcat_{cat['id']}"))

    user_action = user_states.get(chat_id, {}).get("action")

    if user_action == "add_item":
        if parent_id is not None:
            if not has_subcategories(parent_id):
                markup.add(InlineKeyboardButton("1️⃣✅ Добавить в ручную в эту категорию", callback_data="selectcat_done"))
                markup.add(InlineKeyboardButton("📦✅ Добавить из файла в эту категорию", callback_data=f"load_xlsx_{parent_id}"))
            else:
                markup.add(InlineKeyboardButton("❌ Нельзя добавить: есть подкатегории", callback_data="selectcat_back"))

    elif user_action != "view_catalog":
        if parent_id is not None:
            if not has_items(parent_id):
                markup.add(InlineKeyboardButton("✅ Выбрать эту категорию", callback_data="selectcat_done"))
            else:
                markup.add(InlineKeyboardButton("❌ Нельзя выбрать: есть товары", callback_data="selectcat_back"))
        else:
            markup.add(InlineKeyboardButton("✅ Создать категорию", callback_data="selectcat_done"))

    if parent_id is not None:
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="selectcat_back"))

    markup.add(InlineKeyboardButton("🔙 На главную", callback_data="start"))

    return markup






def management_load_xlsx(parent_id):
    safe_from_xlsx(parent_id)








# проверка на наличие товара
def has_items(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items WHERE category_id = %s", (category_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0




def send_or_edit_category_message(chat_id, message_id, markup, parent_id):
    
    path_str = path_show_category_selector(chat_id, parent_id)
    text = f"Выберите категорию: {path_str}" if message_id else "Выберите категорию:"
    
    if message_id:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)



def path_show_category_selector(chat_id, parent_id):
        user_id = chat_id 
        path = user_states.setdefault(user_id, {"action": "view_catalog", "path": []})["path"]
        user_states[user_id]["path"] = path
        path_str = get_path_string(path)
        return path_str




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



# -----------------------------------------------------------------------------------------------------------------------------



def has_subcategories(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (category_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0







def show_items(chat_id, category_id, page=0):
    items = get_items_by_category(category_id)
    total_items = len(items) 
    if not items:
        bot.send_message(chat_id, "❌ В этой категории нет товаров.")
        return
    markup, page_items, total_pages = build_items_markup(items, category_id, page)
    text = f"Страница {page+1}/{total_pages} \nВсего товаров: {total_items}"
    bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)


def build_items_markup(items, category_id, page, items_per_page=8):
    total_pages = (len(items) - 1) // items_per_page + 1
    start = page * items_per_page
    end = start + items_per_page
    page_items = items[start:end]

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(item['title'], callback_data=f"item_{item['id']}") for item in page_items]
    
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    pagination = []
    if page > 0:
        pagination.append(InlineKeyboardButton("◀ Назад", callback_data=f"page_{category_id}_{page-1}"))
    if page < total_pages - 1:
        pagination.append(InlineKeyboardButton("Вперед ▶", callback_data=f"page_{category_id}_{page+1}"))

    if pagination:
        markup.row(*pagination)

    return markup, page_items, total_pages




def get_items_by_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title FROM items WHERE category_id = %s", (category_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return items



def handle_pagination(call):
    _, category_id, page = call.data.split("_")
    category_id = int(category_id)
    page = int(page)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_items(call.message.chat.id, category_id, page)





media_messages = {}


def handle_item_selection(call):
    item_id = int(call.data.split("_")[1])
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT title, description FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()

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

            if call.message.chat.id in media_messages:
                for msg_id in media_messages[call.message.chat.id]:
                    bot.delete_message(call.message.chat.id, msg_id)

            sent_messages = bot.send_media_group(call.message.chat.id, media)

            media_messages[call.message.chat.id] = [msg.message_id for msg in sent_messages]

        except FileNotFoundError:
            bot.send_message(call.message.chat.id, "Ошибка: один из файлов не найден.")

    else:
        bot.send_message(call.message.chat.id, "Товар не найден.")






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




def create_subcategory(chat_id):
    user_states[chat_id] = {"action": "create_subcat", "path": []}
    show_category_selector(chat_id, parent_id=None)


def add_item_func(chat_id):
    user_states[chat_id] = {"action": "add_item", "path": []}
    show_category_selector(chat_id, parent_id=None)






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
        bot.send_message(message.chat.id, f"Подкатегория '{name}' добавлена в '{path}' > {name}.")
    cursor.close()
    conn.close()




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