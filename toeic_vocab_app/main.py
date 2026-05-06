# main.py
"""
TOEIC 智能背单词 App (KivyMD)
Android APK 入口
"""
__version__ = "1.0.0"

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDRoundFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import MDSnackbar

# TTS
try:
    from plyer import tts
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

# ========== 模型 ==========
class WordEntry:
    def __init__(self, id=None, word="", meanings=None, pos="noun", phonetic="", toeic_sentence=""):
        self.id = id
        self.word = word
        self.meanings = meanings or []
        self.pos = pos
        self.phonetic = phonetic
        self.toeic_sentence = toeic_sentence

class ReviewItem:
    def __init__(self, word_id, stage=0, learning_step=0, interval_days=1,
                 review_count=0, correct_count=0, next_review_at=None,
                 last_review_at=None, is_in_unknown_list=0):
        self.word_id = word_id
        self.stage = stage
        self.learning_step = learning_step
        self.interval_days = interval_days
        self.review_count = review_count
        self.correct_count = correct_count
        self.next_review_at = next_review_at
        self.last_review_at = last_review_at
        self.is_in_unknown_list = is_in_unknown_list

# ========== 数据库 ==========
class Database:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE NOT NULL,
            phonetic TEXT,
            meanings TEXT NOT NULL,
            pos TEXT,
            toeic_sentence TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS review_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER UNIQUE NOT NULL,
            stage INTEGER DEFAULT 0,
            learning_step INTEGER DEFAULT 0,
            interval_days INTEGER DEFAULT 1,
            review_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            next_review_at TEXT,
            last_review_at TEXT,
            is_in_unknown_list INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            status INTEGER NOT NULL,
            duration_seconds INTEGER
        )''')
        self.conn.commit()

    def import_json(self, json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        c = self.conn.cursor()
        count = 0
        for item in data:
            try:
                meanings = item['meanings'] if isinstance(item['meanings'], list) else [item['meanings']]
                c.execute('''INSERT INTO words (word, phonetic, meanings, pos, toeic_sentence)
                    VALUES (?,?,?,?,?)''',
                    (item['word'], item.get('phonetic',''), '\uFF1B'.join(meanings),
                     item.get('pos','noun'), item.get('toeic_sentence','')))
                word_id = c.lastrowid
                c.execute('''INSERT INTO review_items (word_id, stage)
                    VALUES (?,0)''', (word_id,))
                count += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return count

    def get_due_words(self, limit=50):
        c = self.conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''SELECT w.* FROM words w
            INNER JOIN review_items r ON w.id = r.word_id
            WHERE r.next_review_at IS NULL OR r.next_review_at <= ?
            ORDER BY r.stage ASC, r.next_review_at ASC
            LIMIT ?''', (now, limit))
        return [self._row_to_word(r) for r in c.fetchall()]

    def get_review_item(self, word_id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM review_items WHERE word_id=?', (word_id,))
        r = c.fetchone()
        if not r:
            return None
        return ReviewItem(
            word_id=r[1], stage=r[2], learning_step=r[3], interval_days=r[4],
            review_count=r[5], correct_count=r[6],
            next_review_at=datetime.fromisoformat(r[7]) if r[7] else None,
            last_review_at=datetime.fromisoformat(r[8]) if r[8] else None,
            is_in_unknown_list=r[9]
        )

    def update_review(self, item):
        c = self.conn.cursor()
        c.execute('''UPDATE review_items SET
            stage=?, learning_step=?, interval_days=?, review_count=?, correct_count=?,
            next_review_at=?, last_review_at=?, is_in_unknown_list=?
            WHERE word_id=?''',
            (item.stage, item.learning_step, item.interval_days,
             item.review_count, item.correct_count,
             item.next_review_at.isoformat() if item.next_review_at else None,
             item.last_review_at.isoformat() if item.last_review_at else None,
             item.is_in_unknown_list, item.word_id))
        self.conn.commit()

    def log_study(self, word_id, status, duration=None):
        c = self.conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('''INSERT INTO study_logs (date, word_id, status, duration_seconds)
            VALUES (?,?,?,?)''', (today, word_id, status, duration))
        self.conn.commit()

    def get_unknown_words(self):
        c = self.conn.cursor()
        c.execute('''SELECT w.* FROM words w
            INNER JOIN review_items r ON w.id = r.word_id
            WHERE r.is_in_unknown_list = 1
            ORDER BY r.last_review_at DESC''')
        return [self._row_to_word(r) for r in c.fetchall()]

    def get_stats(self, days=7):
        c = self.conn.cursor()
        results = []
        for i in range(days-1, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            c.execute('SELECT status, COUNT(*) FROM study_logs WHERE date=? GROUP BY status', (d,))
            rows = dict(c.fetchall())
            total = sum(rows.values()) if rows else 0
            familiar = rows.get(2, 0)
            accuracy = familiar / total if total else 0
            results.append({'date': d, 'total': total, 'familiar': familiar,
                            'vague': rows.get(1,0), 'unknown': rows.get(0,0), 'accuracy': accuracy})
        return results

    def get_word_count(self):
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM words')
        return c.fetchone()[0]

    def get_due_count(self):
        c = self.conn.cursor()
        now = datetime.now().isoformat()
        c.execute('SELECT COUNT(*) FROM review_items WHERE next_review_at IS NULL OR next_review_at<=?', (now,))
        return c.fetchone()[0]

    def _row_to_word(self, r):
        return WordEntry(
            id=r[0], word=r[1], phonetic=r[2] or '', meanings=r[3].split('\uFF1B') if r[3] else [],
            pos=r[4] or 'noun', toeic_sentence=r[5] or ''
        )

# ========== SRS ==========
class SRSEngine:
    LEARNING_INTERVALS = [5, 30, 1440]
    REVIEW_INTERVALS = [1, 3, 7, 14, 30]

    def process(self, item, status, confirmed=True):
        effective = status if confirmed else 0
        item.last_review_at = datetime.now()
        item.review_count += 1
        now = datetime.now()

        if effective == 0:
            item.is_in_unknown_list = 1
            item.stage = 1
            item.learning_step = 0
            item.next_review_at = now + timedelta(minutes=5)
        elif effective == 1:
            item.stage = 1
            item.learning_step = 0
            item.next_review_at = now + timedelta(minutes=5)
        else:
            item.correct_count += 1
            if item.stage == 0:
                item.stage = 2
                item.interval_days = 1
                item.next_review_at = now + timedelta(days=1)
            elif item.stage == 1:
                item.learning_step += 1
                if item.learning_step >= len(self.LEARNING_INTERVALS):
                    item.stage = 2
                    item.interval_days = 1
                    item.next_review_at = now + timedelta(days=1)
                else:
                    mins = self.LEARNING_INTERVALS[item.learning_step]
                    item.next_review_at = now + timedelta(minutes=mins)
            else:
                try:
                    idx = self.REVIEW_INTERVALS.index(item.interval_days)
                except ValueError:
                    idx = 0
                if idx < len(self.REVIEW_INTERVALS) - 1:
                    item.interval_days = self.REVIEW_INTERVALS[idx + 1]
                item.next_review_at = now + timedelta(days=item.interval_days)
        return item

# ========== TOEIC ==========
class ToeicSentences:
    TEMPLATES = {
        'noun': [
            "The {word} plays a crucial role in our quarterly review.",
            "Our manager emphasized the importance of {word}.",
            "Please submit the {word} to HR by Friday.",
        ],
        'verb': [
            "We need to {word} the contract before the deadline.",
            "The team decided to {word} the project scope.",
        ],
        'adj': [
            "The client was {word} with our quarterly results.",
            "We need a {word} approach to this market shift.",
        ],
        'adv': [
            "The shipment arrived {word} than expected.",
            "We {word} completed the audit ahead of schedule.",
        ],
        'prep': [
            "The meeting is scheduled {word} 3 PM.",
        ],
    }

    def generate(self, word):
        templates = self.TEMPLATES.get(word.pos, self.TEMPLATES['noun'])
        idx = abs(hash(word.word)) % len(templates)
        return templates[idx].format(word=word.word)

# ========== 全局 ==========
db = None
srs = SRSEngine()
toeic = ToeicSentences()

# ========== UI ==========
class HomeScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=16)

        self.total_label = MDLabel(text='0', halign='center', font_style='H3')
        self.due_label = MDLabel(text='0', halign='center', font_style='H3')

        layout.add_widget(MDLabel(text='TOEIC 核心词汇', halign='center', font_style='H4', size_hint_y=None, height=60))
        layout.add_widget(MDLabel(text='托业阅读核心词汇智能复习', halign='center', theme_text_color='Secondary'))

        stats = MDBoxLayout(spacing=16, size_hint_y=None, height=100)
        stats.add_widget(self._stat_card('词库总量', self.total_label))
        stats.add_widget(self._stat_card('今日待复习', self.due_label))
        layout.add_widget(stats)

        btn_study = MDRaisedButton(text='开始背单词', on_release=self.start_study, size_hint=(1, None), height=56)
        layout.add_widget(btn_study)

        btn_import = MDRaisedButton(text='导入内置词库', on_release=self.import_vocab, size_hint=(1, None), height=48)
        layout.add_widget(btn_import)

        self.add_widget(layout)

    def _stat_card(self, title, value_label):
        card = MDCard(orientation='vertical', padding=12, radius=12)
        card.add_widget(MDLabel(text=title, halign='center', theme_text_color='Secondary', font_style='Caption'))
        card.add_widget(value_label)
        return card

    def on_enter(self):
        self.refresh_stats()

    def refresh_stats(self):
        if db:
            self.total_label.text = str(db.get_word_count())
            self.due_label.text = str(db.get_due_count())

    def start_study(self, *args):
        app = MDApp.get_running_app()
        app.sm.current = 'study'
        app.study_screen.load_words()

    def import_vocab(self, *args):
        if db:
            path = get_vocab_path()
            if path and os.path.exists(path):
                count = db.import_json(path)
                MDSnackbar(text=f'导入 {count} 个单词').open()
                self.refresh_stats()
            else:
                MDSnackbar(text='词库文件未找到').open()

class StudyScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.words = []
        self.index = 0
        self.current_word = None
        self.last_status = None

        layout = MDBoxLayout(orientation='vertical', padding=16, spacing=12)

        self.progress = MDProgressBar(value=0, max=1)
        layout.add_widget(self.progress)

        # 单词卡片
        self.word_card = MDCard(orientation='vertical', padding=24, spacing=12, radius=16)
        self.word_label = MDLabel(text='', halign='center', font_style='H2', bold=True)
        self.phonetic_label = MDLabel(text='', halign='center', theme_text_color='Secondary')
        self.meaning_label = MDLabel(text='', halign='center', font_style='Body1')
        self.toeic_label = MDLabel(text='', halign='center', theme_text_color='Primary', font_style='Caption')

        self.word_card.add_widget(self.word_label)
        self.word_card.add_widget(self.phonetic_label)
        self.word_card.add_widget(self.meaning_label)
        self.word_card.add_widget(self.toeic_label)
        layout.add_widget(self.word_card)

        # 反馈按钮
        self.feedback_box = MDBoxLayout(spacing=12, size_hint_y=None, height=160)
        self.feedback_box.add_widget(MDRaisedButton(text='熟悉', md_bg_color=(0.18,0.49,0.2,1), on_release=self.on_familiar))
        self.feedback_box.add_widget(MDRaisedButton(text='模糊', md_bg_color=(0.96,0.49,0,1), on_release=self.on_vague))
        self.feedback_box.add_widget(MDRaisedButton(text='不知道', md_bg_color=(0.78,0.16,0.16,1), on_release=self.on_unknown))
        layout.add_widget(self.feedback_box)

        # 确认按钮
        self.confirm_box = MDBoxLayout(orientation='vertical', spacing=8, size_hint_y=None, height=120, opacity=0)
        self.confirm_box.add_widget(MDLabel(text='我记对了吗？', halign='center', font_style='Subtitle1'))
        row = MDBoxLayout(spacing=12)
        row.add_widget(MDRaisedButton(text='记对了', on_release=self.on_confirm_correct))
        row.add_widget(MDRaisedButton(text='记错了', md_bg_color=(0.78,0.16,0.16,1), on_release=self.on_confirm_wrong))
        self.confirm_box.add_widget(row)
        layout.add_widget(self.confirm_box)

        # TTS 按钮
        tts_btn = MDRaisedButton(text='播放发音', on_release=self.play_tts, size_hint=(1, None), height=48)
        layout.add_widget(tts_btn)

        self.add_widget(layout)

    def load_words(self):
        self.words = db.get_due_words(limit=50) if db else []
        for w in self.words:
            if not w.toeic_sentence:
                w.toeic_sentence = toeic.generate(w)
        self.index = 0
        self.last_status = None
        self._update_ui()

    def _update_ui(self):
        if self.index >= len(self.words):
            self.show_finished()
            return
        self.current_word = self.words[self.index]
        w = self.current_word
        self.word_label.text = w.word
        self.phonetic_label.text = w.phonetic or ''
        self.progress.value = (self.index + 1) / max(len(self.words), 1)
        self.meaning_label.text = ''
        self.toeic_label.text = ''
        self.feedback_box.opacity = 1
        self.feedback_box.disabled = False
        self.confirm_box.opacity = 0
        self.confirm_box.disabled = True

    def play_tts(self, *args):
        if TTS_AVAILABLE and self.current_word:
            try:
                tts.speak(self.current_word.word)
            except Exception:
                MDSnackbar(text='TTS 不可用').open()

    def on_familiar(self, *args):
        self.last_status = 2
        self._reveal()

    def on_vague(self, *args):
        self.last_status = 1
        self._reveal()

    def on_unknown(self, *args):
        self.last_status = 0
        self._reveal()

    def _reveal(self):
        w = self.current_word
        self.meaning_label.text = '\uFF1B'.join(w.meanings)
        self.toeic_label.text = f'[TOEIC] {w.toeic_sentence}'
        self.feedback_box.opacity = 0
        self.feedback_box.disabled = True
        self.confirm_box.opacity = 1
        self.confirm_box.disabled = False

    def on_confirm_correct(self, *args):
        self._finish(True)

    def on_confirm_wrong(self, *args):
        self._finish(False)

    def _finish(self, confirmed):
        w = self.current_word
        if not w or not w.id:
            self.index += 1
            self._update_ui()
            return
        item = db.get_review_item(w.id)
        if not item:
            item = ReviewItem(word_id=w.id)
        item = srs.process(item, self.last_status, confirmed)
        db.update_review(item)
        db.log_study(w.id, self.last_status if confirmed else 0)
        self.index += 1
        self._update_ui()

    def show_finished(self):
        self.word_label.text = '\u672C\u8F6E\u5B8C\u6210\uFF01'
        self.phonetic_label.text = ''
        self.meaning_label.text = '\u5B66\u8FC7\u7684\u5355\u8BCD\u4F1A\u6309 SRS \u7B97\u6CD5\u5B89\u6392\u590D\u4E60'
        self.toeic_label.text = ''
        self.feedback_box.opacity = 0
        self.confirm_box.opacity = 0

class DashboardScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', padding=16)
        self.stats_label = MDLabel(text='', halign='left', font_style='Body1')
        scroll = ScrollView()
        scroll.add_widget(self.stats_label)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def on_enter(self):
        self.load_stats()

    def load_stats(self):
        if not db:
            return
        stats = db.get_stats(days=7)
        lines = ['\uD83D\uDCCA 近7日学习统计\n']
        for s in stats:
            lines.append(f"{s['date']}: 共{s['total']}词 | 熟悉{s['familiar']} | 模糊{s['vague']} | 不知道{s['unknown']} | 正确率{s['accuracy']:.0%}")
        self.stats_label.text = '\n'.join(lines)

class UnknownScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', padding=16, spacing=12)
        self.word_list = MDList()
        scroll = ScrollView()
        scroll.add_widget(self.word_list)
        layout.add_widget(scroll)
        btn = MDRaisedButton(text='导出生词本', on_release=self.export_words, size_hint=(1, None), height=48)
        layout.add_widget(btn)
        self.add_widget(layout)

    def on_enter(self):
        self.load_words()

    def load_words(self):
        if not db:
            return
        self.word_list.clear_widgets()
        words = db.get_unknown_words()
        for w in words:
            self.word_list.add_widget(TwoLineListItem(
                text=w.word,
                secondary_text='\uFF1B'.join(w.meanings[:2])
            ))

    def export_words(self, *args):
        if not db:
            return
        words = db.get_unknown_words()
        lines = [f"{w.word}  {'\uFF1B'.join(w.meanings)}" for w in words]
        text = '\n'.join(lines)
        try:
            from android.storage import primary_external_storage_path
            path = os.path.join(primary_external_storage_path(), 'Download', 'unknown_words.txt')
        except Exception:
            path = os.path.join(os.path.expanduser('~'), 'Downloads', 'unknown_words.txt')
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            MDSnackbar(text=f'已导出到 {path}').open()
        except Exception as e:
            MDSnackbar(text=f'导出失败: {e}').open()

# ========== 工具函数 ==========
def get_vocab_path():
    from kivy.resources import resource_find
    for p in ['assets/vocabulary.json', 'vocabulary.json']:
        result = resource_find(p)
        if result and os.path.exists(result):
            return result
    bundle = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    for p in [os.path.join(bundle, 'assets', 'vocabulary.json'),
              os.path.join(bundle, 'vocabulary.json')]:
        if os.path.exists(p):
            return p
    return None

# ========== App ==========
class ToeicApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.theme_style = "Light"
        self.sm = MDScreenManager()

        global db
        db_path = os.path.join(self.user_data_dir, 'toeic.db')
        db = Database(db_path)

        # 尝试导入词库
        vocab_path = get_vocab_path()
        if vocab_path and os.path.exists(vocab_path):
            try:
                count = db.import_json(vocab_path)
                if count:
                    print(f'导入 {count} 个单词')
            except Exception as e:
                print(f'导入词库失败: {e}')

        self.home_screen = HomeScreen(name='home')
        self.study_screen = StudyScreen(name='study')
        self.dashboard_screen = DashboardScreen(name='dashboard')
        self.unknown_screen = UnknownScreen(name='unknown')

        self.sm.add_widget(self.home_screen)
        self.sm.add_widget(self.study_screen)
        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.unknown_screen)

        layout = MDBoxLayout(orientation='vertical')
        toolbar = MDTopAppBar(
            title='TOEIC 背单词',
            right_action_items=[['theme-light-dark', lambda x: self.toggle_theme()]]
        )
        layout.add_widget(toolbar)
        layout.add_widget(self.sm)

        # 底部导航
        nav = MDBoxLayout(adaptive_height=True, padding=4, spacing=2)
        for icon_name, label, screen_name in [
            ('home', '首页', 'home'),
            ('school', '背单词', 'study'),
            ('chart-bar', '看板', 'dashboard'),
            ('bookmark', '生词本', 'unknown'),
        ]:
            btn = MDRaisedButton(text=label, on_release=lambda sc=screen_name: setattr(self.sm, 'current', sc))
            nav.add_widget(btn)
        layout.add_widget(nav)

        return layout

    def toggle_theme(self):
        self.theme_cls.theme_style = 'Dark' if self.theme_cls.theme_style == 'Light' else 'Light'

if __name__ == '__main__':
    ToeicApp().run()
