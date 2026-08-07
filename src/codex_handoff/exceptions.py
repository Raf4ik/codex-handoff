class HandoffError(Exception):
    """Expected user-facing failure."""


class BaselineExistsError(HandoffError):
    pass


class StaleDeviceError(HandoffError):
    pass


class DeviceNotInitializedError(HandoffError):
    pass


class VersionNotFoundError(HandoffError):
    pass


class IntegrityError(HandoffError):
    pass


class CodexRunningError(HandoffError):
    pass


class ConfigurationError(HandoffError):
    pass


class ConcurrentUpdateError(HandoffError):
    pass
