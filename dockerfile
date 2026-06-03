FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -U -r requirements.txt

COPY /source/ .
COPY lotro-com-chain.pem /usr/src/
COPY emojis/ /usr/src/emojis/

CMD [ "python", "./main.py" ]
