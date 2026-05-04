const axios = require('axios');

module.exports.handler = async function (event, context) {
    const YANDEX_WEATHER_KEY = 'da41d5f5-ce05-4b95-a7d3-304665fe5676';  
    const TELEGRAM_BOT_TOKEN = '8445994040:AAEhh4xBpt0ynGz_PR03zrYoGTfVzbKGuPI'; 
    const TELEGRAM_CHAT_ID = '1151038847'; 
    
    const LAT = 45.0448;
    const LON = 38.976;
    
    try {
        console.log('📡 Запрашиваем погоду...');
        
        const weatherResponse = await axios({
            method: 'get',
            url: `https://api.weather.yandex.ru/v2/forecast?lat=${LAT}&lon=${LON}&limit=1&lang=ru_RU`,
            headers: {
                'X-Yandex-API-Key': YANDEX_WEATHER_KEY  
            }
        });
        
        console.log('✅ Погода получена:', weatherResponse.status);
        
        const fact = weatherResponse.data.fact;
        
        // Форматируем сообщение
        const conditionMap = {
            'clear': '☀️ Ясно',
            'partly-cloudy': '⛅ Переменная облачность',
            'cloudy': '☁️ Облачно',
            'overcast': '☁️ Пасмурно',
            'drizzle': '🌧️ Морось',
            'light-rain': '🌦️ Небольшой дождь',
            'rain': '🌧️ Дождь',
            'heavy-rain': '🌧️ Сильный дождь',
            'showers': '🌧️ Ливень',
            'wet-snow': '🌨️ Мокрый снег',
            'light-snow': '🌨️ Небольшой снег',
            'snow': '❄️ Снег',
            'heavy-snow': '❄️ Сильный снег',
            'thunderstorm': '⛈️ Гроза'
        };
        
        const conditionText = conditionMap[fact.condition] || fact.condition;
        
        const now = new Date();
        const date = now.toLocaleDateString('ru-RU', {
            weekday: 'long',
            day: 'numeric',
            month: 'long'
        });
        
        const message = `🌤 *Погода на ${date}*\n\n` +
            `📍 Температура: ${fact.temp}°C\n` +
            `🤔 Ощущается как: ${fact.feels_like}°C\n` +
            `🌬️ Ветер: ${fact.wind_speed} м/с\n` +
            `💧 Влажность: ${fact.humidity}%\n` +
            `🎯 Давление: ${fact.pressure_mm} мм рт. ст.\n` +
            `☁️ ${conditionText}\n\n` +
            `Хорошего дня! 🚀`;
        
        await axios({
            method: 'post',
            url: `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
            data: {
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'Markdown'
            }
        });
        
        console.log('✅ Сообщение отправлено в Telegram');
        
        return {
            statusCode: 200,
            body: JSON.stringify({ 
                success: true, 
                message: 'Погода отправлена успешно',
                temperature: fact.temp
            })
        };
        
    } catch (error) {
        console.error('❌ Ошибка:', error.message);
        
        if (error.response) {
            console.error('Статус ошибки:', error.response.status);
            console.error('Данные ошибки:', JSON.stringify(error.response.data));
            
            if (error.response.status === 403) {
                return {
                    statusCode: 403,
                    body: JSON.stringify({ 
                        error: 'Неверный API-ключ Яндекс.Погоды. Проверьте ключ в developer.tech.yandex.ru' 
                    })
                };
            }
            
            if (error.response.status === 404) {
                return {
                    statusCode: 404,
                    body: JSON.stringify({ 
                        error: 'API недоступен. Проверьте URL и координаты' 
                    })
                };
            }
        }
        
        return {
            statusCode: 500,
            body: JSON.stringify({ 
                error: error.message,
                details: error.response?.data || 'Нет дополнительных данных'
            })
        };
    }
};
