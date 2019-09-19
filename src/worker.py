"""
RabbitMQ Worker to fetch urls from queue then apply the analysis.
"""
from __future__ import absolute_import
import os
import pika
from dotenv import load_dotenv
from main import RepoAnalyzer


class Worker:
    """
    RabbitMQ Worker Class.
    """

    def __init__(self):
        load_dotenv()
        self.analyzer = RepoAnalyzer()
        self.queue_name = os.getenv('QUEUE_NAME')
        self.results_queue = os.getenv('RESULTS_QUEUE')
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        """
        Connect to RabbitMQ Server.
        """
        # Connect to RabbitMQ
        credentials = pika.credentials.PlainCredentials(
            os.getenv('RABBIT_USERNAME'), os.getenv('RABBIT_PASSWORD'))
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(os.getenv('RABBIT_HOST'),
                                      os.getenv('RABBIT_PORT'), '/',
                                      credentials))
        self.channel = self.connection.channel()

        # Create results queue
        self.channel.queue_declare(queue=self.results_queue, durable=True)

    def add_result_to_queue(self, result, ch, delivery_tag):
        """
        Add the results back to rabbitmq.
        """
        ch.basic_publish(exchange='',
                         routing_key=self.results_queue,
                         body=result)
        ch.basic_ack(delivery_tag=delivery_tag)

    def callback(self, ch, method, _, body):
        """
        Handle Message from RabbitMQ.
        """
        url = body.decode('UTF-8')
        print("Processing %r" % url.strip())
        result = self.analyzer.analyze_repo(url.strip())
        print('Done..')
        self.add_result_to_queue(result, ch, method.delivery_tag)

    def start(self):
        """
        Consume urls from queue and process them then add result
        to the results queue.
        """
        # Get messages from queue as long as queue not empty.
        while True:
            method, properties, body = self.channel.basic_get(
                queue=self.queue_name, auto_ack=False)
            if method is None:
                print('Done..')
                self.connection.close()
                break
            self.callback(self.channel, method, properties, body)


if __name__ == "__main__":
    worker = Worker()
    worker.start()
