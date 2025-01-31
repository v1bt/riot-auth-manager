from flask import Flask, render_template, request, jsonify
import requests
from urllib.parse import unquote, parse_qs, urlparse
from easygoogletranslate.easygoogletranslate import EasyGoogleTranslate
import uuid
from concurrent.futures import ThreadPoolExecutor
import re

app = Flask(__name__)

TOKEN_RETRY_INTERVAL = 2
QR_REGENERATION_INTERVAL = 60

LANGUAGE_TO_REGION = {
    'en-US': 'NA',
    'ko-KR': 'KR',
    'ja-JP': 'JP',
    'zh-CN': 'CN',
    'zh-TW': 'TW',
    'es-ES': 'EUW',
    'fr-FR': 'EUW',
    'de-DE': 'EUW',
    'ru-RU': 'RU',
    'ar-SA': 'TR',
    'th-TH': 'TH',
    'vi-VN': 'VN',
    'id-ID': 'ID',
    'ms-MY': 'MY',
    'pl-PL': 'EUN',
    'tr-TR': 'TR',
    'ro-RO': 'EUN',
    'hu-HU': 'EUN',
    'el-GR': 'EUN',
    'cs-CZ': 'EUN',
    'pt-BR': 'BR',
    'it-IT': 'EUW'
}

def get_user_language():
    return request.accept_languages.best_match(LANGUAGE_TO_REGION.keys()) or 'en-US'

def validate_language(lang):
    return lang in LANGUAGE_TO_REGION

def translate_text(text, language):
    if language == "ko-KR":
        return text
    try:
        translator = EasyGoogleTranslate(
            source_language='ko',
            target_language=language.split('-')[0],
            timeout=10
        )
        translated = translator.translate(text)
        return re.sub(r'&#\d+;', '', translated)
    except Exception as e:
        raise Exception(f"Translation failed: {str(e)}")

def handle_error(error_code, message):
    user_lang = get_user_language()
    try:
        error_message = translate_text("오류가 발생했습니다", user_lang)
        return render_template('error.html', 
                            status_code=error_code,
                            message=message,
                            error_message=error_message,
                            lang=user_lang), error_code
    except:
        return render_template('error.html',
                            status_code=error_code,
                            message=message,
                            error_message="An error occurred",
                            lang='en-US'), error_code

def parallel_translate_texts(texts, language):
    with ThreadPoolExecutor() as executor:
        translated_texts = list(executor.map(lambda text: translate_text(text, language), texts))
    return translated_texts

def new_session():
    session = requests.Session()
    return session, str(uuid.uuid4())

def get_region_and_language(lang_code):
    region = LANGUAGE_TO_REGION.get(lang_code)
    language = lang_code.replace('-', '_')
    return region, language

def login_url(country_code):
    session, sdk_sid = new_session()
    
    region, language = get_region_and_language(country_code)
    
    trace_id = uuid.uuid4().hex
    parent_id = uuid.uuid4().hex[:16]
    traceparent = f'00-{trace_id}-{parent_id}-00'

    headers1 = {
        'Host': 'clientconfig.rpg.riotgames.com',
        'user-agent': 'RiotGamesApi/24.9.1.4445 client-config (Windows;10;;Professional, x64) riot_client/0',
        'Accept-Encoding': 'deflate, gzip, zstd',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'baggage': f'sdksid={sdk_sid}',
        'traceparent': traceparent,
        'country-code': country_code
    }

    url1 = 'https://clientconfig.rpg.riotgames.com/api/v1/config/public'
    params = {
        'os': 'windows',
        'region': region,
        'app': 'Riot Client',
        'version': '97.0.1.2366',
        'patchline': 'KeystoneFoundationLiveWin'
    }

    session.get(url1, headers=headers1, params=params)
    headers2 = {
        'Host': 'auth.riotgames.com',
        'user-agent': 'RiotGamesApi/24.9.1.4445 rso-auth (Windows;10;;Professional, x64) riot_client/0',
        'Accept-Encoding': 'deflate, gzip, zstd',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'baggage': f'sdksid={sdk_sid}',
        'traceparent': traceparent,
        'country-code': country_code
    }

    session.get('https://auth.riotgames.com/.well-known/openid-configuration', headers=headers2)

    login_data = {
        "client_id": "riot-client",
        "language": language,
        "platform": "windows",
        "remember": False,
        "type": "auth",
        "qrcode": {}
    }

    headers3 = {
        'Host': 'authenticate.riotgames.com',
        'user-agent': 'RiotGamesApi/24.9.1.4445 rso-authenticator (Windows;10;;Professional, x64) riot_client/0',
        'Accept-Encoding': 'deflate, gzip, zstd',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'baggage': f'sdksid={sdk_sid}',
        'traceparent': traceparent,
        'country-code': country_code
    }

    response = session.post('https://authenticate.riotgames.com/api/v1/login', headers=headers3, json=login_data)
    response_json = response.json()

    cluster = response_json.get("cluster")
    suuid = response_json.get("suuid")
    timestamp = response_json.get("timestamp")

    if not cluster or not suuid or not timestamp:
        return None, "Required data is missing from the response."
    
    login_url = f'https://qrlogin.riotgames.com/riotmobile?cluster={cluster}&suuid={suuid}&timestamp={timestamp}&utm_source=riotclient&utm_medium=client&utm_campaign=qrlogin-riotmobile'
    
    return {
        'login_url': login_url,
        'session': session,
        'sdk_sid': sdk_sid,
        'cluster': cluster,
        'suuid': suuid,
        'timestamp': timestamp
    }, None

