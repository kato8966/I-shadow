from typing import Any, Callable

import numpy as np


class CallbackFlags:
    pass


class DeviceList:
    pass


AudioCallback = Callable[[bytes, int, Any, CallbackFlags], None]


def query_devices(
    device: int | str | None = ...,
    kind: str | None = ...
) -> dict[str, Any] | DeviceList:
    ...


class RawInputStream:
    def __init__(
        self,
        samplerate: float | None = ...,
        blocksize: int | None = ...,
        device: int | str | None = ...,
        channels: int | None = ...,
        dtype: str | np.dtype | None = ...,
        latency: float | str | None = ...,
        extra_settings: Any = ...,
        callback: AudioCallback | None = ...,
        finished_callback: Callable[[], None] | None = ...,
        clip_off: bool | None = ...,
        dither_off: bool | None = ...,
        never_drop_input: bool | None = ...,
        prime_output_buffers_using_stream_callback: bool | None = ...
    ) -> None:
        self.stopped: bool
        ...

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...
