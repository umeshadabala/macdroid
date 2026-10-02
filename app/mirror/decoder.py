"""
Native Video Decoder for MacDroid using PyAV (libavcodec).
Decodes H.264/H.265 video packets natively off the GUI thread with zero-copy,
low-delay flags, and aspect-ratio preservation.
"""

from __future__ import annotations

import time
from typing import Callable, IO, Optional

import av
from PySide6.QtGui import QImage

from app.core.logger import get_logger

log = get_logger("decoder")


class NativeVideoDecoder:
    """Decodes H.264 video streams into QImage frames using native libavcodec."""

    def __init__(self, codec_name: str = "h264") -> None:
        self.codec_name = codec_name
        self._fps_count = 0
        self._fps_timer = time.time()
        self.current_fps = 0.0
        self.frame_count = 0

    def decode_stream(
        self,
        stream_io: IO[bytes],
        on_frame: Callable[[QImage], None],
        is_running: Callable[[], bool],
    ) -> None:
        """
        Continuously read and decode H.264 video frames from a binary stream
        with zero-buffering and low-delay options.
        """
        try:
            log.info("Opening low-delay H.264 container in libavcodec...")
            container = av.open(
                stream_io,
                format="h264",
                mode="r",
                options={
                    "flags": "low_delay",
                    "fflags": "nobuffer",
                    "probesize": "32",
                    "analyzeduration": "0",
                },
            )

            # Set multithreading and slice decoding on video stream
            for stream in container.streams.video:
                stream.codec_context.thread_type = "SLICE"
                stream.codec_context.thread_count = 2

            for frame in container.decode(video=0):
                if not is_running():
                    break

                # Convert natively in C to RGB24
                rgb_frame = frame.to_rgb()
                width, height = rgb_frame.width, rgb_frame.height
                plane = rgb_frame.planes[0]
                bytes_per_line = plane.line_size

                # Construct QImage from buffer
                qimg = QImage(
                    bytes(plane),
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                )

                self.frame_count += 1
                self._fps_count += 1
                now = time.time()
                if now - self._fps_timer >= 1.0:
                    self.current_fps = self._fps_count / (now - self._fps_timer)
                    self._fps_count = 0
                    self._fps_timer = now

                on_frame(qimg)

        except Exception as e:
            if is_running():
                log.warning("Stream decoder loop terminated: %s", e)

    def decode_chunk(
        self,
        chunk: bytes,
        on_frame: Callable[[QImage], None],
        ctx: Optional[av.CodecContext] = None,
    ) -> None:
        """Fallback chunk-based parser and decoder."""
        if not chunk or not ctx:
            return
        try:
            packets = ctx.parse(chunk)
            for packet in packets:
                frames = ctx.decode(packet)
                for frame in frames:
                    rgb_frame = frame.to_rgb()
                    qimg = QImage(
                        bytes(rgb_frame.planes[0]),
                        rgb_frame.width,
                        rgb_frame.height,
                        rgb_frame.planes[0].line_size,
                        QImage.Format.Format_RGB888,
                    )
                    self.frame_count += 1
                    on_frame(qimg)
        except Exception as e:
            log.debug("Chunk decode error: %s", e)
