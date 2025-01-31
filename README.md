# Riot QR Auth
<table>
	<tr>
		<td>
			Don't forget to hit the star ⭐ button
		</td>
	</tr>
</table>
An SDK that helps you obtain Riot access tokens via QR authentication.

## Examples

### Backend (Python)
Get Token and Cookies
```python
import requests
import urllib.parse

BASE_URL = 'https://riot-auth.vercel.app'

headers = {'country-code': 'en-US'} #This header is optional and can be set to 'auto'.
response = requests.post(f'{BASE_URL}/login_url', headers=headers).json()
login_url = response.get('login_url')

enurl = urllib.parse.quote(login_url, safe=':/')
print('Scan QR code:', f'https://api.qrserver.com/v1/create-qr-code/?size=512x512&data={enurl}')
print('\nOr visit:', login_url)

input('\nPress Enter after auth..')
response = requests.post(f'{BASE_URL}/get_token', headers=headers).json()
if response.get('type') == 'success':

    token = response['access_token']
    print('\nAccess Token:', token)

    print('\nUser Info:', requests.get('https://auth.riotgames.com/userinfo', 
        headers={'Authorization': f'Bearer {token}'}).json())

    if 'cookies' in response:
        print('\nssid:', response['cookies']['ssid'])
    else:
        print('No cookies')
else:
    print('Error')
```
<br>

Cookie Reauth

https://github.com/techchrism/riot-auth-test
```python
import requests

BASE_URL = 'https://riot-auth.vercel.app'
ssid = ''

headers = {
    'ssid': ssid 
}

try:
    response = requests.post(
        f'{BASE_URL}/cookie_reauth',
        headers=headers
    ).json()
    
    if 'access_token' in response:
        token = response['access_token']
        print('\nAccess Token:', token)
        
        user_info = requests.get(
            'https://auth.riotgames.com/userinfo',
            headers={'Authorization': f'Bearer {token}'}
        ).json()
        print('\nUser Info:', user_info)
    else:
        print('Error:', response.get('error', 'Unknown error'))
        
except Exception as e:
    print('Error:', str(e))
```
### With iFrame
[`Check out this demo`](https://riot-auth.vercel.app/demo/)

[`Use for store (Only 'kr')`](https://valstore.vercel.app/)
```html
<!DOCTYPE html>
<html>
<head>
    <title>Riot Auth</title>
    <style>
        .auth-frame {
            width: 430px;
            height: 1000px;
            border: none;
        }
    </style>
</head>
<body>
    <iframe src="https://riot-auth.vercel.app/auth/auto/" class="auth-frame"></iframe>
    <div id="token"></div>
    
    <script>
        window.addEventListener('message', function(event) {
            if (event.data.type === 'access_token') {
                const accessToken = event.data.token;
                document.getElementById('token').textContent = 'Access Token: ' + accessToken;
            }
        });
    </script>
</body>
</html>
```
> [!NOTE]  
> This project includes the source code of the [`easygoogletranslate`](https://github.com/ahmeterenodaci/easygoogletranslate) module to minimize external dependencies.
