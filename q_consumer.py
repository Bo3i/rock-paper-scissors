import threading
import pika

# Consumer class for RabbitMQ message consumption in new thread
class Consumer(threading.Thread):
    def __init__(self, queue_name, host, callback, stop_event):
        super().__init__()
        self.queue_name = queue_name
        self.stop_event = stop_event
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_name)
        self.callback = callback

    def run(self):

        while not self.stop_event.is_set():
            method_frame, header_frame, body = self.channel.basic_get(self.queue_name)
            if method_frame:
                self.channel.basic_ack(method_frame.delivery_tag)
                self.callback(self.channel, method_frame, header_frame, body)

    def stop(self):
        self.stop_event.set()
        self.connection.close()


