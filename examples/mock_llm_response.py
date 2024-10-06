import time

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/v1/completions", methods=["POST"])
def completions():
    """Mock endpoint for OpenAI completions API."""
    data = request.json or {}
    prompt = data.get("prompt", "")
    model = data.get("model", "default-model")
    # max_tokens = data.get("max_tokens", 4096)

    response = {
        "id": f"cmpl-{int(time.time())}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "text": f"This is a mock response to: {prompt}",
                "index": 0,
                "logprobs": None,
                "finish_reason": "length",
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 10,
            "total_tokens": len(prompt.split()) + 10,
        },
    }

    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=30000)
