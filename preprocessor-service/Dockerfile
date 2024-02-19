FROM python:3.9
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ENV LOCALSTACK_ENDPOINT_URL="http://localhost:4566"
ENV BATCH_SIZE=10
ENV VISIBILITY_TIMEOUT=30

COPY . .

CMD [ "python", "./main.py" ]
