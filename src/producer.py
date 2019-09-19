"""
RabbitMQ Producer to add the repo urls to queue.
"""
import os
import pika
from dotenv import load_dotenv

load_dotenv()


class Producer:
    """
    RabbitMQ Producer Class.
    """

    def __init__(self):
        load_dotenv()
        self.queue_name = os.getenv('QUEUE_NAME')
        self.connection = None
        self.channel = None
        self.connect()

    @staticmethod
    def read_file(file_path):
        """
        Read the file into string array.
        """
        with open(file_path) as file:
            return file.readlines()

    def fill_queue(self, queue, messages):
        """
        Add all the urls to the queue.
        """
        for message in messages:
            self.channel.basic_publish(exchange='',
                                       routing_key=self.queue_name,
                                       body=message)

    def connect(self):
        """
        Connect to RabbitMQ Server.
        """
        credentials = pika.credentials.PlainCredentials(
            os.getenv('RABBIT_USERNAME'), os.getenv('RABBIT_PASSWORD'))
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(os.getenv('RABBIT_HOST'),
                                      os.getenv('RABBIT_PORT'), '/',
                                      credentials))
        self.channel = self.connection.channel()

    def start(self):
        """
        Load urls from file and add them to queue.
        """
        # read url list
        url = os.path.join(os.path.abspath(
            os.path.dirname(__file__)), '..', 'url_list.txt')
        data = Producer.read_file(url)

        # Connect to urls queue.
        queue = self.channel.queue_declare(
            queue=self.queue_name, durable=True, auto_delete=False)

        # Add messages to queue if not already exists.
        msg_count = queue.method.message_count
        if msg_count < len(data):
            print('Filling queue...')
            self.fill_queue(queue, data)
            print('Queue filled...')
        else:
            print('Queue already filled.')

        self.connection.close()


if __name__ == "__main__":
    producer = Producer()
    producer.start()
