# kafka_clickhouse_integration

[link](https://github.com/Lemberg14/kafka_clickhouse_integration/blob/main/Test%20Task%20Appflame%20.pdf) to the test task

Firstly we need to create docker compose file
```yaml
version: '3.7'

services:
  zookeeper:
    image: zookeeper:latest
    container_name: zookeeper
    restart: always
    networks:
      - kafka_clickhouse_net

  kafka:
    image: bitnami/kafka:latest
    container_name: kafka
    restart: always
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: INSIDE://kafka:9093,OUTSIDE://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: INSIDE:PLAINTEXT,OUTSIDE:PLAINTEXT
      KAFKA_LISTENERS: INSIDE://0.0.0.0:9093,OUTSIDE://0.0.0.0:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: INSIDE
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    depends_on:
      - zookeeper
    networks:
      - kafka_clickhouse_net

  clickhouse:
    image: clickhouse/clickhouse-server
    container_name: clickhouse
    restart: always
    ports:
      - "8123:8123"
      - "9000:9000"
    environment:
      CLICKHOUSE_SERVER_PARAMETERS: --log_level=debug
    networks:
      - kafka_clickhouse_net

  ubuntu:
    image: ubuntu:latest
    container_name: ubuntu
    command: bash -c "apt-get update && apt-get install -y python3 python3-pip && pip3 install kafka-python && tail -f /dev/null"
    depends_on:
      - kafka
    networks:
      - kafka_clickhouse_net

networks:
  kafka_clickhouse_net:
    driver: bridge
```

Now we need to run docker

```
docker-compose -f docker-compose.yml up
```

Next step we need connect to clickhouse and create out tables

For this we need to list docker containers

```
docker ps
```
We have next output
```
CONTAINER ID   IMAGE                          COMMAND                  CREATED          STATUS          PORTS                                                      NAMES
06c47b115d48   ubuntu:latest                  "bash -c 'apt-get up…"   49 minutes ago   Up 49 minutes                                                              ubuntu
9b66880d696d   bitnami/kafka:latest           "/opt/bitnami/script…"   49 minutes ago   Up 49 minutes   0.0.0.0:9092->9092/tcp                                     kafka
b87f2f9a91d1   zookeeper:latest               "/docker-entrypoint.…"   49 minutes ago   Up 49 minutes   2181/tcp, 2888/tcp, 3888/tcp, 8080/tcp                     zookeeper
fe593a2b610f   clickhouse/clickhouse-server   "/entrypoint.sh"         49 minutes ago   Up 49 minutes   0.0.0.0:8123->8123/tcp, 0.0.0.0:9000->9000/tcp, 9009/tcp   clickhouse
```
Next we need to run docker-compose exec -it to connect to clickhouse container

```
docker-compose exec -it fe593a2b610f bash
```

Now we are connected to out clickouse container where we need to launch clickhouse client using next command

```
clickhouse-client
```

Next step we need to create out 3 tables

```sql
CREATE TABLE events (
    ts Int32,
    user_id Int32,    
    operation String,
    status Int32
) Engine = MergeTree()
ORDER BY ts;

CREATE TABLE events_queue (
    ts Int32,
    user_id Int32,    
    operation String,
    status Int32
)
ENGINE = Kafka
SETTINGS kafka_broker_list = 'kafka:9093',
       kafka_topic_list = 'events',
       kafka_group_name = 'events_consumer_group1',
       kafka_format = 'JSONEachRow',
       kafka_max_block_size = 1048576;

CREATE MATERIALIZED VIEW events_queue_mv TO events AS
SELECT ts, user_id, operation, status
FROM events_queue;
```

Open new terminal and use docker ps and docker compoase exec to connect to Kafka container

```
docker-compose exec -it 9b66880d696d bash
```

Here we need to create topic

```
kafka-topics.sh --bootstrap-server localhost:9092 --topic events --create --partitions 6 --replication-factor 1
```

We should get next output
```
Created topic events.
```

Open new terminal and use docker ps and docker compoase exec to connect to Ubuntu container

```
docker-compose exec -it 06c47b115d48 bash
```

Here we need to create and run python script which will send every 5 seconds json file to kafka

Create python file
```
nano python.py
```
And insert script it self
```python
from kafka import KafkaProducer
import json
import time

def send_to_kafka(bootstrap_servers, topic, data):
    producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                             value_serializer=lambda x: json.dumps(x).encode('utf-8'))

    producer.send(topic, value=data)
    producer.flush()
    producer.close()

if __name__ == "__main__":
    bootstrap_servers = 'kafka:9093'  # Kafka service name defined in the Docker Compose file
    topic = 'events'  # Name of the Kafka topic
    data = {
        'ts': 1798128392,
        'user_id': 123,
        'operation': 'like',
        'status': 1
    }  # JSON data to be sent

    while True:
        send_to_kafka(bootstrap_servers, topic, data)
        print("Sent message to Kafka")
        time.sleep(5)  # Send message every 5 seconds
```

To run this script execute 

```
python3 python.py
```
After running the script back to clickhouse terminal and select from events table
```sql
SELECT *
FROM events
```

We should reieve next output

```
SELECT *
FROM events

Query id: e3175f49-5ecc-48ea-b75f-925962ad7e0f

┌─────────ts─┬─user_id─┬─operation─┬─status─┐
│ 1798128392 │     123 │ like      │      1 │
└────────────┴─────────┴───────────┴────────┘
┌─────────ts─┬─user_id─┬─operation─┬─status─┐
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
└────────────┴─────────┴───────────┴────────┘
┌─────────ts─┬─user_id─┬─operation─┬─status─┐
│ 1798128392 │     123 │ like      │      1 │
└────────────┴─────────┴───────────┴────────┘
┌─────────ts─┬─user_id─┬─operation─┬─status─┐
│ 1798128392 │     123 │ like      │      1 │
│ 1798128392 │     123 │ like      │      1 │
└────────────┴─────────┴───────────┴────────┘

11 rows in set. Elapsed: 0.010 sec. 
```
