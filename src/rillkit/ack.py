from enum import Enum


class AckPolicy(str, Enum):
    """What happens to a message when its handler finishes.

    NACK_ON_ERROR  Ack when the handler returns, nack when it raises. This is the default.
    ACK_ALWAYS     Ack when the handler returns or raises. Failures are logged and dropped, never
                   retried.
    ACK_FIRST      Ack before the handler runs. At-most-once: a crash loses the message.
    MANUAL         rillkit never acks. The handler must call ``msg.ack()``. If it returns without
                   acking, or raises, the message stays pending and is retried.
    """

    NACK_ON_ERROR = "nack_on_error"
    ACK_ALWAYS = "ack_always"
    ACK_FIRST = "ack_first"
    MANUAL = "manual"
