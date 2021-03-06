from hazelcast.protocol.client_message import OutboundMessage, REQUEST_HEADER_SIZE, create_initial_buffer
from hazelcast.protocol.builtin import StringCodec

# hex: 0x000400
_REQUEST_MESSAGE_TYPE = 1024
# hex: 0x000401
_RESPONSE_MESSAGE_TYPE = 1025

_REQUEST_INITIAL_FRAME_SIZE = REQUEST_HEADER_SIZE


def encode_request(name, service_name):
    buf = create_initial_buffer(_REQUEST_INITIAL_FRAME_SIZE, _REQUEST_MESSAGE_TYPE)
    StringCodec.encode(buf, name)
    StringCodec.encode(buf, service_name, True)
    return OutboundMessage(buf, False)
