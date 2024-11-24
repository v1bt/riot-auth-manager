import concurrent.futures
import requests
import re
import html
import urllib.parse

# Source: https://github.com/ahmeterenodaci/easygoogletranslate

class EasyGoogleTranslate:
    def __init__(self, source_language='auto', target_language='en', timeout=5):
        self.source_language = source_language
        self.target_language = target_language
        self.timeout = timeout
        self.pattern = r'(?s)class="(?:t0|result-container)">(.*?)<'

    def make_request(self, target_language, source_language, text, timeout):
        escaped_text = urllib.parse.quote(text.encode('utf8'))
        url = 'https://translate.google.com/m?tl=%s&sl=%s&q=%s'%(target_language, source_language, escaped_text)
        response = requests.get(url, timeout=timeout)
        result = response.text.encode('utf8').decode('utf8')
        result = re.findall(self.pattern, result)

        return html.unescape(result[0])

    def translate(self, text, target_language='', source_language='', timeout=''):
        if not target_language:
            target_language = self.target_language
        if not source_language:
            source_language = self.source_language
        if not timeout:
            timeout = self.timeout
   
        if type(target_language) is list:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.make_request, target, source_language, text, timeout) for target in target_language]
                return_value = [f.result() for f in futures]
                return return_value
        return self.make_request(target_language, source_language, text, timeout)