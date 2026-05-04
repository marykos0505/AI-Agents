import json
import requests
import boto3
import fitz 
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOKEN = ""
BUCKET_NAME = "sborinfa"

AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""

s3 = boto3.client(
    "s3",
    endpoint_url="https://storage.yandexcloud.net",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name="ru-central1"
)


KNOWLEDGE_BASE = []

def load_knowledge_base():
    """Скачивает и читает PDF только если память пуста"""
    global KNOWLEDGE_BASE
    if KNOWLEDGE_BASE:
        return KNOWLEDGE_BASE

    chunks = []
    try:
        response = s3.list_objects(Bucket=BUCKET_NAME)
        for obj in response.get('Contents', []):
            if obj['Key'].lower().endswith('.pdf'):
                file_path = f"/tmp/{obj['Key']}"
                

                s3.download_file(BUCKET_NAME, obj['Key'], file_path)
                

                doc = fitz.open(file_path)
                for i, page in enumerate(doc):
                    text = page.get_text().strip()
                    if len(text) > 50: 
                        chunks.append({"text": text, "source": f"{obj['Key']}, стр. {i+1}"})
                doc.close()
                

                os.remove(file_path) 
                
        KNOWLEDGE_BASE = chunks
        print(f"База загружена: {len(chunks)} абзацев.")
    except Exception as e:
        print(f"Ошибка загрузки базы: {e}")
        
    return chunks

def save_file_to_s3(file_id, file_name):
    try:
        file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
        tg_file_path = file_info['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{tg_file_path}"
        
        tmp_path = f"/tmp/{file_name}"
        
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(tmp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        s3.upload_file(tmp_path, BUCKET_NAME, file_name)
        os.remove(tmp_path)
        
        global KNOWLEDGE_BASE
        KNOWLEDGE_BASE = []
        return True
    except Exception as e:
        print(f"Ошибка сохранения файла: {e}")
        return False

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'})

def handler(event, context):
    print(f"DEBUG: Incoming event: {event}") 
    
    try:
        if not event:
            print("DEBUG: Запрос абсолютно пустой.")
            return {'statusCode': 200, 'body': 'OK'}
            
        body_raw = event.get('body')
        
        if body_raw is None:
            body = {}
        elif isinstance(body_raw, str):
            try:
                body = json.loads(body_raw)
            except:
                body = {}
        else:
            body = body_raw 
            
        if isinstance(body, dict):
            msg = body.get('message', {})
        else:
            msg = {}
            
        chat_id = msg.get('chat', {}).get('id')
        
        if not chat_id:
            print("DEBUG: Нет chat_id (это не сообщение из Телеграма).")
            return {'statusCode': 200, 'body': 'OK'}

        user_text = msg.get('text', '')
        if user_text == "/start":
            send_message(chat_id, "Здравствуйте! Задайте мне вопрос по презентациям или отправьте новый PDF-файл, чтобы я добавил его в базу.")
            return {'statusCode': 200}

        if user_text:
            send_message(chat_id, "Читаю документы...")
            
            chunks = load_knowledge_base()
            if not chunks:
                send_message(chat_id, "Моя база данных пуста. Отправьте мне PDF-файл.")
                return {'statusCode': 200}

            texts = [c['text'] for c in chunks]
            vectorizer = TfidfVectorizer()
            
            try:
                tfidf_matrix = vectorizer.fit_transform(texts + [user_text])
                sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
                best_idx = sim.argmax()
                
                if sim[0][best_idx] < 0.05:
                    send_message(chat_id, "Я не нашел точного ответа на этот вопрос в своих документах.")
                    return {'statusCode': 200}
                    
                answer = chunks[best_idx]
                response = f"*Вот что удалось найти:*\n\n_{answer['text'][:800]}..._\n\n*Источник:* {answer['source']}"
                send_message(chat_id, response)
            except Exception as e:
                print(f"Поиск сломался: {e}")
                send_message(chat_id, "Произошла ошибка при анализе текста.")

    except Exception as e:
        print(f"Global error: {e}")

    return {'statusCode': 200}
