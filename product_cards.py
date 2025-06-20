import requests
from bs4 import BeautifulSoup
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_models.gigachat import GigaChat
import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
SITES = ['https://stomatorg.ru', 'https://www.nika-dent.ru']
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE") # Файл с API ключами для Google Sheets
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # Идентификатор Google таблицы


def parse_product_description(url):
    """Парсинг описания товара с сайта конкурента"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        site_data = {}
        country = ''
        brand = ''
        article = ''
        text = ''
        h2 = ''
        meta_info = {
            'title': None,
            'description': None,
            'keywords': None
        }

        meta_info['title'] = soup.find('title').get_text() if soup.find('title') else 'Данные отсутствуют'
        meta_info['description'] = soup.find('description').get_text() if soup.find('description') else 'Данные отсутствуют'
        meta_info['keywords'] = soup.find('keywords').get_text() if soup.find('keywords') else 'Данные отсутствуют'
        site_data['meta'] = meta_info

        # Описание товара для nika-dent.ru
        if 'nika-dent.ru' in url:

            # Бренд и артикул
            product_articles = soup.find_all('div', class_='product-article')
            if product_articles:
                for item in product_articles:
                    if item.find('a'):
                        brand = item.find('a').get_text(strip=True)
                    if item.find('span'):
                        article = item.find('span').get_text(strip=True)

            # Страна
            block_country = soup.find('div', class_='product-country')
            if block_country:
                country = block_country.get_text(strip=True).split(':')[1]

            # DF <h2>
            h2 = soup.find('h1', class_='product-name header2 item-link').get_text(strip=True).split(',')[0]

            # DF основное описание
            block_text = soup.find('div', class_='info-content')
            if block_text:
                text = block_text.get_text(strip=True)

        site_data['brand'] = brand
        site_data['article'] = article
        site_data['text'] = text
        site_data['country'] = country
        site_data['DF <h2>'] = h2

        return site_data if site_data else "Не удалось загрузить даннные"
    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return ""


def generate_unique_description(text):

    giga = GigaChat(
        # Для авторизации запросов ключ, полученный в проекте GigaChat API
        credentials=os.getenv("GIGACHAT_CREDENTIALS"),
        verify_ssl_certs=False,
    )

    messages = [
        SystemMessage(
            content="Напиши своими словами текст"
        )
    ]

    messages.append(HumanMessage(content=text))
    res = giga.invoke(messages)
    messages.append(res)
    return res.content


def save_to_google_sheets(data):
    """Сохранение данных в Google Sheets"""

    try:
        # Авторизация с помощью сервисного аккаунта
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)

        # Подготовка данных для вставки
        values = []
        headers = [
            'URL',
            'Бренд',
            'Страна',
            'DF Артикул',
            'DF META TITLE',
            'DF KEYWORDS',
            'DF Meta Description',
            'DF <h2>',
            'DF основное описание',
            'DF основное описание (измененное)',
        ]
        values.append(headers)
        for item in data:
            row = [
                item.get('url', 'Данные отсутствуют'),
                item.get('brand', 'Данные отсутствуют'),
                item.get('country', 'Данные отсутствуют'),
                item.get('article', 'Данные отсутствуют'),
                item.get('meta', {}).get('title', 'Данные отсутствуют'),
                item.get('meta', {}).get('keywords', 'Данные отсутствуют'),
                item.get('meta', {}).get('description', 'Данные отсутствуют'),
                item.get('DF <h2>', 'Данные отсутствуют'),
                item.get('text', 'Данные отсутствуют'),
                item.get('new_text', 'Данные отсутствуют'),
            ]
            values.append(row)
        
        # Определение диапазона для записи (первый лист)
        range_name = 'A1:K' + str(len(values))
        
        # Формирование тела запроса
        body = {
            'values': values
        }
        
        # Выполнение запроса
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Данные успешно сохранены в таблицу")
        
    except Exception as e:
        print(f"Ошибка при сохранении в Google Sheets: {e}")

def main():
    start_time = time.time()
    # Пример списка товаров для обработки
    products_to_process = [
        {'url': 'https://www.nika-dent.ru/catalog/khirurgiya/irrigatsionnye-sistemy/trubki-irrigatsionnye-accentmed-dlya-w-h-1sht/'},
        {'url': 'https://www.nika-dent.ru/catalog/terapiya/plombirovochnye-materialy/svetovye-kompozity/filtek-ultimate/filtek-ultimeyt-filtek-ultimate-a3d-shprits-4-g-3920-3m/'},
        {'url': 'https://www.nika-dent.ru/catalog/bory/bory-pryamye/bory-almaznye-sf-11-5sht-mani/'},
        # Добавьте другие товары по аналогии
    ]
    
    results = []
    
    for product in products_to_process:
        # 1. Парсинг описания с сайта конкурента и meta
        original_description_meta = parse_product_description(product['url'])
        original_description_meta['url'] = str(product)

        # 2. Генерация уникального описания
        if original_description_meta and original_description_meta != "Не удалось загрузить даннные":
            new_text = generate_unique_description(original_description_meta.get('text'))
        else:
            new_text = "Не удалось сгенерировать описание"

        original_description_meta['new_text'] = new_text
        results.append(original_description_meta)
    
    # 4. Сохранение в Google Sheets
    if results:
        save_to_google_sheets(results)
        time.sleep(2)
    
    # Вывод времени выполнения
    execution_time = time.time() - start_time
    print(f"Скрипт выполнен за {execution_time:.2f} секунд")
    

if __name__ == '__main__':
    main()
