from pygl.gltypes import GLdouble

from ctypes import CDLL
from ctypes.util import find_library

from sys import platform

if platform == 'win32':
    raise RuntimeError('Windows not supported')
else:
    lib = CDLL(find_library('GLU'))

Perspective = lib.gluPerspective
Perspective.argtypes = [GLdouble] * 4
