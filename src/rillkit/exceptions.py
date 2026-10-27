"""Exceptions raised by rillkit, and control-flow exceptions handlers can raise."""


class RillkitError(Exception):
    """Base class for all rillkit errors."""


class PublishError(RillkitError):
    """The message could not be written to the stream."""


class DecodeError(RillkitError):
    """The body could not be decoded or validated. Never retried, goes straight to the DLQ."""


class AckMessage(RillkitError):
    """Raise from a handler to stop processing and acknowledge the message."""


class RejectMessage(RillkitError):
    """Raise from a handler to stop processing and send the message to the DLQ without retrying.

    The text of the exception is stored as the DLQ ``x-error``.
    """


class NackMessage(RillkitError):
    """Raise from a handler to stop processing and nack the message so it is retried."""
