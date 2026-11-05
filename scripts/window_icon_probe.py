"""Read actual Win32 window icon bitmap sizes; never changes another window."""
import ctypes
from ctypes import wintypes
import struct
from pathlib import Path


def probe(output=None, title_prefix='MdPersia'):
    user = ctypes.WinDLL('user32', use_last_error=True)
    gdi = ctypes.WinDLL('gdi32', use_last_error=True)
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback, wintypes.LPARAM]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user.SendMessageW.restype = ctypes.c_ssize_t
    class_icon = user.GetClassLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user.GetClassLongW
    class_icon.argtypes = [wintypes.HWND, ctypes.c_int]
    class_icon.restype = ctypes.c_size_t
    user.GetIconInfo.argtypes = [wintypes.HICON, ctypes.c_void_p]
    gdi.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    user.GetDC.argtypes = [wintypes.HWND]
    user.GetDC.restype = wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    class IconInfo(ctypes.Structure):
        _fields_ = [('icon', wintypes.BOOL), ('x', wintypes.DWORD), ('y', wintypes.DWORD),
                    ('mask', wintypes.HBITMAP), ('color', wintypes.HBITMAP)]
    class Bitmap(ctypes.Structure):
        _fields_ = [('kind', wintypes.LONG), ('width', wintypes.LONG), ('height', wintypes.LONG),
                    ('stride', wintypes.LONG), ('planes', wintypes.WORD), ('bits', wintypes.WORD), ('data', ctypes.c_void_p)]
    result = []
    @callback
    def visit(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        user.GetWindowTextW(hwnd, title, len(title))
        if not title.value.startswith(title_prefix):
            return True
        record = {'title': title.value, 'hwnd': hwnd}
        for name, slot in [('large', 1), ('small', 0), ('small2', 2)]:
            icon = user.SendMessageW(hwnd, 0x7F, slot, 0)
            source = 'WM_GETICON'
            if not icon:
                # A window may inherit its class icon instead of setting WM_SETICON.
                icon = class_icon(hwnd, -14 if name == 'large' else -34)
                source = 'class'
            info = IconInfo()
            if icon and user.GetIconInfo(icon, ctypes.byref(info)):
                bitmap = Bitmap()
                if gdi.GetObjectW(info.color, ctypes.sizeof(bitmap), ctypes.byref(bitmap)):
                    record[name] = [bitmap.width, bitmap.height]
                    record[name + 'Source'] = source
                    if output:
                        from PIL import Image
                        width, height = bitmap.width, bitmap.height
                        header = ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, width*height*4, 0, 0, 0, 0))
                        pixels = ctypes.create_string_buffer(width*height*4)
                        dc = user.GetDC(None)
                        if gdi.GetDIBits(dc, info.color, 0, height, pixels, header, 0):
                            image = Image.frombytes('RGBA', (width,height), pixels.raw, 'raw', 'BGRA')
                            target = Path(output)
                            target.mkdir(parents=True, exist_ok=True)
                            image.save(target / f'window-{name}.png')
                        user.ReleaseDC(None, dc)
                if info.mask:
                    gdi.DeleteObject(info.mask)
                if info.color:
                    gdi.DeleteObject(info.color)
        result.append(record)
        return True
    user.EnumWindows(visit, 0)
    return result
