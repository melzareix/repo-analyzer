import pika
import time
from pprint import pprint
from dotenv import load_dotenv
import os
import logging
logging.basicConfig()

load_dotenv()
queue_name = os.getenv('QUEUE_NAME')


def read_file(file_path):
    """
    Read the file into string array.
    """
    with open(file_path) as file:
        return file.readlines()


def fill_queue(queue, messages):
    """
    Add all the urls to the queue.
    """
    for message in messages:
        channel.basic_publish(exchange='',
                              routing_key=queue_name,
                              body=message)


data = read_file('url_list.txt')


# Connect to server.
connection = pika.BlockingConnection(pika.ConnectionParameters('127.0.0.1'))
channel = connection.channel()

# Connect to urls queue.
queue = channel.queue_declare(queue=queue_name, durable=True)

# Add messages to queue if not already exists.
msg_count = queue.method.message_count
if msg_count < len(data):
    print('Filling queue...')
    fill_queue(queue, data)
    print('Queue filled...')
else:
    print('Queue already filled.')

connection.close()