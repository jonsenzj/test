
import pytest
import requests

@pytest.fixture
def login_url():
    return "http://localhost:5000/login"

def test_correct_login(login_url):
    response = requests.post(login_url, json={"username": "testuser", "password": "Test@123456"})
    assert response.status_code == 200
    assert response.json()['message'] == '登录成功'

def test_wrong_password(login_url):
    response = requests.post(login_url, json={"username": "testuser", "password": "WrongPass"})
    assert response.status_code == 401
    assert response.json()['message'] == '密码错误，请重试'

def test_empty_password(login_url):
    response = requests.post(login_url, json={"username": "testuser", "password": ""})
    assert response.status_code == 401
    assert response.json()['message'] == '密码不能为空'

def test_password_masking(login_url):
    response = requests.post(login_url, json={"username": "testuser", "password": "password"})
    assert response.status_code == 200
    assert response.json()['code'] == 200

def test_wrong_username(login_url):
    response = requests.post(login_url, json={"username": "wronguser", "password": "Test@123456"})
    assert response.status_code == 401
    assert response.json()['message'] == '用户名不存在，请重试'
