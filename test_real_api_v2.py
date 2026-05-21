import requests

BASE_URL = "https://jsonplaceholder.typicode.com"

def test_post_create_001():
    response = requests.post(f"{BASE_URL}/posts", json={"title": "Test Title", "body": "Test Body", "userId": 1})
    assert response.status_code == 201
    assert "id" in response.json()
    assert "title" in response.json()
    assert "body" in response.json()
    assert "userId" in response.json()

def test_post_create_002():
    response = requests.post(f"{BASE_URL}/posts", json={"title": "Test Title", "body": "Test Body", "userId": 999})
    assert response.status_code == 400

def test_post_list_001():
    response = requests.get(f"{BASE_URL}/posts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_post_list_002():
    response = requests.get(f"{BASE_URL}/posts")
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_post_get_001():
    response = requests.get(f"{BASE_URL}/posts/1")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)

def test_post_get_002():
    response = requests.get(f"{BASE_URL}/posts/999")
    assert response.status_code == 404

def test_post_update_001():
    response = requests.put(f"{BASE_URL}/posts/1", json={"title": "Updated Title", "body": "Updated Body", "userId": 1})
    assert response.status_code == 200
    assert "id" in response.json()
    assert "title" in response.json()
    assert "body" in response.json()
    assert "userId" in response.json()

def test_post_update_002():
    response = requests.put(f"{BASE_URL}/posts/999", json={"title": "Updated Title", "body": "Updated Body", "userId": 1})
    assert response.status_code == 404