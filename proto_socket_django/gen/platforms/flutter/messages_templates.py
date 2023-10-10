cache_keys_table_class = '''
class {prefix}{proto}Table {{
  final {prefix}{proto} message;
  {fields}

  {prefix}{proto}Table(this.message, table) : {initializers};
}}
'''

cache_keys_class = '''
class {prefix}{proto}CacheKeys extends CacheKeys {{
  {fields}

  const {prefix}{proto}CacheKeys() : super(textKeys: const [{text_keys}], realKeys: const [{real_keys}], dateKeys: const [{date_keys}]);
}}'''

rx_message_class = '''class Rx{proto} extends SocketRxMessage{table_type} {{
  static const String type = '{type}';
  final {proto} data = {proto}();
  {fields}

  Rx{proto}([SocketRxMessageData? message]) : super(type, message);

  @override
  Rx{proto} fromMessage(SocketRxMessageData message) => Rx{proto}(message);{table}
}}
'''

tx_message_class = '''class Tx{proto} extends SocketTxMessage {{
  static const String type = '{type}';
  final {proto} proto;
  {fields}

  const Tx{proto}(this.proto) : super(type, authRequired: {auth});

  static {proto} get newProto => {proto}();

  static Tx{proto} create([{proto} Function({proto} data)? setData]) => Tx{proto}((setData ?? (p) => p)(Tx{proto}.newProto));
}}
'''