def get_login_token(session, sdk_sid, country_code):
    traceparent = f'00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-00'
    check_headers = {
        'Host': 'authenticate.riotgames.com',
        'user-agent': 'RiotGamesApi/24.9.1.4445 rso-authenticator (Windows;10;;Professional, x64) riot_client/0',
        'Accept-Encoding': 'deflate, gzip, zstd',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'baggage': f'sdksid={sdk_sid}',
        'traceparent': traceparent,
        'country-code': country_code
    }

    response = session.get('https://authenticate.riotgames.com/api/v1/login', headers=check_headers)
    if response.status_code == 200:
        return response.json()
    return None

def get_access_token(login_token):
    session = requests.Session()
    sdk_sid = str(uuid.uuid4())
    traceparent = f'00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-00'

    headers1 = {
        'Host': 'auth.riotgames.com',
        'user-agent': 'RiotGamesApi/24.10.1.4471 rso-auth (Windows;10;;Professional, x64) riot_client/0',
        'Accept-Encoding': 'deflate, gzip, zstd',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'baggage': f'sdksid={sdk_sid}',
        'traceparent': traceparent
    }

    data1 = {
        "authentication_type": None,
        "code_verifier": "",
        "login_token": login_token,
        "persist_login": False
    }

    response1 = session.post('https://auth.riotgames.com/api/v1/login-token', headers=headers1, json=data1)
    
    if response1.status_code != 204:
        return None, "Login token submission failed", None

    headers2 = {
        'Host': 'auth.riotgames.com',
        'user-agent': 'RiotGamesApi/24.10.1.4471 rso-auth (Windows;10;;Professional, x64) riot_client/0',
        'Accept-Encoding': 'deflate, gzip, zstd',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'baggage': f'sdksid={sdk_sid}',
        'traceparent': traceparent
    }

    data2 = {
        "acr_values": "",
        "claims": "",
        "client_id": "riot-client",
        "code_challenge": "",
        "code_challenge_method": "",
        "nonce": str(uuid.uuid4()),
        "redirect_uri": "http://localhost/redirect",
        "response_type": "token id_token",
        "scope": "openid link ban lol_region account"
    }

    response2 = session.post('https://auth.riotgames.com/api/v1/authorization', headers=headers2, json=data2)
    
    if response2.status_code != 200:
        return None, "Authorization failed", None

    cookies = dict(response2.cookies)
    
    response_data = response2.json()
    if 'response' in response_data and 'parameters' in response_data['response']:
        return response_data['response']['parameters']['uri'], None, cookies
    
    return None, "Failed to get access token URI", None

current_session_data = None

