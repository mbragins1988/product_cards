import json
import subprocess

curl_cmd = [
    'curl',
    '-k',
    '-X', 'POST',
    '-H', 'Content-Type: application/x-www-form-urlencoded',
    '-H', 'Accept: application/json',
    '-H', 'RqUID: 1d8f883a-2bf6-4389-b2c2-ca8e3e03a214',
    '-H', 'Authorization: Basic MDA5MTQ2NzItNDUyZi00YTQ0LTkwMTEtM2U0MTE1MjNhYzQzOmI1MmIwMTMxLWE2N2MtNGJhMC04M2VhLTkwZjVkNmRlNTJhYw==',
    '--data-urlencode', 'scope=GIGACHAT_API_PERS',
    'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
]

result = subprocess.run(curl_cmd, capture_output=True, text=True)

# Проверка успешности запроса
if result.returncode == 0:
    try:
        response_data = json.loads(result.stdout)
        access_token = response_data['access_token']
        print("Полученный токен:", access_token)
    except (json.JSONDecodeError, KeyError) as e:
        print("Ошибка парсинга ответа:", e)
        print("Полный ответ:", result.stdout)
else:
    print("Ошибка выполнения curl:", result.stderr)