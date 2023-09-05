import threading
import time
import traceback
from sqlite3 import InterfaceError
from typing import Callable, Any, List, Union, Type, Dict, Tuple
from attr import dataclass
from django.conf import settings
from proto.messages import RxMessage
from django.db import connections
import queue
import asyncio

@dataclass
class LongRunningTask:
    handler: Callable
    args: Tuple
    kwargs: Dict
    run: Callable[[], None]
    on_result: Union[Callable[[Union[None, 'proto_socket_django.FPSReceiverError']], None], None] = None
    is_coroutine: bool = False
    ack: bool = False


class SyncWorker:
    task_queue: queue.Queue = queue.Queue()

    def __init__(self):
        self.thread = threading.Thread(target=self.runner)
        self.thread.setDaemon(True)
        self.thread.start()
        self.last_db_check = time.time()

    def check_db(self):
        try:
            if time.time() - self.last_db_check > 10:
                self.last_db_check = time.time()
                for conn in connections.all():
                    conn.close_if_unusable_or_obsolete()
        except:
            traceback.print_exc()

    def runner(self):
        forward_exceptions = getattr(settings, 'PSD_FORWARD_EXCEPTIONS', False)
        format_exception = getattr(settings, 'PSD_EXCEPTION_FORMATTER', lambda e: str(e))

        while True:
            async_message = self.task_queue.get()
            self.check_db()
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
            except Exception as e:
                from proto_socket_django import FPSReceiverError
                if forward_exceptions and async_message.ack:
                    async_message.on_result(FPSReceiverError(format_exception(e)))
                elif not forward_exceptions:
                    raise
                traceback.print_exc()


class AsyncWorker:
    task_queue: asyncio.Queue = None

    def __init__(self):
        if self.task_queue is not None:
            raise Exception('AsyncWorker already initialized')
        self.task_queue = asyncio.Queue()
        self.thread = threading.Thread(target=self._start)
        self.thread.setDaemon(True)
        self.thread.start()
        self.last_db_check = time.time()
        self.loop = None

    def check_db(self):
        try:
            if time.time() - self.last_db_check > 10:
                self.last_db_check = time.time()
                for conn in connections.all():
                    conn.close_if_unusable_or_obsolete()
        except:
            traceback.print_exc()

    def _start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.runner())

    async def runner(self):
        forward_exceptions = getattr(settings, 'PSD_FORWARD_EXCEPTIONS', False)
        format_exception = getattr(settings, 'PSD_EXCEPTION_FORMATTER', lambda e: str(e))
        while True:
            async_task = await self.task_queue.get()
            self.check_db()
            try:
                result = await async_task.handler(*async_task.args, **async_task.kwargs)
                if async_task.on_result:
                    async_task.on_result(result)
            except InterfaceError:
                traceback.print_exc()
                print('restarting worker')
                self.thread = threading.Thread(target=self.runner)
                self.thread.setDaemon(True)
                self.thread.start()
                return
            except Exception as e:
                from proto_socket_django import FPSReceiverError
                if forward_exceptions and async_task.ack:
                    async_task.on_result(FPSReceiverError(format_exception(e)))
                elif not forward_exceptions:
                    raise
                traceback.print_exc()
