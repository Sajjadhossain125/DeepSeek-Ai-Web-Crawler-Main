# log_stream.py
from queue import Queue

log_queue = Queue()

def stream_log(message: str):
    print(message)  # Still log to terminal
    log_queue.put(message)