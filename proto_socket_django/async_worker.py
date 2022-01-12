import threading
import time
import traceback
from typing import Callable, Any, List, Union, Type, Dict, Tuple
from attr import dataclass
from proto.messages import RxMessage


@dataclass
class AsyncMessage:
    handler: Callable
    args: Tuple
    kwargs: Dict
    on_result: Union[Callable[[Union[None, 'proto_socket_django.FPSReceiverError']], None], None] = None


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
                    result = async_message.handler(*async_message.args, **async_message.kwargs)
                    if async_message.on_result:
                        async_message.on_result(result)
                except:
                    traceback.print_exc()
            else:
                time.sleep(0.05)
