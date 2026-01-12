FROM python:3.10-slim-bookworm

# WeasyPrint native deps (Cairo/Pango/Harfbuzz/Fribidi/GDK-Pixbuf/GLib) + fonts
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfribidi0 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libffi8 \
    libxml2 \
    libxslt1.1 \
    fonts-dejavu-core \
    fonts-noto-core \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt

COPY . .

# Start server (use sh because slim images may not have bash)
CMD ["sh","-lc","python -m uvicorn app:app --host 0.0.0.0 --port ${PORT} --log-level debug --access-log"]
