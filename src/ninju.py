import os
import inspect

import ninja_syntax
from ninja_syntax import as_list

class _NVar(object):
    def __init__(self, name, value, indent=0):
        super(_NVar, self).__init__()
        self.name = name
        self.value = value
        self.indent = indent

    def write(self, writer):
        writer.variable(self.name, self.value, self.indent)

class _NPool(object):
    def __init__(self, name, depth):
        super(_NPool, self).__init__()
        self.name = name
        self.depth = depth

    def write(self, writer):
        writer.pool(self.name, self.depth)

class _NRule(object):
    def __init__(self, name, command, description=None, depfile=None,
             generator=False, pool=None, restat=False, rspfile=None,
             rspfile_content=None, deps=None):
        super(_NRule, self).__init__()
        self.name = name
        self.command = command
        self.description = description
        self.depfile = depfile
        self.generator = generator
        self.pool = pool
        self.restat = restat
        self.rspfile = rspfile
        self.rspfile_content = rspfile_content
        self.deps = deps

    def write(self, writer):
        writer.rule(
            self.name,
            self.command,
            self.description,
            depfile=self.depfile,
            generator=self.generator,
            pool=self.pool,
            restat=self.restat,
            rspfile=self.rspfile,
            rspfile_content=self.rspfile_content,
            deps=self.deps)

    def build_fn(self, ninju):
        _self = self
        def fn(inputs, outputs=None, implicit=None, order_only=None,
                variables=None, implicit_outputs=None):
            outs = _normalize_outputs(outputs, ninju._gen_name, 'build')
            b = _NBuild(
                    outs,
                    _self.name,
                    inputs=inputs,
                    implicit=implicit,
                    order_only=order_only,
                    variables=variables,
                    implicit_outputs=implicit_outputs)
            ninju._seq.append(b)
            return O(outs, ninju)
        return fn

class _NBuild(object):
    def __init__(self, outputs, rule, inputs=None, implicit=None, order_only=None,
            variables=None, implicit_outputs=None):
        self.outputs = outputs
        self.rule = rule
        self.inputs = inputs
        self.implicit = implicit
        self.order_only = order_only
        self.variables = variables
        self.implicit_outputs = implicit_outputs

    def write(self, writer):
        outs = []
        for o in as_list(self.outputs):
            outs.append(str(o))

        ins = []
        for o in as_list(self.inputs):
            ins.append(str(o))

        writer.build(
            outs,
            self.rule,
            inputs=ins,
            implicit=self.implicit,
            order_only=self.order_only,
            variables=self.variables,
            implicit_outputs=self.implicit_outputs)

class O(object):

    def __init__(self, paths, ninju):
        super(O, self).__init__()
        self.paths = paths
        self._n = ninju

    def __getattr__(self, name):
        if name in self._n._commands:
            cmd = self._n._commands[name]
            p = self.paths
            def fn(outputs=None, implicit=None, order_only=None,
                    variables=None, implicit_outputs=None):
                return cmd(p, outputs=outputs, implicit=implicit, order_only=order_only,
                        variables=variables, implicit_outputs=implicit_outputs)
            return fn
        else:
            raise AttributeError

    def __repr__(self):
        return self.paths.__repr__()

    def __str__(self):
        return self.paths.__str__()

    def __bytes__(self):
        return self.paths.__bytes__()

    def __format__(self, format_spec):
        return self.paths.__format__(format_spec)

class Ninju(object):

    """docstring for Ninju."""
    def __init__(self, build_file='build.ninja', build_dir='.builddir'):
        super(Ninju, self).__init__()
        self._build_file = build_file
        self._build_dir = build_dir
        self._seq = []
        self._name_count = 0
        self._commands = {}

        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if os.path.isabs(module.__file__):
            self._root_dir = os.path.dirname(module.__file__)
        else:
            self._root_dir = os.path.dirname(os.path.abspath(module.__file__))

        self.var('root', '.')

    """returns a directory function.
    If var is specified it also create a new variable.
    """
    def dir(self, *args, var=None):
        if len(args) == 0:
            p = '${root}'
        else:
            p = os.path.join('${root}', *args)

        if var:
            v = self.var(var, p)
            p = v

        _self = self
        def dirfn(*args):
            return O(os.path.join(p, *args), _self)
        return dirfn

    def root(self):
        return self.dir()

    def var(self, key, value):
        v = _NVar(key, value)
        self._seq.append(v)
        return "${" + key + "}"

    def cmd(self, name, command, description=None, depfile=None,
             generator=False, pool=None, restat=False, rspfile=None,
             rspfile_content=None, deps=None):
        v = _NRule(
                    name,
                    command,
                    description=description,
                    depfile=depfile,
                    generator=generator,
                    pool=pool,
                    restat=restat,
                    rspfile=rspfile,
                    rspfile_content=rspfile_content,
                    deps=deps)
        self._seq.append(v)
        self._commands[name] = v.build_fn(self)

    def execute(self):
        pass

    def _gen_name(self, suffix):
        self._name_count += 1
        return 'ninju_{suffix}_{index}'.format(suffix=suffix, index=self._name_count)

    def generate(self, newline=True):
        output = open(os.path.join(self._root_dir, self._build_file), 'w')
        w = self._generate(output, newline)
        w.close()

    def _generate(self, output, newline=True):
        writer = ninja_syntax.Writer(output)
        for task in self._seq:
            task.write(writer)
            if newline:
                writer.newline()
        return writer

def _normalize_outputs(outputs, gen_name, suffix):
    if not outputs:
        return [gen_name(suffix)]
    elif isinstance(outputs, int):
        outs = []
        for i in range(outputs):
            outs.append(gen_name(suffix))
        return outs
    else:
        return as_list(outputs)
