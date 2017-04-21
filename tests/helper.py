from io import StringIO

def generate_ninja(ninju, newline=True):
  o = StringIO()
  w = ninju._generate(o, newline)
  result = o.getvalue()
  w.close()
  return result
