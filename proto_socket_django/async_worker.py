import threading
import time
import traceback
from sqlite3 import InterfaceError
from typing import Callable, Any, List, Union, Type, Dict, Tuple
from attr import dataclass
from proto.messages import RxMessage
from django.db import connections


@dataclass
class AsyncMessage:
    handler: Callable
    args: Tuple
    kwargs: Dict
    run: Callable[[], None]
    on_result: Union[Callable[[Union[None, 'proto_socket_django.FPSReceiverError']], None], None] = None


class AsyncWorker:
    message_queue: List[AsyncMessage] = []

    def __init__(self):
        self.thread = threading.Thread(target=self.runner)
        self.thread.setDaemon(True)
        self.thread.start()

    def runner(self):
        last_conn_check = time.time()
        while True:
            if self.message_queue:
                async_message = self.message_queue.pop(0)
                try:
                    result = async_message.handler(*async_message.args, **async_message.kwargs)
                    if async_message.on_result:
                        async_message.on_result(result)
                except InterfaceError:
                    traceback.print_exc()
                    print('restarting worker')
                    self.thread = threading.Thread(target=self.runner)
                    self.thread.setDaemon(True)
                    self.thread.start()
                    return
                except:
                    traceback.print_exc()

            else:
                time.sleep(0.05)
                try:
                    if time.time() - last_conn_check > 10:
                        last_conn_check = time.time()
                        for conn in connections.all():
                            conn.close_if_unusable_or_obsolete()
                except:
                    traceback.print_exc()
