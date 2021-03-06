from hazelcast.future import ImmediateFuture, Future
from hazelcast.protocol.codec import ringbuffer_add_all_codec, ringbuffer_add_codec, ringbuffer_capacity_codec, \
    ringbuffer_head_sequence_codec, ringbuffer_read_many_codec, ringbuffer_read_one_codec, \
    ringbuffer_remaining_capacity_codec, ringbuffer_size_codec, ringbuffer_tail_sequence_codec
from hazelcast.proxy.base import PartitionSpecificProxy
from hazelcast.util import check_not_negative, check_not_none, check_not_empty, check_true, ImmutableLazyDataList

OVERFLOW_POLICY_OVERWRITE = 0
"""
Configuration property for DEFAULT overflow policy. When an item is tried to be added on full Ringbuffer, oldest item in
the Ringbuffer is overwritten and item is added.
"""

OVERFLOW_POLICY_FAIL = 1
"""
Configuration property for overflow policy. When an item is tried to be added on full Ringbuffer, the call fails and
item is not added.

The reason that FAIL exist is to give the opportunity to obey the ttl. If blocking behavior is required, this can be
implemented using retrying in combination with an exponential backoff.

    >>> sleepMS = 100;
    >>> while true:
    >>>     result = ringbuffer.add(item, -1)
    >>>     if result != -1:
    >>>         break
    >>>     sleep(sleepMS / 1000)
    >>>     sleepMS *= 2
"""
MAX_BATCH_SIZE = 1000
"""
The maximum number of items to be added to RingBuffer or read from RingBuffer at a time.
"""


