import sqlite3
import os
import sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Characters table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        main_prompt TEXT,
        front_view_prompt TEXT,
        side_view_prompt TEXT,
        back_view_prompt TEXT,
        concept_art_url TEXT
    )
    ''')
    # Storyboards table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS storyboards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scene_index INTEGER,
        description TEXT,
        character_name TEXT,
        dialogue TEXT,
        bgm_sfx TEXT,
        image_prompt TEXT,
        image_url TEXT,
        video_url TEXT,
        duration INTEGER
    )
    ''')
    conn.commit()
    conn.close()

def add_character(name, main_prompt, front, side, back, concept_url=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO characters (name, main_prompt, front_view_prompt, side_view_prompt, back_view_prompt, concept_art_url)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, main_prompt, front, side, back, concept_url))
        conn.commit()
    except Exception as e:
        print(f"Error adding character: {e}")
    finally:
        conn.close()

def get_character(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM characters WHERE name = ?', (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "name": row[1],
            "main_prompt": row[2],
            "front": row[3],
            "side": row[4],
            "back": row[5],
            "concept_url": row[6]
        }
    return None

def add_storyboard(scene_idx, description, char_name, dialogue, bgm_sfx, img_prompt, img_url=None, vid_url=None, duration=4):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO storyboards (scene_index, description, character_name, dialogue, bgm_sfx, image_prompt, image_url, video_url, duration)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (scene_idx, description, char_name, dialogue, bgm_sfx, img_prompt, img_url, vid_url, duration))
    conn.commit()
    conn.close()
