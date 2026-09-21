from flask import Flask, jsonify
import os

app = Flask(__name__)

VERSION = os.getenv("APP_VERSION", "4.2.0")
PAYMENT_STATUS = os.getenv("PAYMENT_STATUS", "CONFLICT_BRANCH")


@app.route("/")
def home():
    return jsonify({
        "application": "Retail Platform",
        "version": VERSION,
        "payment_status": PAYMENT_STATUS,
         "environment": os.getenv("APP_ENV", "development"),
        "status": "running"
    })


@app.route("/health")
def health():
    if PAYMENT_STATUS == "BROKEN":
        return jsonify({
            "status": "unhealthy",
            "version": VERSION
        }), 500

    return jsonify({
        "status": "healthy",
        "version": VERSION
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)