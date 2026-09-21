import os 
import sys
sys.path.insert(0,os.path.abspath("../app"))
from app import app
def test_home():
    client = app.test_client()
    response = client.get("/")
    assert response.ststus_code == 200
def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200