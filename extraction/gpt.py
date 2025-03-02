from openai import OpenAI
import os
import sqlite3
import pdfplumber
import json

class GPT:
    def __init__(self, model_name='o3-mini', temperature=0, db_path='./decisions.db'):
        self.api_key = os.environ.get('API_KEY')
        if not self.api_key:
            raise ValueError("Переменная окружения API_KEY не установлена")
        self.client = OpenAI(api_key=self.api_key,
                             base_url="https://api.proxyapi.ru/openai/v1")
        self.model_name = model_name
        self.temperature = temperature
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Инициализирует базу данных SQLite и создает таблицу для хранения результатов.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_date TEXT,
                debt_amount TEXT,
                fine_amount TEXT
            )
        """)
        conn.commit()
        conn.close()

    def extract_text_from_pdf(self, pdf_path):
        """
        Извлекает и возвращает текст из PDF-файла.
        """
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Ошибка при извлечении текста из {pdf_path}: {e}")
        return text.strip()

    def store_result_in_db(self, decision_date, debt_amount, fine_amount):
        """
        Сохраняет результаты для файла в базу данных.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO decisions (decision_date, debt_amount, fine_amount)
            VALUES (?, ?, ?)
        """, (decision_date, debt_amount, fine_amount))
        conn.commit()
        conn.close()


    def generate_prompt(self, text):
        """
        Генерирует промпт для извлечения структурированных данных из текста судебного решения.
        
        Аргумент:
          text (str): полный текст судебного решения.
        Возвращает:
          str: промпт, который можно отправить в модель.
        """
        prompt = (
            "Дано судебное решение:\n"
            f"\"{text}\"\n\n"
            "Извлеки следующие данные:\n"
            "- decision_date: дата судебного решения в формате число.месяц.год,\n"
            "- debt_amount: сумма долга без указания валюты (если отсутствует, то null),\n"
            "- fine_amount: сумма штрафа без указания валюты (если отсутствует, то null).\n\n"
            "Верни ответ в формате JSON."
        )
        return prompt

    def get_model_response(self, prompt):
            """
            Отправляет промпт в OpenAI Chat API и возвращает ответ модели.
            """
            messages = [
                {"role": "system", "content": "Ты ассистент, который извлекает структурированные данные из текста судебного решения."},
                {"role": "user", "content": prompt}
            ]
            try:
                response = self.client.chat.completions.create(model=self.model_name,
                messages=messages)
                #temperature=self.temperature)
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"Ошибка при вызове OpenAI API: {e}")
                return None

    def process_pdf_folder(self, folder_path):
        """
        Обрабатывает все PDF-файлы из указанной папки:
         - Извлекает текст из каждого файла.
         - Генерирует промпт и получает ответ модели.
         - Сохраняет результаты в базу данных.
        """
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
        for pdf_file in pdf_files:
            pdf_path = os.path.join(folder_path, pdf_file)
            print(f"Обрабатывается файл: {pdf_file}")
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                print(f"Не удалось извлечь текст из файла: {pdf_file}")
                continue
            prompt = self.generate_prompt(text)
            response = self.get_model_response(prompt)
            try:
                data = json.loads(response)
                decision_date = data.get("decision_date")
                debt_amount = data.get("debt_amount")
                fine_amount = data.get("fine_amount")
            except Exception as e:
                print(f"Ошибка при разборе JSON для файла {pdf_file}: {e}")
                decision_date, debt_amount, fine_amount = None, None, None

            # Сохраняем результат в базу данных
            self.store_result_in_db(decision_date, debt_amount, fine_amount)
            print(f"Результат для {pdf_file} сохранен в БД.")

    

