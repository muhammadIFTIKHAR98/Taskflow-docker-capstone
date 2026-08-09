from flask import Flask, jsonify
import os

app= Flask(__name__)

@app.route("/health")
def health():
    return jsonify(status="ok", service="taskflow-api")

@app.route("/")
def index():
    return jsonify(message="TaskFlow API is running")

if __name__ == "__main__":
   app.run(host="0.0.0.0", port=5000)

