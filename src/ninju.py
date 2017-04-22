import inspect
import os
import shutil
import sys
import warnings
from string import Template

import ninja_syntax
from ninja_syntax import as_list

NINJU_VERSION = '0.1.0'
NINJU_URL = 'https://github.com/frm-adiputra/Ninju'
NINJA_REQUIRED_VERSION = '1.7'

NINJU_MODULE_PATH = os.path.abspath(__file__)
NINJA_SYNTAX_MODULE_PATH = os.path.abspath(ninja_syntax.__file__)


class NinjuWarning(Warning):
    pass


class ExecutionError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ConfigurationError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class GeneratorError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


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


class _NBuildRule(object):
    def __init__(self, name, executable, args=None, description=None, depfile=None,
                 generator=False, pool=None, restat=False, rspfile=None,
                 rspfile_content=None, deps=None):
        super(_NBuildRule, self).__init__()
        self.name = name
        self.executable = executable
        self.args = args
        self.description = description
        self.depfile = depfile
        self.generator = generator
        self.pool = pool
        self.restat = restat
        self.rspfile = rspfile
        self.rspfile_content = rspfile_content
        self.deps = deps

    def write(self, writer):
        if self.args != None:
            command = ' '.join([self.executable, self.args])
        else:
            command = self.executable

        writer.rule(
            self.name,
            command,
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
            outs = _normalize_outputs(outputs, ninju._gen_name)
            b = _NBuild(
                outs,
                _self.name,
                inputs=inputs,
                implicit=ninju.files(_self.executable, implicit),
                order_only=order_only,
                variables=variables,
                implicit_outputs=implicit_outputs)
            ninju._seq.append(b)
            return ninju.files(*outs)
        return fn


class _NExecRule(object):
    def __init__(self, name, executable, args=None, description=None,
                 rspfile=None, rspfile_content=None):
        super(_NExecRule, self).__init__()
        self.name = name
        self.executable = executable
        self.args = args
        self.description = description
        self.rspfile = rspfile
        self.rspfile_content = rspfile_content

    def write(self, writer):
        if self.args != None:
            command = ' '.join([self.executable, self.args])
        else:
            command = self.executable

        writer.rule(
            self.name,
            command,
            self.description,
            pool='console',
            rspfile=self.rspfile,
            rspfile_content=self.rspfile_content)

    def exec_fn(self, ninju):
        _self = self

        def fn(target, inputs=None, variables=None):
            if not _is_single_item(target):
                raise ConfigurationError('exec_cmd can only have one target')
            outs = _normalize_outputs(target, ninju._gen_name)
            b = _NBuild(
                outs,
                _self.name,
                inputs=inputs,
                variables=variables)
            ninju._seq.append(b)
            return _Files(ninju, target)
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
        if not self.outputs:
            raise GeneratorError('no output')

        for o in self.outputs:
            outs.append(str(o))

        writer.build(
            outs,
            self.rule,
            inputs=_as_string_list(self.inputs),
            implicit=_as_string_list(self.implicit),
            order_only=_as_string_list(self.order_only),
            variables=self.variables,
            implicit_outputs=_as_string_list(self.implicit_outputs))


class _NPhony(object):
    def __init__(self, name, inputs):
        super(_NPhony, self).__init__()
        self.name = name
        self.inputs = inputs

    def write(self, writer):
        ins = []
        for o in self.inputs:
            ins.append(str(o))

        writer.build(self.name, 'phony', inputs=ins)


class _NDefault(object):
    def __init__(self, targets):
        super(_NDefault, self).__init__()
        self.targets = targets

    def write(self, writer):
        targs = []
        for o in self.targets:
            targs.append(str(o))

        writer.default(targs)


class _Target(object):
    def __init__(self, ninju, target):
        super(_Target, self).__init__()
        self._n = ninju
        self.target = target

    def __getattr__(self, name):
        if name in self._n._exec_cmds:
            cmd = self._n._exec_cmds[name]
            t = self.target

            def fn(inputs=None, variables=None):
                return cmd(t, inputs=inputs, variables=variables)
            return fn
        else:
            raise AttributeError

    def phony(self, inputs):
        self._n._seq.append(_NPhony(self.target, self._n.files(inputs)))

    def __repr__(self):
        return self.target.__repr__()

    def __str__(self):
        return self.target.__str__()

    def __bytes__(self):
        return self.target.__bytes__()

    def __format__(self, format_spec):
        return self.target.__format__(format_spec)


class _Files(object):
    def __init__(self, ninju, *files):
        super(_Files, self).__init__()
        self._n = ninju
        self.files = _flatten(files)

    def __getattr__(self, name):
        if name in self._n._cmds:
            cmd = self._n._cmds[name]
            p = self.files

            def fn(outputs=None, implicit=None, order_only=None,
                    variables=None, implicit_outputs=None):
                return cmd(p, outputs=outputs, implicit=implicit, order_only=order_only,
                           variables=variables, implicit_outputs=implicit_outputs)
            return fn
        else:
            raise AttributeError

    def __repr__(self):
        return self.files.__repr__()

    def __str__(self):
        return self.files.__str__()

    def __bytes__(self):
        return self.files.__bytes__()

    def __format__(self, format_spec):
        return self.files.__format__(format_spec)

    def __iter__(self):
        return self.files.__iter__()

    def __next__(self):
        return self.files.__next__()


class Ninju(object):
    """
    cwd_check is used only in test to bypass CWD check.
    """

    def __init__(self, build_file='build.ninja', build_dir='.builddir', generators=[], no_cwd_check=False):
        super(Ninju, self).__init__()
        self._build_file = build_file
        self._build_dir = build_dir
        self._seq = []
        self._name_count = 0
        self._cmds = {}
        self._exec_cmds = {}
        self._pools = {}
        self._vars = {}

        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        self._file = os.path.abspath(module.__file__)
        self._root_dir = os.path.dirname(self._file)

        if not no_cwd_check and self._root_dir != os.getcwd():
            print('Cannot run from outside directory "{}"'.format(self._root_dir))
            exit(1)

        self.var('ninja_required_version', NINJA_REQUIRED_VERSION)
        self.var('root', '.')
        self.var('builddir', os.path.join('${root}', self._build_dir))
        self.cmd('configure', self._file,
                 description='Regenerate ninja build file',
                 generator=True)

        gens = [
            NINJU_MODULE_PATH,
            NINJA_SYNTAX_MODULE_PATH]
        for g in generators:
            gens.append(g.__file__)

        self.files().configure(self.root(self._build_file),
                               implicit=gens)

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
            return _Files(_self, os.path.join(p, *args))
        return dirfn

    def root(self, *args):
        return _Files(self, os.path.join('${root}', *args))

    def builddir(self, *args):
        return _Files(self, os.path.join('${builddir}', *args))

    def var(self, key, value):
        v = _NVar(key, value)
        self._seq.append(v)
        expval = Template(value).substitute(self._vars)
        self._vars[key] = expval
        return "${" + key + "}"

    def cmd(self, name, executable, args=None, description=None, depfile=None,
            generator=False, pool=None, restat=False, rspfile=None,
            rspfile_content=None, deps=None):
        r = self._find_exe(executable)
        exe = r[1]
        if not r[0]:
            warnings.warn('executable not found: {}'.format(exe),
                          NinjuWarning, stacklevel=2)

        pool_name = self._setup_pool(pool)
        v = _NBuildRule(
            name,
            exe,
            args=args,
            description=description,
            depfile=depfile,
            generator=generator,
            pool=pool_name,
            restat=restat,
            rspfile=rspfile,
            rspfile_content=rspfile_content,
            deps=deps)
        self._seq.append(v)
        self._cmds[name] = v.build_fn(self)

    def exec_cmd(self, name, executable, args=None, description=None,
                 rspfile=None, rspfile_content=None):
        r = self._find_exe(executable)
        exe = r[1]
        if not r[0]:
            warnings.warn('executable not found: {}'.format(exe),
                          NinjuWarning, stacklevel=2)

        v = _NExecRule(
            name,
            exe,
            args=args,
            description=description,
            rspfile=rspfile,
            rspfile_content=rspfile_content)
        self._seq.append(v)
        self._exec_cmds[name] = v.exec_fn(self)

    def _gen_name(self, ext='tmp'):
        self._name_count += 1
        return '${builddir}' + ('/.ninju_{index}.{ext}'.format(ext=ext, index=self._name_count))

    def generate(self, newline=True):
        output = open(os.path.join(self._root_dir, self._build_file), 'w')
        w = self._generate(output, newline)
        w.close()

    def files(self, *args):
        return _Files(self, *args)

    def target(self, target):
        return _Target(self, target)

    def default(self, *targets):
        v = _NDefault(self.files(*targets))
        self._seq.append(v)

    def _find_exe(self, path):
        ff = self.files(path)
        if len(ff.files) != 1:
            raise ConfigurationError('Only one executable required')

        fpath = ff.files[0]
        fp = Template(str(fpath)).substitute(self._vars)
        if os.path.isfile(fp) and os.access(fp, os.X_OK):
            return (True, fpath)
        try:
            p = shutil.which(fp)
            if p == None:
                return (False, fpath)
            return (True, p)
        except Exception:
            return (False, fpath)

    def _setup_pool(self, pool):
        if pool == None:
            return None

        if isinstance(pool, int):
            if pool < 1:
                raise ConfigurationError(
                    'pool must be an integer greater than 1 or \'console\'')
            pool_name = 'pool_{}'.format(pool)
            if not (pool_name in self._pools):
                self._seq.append(_NPool(pool_name, pool))
                self._pools[pool_name] = True
            return pool_name

        if pool == 'console':
            return pool

        raise ConfigurationError(
            'pool must be an integer greater than 1 or \'console\'')

    def _generate(self, output, newline=True):
        writer = ninja_syntax.Writer(output)
        writer.comment('This file is generated by Ninju v{} ({})'.format(
            NINJU_VERSION, NINJU_URL))
        writer.newline()

        for task in self._seq:
            task.write(writer)
            if newline:
                writer.newline()
        return writer


def _normalize_outputs(outputs, gen_name, ext='tmp'):
    if not outputs:
        return [gen_name(ext)]
    elif isinstance(outputs, int):
        outs = []
        for i in range(outputs):
            outs.append(gen_name(ext))
        return outs
    elif type(outputs) == _Files:
        return outputs.files
    elif isinstance(outputs, list):
        return outputs
    else:
        return as_list(outputs)


def _is_single_item(t):
    return not ((type(t) == _Files and len(t.files) != 1)
                or ((isinstance(t, list) or isinstance(t, tuple)) and len(t) != 1))


def _as_string_list(t):
    if t == None:
        return None
    l = []
    for o in t:
        l.append(str(o))
    return l


def _flatten(l):
    if l == None:
        return []

    if not (isinstance(l, list) or isinstance(l, tuple) or type(l) == _Files):
        return [l]

    if type(l) == _Files:
        l0 = l.files
    else:
        l0 = l

    return _flatten_list(l0)


def _flatten_list(l):
    result = []
    for v in l:
        if not (isinstance(v, list) or isinstance(v, tuple) or type(v) == _Files):
            if v != None:
                result.append(v)
            continue

        if type(v) == _Files:
            l0 = v.files
        else:
            l0 = v
        result.extend(_flatten_list(l0))
    return result
