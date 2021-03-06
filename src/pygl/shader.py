#FIXME: stop using POINTER(GLchar) except for buffer construction?
#FIXME: possible if c_str(POINTER((GLchar * size)())) is valid from ctypes import c_char_p as c_str
from ctypes import POINTER
from ctypes import addressof
from ctypes import create_string_buffer
from ctypes import cast
from ctypes import c_char_p as c_str

from pygl.gltypes import GLenum
from pygl.gltypes import GLint, GLuint
from pygl.gltypes import GLchar
from pygl.gltypes import GLsizei
from pygl.gltypes import NULL
import pygl

from pygl.constants import VERTEX_SHADER, FRAGMENT_SHADER

from pygl._gl import Functionality

from pygl.util import _split_enum_name, _cap_name
from pygl.util import _lookup_enum

from pygl.glerror import _check_errors

from pygl.shader_functions import *

def _get_info_log(getter):
    def _wrapped_get_info_log(self):
        log_length = self.info_log_length
        log = create_string_buffer('', log_length)
        getter(self._object,
               GLuint(log_length),
               cast(NULL, POINTER(GLuint)),
               c_str(addressof(log))
              )
        return log.value
    return _wrapped_get_info_log

def _info_log_property(getter):
    return property(_get_info_log(getter))

class ObjectProperty(object):
    _convert = lambda x: x
    def __get__(self, program, owner):
        value = GLint(0)
        self._get(program._object,
                     self._property,
                     value
                 )
        return self._convert(value.value)
    def __set__(self, program, value): pass

def _add_properties(object, getter, properties):
    for type, properties in properties.iteritems():
        for property in properties:
            name = _split_enum_name(property)
            caps = _cap_name(name)

            from pygl import constants #FIXME: move to top like normal?

            class Property(ObjectProperty):
                _get = getter
                _property = getattr(constants, property)
                _convert = type

            setattr(object, '_'.join(map(str.lower, name)), Property())

_shader_properties = {
                      GLenum: ['SHADER_TYPE'],
                      bool: ['DELETE_STATUS', 'COMPILE_STATUS'],
                      int: ['INFO_LOG_LENGTH', 'SHADER_SOURCE_LENGTH']
                      }

def _object_properties(getter, properties):
    def _wrapped_add_properties(cls):
        _add_properties(cls, getter, properties)
        return cls
    return _wrapped_add_properties

@_object_properties(GetShaderiv, _shader_properties)
class Shader(object):
    log = _info_log_property(GetShaderInfoLog)
    def __init__(self):
        self._object = CreateShader(self._shader_type)
        #_add_properties(self, GetShaderiv, _shader_properties)

    def _stringify(self, source):
        stringified = str(source)
        if source == stringified:
            #FIXME: is this really an ok test for string-likeness?
            return source
        else:
            return ''.join([line for line in source])

    def compile(self):
        CompileShader(self._object)
        _check_errors()
        return self.compile_status

    @property
    def sources(self): pass
        #TODO: GetSources()

    @sources.setter
    def sources(self, sources):
        #FIXME: looking at that for a second time, that is UGLY
        c_str_array = (c_str * len(sources))(*[
                                                c_str(''.join(source)) if hasattr(source, 'read')
                                                    else c_str(source)
                                                        for source in sources
                                              ])
        ShaderSource(self._object,
                     len(sources),
                     c_str_array,
                     cast(NULL, POINTER(GLuint))
                    )
        _check_errors()

class VertexShader(Shader):
    _shader_type = VERTEX_SHADER

class FragmentShader(Shader):
    _shader_type = FRAGMENT_SHADER

class AttachedShaders(object):
    def __init__(self, program):
        self._program = program
        self._shaders = []

    def append(self, shader):
        self._shaders.append(shader)

        AttachShader(self._program._object, shader._object)
        _check_errors()

    def extend(self, shaders):
        self._shaders.extend(shaders)
        for shader in shaders:
            AttachShader(self._program._object, shader._object)

    def remove(self, shader):
        DetachShader(self._program._object,
                     shader._object)
        _check_errors()

    def __iter__(self): return iter(self._shaders)

class ProgramVariable(object):
    def __init__(self, name, type, size, location):
        self._name = name
        self._type = type
        self._size = size
        self._location = location

class Attribute(ProgramVariable):
    def __call__(self, *args): pass

class Sampler(ProgramVariable):
    def set(self, value):
        try:
            Uniform1i(self._location, value._unit)
        except AttributeError:
            Uniform1i(self._location, GLuint(value))

# Generate the names of sampler uniform constants
_sampler_types = (getattr(pygl.constants, '_'.join(['SAMPLER', suffix])).value for suffix in (
                                                    '1D', '2D', '3D',
                                                    'CUBE', '1D_SHADOW', '2D_SHADOW')
                                                    )