@app.route('/login_url', methods=['POST'])
def login_url_route():
    global current_session_data
    
    country_code = request.headers.get('country-code')
    if not country_code or country_code.lower() == 'auto':
        accept_language = request.headers.get('Accept-Language', '')
        if ',' in accept_language:
            accept_language = accept_language.split(',')[0]
        country_code = accept_language.split(';')[0]
        if not country_code:
            country_code = 'en-US'
    
    result, error = login_url(country_code)
    if error:
        return jsonify({'error': error}), 400
    
    current_session_data = {
        'session': result['session'],
        'sdk_sid': result['sdk_sid'],
        'country_code': country_code
    }
    
    return jsonify({
        'login_url': result['login_url'],
        'cluster': result['cluster'],
        'suuid': result['suuid'],
        'timestamp': result['timestamp']
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/demo/')
def demo():
    return render_template('demo.html')

@app.after_request
def after_request(response):
    response.headers.remove('X-Frame-Options')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/auth/<lang>/')
def auth(lang):
    try:
        language = unquote(lang)
        
        if language.lower() == 'auto':
            accept_language = request.headers.get('Accept-Language', '')
            if ',' in accept_language:
                accept_language = accept_language.split(',')[0]
            language = accept_language.split(';')[0]
        else:
            if not validate_language(language):
                return handle_error(404, f"Unsupported language: {language}")
        
        texts = [
            '로그인', '라이엇 모바일을 통해 로그인', '로그인 Url 생성중..',
            '로그인 Url 생성 실패', '모바일 환경에서 바로 로그인하기',
            'QR코드를 스캔하거나 Url에 방문해주세요.', '로그인 Url만료 새 Url을 생성합니다.',
            '남은 시간', '토큰 확인 중 오류 발생', '로그인 완료',
            '고객지원', '개인정보 처리방침', '서비스 약관', '쿠키 설정', '언어를 선택하세요.', '소스 코드'
        ]
        
        translated_texts = parallel_translate_texts(texts, language)
        
        return render_template(
            'auth.html',
            title=translated_texts[0],
            dis=translated_texts[1],
            wait=translated_texts[2],
            fail=translated_texts[3],
            md=translated_texts[4],
            plzscan=translated_texts[5],
            end=translated_texts[6],
            rm=translated_texts[7],
            tf=translated_texts[8],
            sus=translated_texts[9],
            gg=translated_texts[10],
            pp=translated_texts[11],
            sp=translated_texts[12],
            cs=translated_texts[13],
            cl=translated_texts[14],
            ss=translated_texts[15],
            lang=language.split('-')[0]
        )
    except Exception as e:
        return handle_error(500, str(e))
    

@app.route('/get_token', methods=['POST'])
def fetch_token():
    global current_session_data
    
    if not current_session_data:
        return jsonify({'error': 'No active session'}), 400
    
    token_data = get_login_token(
        current_session_data['session'], 
        current_session_data['sdk_sid'],
        current_session_data['country_code']
    )
    
    if not token_data:
        new_url, error = login_url(current_session_data['country_code'])
        if error:
            return jsonify({'error': error}), 400
        
        current_session_data = {
            'session': new_url['session'],
            'sdk_sid': new_url['sdk_sid'],
            'country_code': current_session_data['country_code']
        }
        
        return jsonify({
            'error': 'Token expired', 
            'new_url': new_url['login_url']
        })
    
    if token_data.get('type') == 'success':
        login_token = token_data['success']['login_token']
        uri, error, cookies = get_access_token(login_token)
        if error:
            return jsonify({'error': error}), 400
        
        try:
            access_token = uri.split('#access_token=')[1].split('&')[0]
            token_data['access_token'] = access_token
        except:
            return jsonify({'error': 'Failed to extract access token'}), 400
        
        token_data['cookies'] = cookies
        token_data.pop('uri', None)
    
    return jsonify(token_data)
    
@app.errorhandler(404)
def not_found_error(error):
    return handle_error(404, "Page not found")

@app.errorhandler(500)
def internal_error(error):
    return handle_error(500, "Internal server error")

@app.route('/cookie_reauth', methods=['POST'])
def cookie_reauth():
    ssid = request.headers.get('ssid')
    if not ssid:
        return jsonify({'error': 'Cookie is required'}), 400

    params = {
        'redirect_uri': 'https://playvalorant.com/opt_in',
        'client_id': 'play-valorant-web-prod',
        'response_type': 'token id_token',
        'nonce': '1',
        'scope': 'account openid'
    }

    try:
        response = requests.get(
            'https://auth.riotgames.com/authorize',
            params=params,
            cookies={'ssid': ssid},
            allow_redirects=False
        )

        location = response.headers.get('Location', '')
        if 'access_token' not in location:
            return jsonify({'error': 'Invalid Cookie'}), 401

        fragment = urlparse(location).fragment
        tokens = parse_qs(fragment)
        access_token = tokens.get('access_token', [None])[0]

        if not access_token:
            return jsonify({'error': 'Failed to get access token'}), 500

        return jsonify({'access_token': access_token})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
