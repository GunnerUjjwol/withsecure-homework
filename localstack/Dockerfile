FROM localstack/localstack:0.14.2

COPY init-resources.sh /docker-entrypoint-initaws.d/

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY kinesis_consumer.py ./

ENV SERVICES=kinesis,lambda,sqs
ENV KINESIS_ERROR_PROBABILITY=0.1
