from flask import Flask, Response, request
import subprocess
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
proc = None

@app.route("/run")
def run():
    start = request.args.get("start")
    end = request.args.get("end")

    def search_proc():
        global proc
        if proc is not None and proc.poll() is None:
            yield "data: Stopping prev search\n\n"
            proc.terminate()

        yield f"data: Search {start} to {end}\n\n"
        proc = subprocess.Popen(
            ["python", "-u", "WikiExplorer.py", start, end],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in proc.stdout:
            yield f"data: {line}\n\n"

        proc.wait()
        yield "data: ✅ Finished\n\n"

    return Response(search_proc(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True)
