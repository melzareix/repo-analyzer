from __future__ import absolute_import
import pika
import os
import json
from dotenv import load_dotenv
from main import analyze_repo

load_dotenv()
queue_name = os.getenv('QUEUE_NAME')
results_queue = os.getenv('RESULTS_QUEUE')

# Connect
connection = pika.BlockingConnection(
    pika.ConnectionParameters(os.getenv('RABBIT_HOST')))
channel = connection.channel()

# Create results queue
channel.queue_declare(queue=results_queue, durable=True)


def add_result_to_queue(result, ch, delivery_tag):
    """
    Add the results back to rabbitmq.
    """
    print(delivery_tag)
    ch.basic_publish(exchange='',
                     routing_key=results_queue,
                     body=result)
    ch.basic_ack(delivery_tag=delivery_tag)


def callback(ch, method, properties, body):
    """
    Handle Message from RabbitMQ.
    """
    url = body.decode('UTF-8')
    print("Processing %r" % url.strip())
    result = analyze_repo(url.strip())
    print('Done..')
    add_result_to_queue(result, ch, method.delivery_tag)


channel.basic_consume(queue=queue_name,
                      auto_ack=False,
                      on_message_callback=callback)
print(' [*] Waiting for messages. To exit press CTRL+C')
channel.start_consuming()

# connection.close()
