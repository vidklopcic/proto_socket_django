import threading
import time
import traceback
from typing import Callable, Any, List
from attr import dataclass
from proto.messages import RxMessage


@dataclass
class AsyncMessage:
    handler: Callable[[RxMessage], Any]
    message: RxMessage


class AsyncWorker:
    message_queue: List[AsyncMessage] = []

    def __init__(self):
        self.thread = threading.Thread(target=self.runner)
        self.thread.setDaemon(True)
        self.thread.start()

    def runner(self):
        while True:
            if self.message_queue:
                async_message = self.message_queue.pop(0)
                try:
                    async_message.handler(async_message.message)
                except:
                    traceback.print_exc()
            else:
                time.sleep(0.05)
