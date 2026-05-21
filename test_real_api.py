import pytest
import requests

BASE_URL = "https://jsonplaceholder.typicode.com"

# 不再需要 login_user fixture，JSONPlaceholder 无需认证

def test_create_post_success():
    """正常创建帖子"""
    payload = {"title": "Test Post 1", "body": "This is a test post", "userId": 1}
    response = requests.post(f"{BASE_URL}/posts", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Post 1"
    assert data["body"] == "This is a test post"
    assert data["userId"] == 1
    assert "id" in data

def test_create_post_unauthorized():
    """未认证创建（模拟，实际该API无认证，我们换个思路测必填字段缺失）"""
    payload = {"title": "Test Post 2"}  # 缺少 body 和 userId
    response = requests.post(f"{BASE_URL}/posts", json=payload)
    # JSONPlaceholder 不校验字段，都会返回201，因此改为验证它仍然创建成功
    assert response.status_code == 201
    assert response.json()["title"] == "Test Post 2"

def test_get_all_posts():
    """获取帖子列表"""
    response = requests.get(f"{BASE_URL}/posts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_post_by_id():
    """根据有效ID获取帖子"""
    response = requests.get(f"{BASE_URL}/posts/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_get_post_not_found():
    """查询不存在的帖子"""
    response = requests.get(f"{BASE_URL}/posts/99999")
    assert response.status_code == 404

def test_update_post():
    """更新帖子"""
    payload = {"title": "Updated Title", "body": "Updated body"}
    response = requests.put(f"{BASE_URL}/posts/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["body"] == "Updated body"

def test_delete_post():
    """删除帖子"""
    response = requests.delete(f"{BASE_URL}/posts/1")
    # JSONPlaceholder 删除资源返回 200，且返回空对象
    assert response.status_code == 200

def test_delete_post_not_found():
    """删除不存在的帖子（模拟）"""
    response = requests.delete(f"{BASE_URL}/posts/99999")
    # 同样返回 200，但这就是 API 的行为
    assert response.status_code == 200