class Ringbuffer(PartitionSpecificProxy):
    """A Ringbuffer is a data-structure where the content is stored in a ring like structure. 
    
    A Ringbuffer has a capacity so it won't grow beyond that capacity and endanger the stability of the system. 
    If that capacity is exceeded, than the oldest item in the Ringbuffer is overwritten. 
    The Ringbuffer has 2 always incrementing sequences:

    - Tail_sequence: This is the side where the youngest item is found. So the tail is the side of the Ringbuffer
      where items are added to.
    - Head_sequence: This is the side where the oldest items are found. So the head is the side where items gets
      discarded.
            
    The items in the Ringbuffer can be found by a sequence that is in between (inclusive) the head and tail sequence.
    
    A Ringbuffer currently is not a distributed data-structure. So all data is stored in a single partition; comparable
    to the IQueue implementation. But we'll provide an option to partition the data in the near future. A Ringbuffer
    can be used in a similar way as a queue, but one of the key differences is that a queue.take is destructive,
    meaning that only 1 thread is able to take an item. A Ringbuffer.read is not destructive, so you can have multiple
    threads reading the same item multiple times.
    """
    def __init__(self, service_name, name, context):
        super(Ringbuffer, self).__init__(service_name, name, context)
        self._capacity = None

    def capacity(self):
        """Returns the capacity of this Ringbuffer.
        
        Returns:
            hazelcast.future.Future[int]: The capacity of Ringbuffer.
        """
        if not self._capacity:
            def handler(message):
                self._capacity = ringbuffer_capacity_codec.decode_response(message)
                return self._capacity

            request = ringbuffer_capacity_codec.encode_request(self.name)
            return self._invoke(request, handler)
        return ImmediateFuture(self._capacity)

    def size(self):
        """Returns number of items in the Ringbuffer.
        
        Returns:
            hazelcast.future.Future[int]: The size of Ringbuffer.
        """
        request = ringbuffer_size_codec.encode_request(self.name)
        return self._invoke(request, ringbuffer_size_codec.decode_response)

    def tail_sequence(self):
        """Returns the sequence of the tail. 
        
        The tail is the side of the Ringbuffer where the items are added to. The initial value of the tail is -1.

        Returns:
            hazelcast.future.Future[int]: The sequence of the tail.
        """
        request = ringbuffer_tail_sequence_codec.encode_request(self.name)
        return self._invoke(request, ringbuffer_tail_sequence_codec.decode_response)

    def head_sequence(self):
        """Returns the sequence of the head. 
        
        The head is the side of the Ringbuffer where the oldest items in the Ringbuffer are found. 
        If the Ringbuffer is empty, the head will be one more than the tail. The initial value of
        the head is 0 (1 more than tail).
        
        Returns:
            hazelcast.future.Future[int]: The sequence of the head.
        """
        request = ringbuffer_head_sequence_codec.encode_request(self.name)
        return self._invoke(request, ringbuffer_head_sequence_codec.decode_response)

    def remaining_capacity(self):
        """Returns the remaining capacity of the Ringbuffer.
        
        Returns:
            hazelcast.future.Future[int]: The remaining capacity of Ringbuffer.
        """
        request = ringbuffer_remaining_capacity_codec.encode_request(self.name)
        return self._invoke(request, ringbuffer_remaining_capacity_codec.decode_response)

    def add(self, item, overflow_policy=OVERFLOW_POLICY_OVERWRITE):
        """Adds the specified item to the tail of the Ringbuffer. 
        
        If there is no space in the Ringbuffer, the action is determined by overflow policy 
        as ``OVERFLOW_POLICY_OVERWRITE`` or ``OVERFLOW_POLICY_FAIL``.

        Args:
            item: The specified item to be added.
            overflow_policy (int): the OverflowPolicy to be used when there is no space.

        Returns:
            hazelcast.future.Future[int]: The sequenceId of the added item, or ``-1`` if the add failed.
        """
        item_data = self._to_data(item)
        request = ringbuffer_add_codec.encode_request(self.name, overflow_policy, item_data)
        return self._invoke(request, ringbuffer_add_codec.decode_response)

    def add_all(self, items, overflow_policy=OVERFLOW_POLICY_OVERWRITE):
        """Adds all of the item in the specified collection to the tail of the Ringbuffer. 
        
        An add_all is likely to outperform multiple calls to add(object) due to better io utilization 
        and a reduced number of executed operations. The items are added in the order of the Iterator of the collection.
        
        If there is no space in the Ringbuffer, the action is determined by overflow policy 
        as ``OVERFLOW_POLICY_OVERWRITE`` or ``OVERFLOW_POLICY_FAIL``.

        Args:
            items (list): The specified collection which contains the items to be added.
            overflow_policy (int): The OverflowPolicy to be used when there is no space.

        Returns:
            hazelcast.future.Future[int]: The sequenceId of the last written item, or ``-1`` 
                of the last write is failed.
        """
        check_not_empty(items, "items can't be empty")
        if len(items) > MAX_BATCH_SIZE:
            raise AssertionError("Batch size can't be greater than %d" % MAX_BATCH_SIZE)

        item_data_list = []
        for item in items:
            check_not_none(item, "item can't be None")
            item_data_list.append(self._to_data(item))

        request = ringbuffer_add_all_codec.encode_request(self.name, item_data_list, overflow_policy)
        return self._invoke(request, ringbuffer_add_all_codec.decode_response)

    def read_one(self, sequence):
        """Reads one item from the Ringbuffer. 
        
        If the sequence is one beyond the current tail, this call blocks until an item is added. 
        Currently it isn't possible to control how long this call is going to block.

        Args:
            sequence (int): The sequence of the item to read.

        Returns:
            The read item.
        """
        check_not_negative(sequence, "sequence can't be smaller than 0")

        def handler(message):
            return self._to_object(ringbuffer_read_one_codec.decode_response(message))

        request = ringbuffer_read_one_codec.encode_request(self.name, sequence)
        return self._invoke(request, handler)

    def read_many(self, start_sequence, min_count, max_count):
        """Reads a batch of items from the Ringbuffer. 
        
        If the number of available items after the first read item is smaller than the max_count, 
        these items are returned. So it could be the number of items read is smaller than the max_count. 
        If there are less items available than min_count, then this call blocks. Reading a batch of items
        is likely to perform better because less overhead is involved.

        Args:
            start_sequence (int): The start_sequence of the first item to read.
            min_count (int): The minimum number of items to read.
            max_count (int): The maximum number of items to read.

        Returns:
            hazelcast.future.Future[list]: The list of read items.
        """
        check_not_negative(start_sequence, "sequence can't be smaller than 0")
        check_true(max_count >= min_count, "max count should be greater or equal to min count")
        check_true(max_count < MAX_BATCH_SIZE, "max count can't be greater than %d" % MAX_BATCH_SIZE)

        future = Future()
        request = ringbuffer_read_many_codec.encode_request(self.name, start_sequence, min_count, max_count, None)

        def handler(message):
            return ImmutableLazyDataList(ringbuffer_read_many_codec.decode_response(message)["items"], self._to_object)

        def check_capacity(capacity):
            try:
                capacity = capacity.result()
                check_true(min_count <= capacity, "min count: %d should be smaller or equal to capacity: %d"
                           % (min_count, capacity))
                f = self._invoke(request, handler)
                f.add_done_callback(set_result)
            except Exception as e:
                future.set_exception(e)

        def set_result(f):
            try:
                future.set_result(f.result())
            except Exception as e:
                future.set_exception(e)

        self.capacity().add_done_callback(check_capacity)
        return future
