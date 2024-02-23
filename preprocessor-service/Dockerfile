FROM python:3.12
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ENV AWS_ENDPOINT_URL="http://localstack:4566"
ENV BATCH_SIZE=10
ENV VISIBILITY_TIMEOUT=30

COPY . .

CMD [ "python", "./main.py" ]
