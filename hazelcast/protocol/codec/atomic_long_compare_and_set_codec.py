from hazelcast.serialization.bits import *
from hazelcast.protocol.builtin import FixSizedTypesCodec
from hazelcast.protocol.client_message import OutboundMessage, REQUEST_HEADER_SIZE, create_initial_buffer, RESPONSE_HEADER_SIZE
from hazelcast.protocol.codec.custom.raft_group_id_codec import RaftGroupIdCodec
from hazelcast.protocol.builtin import StringCodec

# hex: 0x090400
_REQUEST_MESSAGE_TYPE = 590848
# hex: 0x090401
_RESPONSE_MESSAGE_TYPE = 590849

_REQUEST_EXPECTED_OFFSET = REQUEST_HEADER_SIZE
_REQUEST_UPDATED_OFFSET = _REQUEST_EXPECTED_OFFSET + LONG_SIZE_IN_BYTES
_REQUEST_INITIAL_FRAME_SIZE = _REQUEST_UPDATED_OFFSET + LONG_SIZE_IN_BYTES
_RESPONSE_RESPONSE_OFFSET = RESPONSE_HEADER_SIZE


def encode_request(group_id, name, expected, updated):
    buf = create_initial_buffer(_REQUEST_INITIAL_FRAME_SIZE, _REQUEST_MESSAGE_TYPE)
    FixSizedTypesCodec.encode_long(buf, _REQUEST_EXPECTED_OFFSET, expected)
    FixSizedTypesCodec.encode_long(buf, _REQUEST_UPDATED_OFFSET, updated)
    RaftGroupIdCodec.encode(buf, group_id)
    StringCodec.encode(buf, name, True)
    return OutboundMessage(buf, False)


def decode_response(msg):
    initial_frame = msg.next_frame()
    return FixSizedTypesCodec.decode_boolean(initial_frame.buf, _RESPONSE_RESPONSE_OFFSET)
