"""Request normal close only for visible windows belonging to this exact suite."""
import ctypes
from ctypes import wintypes
from pathlib import Path

APP_PATHS=('WiringWorkbench/WiringWorkbench.exe','OLEDWorkbench/OLEDWorkbench.exe')

def allowed_paths(root):
    return {str((Path(root)/p).resolve()).casefold() for p in APP_PATHS}

def windows(root):
    if not hasattr(ctypes,'WinDLL'):return []
    user=ctypes.WinDLL('user32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes=[wintypes.HWND]
    user.GetWindow.argtypes=[wintypes.HWND,wintypes.UINT];user.GetWindow.restype=wintypes.HWND
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    targets=allowed_paths(root);found=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def visit(hwnd,_):
        if not user.IsWindowVisible(hwnd) or user.GetWindow(hwnd,4):return True
        pid=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        handle=kernel.OpenProcess(0x1000,False,pid.value)
        if not handle:return True
        try:
            size=wintypes.DWORD(32768);buffer=ctypes.create_unicode_buffer(size.value)
            if kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)) and str(Path(buffer.value).resolve()).casefold() in targets:
                found.append({'hwnd':int(hwnd),'pid':pid.value,'path':buffer.value})
        finally:kernel.CloseHandle(handle)
        return True
    callback=callback_type(visit)
    user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user.EnumWindows(callback,0)
    return found

def request_close(root):
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    found=windows(root);sent=0
    for item in found:
        if user.PostMessageW(item['hwnd'],0x0010,0,0):sent+=1  # WM_CLOSE, never TerminateProcess.
    return {'found':len(found),'requested':sent}
