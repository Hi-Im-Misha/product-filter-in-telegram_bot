import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from MySQL_settings import get_db_connection

TOKEN = '7777122360:AAFqDFBpG66zvf95v5T8u5TRqZT386D_8r4'
ADMIN_ID = 5257065430

bot = telebot.TeleBot(TOKEN)

user_paths = {} 
user_states = {}

# /start
@bot.message_handler(commands=['start'])
def start_handler(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "Доступ запрещён.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📁 Создать категорию", callback_data="create_cat"),
        InlineKeyboardButton("🗂 Создать подкатегорию", callback_data="create_subcat"),
        InlineKeyboardButton("➕ Добавить товар", callback_data="add_item"),
        InlineKeyboardButton("💰 Вывести каталог", callback_data="catalog")
    )

    bot.send_message(message.chat.id, "Привет, админ! Выберите действие:", reply_markup=markup)



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Доступ запрещён.")
        return

    bot.answer_callback_query(call.id)

    if call.data == "create_cat":
        create_category(call.message.chat.id)
    
    elif call.data == "create_subcat":
        create_subcategory(call.message.chat.id)
    
    elif call.data == "add_item":
        add_item(call.message.chat.id)
    
    elif call.data == "catalog":
        show_categories(call.message.chat.id, parent_id=None)

    elif call.data == "back":
        navigate_back(call)
    elif call.data.startswith("cat_"):
        navigate_to_category(call)
    elif call.data == "back_main_page":
        show_categories(call.message.chat.id, parent_id=None)
    elif call.data.startswith("selectcat_"):
        handle_category_selection(call)

        




def handle_category_selection(call):
    user_id = call.message.chat.id
    if user_id not in user_states:
        return

    action_state = user_states[user_id]

    if call.data == "selectcat_back":
        if action_state["path"]:
            action_state["path"].pop()
        parent_id = action_state["path"][-1] if action_state["path"] else None
        show_category_selector(user_id, parent_id)
    elif call.data == "selectcat_done":
        if action_state["action"] == "create_subcat":
            path = action_state["path"]
            if not path:
                bot.send_message(user_id, "Сначала выберите категорию.")
                return
            parent_id = path[-1]
            msg = bot.send_message(user_id, "Введите имя подкатегории:")
            bot.register_next_step_handler(msg, lambda m: save_subcategory(m, parent_id, get_path_string(path)))
            del user_states[user_id]
        elif action_state["action"] == "add_item":
            # Тоже самое: запрашиваем название товара
            path = action_state["path"]
            category_id = path[-1]
            msg = bot.send_message(user_id, "Введите название товара:")
            bot.register_next_step_handler(msg, lambda m: ask_for_item_description(m, get_path_string(path), category_id))
            del user_states[user_id]
    else:
        cat_id = int(call.data.split("_")[1])
        action_state["path"].append(cat_id)
        show_category_selector(user_id, cat_id)




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
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    markup.add(InlineKeyboardButton("⬅️ На главную", callback_data="back_main_page"))

    bot.send_message(chat_id, "Выберите категорию:", reply_markup=markup)

    cursor.close()
    conn.close()




def show_items(chat_id, category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items WHERE category_id = %s", (category_id,))
    items = cursor.fetchall()
    if items:
        for item in items:
            text = f"<b>{item['title']}</b>\n{item['description']}"
            bot.send_message(chat_id, text, parse_mode='HTML')
    else:
        bot.send_message(chat_id, "Нет товаров в этой категории.")
    cursor.close()
    conn.close()



#Назад
def navigate_to_category(call):
    print('Категория выбрана')
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


def navigate_back(call):
    print('⬅️ Назад нажата')
    user_id = call.message.chat.id
    if user_id not in user_paths or not user_paths[user_id]:
        return show_categories(user_id, parent_id=None)

    user_paths[user_id].pop()  # удаляем текущий
    if user_paths[user_id]:
        parent_id = user_paths[user_id][-1]
        show_categories(user_id, parent_id=parent_id)
    else:
        show_categories(user_id, parent_id=None)





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



def show_category_selector(chat_id, parent_id):
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
    markup.add(InlineKeyboardButton("✅ Выбрать эту категорию", callback_data="selectcat_done"))
    bot.send_message(chat_id, "Выберите категорию:", reply_markup=markup)

    cursor.close()
    conn.close()



def ask_for_subcat_name(message):
    path = message.text.strip()
    parent_id = get_category_id_by_path(path)
    if parent_id is None:
        bot.send_message(message.chat.id, "Путь не найден.")
        return
    msg = bot.send_message(message.chat.id, f"Введите имя подкатегории для {path}:")
    bot.register_next_step_handler(msg, lambda m: save_subcategory(m, parent_id, path))


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


def get_category_id_by_path(path):
    parts = [p.strip() for p in path.split(">")]
    conn = get_db_connection()
    cursor = conn.cursor()
    parent_id = None
    for part in parts:
        if parent_id is None:
            cursor.execute("SELECT id FROM categories WHERE name = %s AND parent_id IS NULL", (part,))
        else:
            cursor.execute("SELECT id FROM categories WHERE name = %s AND parent_id = %s", (part, parent_id))
        row = cursor.fetchone()
        if row is None:
            cursor.close()
            conn.close()
            return None
        parent_id = row[0]
    cursor.close()
    conn.close()
    return parent_id


# Добавление товара
def add_item(chat_id):
    user_states[chat_id] = {"action": "add_item", "path": []}
    show_category_selector(chat_id, parent_id=None)



def ask_for_item_title(message):
    path = message.text.strip()
    category_id = get_category_id_by_path(path)
    if category_id is None:
        bot.send_message(message.chat.id, "Путь не найден.")
        return
    msg = bot.send_message(message.chat.id, "Введите название товара:")
    bot.register_next_step_handler(msg, lambda m: ask_for_item_description(m, path, category_id))


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

    bot.send_message(message.chat.id, f"Товар '{title}' успешно добавлен в {path}.")


bot.polling()
