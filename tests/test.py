import inspect
import os
import sys
import unittest
from io import StringIO

sourcedir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(sourcedir, '../src'))

from ninju import Ninju, O

def _generate(ninju, newline=True):
  o = StringIO()
  w = ninju._generate(o, newline)
  result = o.getvalue()
  w.close()
  return result

expected = [
# 0
"""root = .
myvar = myvalue
""",

# 1
"""root = .
rule echo
  command = /usr/bin/echo
  description = echo test
""",

# 2
"""root = .
dst = ${root}/dst/dir1
rule copy
  command = /usr/bin/cp ${in} ${out}
  description = copy file
build ${root}/tmp/file2.txt: copy ${root}/file1.txt
build ${dst}/file4.txt: copy ${root}/file3.txt
""",

# 3
"""root = .
rule copy
  command = /usr/bin/cp ${in} ${out}
  description = copy file
build ${root}/tmp/file2.txt: copy ${root}/file1.txt
build ${root}/file3.txt: copy ${root}/tmp/file2.txt
"""
]
class TestStringMethods(unittest.TestCase):

  def test_var(self):
      n = Ninju()
      n.var('myvar', 'myvalue')
      result = _generate(n, newline=False)
      self.assertEqual(result, expected[0])

  def test_cmd(self):
      n = Ninju()
      n.cmd('echo', '/usr/bin/echo', description='echo test')
      result = _generate(n, newline=False)
      self.assertEqual(result, expected[1])

  def test_dir(self):
      n = Ninju()
      root = n.root()
      tmp = n.dir('tmp')
      dst = n.dir('dst', 'dir1', var='dst')
      n.cmd('copy', '/usr/bin/cp ${in} ${out}', description='copy file')
      root('file1.txt').copy(tmp('file2.txt'))
      root('file3.txt').copy(dst('file4.txt'))
      result = _generate(n, newline=False)
      self.assertEqual(result, expected[2])

  def test_build(self):
      n = Ninju()
      root = n.dir()
      src = n.dir('src')
      tmp = n.dir('tmp')
      n.cmd('copy', '/usr/bin/cp ${in} ${out}', description='copy file')
      a = root('file1.txt').copy(tmp('file2.txt'))
      a.copy(os.path.join('${root}', 'file3.txt'))
      result = _generate(n, newline=False)
      self.assertEqual(result, expected[3])

if __name__ == '__main__':
  unittest.main()
