"""
RabbitMQ Worker to fetch urls from queue then apply the analysis.
"""
from __future__ import absolute_import
import pika
import os
import json
from dotenv import load_dotenv
from main import analyze_repo

load_dotenv()
queue_name = os.getenv('QUEUE_NAME')
results_queue = os.getenv('RESULTS_QUEUE')

# Connect to RabbitMQ
credentials = pika.credentials.PlainCredentials(
    os.getenv('RABBIT_USERNAME'), os.getenv('RABBIT_PASSWORD'))
connection = pika.BlockingConnection(
    pika.ConnectionParameters(os.getenv('RABBIT_HOST'),
                              os.getenv('RABBIT_PORT'), '/', credentials))
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
    url = body.decode('UTF-8')
    print("Processing %r" % url.strip())
    result = analyze_repo(url.strip())
    print('Done..')
    add_result_to_queue(result, ch, method.delivery_tag)


# Get messages from queue as long as queue not empty.
while True:
    method, properties, body = channel.basic_get(
        queue=queue_name, auto_ack=False)
    if method is None:
        print('Done..')
        connection.close()
        break
    callback(channel, method, properties, body)
