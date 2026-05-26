import os
import ctypes

path = r"C:\Users\Célia A\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\mediapipe\tasks\python\core\mediapipe_c_bindings.py"

if not os.path.exists(path):
    print("Error: file does not exist!")
    exit(1)

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = '  # Register "free()"\n  _shared_lib.free.argtypes = [ctypes.c_void_p]\n  _shared_lib.free.restype = None'

replacement = """  # Register "free()"
  try:
    _shared_lib.free.argtypes = [ctypes.c_void_p]
    _shared_lib.free.restype = None
  except AttributeError:
    import platform
    if platform.system() == 'Windows':
      _shared_lib.free = ctypes.CDLL('msvcrt').free
    else:
      try:
        _shared_lib.free = ctypes.CDLL(None).free
      except Exception:
        pass"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch applied successfully!")
else:
    if 'try:\n    _shared_lib.free.argtypes = [ctypes.c_void_p]' in content:
        print("Patch was already applied previously!")
    else:
        print("Error: Target content not found!")
