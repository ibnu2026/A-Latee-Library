"""ZKTeco ZKFinger USB fingerprint adapter for Windows."""

from __future__ import annotations

import ctypes
import os
from ctypes import POINTER, byref, c_int, c_uint, c_ubyte, c_void_p
from pathlib import Path
from typing import Optional, Tuple


class ZKTecoFingerprintHandler:
    """Small Python adapter around the ZKFinger native Windows SDK."""

    REGISTER_FINGER_COUNT = 3
    TEMPLATE_BUFFER_SIZE = 2048
    PARAM_IMAGE_WIDTH = 1
    PARAM_IMAGE_HEIGHT = 2
    ERR_OK = 0

    def __init__(self, sdk_path: Optional[str] = None):
        configured_path = sdk_path or os.environ.get("ZKTECO_SDK_PATH")
        self.sdk_path = Path(configured_path) if configured_path else Path(__file__).parent / "vendor" / "zkteco"
        self.library = None
        self.device = c_void_p()
        self.db = c_void_p()
        self.image_buffer = None
        self.image_size = 0
        self.enrollment_templates: list[bytes] = []
        self.used_ids: set[int] = set()
        self.last_error: Optional[str] = None
        self.connected = False

    def _load_library(self):
        candidates = [
            self.sdk_path / "libzkfp.dll",
            self.sdk_path / "x64" / "libzkfp.dll",
            self.sdk_path / "lib" / "x64" / "libzkfp.dll",
            Path(os.environ.get("WINDIR", "C:\\Windows")) / "System32" / "libzkfp.dll",
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "ZKFinger SDK" / "libzkfp.dll",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "ZKFinger SDK" / "libzkfp.dll",
        ]
        for candidate in candidates:
            if candidate.exists():
                return ctypes.WinDLL(str(candidate))
        try:
            return ctypes.WinDLL("libzkfp.dll")
        except OSError as error:
            raise RuntimeError(
                "libzkfp.dll belum ditemukan. Jalankan setup.exe SDK ZKTeco "
                "atau salin DLL native x64 ke vendor\\zkteco."
            ) from error

    def _bind_api(self):
        lib = self.library
        lib.ZKFPM_Init.restype = c_int
        lib.ZKFPM_Terminate.restype = c_int
        lib.ZKFPM_GetDeviceCount.restype = c_int
        lib.ZKFPM_OpenDevice.argtypes = [c_int]
        lib.ZKFPM_OpenDevice.restype = c_void_p
        lib.ZKFPM_CloseDevice.argtypes = [c_void_p]
        lib.ZKFPM_CloseDevice.restype = c_int
        lib.ZKFPM_GetParameters.argtypes = [c_void_p, c_int, POINTER(c_ubyte), POINTER(c_uint)]
        lib.ZKFPM_GetParameters.restype = c_int
        lib.ZKFPM_AcquireFingerprint.argtypes = [c_void_p, POINTER(c_ubyte), c_uint, POINTER(c_ubyte), POINTER(c_uint)]
        lib.ZKFPM_AcquireFingerprint.restype = c_int
        lib.ZKFPM_DBInit.restype = c_void_p
        lib.ZKFPM_DBFree.argtypes = [c_void_p]
        lib.ZKFPM_DBFree.restype = c_int
        lib.ZKFPM_DBAdd.argtypes = [c_void_p, c_uint, POINTER(c_ubyte), c_uint]
        lib.ZKFPM_DBAdd.restype = c_int
        lib.ZKFPM_DBMerge.argtypes = [c_void_p, POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_uint)]
        lib.ZKFPM_DBMerge.restype = c_int
        lib.ZKFPM_DBIdentify.argtypes = [c_void_p, POINTER(c_ubyte), c_uint, POINTER(c_uint), POINTER(c_uint)]
        lib.ZKFPM_DBIdentify.restype = c_int

    def connect(self) -> bool:
        try:
            if os.name != "nt":
                raise RuntimeError("ZKTeco ZKFinger SDK ini hanya mendukung Windows")
            self.library = self._load_library()
            self._bind_api()
            result = self.library.ZKFPM_Init()
            if result != self.ERR_OK:
                raise RuntimeError(f"ZKFPM_Init gagal ({result})")
            if self.library.ZKFPM_GetDeviceCount() <= 0:
                raise RuntimeError("Perangkat ZKTeco tidak ditemukan")
            self.device = self.library.ZKFPM_OpenDevice(0)
            if not self.device:
                raise RuntimeError("Gagal membuka perangkat ZKTeco")
            self.db = self.library.ZKFPM_DBInit()
            if not self.db:
                raise RuntimeError("Gagal membuat database fingerprint SDK")
            self.image_size = self._get_parameter(self.PARAM_IMAGE_WIDTH) * self._get_parameter(self.PARAM_IMAGE_HEIGHT)
            self.image_buffer = (c_ubyte * max(self.image_size, 1))()
            self.connected = True
            return True
        except Exception as error:
            self.last_error = str(error)
            self.disconnect()
            return False

    def _get_parameter(self, code: int) -> int:
        value = (c_ubyte * 4)()
        size = c_uint(4)
        result = self.library.ZKFPM_GetParameters(self.device, code, value, byref(size))
        if result != self.ERR_OK:
            raise RuntimeError(f"Gagal membaca parameter SDK ({code}, {result})")
        return int.from_bytes(bytes(value), "little")

    def disconnect(self):
        try:
            if self.library and self.db:
                self.library.ZKFPM_DBFree(self.db)
            if self.library and self.device:
                self.library.ZKFPM_CloseDevice(self.device)
            if self.library:
                self.library.ZKFPM_Terminate()
        finally:
            self.device = c_void_p()
            self.db = c_void_p()
            self.connected = False

    def is_connected(self) -> bool:
        return self.connected and bool(self.device) and bool(self.db)

    def get_last_error(self) -> Optional[str]:
        return self.last_error

    def load_fingerprints_from_db(self, db_handler) -> int:
        if not self.is_connected():
            return 0
        count = 0
        cursor = db_handler.conn.cursor()
        cursor.execute("SELECT santri_id, template_data FROM santri_fingerprints WHERE status='active'")
        for santri_id, template_data in cursor.fetchall():
            self.used_ids.add(int(santri_id))
            if not isinstance(template_data, bytes):
                template_data = bytes.fromhex(str(template_data))
            template = (c_ubyte * len(template_data)).from_buffer_copy(template_data)
            result = self.library.ZKFPM_DBAdd(self.db, int(santri_id), template, len(template_data))
            if result == self.ERR_OK:
                count += 1
        return count

    def _capture(self) -> Optional[bytes]:
        if not self.is_connected():
            self.last_error = "Perangkat ZKTeco belum terhubung"
            return None
        template = (c_ubyte * self.TEMPLATE_BUFFER_SIZE)()
        template_size = c_uint(self.TEMPLATE_BUFFER_SIZE)
        result = self.library.ZKFPM_AcquireFingerprint(
            self.device, self.image_buffer, self.image_size, template, byref(template_size)
        )
        if result != self.ERR_OK:
            self.last_error = f"Capture fingerprint gagal ({result})"
            return None
        return bytes(template[:template_size.value])

    def start_enrollment(self) -> bool:
        if not self.is_connected():
            self.last_error = "Perangkat ZKTeco belum terhubung"
            return False
        self.enrollment_templates = []
        return True

    def _find_matching_id(self, template: bytes) -> Optional[int]:
        template_buffer = (c_ubyte * len(template)).from_buffer_copy(template)
        fingerprint_id = c_uint(0)
        score = c_uint(0)
        result = self.library.ZKFPM_DBIdentify(
            self.db,
            template_buffer,
            len(template),
            byref(fingerprint_id),
            byref(score),
        )
        if result == self.ERR_OK:
            return int(fingerprint_id.value)
        return None

    def add_enrollment_scan(self) -> Tuple[bool, int]:
        template = self._capture()
        if not template:
            return False, 0
        matching_id = self._find_matching_id(template)
        if matching_id is not None:
            self.last_error = f"Fingerprint sudah terdaftar (ID: {matching_id})"
            return False, 0
        self.enrollment_templates.append(template)
        return True, len(self.enrollment_templates)

    def save_enrollment(self, owner_name: str = "Unknown") -> Optional[Tuple[int, bytes]]:
        del owner_name
        if len(self.enrollment_templates) != self.REGISTER_FINGER_COUNT:
            self.last_error = "Enrollment membutuhkan 3 scan fingerprint"
            return None
        buffers = [
            (c_ubyte * len(template)).from_buffer_copy(template)
            for template in self.enrollment_templates
        ]
        merged = (c_ubyte * self.TEMPLATE_BUFFER_SIZE)()
        merged_size = c_uint(self.TEMPLATE_BUFFER_SIZE)
        result = self.library.ZKFPM_DBMerge(
            self.db, buffers[0], buffers[1], buffers[2], merged, byref(merged_size)
        )
        if result != self.ERR_OK:
            self.last_error = f"Penggabungan fingerprint gagal ({result})"
            return None
        matching_id = self._find_matching_id(bytes(merged[:merged_size.value]))
        if matching_id is not None:
            self.last_error = f"Fingerprint sudah terdaftar (ID: {matching_id})"
            return None
        fingerprint_id = self._next_id()
        result = self.library.ZKFPM_DBAdd(self.db, fingerprint_id, merged, merged_size.value)
        if result != self.ERR_OK:
            self.last_error = f"Penyimpanan fingerprint SDK gagal ({result})"
            return None
        self.enrollment_templates = []
        return fingerprint_id, bytes(merged[:merged_size.value])

    def _next_id(self) -> int:
        fingerprint_id = max(self.used_ids, default=0) + 1
        self.used_ids.add(fingerprint_id)
        return fingerprint_id

    def cancel_enrollment(self):
        self.enrollment_templates = []

    def scan_fingerprint(self, verbose: bool = False) -> Optional[int]:
        del verbose
        template = self._capture()
        if not template:
            return None
        template_buffer = (c_ubyte * len(template)).from_buffer_copy(template)
        fingerprint_id = c_uint(0)
        score = c_uint(0)
        result = self.library.ZKFPM_DBIdentify(
            self.db, template_buffer, len(template), byref(fingerprint_id), byref(score)
        )
        if result != self.ERR_OK:
            self.last_error = f"Fingerprint tidak dikenali ({result})"
            return None
        return int(fingerprint_id.value)
