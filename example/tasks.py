import os
import sys

sourcedir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(sourcedir, '../src'))

from ninju import Ninju

n = Ninju()

# all directories are relative to $ROOT
tmp = n.dir('tmp')
data_panitia_PTN1 = n.dir('data', 'DataPendaftaran')
data_panitia_PTN2 = n.dir('data', 'DataPendaftaranPTN2')

n.cmd('convert_data_panitia',
      '${scriptdir}/convert-data-panitia.sh ${in} ${out} ${dlm}',
      description='Convert CSV from Panitia ${in}'
      )

n.cmd('union_data',
      '${scriptdir}/union-data.sh ${in} ${out}',
      description='Combine data ${in}'
      )

x = n.exec_cmd('mycmd', 'cmd ${in}')
x('xxx')

arr = [
    ('Data_Sekolah.csv', 'csv_sekolah.csv'),
    ('Data_Siswa.csv', 'csv_siswa.csv'),
    ('Data_Pilihan.csv', 'csv_pilihan.csv'),
    ('Data_Jurusan.csv', 'csv_jurusan.csv'),
    ('Ref_Jurusan.csv', 'csv_ref_jurusan.csv'),
]

unions = []
for v in arr:
    a = data_panitia_PTN1(v[0]).convert_data_panitia()
    b = data_panitia_PTN2(v[0]).convert_data_panitia()
    c = n.files(a, b).union_data(tmp(v[1]))
    unions.append(c)

n.generate()
