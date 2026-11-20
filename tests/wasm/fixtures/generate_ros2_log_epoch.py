#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Deterministic ROS2 rosout fixture, six rows at nonzero Unix-epoch times.
Run with mcap==1.3.1; generated data is synthetic and repository-licensed.
"""
import base64
import hashlib
import io
from pathlib import Path
from importlib.metadata import version
from mcap.reader import make_reader
from mcap.writer import Writer, CompressionType, IndexType
from scene3d_data_fixture_support import CdrWriter, timestamp

SCHEMA = b'''builtin_interfaces/Time stamp
uint8 level
string name
string msg
string file
string function
uint32 line
================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec
'''
EPOCH_NS = 1_700_000_000_000_000_000


def build():
    stream = io.BytesIO()
    writer = Writer(stream, compression=CompressionType.NONE, index_types=IndexType.NONE,
                    use_chunking=False, enable_crcs=True)
    writer.start(profile='ros2', library='pj-log-epoch-fixture/1')
    schema = writer.register_schema(name='rcl_interfaces/msg/Log', encoding='ros2msg', data=SCHEMA)
    channel = writer.register_channel(topic='/rosout', message_encoding='cdr', schema_id=schema)
    for index in range(6):
        stamp = EPOCH_NS + index * 1_000_000_000
        cdr = CdrWriter()
        timestamp(cdr, stamp)
        cdr.data.append(20)
        for value in ('fixture-node', f'epoch-log-{index}', 'fixture.cpp', 'emit'):
            cdr.string(value)
        cdr.uint32(index + 1)
        writer.add_message(channel, stamp, bytes(cdr.data), publish_time=stamp, sequence=index)
    writer.finish()
    data = stream.getvalue()
    messages = list(make_reader(io.BytesIO(data), validate_crcs=True).iter_messages())
    assert len(messages) == 6
    assert [m.log_time for _, _, m in messages] == [EPOCH_NS + i * 1_000_000_000 for i in range(6)]
    assert all(schema.name == 'rcl_interfaces/msg/Log' and channel.topic == '/rosout'
               for schema, channel, _ in messages)
    return data


if __name__ == '__main__':
    assert version('mcap') == '1.3.1'
    payload = build()
    Path(__file__).with_name('ros2_log_epoch.mcap.b64').write_text(base64.b64encode(payload).decode() + '\n')
    print(len(payload), hashlib.sha256(payload).hexdigest())
