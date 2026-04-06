import requests

# 测试登录
login_data = {
    "username": "testuser",
    "password": "123456"
}

response = requests.post('http://localhost:8000/api/v1/auth/login', json=login_data)
print(f"Login Status Code: {response.status_code}")
print(f"Login Response: {response.json()}")

# 测试获取用户信息
if response.status_code == 200:
    token = response.json().get('access_token')
    if token:
        headers = {
            "Authorization": f"Bearer {token}"
        }
        user_response = requests.get('http://localhost:8000/api/v1/users/me', headers=headers)
        print(f"\nUser Info Status Code: {user_response.status_code}")
        print(f"User Info Response: {user_response.json()}")
