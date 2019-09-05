import pika
import os
import json
from dotenv import load_dotenv

load_dotenv()
queue_name = os.getenv('QUEUE_NAME')
results_queue = os.getenv('RESULTS_QUEUE')

# Connect
connection = pika.BlockingConnection(pika.ConnectionParameters('127.0.0.1'))
channel = connection.channel()

# Create results queue
channel.queue_declare(queue=results_queue, durable=True)


def add_result_to_queue(result, ch, delivery_tag):
    """
    Add the results back to rabbitmq.
    """
    ch.basic_publish(exchange='',
                     routing_key=results_queue,
                     body=result)
    ch.basic_ack(delivery_tag=delivery_tag)


def callback(ch, method, properties, body):
    """
    Handle Message from RabbitMQ.
    """
    print("Processing %r" % body)
    add_result_to_queue(body, ch, method.delivery_tag)


channel.basic_consume(queue=queue_name,
                      auto_ack=False,
                      on_message_callback=callback)
print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()

# connection.close()
