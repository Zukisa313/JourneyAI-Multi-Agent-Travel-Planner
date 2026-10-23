"""Flask app: serves the UI and streams agent progress to the browser."""
import json

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

load_dotenv()  # must run before backend imports so tools see the env vars

from backend import graph  # noqa: E402

app = Flask(__name__, template_folder="template", static_folder="static")

REQUIRED = ("origin", "destination", "start_date", "end_date")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/plan")
def plan():
    data = request.get_json(silent=True) or {}
    missing = [k for k in REQUIRED if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    state = {
        "origin": data["origin"].strip(),
        "destination": data["destination"].strip(),
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "travelers": int(data.get("travelers") or 1),
        "budget": (data.get("budget") or "").strip(),
        "interests": (data.get("interests") or "").strip(),
    }

    def generate():
        """Newline-delimited JSON: one event per finished agent node."""
        try:
            for update in graph.stream(state, stream_mode="updates"):
                for node, output in update.items():
                    yield json.dumps({"node": node, "output": output}) + "\n"
            yield json.dumps({"node": "done"}) + "\n"
        except Exception as exc:  # noqa: BLE001
            yield json.dumps({"node": "error", "message": str(exc)}) + "\n"

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
