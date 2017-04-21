import inspect
import os
import sys
import unittest
from io import StringIO
from helper import generate_ninja, HEADER

sourcedir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(sourcedir, '../src'))

from ninju import Ninju, ConfigurationError

expected = [
    # 0
    HEADER + """
myvar = myvalue
""",

    # 1
    HEADER + """
rule echo
  command = /usr/bin/echo
  description = echo test
""",

    # 2
    HEADER + """
dst = ${root}/dst/dir1
rule copy
  command = /usr/bin/cp ${in} ${out}
  description = copy file
build ${root}/tmp/file2.txt: copy ${root}/file1.txt
build ${dst}/file4.txt: copy ${root}/file3.txt
""",

    # 3
    HEADER + """
rule copy
  command = /usr/bin/cp ${in} ${out}
  description = copy file
build ${root}/tmp/file2.txt: copy ${root}/file1.txt
build ${root}/file3.txt: copy ${root}/tmp/file2.txt
""",

    # 4
    HEADER + """
rule cmd1
  command = bin1 ${in} ${out}
build ${root}/file2.txt: cmd1 ${root}/file1.txt
build ${builddir}/.ninju_1.tmp ${builddir}/.ninju_2.tmp: cmd1 $
    ${root}/file3.txt
build one: phony ${root}/file2.txt
build all: phony ${root}/file2.txt ${builddir}/.ninju_1.tmp $
    ${builddir}/.ninju_2.tmp
""",

    # 5
    HEADER + """
rule cmd1
  command = bin1 ${in} ${out}
  pool = console
build target: cmd1
""",

    # 6
    HEADER + """
rule cmd1
  command = bin1 ${in} ${out}
build ${root}/file2.txt: cmd1 ${root}/file1.txt
build ${builddir}/.ninju_1.tmp ${builddir}/.ninju_2.tmp: cmd1 $
    ${root}/file3.txt
build one: phony ${root}/file2.txt
build all: phony ${root}/file2.txt ${builddir}/.ninju_1.tmp $
    ${builddir}/.ninju_2.tmp
default one
default all ${root}/file2.txt ${builddir}/.ninju_1.tmp $
    ${builddir}/.ninju_2.tmp
""",

    # 7
    HEADER + """
pool pool_1
  depth = 1
rule cmd1
  command = bin1
  pool = pool_1
pool pool_3
  depth = 3
rule cmd2
  command = bin2
  pool = pool_3
rule cmd3
  command = bin3
  pool = console
"""
]


class TestCore(unittest.TestCase):

    def test_var(self):
        n = Ninju()
        n.var('myvar', 'myvalue')
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[0])

    def test_cmd(self):
        n = Ninju()
        n.cmd('echo', '/usr/bin/echo', description='echo test')
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[1])

    def test_dir(self):
        n = Ninju()
        root = n.root
        tmp = n.dir('tmp')
        dst = n.dir('dst', 'dir1', var='dst')
        n.cmd('copy', '/usr/bin/cp ${in} ${out}', description='copy file')
        root('file1.txt').copy(tmp('file2.txt'))
        root('file3.txt').copy(dst('file4.txt'))
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[2])

    def test_build(self):
        n = Ninju()
        root = n.dir()
        src = n.dir('src')
        tmp = n.dir('tmp')
        n.cmd('copy', '/usr/bin/cp ${in} ${out}', description='copy file')
        a = root('file1.txt').copy(tmp('file2.txt'))
        a.copy(os.path.join('${root}', 'file3.txt'))
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[3])

    def test_phony(self):
        n = Ninju()
        root = n.dir()
        n.cmd('cmd1', 'bin1 ${in} ${out}')
        a = root('file1.txt').cmd1(root('file2.txt'))
        b = root('file3.txt').cmd1(outputs=2)
        n.target('one').phony(a)
        n.target('all').phony(n.files(a, b))
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[4])

    def test_exec_cmd(self):
        n = Ninju()
        root = n.dir()
        n.exec_cmd('cmd1', 'bin1 ${in} ${out}')
        n.target('target').cmd1()
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[5])

    def test_default(self):
        n = Ninju()
        root = n.dir()
        n.cmd('cmd1', 'bin1 ${in} ${out}')
        a = root('file1.txt').cmd1(root('file2.txt'))
        b = root('file3.txt').cmd1(outputs=2)
        n.target('one').phony(a)
        n.target('all').phony(n.files(a, b))
        n.default('one')
        n.default('all', a, b)
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[6])

    def test_pool(self):
        n = Ninju()
        n.cmd('cmd1', 'bin1', pool=1)
        n.cmd('cmd2', 'bin2', pool=3)
        n.cmd('cmd3', 'bin3', pool='console')
        result = generate_ninja(n, newline=False)
        self.assertEqual(result, expected[7])

    def test_pool_exception1(self):
        n = Ninju()
        
        with self.assertRaises(ConfigurationError):
            n.cmd('cmd1', 'bin1', pool=0)

        with self.assertRaises(ConfigurationError):
            n.cmd('cmd1', 'bin1', pool='1')

        with self.assertRaises(ConfigurationError):
            n.cmd('cmd1', 'bin1', pool='pool_1')
