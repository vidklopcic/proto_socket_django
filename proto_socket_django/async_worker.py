import threading
import time
import traceback
from typing import Callable, Any, List, Union
from attr import dataclass
from proto.messages import RxMessage

from proto_socket_django import FPSReceiverError


@dataclass
class AsyncMessage:
    handler: Callable[[RxMessage], Union[FPSReceiverError, None]]
    message: RxMessage
    on_result: Union[Callable[[Union[None, FPSReceiverError]], None], None] = None


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
                    result = async_message.handler(async_message.message)
                    if async_message.on_result:
                        async_message.on_result(result)
                except:
                    traceback.print_exc()
            else:
                time.sleep(0.05)
