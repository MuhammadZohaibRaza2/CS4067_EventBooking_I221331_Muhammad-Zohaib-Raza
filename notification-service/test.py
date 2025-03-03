import pika, json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='booking_confirmed')

test_data = {
    "booking_id": "TEST_123",
    "user_email": "zohaibasit786@gmail.com",
    "status": "CONFIRMED"
}

channel.basic_publish(
    exchange='',
    routing_key='booking_confirmed',
    body=json.dumps(test_data)
)
connection.close()




