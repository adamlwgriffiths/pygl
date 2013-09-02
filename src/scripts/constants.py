from sys import stdin
import re

def print_constant(constant, value):
    print "%s = GLenum(0x%.4X)" % (constant, value)

def read_header(file):
    constant = re.compile('#define\s+(GL_[A-Z0-9_x]+)\s+(0x[0-9A-Fa-f]+|[0-9]+L?)')

    constants = {}
    for line in file:
        m = constant.search(line)
        if m:
            name, value = m.groups([1, 2])
            constants[name] = value

    return constants

def parse_values(constants):
    transformed_constants = {}

    for name, value in constants.iteritems():
        transformed_constants[name] = eval(value)
    return transformed_constants

def select(constants, selection):
    transformed_constants = {}

    selected = re.compile('^(GL_)?(%s)(_[A-Z]+)?$' % '|'.join(selection)) # results in some false positives
                                                                       # can remedy with list of vendor names
    for name, value in constants.iteritems():
        if selected.match(name):
            transformed_constants[name] = value

    return transformed_constants

def remove_prefix(constants):
    transformed_constants = {}

    prefix = re.compile('^GL_(.*)$')

    for name, value in constants.iteritems():
        m = prefix.match(name)

        if m:
            name = m.group(1)

        # avoid GL_3D etc causing invalid variables starting with numbers
        try:
            int(name[0])
            name = '_' + name
        except:
            pass

        transformed_constants[name] = value

    return transformed_constants

def remove_duplicates(constants, cull_list):
    suffix_regex = re.compile("^([A-Za-z0-9_]+)_(%s)$" % '|'.join(cull_list))

    def compare_suffixes(a, b):
        try:
            a = cull_list.index(a)
        except ValueError:
            return -1

        try:
            b = cull_list.index(b)
        except ValueError:
            return 1

        return b - a

    values = {}
    for constant, value in constants.iteritems():
        try:
            values[value].append(constant)
        except KeyError:
            values[value] = [constant]

    transformed_constants = {}
    for value, constants in values.iteritems():
        duplicates = {}
        for constant in constants:
            m = suffix_regex.match(constant)
            if not m:
                root = constant
                suffix = None
            else:
                root, suffix = m.groups([1, 2])
            
            try:
                duplicates[root].append((constant, suffix))
            except KeyError:
                duplicates[root] = [(constant, suffix)]
        
        for root, suffixes in duplicates.iteritems():
            suffixes.sort(cmp=compare_suffixes, key=lambda x: x[1]) 

            transformed_constants[suffixes[0][0]] = value

    return transformed_constants



def main():
    import argparse
    parser = argparse.ArgumentParser(description='Manages the constants.py file.')
    parser.add_argument('--header',
        help='the gl header to parse'
    )
    parser.add_argument('-c', '--cull', dest='cull', action='append',
        default=['APPLE', 'SGIX', 'ATI', 'NV', 'EXT', 'ARB'],
        help="Define a preference for constant suffixes, from least preferred to most."
    )
    parser.add_argument('--clear-cull', dest='cull', action='store_const', const=list(),
        help="There is a predefined list of suffixes to cull, this clears them."
    )
    parser.add_argument('-s', '--select', dest='select', action='append',
        default=[],
        help="Select which constants you want to retrieve"
    )

    args = vars(parser.parse_args())

    if args['header']:
        header = args['header']
    else:
        from sys import platform
        if 'darwin' in platform:
            header = '/System/Library/Frameworks/OpenGL.framework/Versions/A/Headers/gl.h'
        elif 'linux' in platform:
            header = '/usr/include/GL/glext.h'
        elif 'win32' in platform:
            raise ValueError('Win32 not supported')
        else:
            raise ValueError('Unknown platform')

    with open(header) as f:
        constants = read_header(f)

    if len(args['select']):
        constants = select(constants, args['select'])
    constants = remove_prefix(constants) # remove GL_ from constant names
    constants = parse_values(constants)  # transform strings into integers for constant values
    constants = remove_duplicates(constants, args['cull'])

    print "from gltypes import GLenum"
    print
    keys = constants.keys()
    keys.sort()
    for constant in keys:
        value = constants[constant]
        print_constant(constant, value)



if __name__ == '__main__':
    main()
