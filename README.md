# Proto Socket Django

A library for seamless communication between Django backends and JavaScript frontends using Protocol Buffers over WebSockets.

## Installation

### Backend
```bash
pip install proto_socket_django
```

### Frontend
```bash
npm install proto_socket_typescript
```

## Commands

### Backend
- Regenerate protobuf messages and models:
  ```bash
  python3 -m proto_socket_django generate
  ```

### Frontend
- Regenerate protobuf messages and models:
  ```bash
  python3 -m proto_socket_django generate
  ```

## Architecture Overview

Proto Socket Django enables bidirectional communication between Django backends and JavaScript frontends:
- WebSockets using Django Channels for transport
- Protocol Buffers for message serialization
- Routing and message delivery handled by `proto_socket_django` (backend) and `proto_socket_typescript` (frontend)

## Implementing a New Message

### Step 1: Define Protocol Buffers

1. Locate a suitable file/package in your proto directory or create a new one:
   - File name (e.g., `admin_elastic.proto`) should match the proto package name
   - All proto files should be in the root directory
   - Annotate messages with special comments to enable transport

Example:
```protobuf
/*
type = 'get-data'
origin = client
 */
message GetData {
  string id = 1;
}

/*
type = 'data'
origin = server
 */
message Data {
  string id = 1;
  repeated string test_field = 2;
  NestedModel nested = 3;
}

message NestedModel {
  string test = 1;
}
```

2. Generate code:
   ```bash
   python3 -m proto_socket_django generate
   ```

3. This will generate:
   - All protobuf definitions (`GetData`, `Data`, `NestedModel`)
   - Backend: `RxGetData`, `TxData` (based on annotations)
   - Frontend: `TxGetData`, `RxData`

### Step 2: Backend Implementation

1. Find or create a receiver class inheriting from `psd.FPSReceiver`
   - If creating a new one, add it to `api.consumers.BaseConsumer.receivers`

2. Create a handler function in the receiver:
```python
import proto_socket_django as psd
import proto.messages as pb

@psd.receive(whitelist_groups=[UserGroups.admin], auth=True)
def admin_load_news_app(self, message: pb.RxAdminLoadNewsApp):
    # Function name should be snake_case version of message
    self.consumer.send_message(AdminNewsAppSerializer().msg())
```

3. Create serializers for outgoing messages:
```python
import proto.messages as pb
from proto_socket_django.serializers import ProtoSerializer

class DataSerializer(pb.Data, ProtoSerializer):
    tx = pb.TxData  # Specifies which message type to send
    
    def __init__(self, model: DataModel):
        # Map model fields to proto fields
        self.test_field = model.test_fields
        self.nested = NestedModelSerializer(model.nested)
        
class NestedModelSerializer(pb.NestedModel, ProtoSerializer):
    def __init__(self, model: NestedModel):
        self.test = model.test
```

4. Send the message:
```python
self.consumer.send_message(DataSerializer(model).msg())
```

5. For long-running tasks:
```python
@psd.receive(whitelist_groups=[UserGroups.admin])
def admin_start_index_job(self, message: pb.RxAdminStartIndexJob):
    indexer = PublicationIndexer(
        user=self.consumer.user,
        publications=Publication.objects.filter(metadata__isnull=False, menu__isnull=False),
    )
    indexer.create_job()

    def _async():
        try:
            indexer.start()
        except Exception as e:
            traceback.print_exc()
            indexer.job.error = str(e)
            indexer.job.finished = timezone.now()
            indexer.job.save()

    return self.continue_async(_async)  # Returns ack only after completion
    
    # Alternatively:
    # self.continue_async(_async).run()  # Returns ack immediately
```

### Step 3: Frontend Implementation

1. Receive messages in Mobx stores:
```typescript
import {proto} from "../../proto/messages";

class YourStore {
    disposer = new DisposeUtils();
    
    constructor() {
        this.disposer.add(
            api.getMessageHandler(
                new proto.RxData()
            ).subscribe((m) => this.onData(m))
        );
    }
    
    dispose() {
        this.disposer.dispose();
    }
    
    private onData(m: proto.RxData) {
        console.log(m.proto.test_field);
        console.log(m.proto.nested.test);
    }
}
```

2. Send messages to backend:
```typescript
// With acknowledgment
const response = await api.sendMessage(
    proto.TxGetData.create({id: 'test'}),
    {ack: true}
);

if (response.status !== SocketApiAckStatus.success) {
    toast.error(response.errorMessage ?? 'Unknown error');
}

// Helper method for request-response pattern
try {
    const response = await api.fetch(
        proto.TxGetData.create({id: 'test'}),
        new RxData()
    );
    console.log('Backend returned:', response.proto.test_field);
} catch (e) {
    ErrorUtils.fromFetch(e);
}
```

## Code Style Guidelines

- Always import protobuf definitions as `import proto.messages as pb`
- Always import the library as `import proto_socket_django as psd`