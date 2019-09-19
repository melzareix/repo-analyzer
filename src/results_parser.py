"""
RabbitMQ Worker to get the JSON results for each repo.
"""
from __future__ import absolute_import
import os
import json
import pika
from dotenv import load_dotenv


class ResultsParser:
    """
    Result Parser from the results queue and save to json file on disk Class.
    """

    def __init__(self):
        load_dotenv()
        self.queue_name = os.getenv('RESULTS_QUEUE')
        self.connection = None
        self.channel = None
        self.results = []
        self.script_path = os.path.abspath(os.path.dirname(__file__))
        self.save_interval = int(os.getenv('SAVE_EVERY'))
        self.connect()

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

        # Create results queue
        self.channel.queue_declare(
            queue=self.queue_name, durable=True, passive=True)

    def callback(self, ch, method, properties, body):
        """
        Get message from rabbit and add it to results list
        write the data to disk every SAVE_EVERY message.
        """
        self.results.append(json.loads(body))
        if method.delivery_tag % self.save_interval == 0:
            file_name = 'results_{}.json'.format(str(method.delivery_tag))
            file_path = os.path.join(self.script_path, '../results', file_name)
            with open(file_path, 'w') as f:
                f.write(json.dumps(self.results))

    def start(self):
        """
        Fetch results from rabbitmq results queue.
        """
        print('Fetching Results..')
        while True:
            method, properties, body = self.channel.basic_get(
                queue=self.queue_name, auto_ack=False)
            if method is None:
                print('Data written to disk.')
                self.connection.close()
            self.callback(self.channel, method, properties, body)


if __name__ == "__main__":
    parser = ResultsParser()
    parser.start()
