import inspect
import os
import sys
import unittest
import warnings
from io import StringIO
from helper import generate_ninja, Header

sourcedir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(sourcedir, '../src'))

from ninju import Ninju, NinjuWarning

MODULE_FILE = os.path.abspath(__file__)

expected = [
    # 0
    Header(MODULE_FILE) + """
rule cmd1
  command = bin1 ${in} ${out}
rule cmd2
  command = bin2 ${in} ${out}
rule cmd3
  command = bin3 ${in} ${out}
build ${builddir}/.ninju_1.tmp: cmd1 ${root}/src/a.txt | bin1
build ${builddir}/.ninju_2.tmp: cmd2 ${builddir}/.ninju_1.tmp | bin2
build ${builddir}/b.txt: cmd3 ${builddir}/.ninju_2.tmp | bin3
""",

    # 1
    Header(MODULE_FILE) + """
rule cmd1
  command = bin1 ${in} ${out}
rule cmd2
  command = bin2 ${in} ${out}
rule cmd3
  command = bin3 ${in} ${out}
build ${builddir}/.ninju_1.tmp: cmd1 ${root}/src/a.txt | bin1
build ${builddir}/.ninju_2.tmp: cmd2 ${root}/src/b.txt | bin2
build ${builddir}/.ninju_3.tmp: cmd3 ${builddir}/.ninju_1.tmp $
    ${builddir}/.ninju_2.tmp | bin3
""",

    # 2
    Header(MODULE_FILE) + """
rule cmd1
  command = bin1 ${in} ${out}
rule cmd2
  command = bin2 ${in} ${out}
build ${builddir}/.ninju_1.tmp ${builddir}/.ninju_2.tmp: cmd1 $
    ${root}/src/a.txt | bin1
build ${builddir}/.ninju_3.tmp: cmd2 ${builddir}/.ninju_1.tmp $
    ${builddir}/.ninju_2.tmp | bin2
"""
]


class TestUseCases(unittest.TestCase):

    def test_pipeline(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=NinjuWarning)
            n = Ninju(no_cwd_check=True)
            src = n.dir('src')
            n.cmd('cmd1', 'bin1', '${in} ${out}')
            n.cmd('cmd2', 'bin2', '${in} ${out}')
            n.cmd('cmd3', 'bin3', '${in} ${out}')

            input = src('a.txt')
            output = n.builddir('b.txt')
            input.cmd1().cmd2().cmd3(output)

            result = generate_ninja(n, newline=False)
            self.assertEqual(result, expected[0])

    def test_inputs_from_multiple_commands(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=NinjuWarning)
            n = Ninju(no_cwd_check=True)
            src = n.dir('src')
            n.cmd('cmd1', 'bin1', '${in} ${out}')
            n.cmd('cmd2', 'bin2', '${in} ${out}')
            n.cmd('cmd3', 'bin3', '${in} ${out}')

            a = src('a.txt')
            b = src('b.txt')
            c = a.cmd1()
            d = b.cmd2()
            e = n.files(c, d).cmd3()

            result = generate_ninja(n, newline=False)
            self.assertEqual(result, expected[1])

    def test_multiple_outputs(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=NinjuWarning)
            n = Ninju(no_cwd_check=True)
            src = n.dir('src')
            n.cmd('cmd1', 'bin1', '${in} ${out}')
            n.cmd('cmd2', 'bin2', '${in} ${out}')

            a = src('a.txt')
            b = a.cmd1(outputs=2)
            c = b.cmd2()

            result = generate_ninja(n, newline=False)
            self.assertEqual(result, expected[2])
