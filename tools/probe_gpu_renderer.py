#!/usr/bin/env python3
"""Create a surfaceless EGL/OpenGL context and require the NVIDIA renderer."""

import argparse
import ctypes
import json
import os
import sys
from pathlib import Path
from typing import Any

EGL_DEFAULT_DISPLAY = None
EGL_PLATFORM_SURFACELESS_MESA = 0x31DD
EGL_NONE = 0x3038
EGL_VENDOR = 0x3053
EGL_SURFACE_TYPE = 0x3033
EGL_PBUFFER_BIT = 0x0001
EGL_RENDERABLE_TYPE = 0x3040
EGL_OPENGL_BIT = 0x0008
EGL_RED_SIZE = 0x3024
EGL_GREEN_SIZE = 0x3023
EGL_BLUE_SIZE = 0x3022
EGL_WIDTH = 0x3057
EGL_HEIGHT = 0x3056
EGL_OPENGL_API = 0x30A2
EGL_CONTEXT_MAJOR_VERSION = 0x3098
EGL_NO_DISPLAY = None
EGL_NO_SURFACE = None
EGL_NO_CONTEXT = None
GL_VENDOR = 0x1F00
GL_RENDERER = 0x1F01
GL_VERSION = 0x1F02


def _egl_error(egl: Any, operation: str) -> RuntimeError:
    egl.eglGetError.restype = ctypes.c_uint
    return RuntimeError(f"{operation} failed with EGL error 0x{egl.eglGetError():04x}")


def _extension_function(egl: Any, name: bytes, restype: Any, argtypes: list[Any]) -> Any:
    egl.eglGetProcAddress.restype = ctypes.c_void_p
    address = egl.eglGetProcAddress(name)
    if not address:
        raise RuntimeError(f"EGL extension function {name.decode()} is unavailable")
    return ctypes.CFUNCTYPE(restype, *argtypes)(address)


def query_renderer() -> dict[str, Any]:
    egl = ctypes.CDLL("libEGL.so.1")
    display_fn = _extension_function(
        egl, b"eglGetPlatformDisplayEXT", ctypes.c_void_p,
        [ctypes.c_uint, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)],
    )
    display = display_fn(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, None)
    if not display:
        raise _egl_error(egl, "eglGetPlatformDisplayEXT")

    egl.eglInitialize.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
    egl.eglInitialize.restype = ctypes.c_uint
    major, minor = ctypes.c_int(), ctypes.c_int()
    if not egl.eglInitialize(display, ctypes.byref(major), ctypes.byref(minor)):
        raise _egl_error(egl, "eglInitialize")

    egl.eglBindAPI.argtypes = [ctypes.c_uint]
    egl.eglBindAPI.restype = ctypes.c_uint
    if not egl.eglBindAPI(EGL_OPENGL_API):
        raise _egl_error(egl, "eglBindAPI(OpenGL)")

    attributes = (ctypes.c_int * 11)(
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT,
        EGL_RED_SIZE, 8,
        EGL_GREEN_SIZE, 8,
        EGL_BLUE_SIZE, 8,
        EGL_NONE,
    )
    config = ctypes.c_void_p()
    count = ctypes.c_int()
    egl.eglChooseConfig.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_void_p), ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    egl.eglChooseConfig.restype = ctypes.c_uint
    if not egl.eglChooseConfig(display, attributes, ctypes.byref(config), 1, ctypes.byref(count)) or count.value < 1:
        raise _egl_error(egl, "eglChooseConfig")

    surface_attributes = (ctypes.c_int * 5)(EGL_WIDTH, 1, EGL_HEIGHT, 1, EGL_NONE)
    egl.eglCreatePbufferSurface.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    egl.eglCreatePbufferSurface.restype = ctypes.c_void_p
    surface = egl.eglCreatePbufferSurface(display, config, surface_attributes)
    if not surface:
        raise _egl_error(egl, "eglCreatePbufferSurface")

    # Ask for an OpenGL 3.0 context; driver defaults are used if it lacks KHR_create_context.
    context_attributes = (ctypes.c_int * 3)(EGL_CONTEXT_MAJOR_VERSION, 3, EGL_NONE)
    egl.eglCreateContext.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    egl.eglCreateContext.restype = ctypes.c_void_p
    context = egl.eglCreateContext(display, config, EGL_NO_CONTEXT, context_attributes)
    if not context:
        context_attributes = (ctypes.c_int * 1)(EGL_NONE)
        context = egl.eglCreateContext(display, config, EGL_NO_CONTEXT, context_attributes)
    if not context:
        raise _egl_error(egl, "eglCreateContext")

    egl.eglMakeCurrent.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    egl.eglMakeCurrent.restype = ctypes.c_uint
    if not egl.eglMakeCurrent(display, surface, surface, context):
        raise _egl_error(egl, "eglMakeCurrent")

    gl = ctypes.CDLL("libGL.so.1")
    gl.glGetString.argtypes = [ctypes.c_uint]
    gl.glGetString.restype = ctypes.c_char_p
    strings = {
        "gl_vendor": gl.glGetString(GL_VENDOR),
        "gl_renderer": gl.glGetString(GL_RENDERER),
        "gl_version": gl.glGetString(GL_VERSION),
    }
    for key, value in strings.items():
        if value is None:
            raise RuntimeError(f"glGetString({key}) returned null")
        strings[key] = value.decode("utf-8", errors="replace")

    egl.eglQueryString.argtypes = [ctypes.c_void_p, ctypes.c_int]
    egl.eglQueryString.restype = ctypes.c_char_p
    vendor = egl.eglQueryString(display, EGL_VENDOR)
    egl_vendor = vendor.decode("utf-8", errors="replace") if vendor else None
    return {
        "egl_vendor": egl_vendor,
        "egl_version": f"{major.value}.{minor.value}",
        **strings,
        "egl_platform": "surfaceless",
        "egl_vendor_library_override": os.environ.get("__EGL_VENDOR_LIBRARY_FILENAMES"),
        "nvidia_driver_capabilities": os.environ.get("NVIDIA_DRIVER_CAPABILITIES"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = query_renderer()
        vendor = (report.get("gl_vendor") or "").lower()
        renderer = (report.get("gl_renderer") or "").lower()
        report["nvidia_backend"] = "nvidia" in vendor and "nvidia" in renderer and not any(x in renderer for x in ("llvmpipe", "softpipe", "software rasterizer"))
        if not report["nvidia_backend"]:
            raise RuntimeError(f"OpenGL selected a non-NVIDIA renderer: {report}")
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded)
        sys.stdout.write(encoded)
        return 0
    except Exception as exc:
        print(f"GPU_RENDERER_PREFLIGHT_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
