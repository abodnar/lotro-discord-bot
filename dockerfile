FROM python:3

RUN apt-get update && apt-get install -y gettext && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -U -r requirements.txt

COPY /source/ .
COPY lotro-com-chain.pem /usr/src/

CMD [ "python", "./main.py" ]
