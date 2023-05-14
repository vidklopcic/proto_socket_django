rx_message_class = '''export class Rx{proto} extends SocketRxMessage<{package}.{proto}> {{
    static type: string = '{type}';
    proto = {package}.{proto}.create({{}});
    protoClass = {package}.{proto};
    {fields}

    constructor(message: SocketRxMessageData | null = null) {{
        super(Rx{proto}.type, message);
        if (message !== null) {{
            this.proto = this.protoClass.fromObject(message.body);
        }}
    }}

    fromMessage(message: SocketRxMessageData) {{
        return new Rx{proto}(message);
    }};
}}
'''

tx_message_class = '''export class Tx{proto} extends SocketTxMessage<{package}.{proto}> {{
    static type: string = '{type}';
    proto: {package}.{proto};
    protoClass = {package}.{proto};
    {fields}

    constructor(proto: {package}.{proto}) {{
        super(Tx{proto}.type, true);
        this.proto = proto;
    }}

    static create(properties: {package}.I{proto} = {{}}) {{
        return new Tx{proto}({package}.{proto}.create(properties));
    }}
}}
'''