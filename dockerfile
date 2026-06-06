FROM python:3

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends gettext && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -U -r requirements.txt

COPY /source/ .
COPY lotro-com-chain.pem /usr/src/

ARG VERSION=dev
RUN sed -i 's/__version__ = "[^"]*"/__version__ = "'"${VERSION}"'"/' __init__.py

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import sqlite3, os; db=os.environ.get('DB_PATH','raid_db'); sqlite3.connect(db).execute('SELECT 1')" || exit 1

CMD [ "python", "./main.py" ]
