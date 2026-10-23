"""Passwortprüfung über PAM (libpam per ctypes, ohne Fremdpakete).

Für den eigenen Nutzer funktioniert das ohne Root: pam_unix ruft dafür unix_chkpwd auf.
"""

import ctypes
import ctypes.util
import pwd
import os
from ctypes import CFUNCTYPE, POINTER, Structure, c_char, c_char_p, c_int, c_size_t, c_void_p, cast, sizeof

PAM_SUCCESS = 0
PAM_PROMPT_ECHO_OFF = 1
PAM_PROMPT_ECHO_ON = 2

DEFAULT_SERVICE = "login"


class _PamHandle(Structure):
    _fields_ = [("handle", c_void_p)]


class _PamMessage(Structure):
    _fields_ = [("msg_style", c_int), ("msg", c_char_p)]


class _PamResponse(Structure):
    _fields_ = [("resp", c_char_p), ("resp_retcode", c_int)]


_CONV_FUNC = CFUNCTYPE(c_int, c_int, POINTER(POINTER(_PamMessage)), POINTER(POINTER(_PamResponse)), c_void_p)


class _PamConv(Structure):
    _fields_ = [("conv", _CONV_FUNC), ("appdata_ptr", c_void_p)]


class PamUnavailable(RuntimeError):
    pass


def _load():
    try:
        libpam = ctypes.CDLL(ctypes.util.find_library("pam") or "libpam.so.0")
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
    except OSError as exc:
        raise PamUnavailable(f"libpam nicht gefunden: {exc}") from exc

    libpam.pam_start.argtypes = [c_char_p, c_char_p, POINTER(_PamConv), POINTER(_PamHandle)]
    libpam.pam_start.restype = c_int
    libpam.pam_authenticate.argtypes = [_PamHandle, c_int]
    libpam.pam_authenticate.restype = c_int
    libpam.pam_end.argtypes = [_PamHandle, c_int]
    libpam.pam_end.restype = c_int
    libc.calloc.argtypes = [c_size_t, c_size_t]
    libc.calloc.restype = c_void_p
    # POINTER(c_char), nicht c_char_p: der Speicher gehört danach PAM und wird dort freigegeben
    libc.strdup.argtypes = [c_char_p]
    libc.strdup.restype = POINTER(c_char)
    return libpam, libc


def current_user() -> str:
    return pwd.getpwuid(os.getuid()).pw_name


def authenticate(password: str, user: str | None = None, service: str = DEFAULT_SERVICE) -> bool:
    """True, wenn das Passwort des Nutzers stimmt."""
    libpam, libc = _load()
    user = user or current_user()
    secret = password.encode("utf-8")

    @_CONV_FUNC
    def conversation(n_messages, messages, response, _appdata):
        address = libc.calloc(n_messages, sizeof(_PamResponse))
        if not address:
            return 1
        response[0] = cast(address, POINTER(_PamResponse))
        for i in range(n_messages):
            style = messages[i].contents.msg_style
            if style == PAM_PROMPT_ECHO_OFF:
                answer = secret
            elif style == PAM_PROMPT_ECHO_ON:
                answer = user.encode("utf-8")
            else:
                continue
            response.contents[i].resp = cast(libc.strdup(answer), c_char_p)
            response.contents[i].resp_retcode = 0
        return PAM_SUCCESS

    handle = _PamHandle()
    conv = _PamConv(conversation, 0)
    status = libpam.pam_start(service.encode(), user.encode("utf-8"), ctypes.byref(conv), ctypes.byref(handle))
    if status != PAM_SUCCESS:
        raise PamUnavailable(f"pam_start fehlgeschlagen ({status})")
    try:
        status = libpam.pam_authenticate(handle, 0)
        return status == PAM_SUCCESS
    finally:
        libpam.pam_end(handle, status)
