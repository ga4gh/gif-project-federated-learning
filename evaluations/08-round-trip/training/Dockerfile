# Training step for the round-trip acceptance test.
# Small and multi-arch (amd64 + arm64): python-slim + NumPy only.
FROM python:3.12-slim
RUN pip install --no-cache-dir "numpy>=1.26,<3"
WORKDIR /app
COPY train_round.py fedavg.py make_toy_data.py /app/
# No ENTRYPOINT: TES executors give the full command, e.g.
#   ["python", "/app/train_round.py", "--data-in", "/in/data.csv", ...]
CMD ["python", "/app/train_round.py", "--help"]
