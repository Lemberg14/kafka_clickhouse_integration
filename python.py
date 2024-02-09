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
    topic = 'readings'  # Name of the Kafka topic
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