#FIXME: what represents the "preferred" vector? 1x3 or 3x1?
#FIXME: or does opengl switch between column and row vectors
#FIXME: as needed?
_numeric_variable_types = {
                   float: [(1, 1), (1, 2), (1, 3), (1, 4),
                           (2, 2), (3, 3), (4, 4),
                           (2, 3), (2, 4), # nonsquare
                           (3, 2), (3, 4), # nonsquare
                           (4, 2), (4, 3)],# nonsquare
                   int:   [(1, 1), (1, 2), (1, 3), (1, 4)],
                   bool:  [(1, 1), (1, 2), (1, 3), (1, 4)]
                   }

_type_names = {float: "FLOAT",
          int:   "INT",
          bool:  "BOOL"}

_variable_types = {}
for type, sizes in _numeric_variable_types.iteritems():
    for size in sizes:
        if size[0] == size[1] == 1:
            constant_name = _type_names[type]
        elif size[0] == 1:
            constant_name = "%(name)s_VEC%(size)d" % {
                                                      'name': _type_names[type],
                                                      'size': size[1]
                                                     }
        else:
            constant_name = "%(name)s_MAT%(size)s" % {
                                                      'name': _type_names[type],
                                                      'size': str(size[1]) if size[0] == size[1] else '%dx%d' % size
                                                     }

        # lookup constant value
        constant = getattr(pygl.constants, constant_name).value

        print "%s: %d" % (constant_name, constant)

        #   _variable_types[constant] = ProgramVariable(type, size)

# fill in shader types
for type in _sampler_types:
    _variable_types[type] = Sampler

class ProgramVariables(object):
    def __init__(self, program):
        self._program = program
        self._get_all()

    def _get_info(self, index):
        namelen = GLsizei(0)
        attrib_size = GLint(0)
        type = GLenum(0)

        name = create_string_buffer('', self._max_name_length())
        
        self._get_variable(self._program._object,
                        GLuint(index),
                        GLsizei(self._max_name_length()),
                        namelen,
                        attrib_size,
                        type,
                        name
                       )

        return name.value, type, attrib_size.value

    def _dump(self):
        for name, info in self._variable_info.iteritems():
            print "%s:" % name
            print "\ttype: %d (%s)" % (info[0].value, _lookup_enum(info[0])[0])
            print "\tsize: %d" % info[1]
            print "\tlocation: %d" % info[2]

    def _get_all(self):
        self._variable_info = {}
        for index in xrange(0, self._get_variable_count()):
            name, type, size = self._get_info(index)
            self._variable_info[name] = (type, size,
                                         self._get_location(self._program._object, c_str(name))) #TODO: c_str necessary?

            self._variables = [None] * len(self._variable_info)

        for name, (type, size, location) in self._variable_info.iteritems():
            try:
                self._variables[location] = _variable_types[type.value](name, type, size, location)
            except KeyError: pass #FIXME: only samplers implemented! Shouldn't need this guard!

    def __getitem__(self, name): pass #TODO: getuniform/getattrib

        #TODO: how to handle setting?!?
        #TODO: check for _n _m and _data?
        #TODO: seems a bit magical, but would make everything easier to use

    def __setitem__(self, name, value):
        location = self._variable_info[name][2]
        self._variables[location].set(value)

class ProgramAttributes(ProgramVariables):
    _get_variable = GetActiveAttrib
    _get_location = GetAttribLocation
    def _get_variable_count(self):
        return self._program.active_attributes
    def _max_name_length(self):
        return self._program.active_attribute_max_length

class ProgramUniforms(ProgramVariables):
    _get_variable = GetActiveUniform
    _get_location = GetUniformLocation
    def _get_variable_count(self):
        return self._program.active_uniforms
    def _max_name_length(self):
        return self._program.active_uniform_max_length

_program_properties = {
                      bool: ['DELETE_STATUS', 'LINK_STATUS', 'VALIDATE_STATUS'],
                      int: ['INFO_LOG_LENGTH', 'ATTACHED_SHADERS', 'ACTIVE_ATTRIBUTES', 'ACTIVE_ATTRIBUTE_MAX_LENGTH', 'ACTIVE_UNIFORMS', 'ACTIVE_UNIFORM_MAX_LENGTH']
                      }

@_object_properties(GetProgramiv, _program_properties)
class Program(object):
    log = _info_log_property(GetProgramInfoLog)
    def __init__(self):
        self._object = CreateProgram()
        self._shaders = AttachedShaders(self)

    def link(self):
        LinkProgram(self._object)
        _check_errors()

        self._attribs = ProgramAttributes(self)
        self._uniforms = ProgramUniforms(self)
        return self.link_status

    def validate(self):
        ValidateProgram(self._object)
        return self.validate_status

    def use(self):
        UseProgram(self._object)
        _check_errors()

    @property
    def attribs(self): return self._attribs

    @property
    def uniforms(self): return self._uniforms

    @property
    def shaders(self):
        return self._shaders

class FixedFunction(object):
    def use(self): UseProgram(0)

fixed_function = FixedFunction()
