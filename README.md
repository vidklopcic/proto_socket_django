# Proto Socket Django

A Django-based library for building real-time web applications using WebSocket communication with protocol buffers.
Supports Django, Flutter, and React clients.

## Features

- WebSocket-based real-time communication
- Protocol Buffer message serialization
- Authentication support with JWT tokens
- Support for synchronous and asynchronous message handling
- Automatic message routing and handling
- Built-in support for Flutter and React clients
- Message acknowledgment system
- Group-based broadcasting
- File upload handling

## Installation

```bash
pip install proto-socket-django
```

## Quick Start

### 1. Configure Django Settings

```python
INSTALLED_APPS = [
    ...
    'channels',
    'proto_socket_django',
]

# Worker configuration
PSD_N_SYNC_WORKERS = 2  # Number of sync workers
PSD_RUN_ASYNC_WORKER = True  # Enable async worker
PSD_DEFAULT_AUTH = True  # Default authentication requirement
PSD_FORWARD_EXCEPTIONS = False  # Forward exceptions to client
```

### 2. Create a Consumer

```python
from proto_socket_django import ApiWebsocketConsumer


class MyConsumer(ApiWebsocketConsumer):
    receivers = [
        AuthenticationReceiver,
        CustomReceiver,
        # Add your receivers here
    ]

    # Optional: Define consumer groups
    APP_GROUP = 'my_consumer_group'
    groups = [APP_GROUP]
```

### 3. Create Receivers

```python
import proto_socket_django as psd
import proto.messages as pb


class CustomReceiver(psd.FPSReceiver):
    @psd.receive()
    def custom_message(self, message: pb.RxCustomMessage):
        # Simple synchronous handler
        self.consumer.send_message(pb.TxResponse(data="Success"))
```

## Message Handling

### 1. Basic Handler Pattern

Handlers are automatically connected based on their type hints. By convention, the method name should match the proto
message name in snake_case:

```python
import proto_socket_django as psd
import proto.messages as pb


class CustomReceiver(psd.FPSReceiver):
    @psd.receive()
    def custom_message(self, message: pb.RxCustomMessage):
        # If message is defined as 'CustomMessage' in proto file,
        # method should be named 'custom_message'
        self.consumer.send_message(pb.TxResponse(data="Success"))

    @psd.receive(auth=False)  # Disable authentication for this handler
    def login_user(self, message: pb.RxLoginUser):
        # Message type hint pb.RxLoginUser automatically connects 
        # this handler to incoming LoginUser messages
        pass
```

### 2. Async Processing

Async processing is optional and recommended for long-running tasks. Two approaches are available:

#### Using Threading (via `continue_async`):

```python
class CustomReceiver(psd.FPSReceiver):
    @psd.receive()
    def process_data(self, message: pb.RxProcessData):
        # Handler will return immediately, processing continues in background
        return self.continue_async(self.background_processing, message)

    def background_processing(self, message):
        # This runs in a separate thread
        result = expensive_operation()
        self.consumer.send_message(pb.TxProcessingComplete(result=result))
```

#### Using Coroutines:

```python
class CustomReceiver(psd.FPSReceiver):
    @psd.receive()
    def process_async(self, message: pb.RxProcessAsync):
        # Will be executed in the async worker
        return self.continue_async(self.coroutine_processing, message)

    async def coroutine_processing(self, message):
        result = await async_operation()
        self.consumer.send_message(pb.TxProcessingComplete(result=result))
```

### 3. Error Handling

Handlers can return errors that will be sent back to the client:

```python
class CustomReceiver(psd.FPSReceiver):
    @psd.receive()
    def fetch_resource(self, message: pb.RxFetchResource):
        try:
            resource = Resource.objects.get(id=message.proto.id)
        except Resource.DoesNotExist:
            # Client will receive error message and code
            return psd.FPSReceiverError(
                message='Resource not found',
                code=404
            )

        # Success case
        self.consumer.send_message(pb.TxResource(data=resource.data))
```

### 4. Authentication & Permissions

```python
@psd.receive(
    auth=True,  # Require authentication
    permissions=['app.permission'],  # Required permissions
    whitelist_groups=['group1'],  # Allowed groups
    blacklist_groups=['group2']  # Blocked groups
)
```

### 5. Serializers

```python
from proto_socket_django.serializers import ProtoSerializer


class CustomSerializer(pb.CustomProto, ProtoSerializer):
    tx = pb.TxCustomMessage  # Define transmission message type

    def __init__(self, data):
        self.field = process_data(data)
```

## Proto File Configuration

Define messages in .proto files with docstring metadata:

```protobuf
/*
type = 'custom-message'
origin = client/server
auth = true/false
client cache = days(7)  # Only supported in Flutter frontend
*/
message CustomMessage {
  string field = 1;
}
```

### Client Caching

The client cache configuration in proto files is only supported when using the Flutter frontend:

```protobuf
/*
type = 'user-data'
origin = server
client cache = days(7)  # Only works with Flutter clients
client cache_keys = text('username')  # Cache key configuration
*/
message UserData {
  string username = 1;
  string data = 2;
}
```

## Broadcasting

```python
# Send to specific group
ApiWebsocketConsumer.broadcast('group_name', message)

# Add consumer to group
self.consumer.add_group('group_name')

# Remove from group
self.consumer.remove_group('group_name')
```

## Working with Proto Files

### Generate Messages

```bash
python -m proto_socket_django generate
```

Supports:

- Django
- Flutter
- React

### Configuration

Create `fps_config.json`:

```json
{
  "protos": [
    "path/to/proto/files"
  ],
  "include_common": true
}
```

## Important Notes

1. **Handler Auto-Connection**: The library automatically connects message handlers based on their type hints. You don't
   need to manually register handlers.

2. **Naming Convention**: Method names should match the proto message names in snake_case format. For example:
    - Proto message: `CustomMessage` → Method name: `custom_message`
    - Proto message: `FetchUserData` → Method name: `fetch_user_data`

3. **Async Processing**: Use async processing only when needed for long-running operations. Simple handlers can return
   directly.

4. **Client Caching**: The caching configuration in proto files (`client cache = ...`) is only functional when using the
   Flutter frontend. React and other clients will ignore these settings.

## Best Practices

1. **Message Handling**
    - Use async processing for long-running operations
    - Handle errors appropriately using try/except
    - Validate input data

2. **Authentication**
    - Use JWT tokens for authentication
    - Implement proper token refresh handling
    - Set appropriate permissions

3. **Performance**
    - Use appropriate worker configuration
    - Implement caching when needed
    - Handle group subscriptions efficiently

4. **Organization**
    - Group related receivers together
    - Use meaningful message and handler names
    - Follow consistent naming patterns

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.