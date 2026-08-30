from __future__ import annotations

import ctypes
import os
import shutil
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ResourceProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cpu_count: int
    ram_bytes: int
    disk_free_bytes: int
    docker_available: bool
    nvidia_smi_available: bool
    actual_cash_cost_vnd: int = 0


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


def _windows_ram_bytes() -> int:
    status = _MemoryStatusEx()
    status.length = ctypes.sizeof(status)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    global_memory_status = kernel32.GlobalMemoryStatusEx
    global_memory_status.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
    global_memory_status.restype = ctypes.c_int
    if not global_memory_status(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(status.total_physical)


def _ram_bytes() -> int:
    if sys.platform == "win32":
        return _windows_ram_bytes()

    sysconf = getattr(os, "sysconf", None)
    if sysconf is None:
        raise OSError("physical RAM detection is unsupported on this platform")
    ram_bytes = int(sysconf("SC_PAGE_SIZE")) * int(sysconf("SC_PHYS_PAGES"))
    if ram_bytes <= 0:
        raise OSError("physical RAM detection returned a non-positive capacity")
    return ram_bytes


def collect_resource_profile(workspace: Path) -> ResourceProfile:
    return ResourceProfile(
        cpu_count=os.cpu_count() or 1,
        ram_bytes=_ram_bytes(),
        disk_free_bytes=shutil.disk_usage(workspace).free,
        docker_available=shutil.which("docker") is not None,
        nvidia_smi_available=shutil.which("nvidia-smi") is not None,
    )
