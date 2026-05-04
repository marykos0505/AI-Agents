import json
import requests
import time
import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator

TOKEN = "8640854788:AAFUI4KA5RryAjqiQQDI3XoDLA1LUfJrB1c"

def translate_text(text, target='ru'):
    try: 
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception as e: 
        print(f"Translate error: {e}")
        return text

def search_arxiv(query):
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}", 
        "start": 0,
        "max_results": 3,
        "sortBy": "relevance"
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ScienceAgent/2.0'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 429:
            return "ERROR_429"
        
        response.raise_for_status()
        root = ET.fromstring(response.text)
        articles = []
        
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
            link = entry.find('{http://www.w3.org/2005/Atom}id').text.strip()
            summary = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            
            articles.append({
                "title": translate_text(title), 
                "link": link,
                "summary": translate_text(summary[:400] + "...")
            })
        return articles
    except Exception as e: 
        print(f"ArXiv request error: {e}")
        return None

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'})

def handler(event, context):
    try:
        body_raw = event.get('body', '{}')
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        
        msg = body.get('message', {})
        chat_id = msg.get('chat', {}).get('id')
        text = msg.get('text', '')

        if not chat_id: 
            return {'statusCode': 200}
            
        if text == "/start":
            send_message(chat_id, "Здравствуйте! Введите тему для поиска (на русском или английском).")
            return {'statusCode': 200}

        query_en = translate_text(text, target='en')
        send_message(chat_id, f"🔎 Перевел запрос и ищу: _{query_en}_...")

        results = search_arxiv(query_en)

        if results == "ERROR_429":
            send_message(chat_id, "Сервер ArXiv сейчас защищается от частых запросов (ошибка 429). Подождите минуту и попробуйте снова.")
        elif not results:
            send_message(chat_id, "Ничего не найдено. Попробуйте написать запрос иначе.")
        else:
            res_text = "*Вот лучшие совпадения с темой:*\n\n"
            for a in results:
                res_text += f"> *{a['title']}*\n _{a['summary']}_\n🔗 [Читать статью в оригинале]({a['link']})\n\n"
            
            send_message(chat_id, res_text[:4000])
            
    except Exception as e: 
        print(f"Handler error: {e}")
        
    return {'statusCode': 200}
