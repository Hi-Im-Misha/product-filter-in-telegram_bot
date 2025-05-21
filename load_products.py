import pandas as pd
from MySQL_settings import get_db_connection

def safe_value(val):
    if pd.isna(val) or val == '':
        return None
    if isinstance(val, str) and val.strip().lower() == 'nan':
        return None
    return val

def safe_from_xlsx(parent_id):
    file_path = r'C:\mylife\Git_project\filteg_tg\catalog.xlsx'
    print(f"Загрузка данных для категории {parent_id} из файла {file_path}...")

    df = pd.read_excel(file_path, sheet_name='Sheet 1')

    conn = get_db_connection()
    cursor = conn.cursor()

    sql = "INSERT INTO items (title, description, photo_id, video_id, category_id) VALUES (%s, %s, %s, %s, %s)"

    for _, row in df.iterrows():
        title = safe_value(row.get('title')) 
        description = safe_value(row.get('description')) 
        photo_id = safe_value(row.get('photo_id')) 
        video_id = safe_value(row.get('video_id'))  
        category_id = parent_id

        cursor.execute(sql, (title, description, photo_id, video_id, category_id))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Загрузка завершена для категории {parent_id}.")


