# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This is a wrapper for the Cinema 4D source processor that generate a
dependency file for the files that have been parsed to produce the
generated files.
"""

import argparse
import os
import nr.fs
import subprocess as sp
import shutil
import sys

escape = lambda x: x.replace(' ', '\\ ')

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('sourceprocessor', help='Path to the sourceprocessor.py')
  parser.add_argument('directory', help='The directory to process.')
  parser.add_argument('--write-temp-projectdefinition', action='store_true')
  parser.add_argument('--module-id')
  parser.add_argument('--type')
  parser.add_argument('argv', nargs='...')
  args = parser.parse_args()

  projectdefs = os.path.join(args.directory, 'project', 'projectdefinition.txt')
  remove_project_dir = False
  if args.write_temp_projectdefinition and not os.path.isfile(projectdefs):
    print('Creating temporary projectdefinitions.txt...')
    remove_project_dir = not os.path.isdir(os.path.dirname(projectdefs))
    nr.fs.makedirs(os.path.dirname(projectdefs))
    with open(projectdefs, 'w') as fp:
      if args.type:
        print('Type={}'.format(args.type), file=fp)
      if args.module_id:
        print('ModuleId={}'.format(args.module_id), file=fp)
      print('stylecheck=false'.format(args.type), file=fp)

  try:
    proc = sp.Popen([sys.executable, args.sourceprocessor, args.directory] + args.argv, stdout=sp.PIPE, stderr=sp.STDOUT)
    files = []
    for line in proc.stdout:
      line = line.decode()
      print(line, end='')
      line = line.strip()
      if line.startswith('Parsing') and line.endswith('...'):
        files.append(line[7:-3].strip())
    proc.communicate()
  finally:
    if args.write_temp_projectdefinition:
      if remove_project_dir:
        shutil.rmtree(os.path.dirname(projectdefs))
      else:
        os.remove(projectdefs)

  registercpp = os.path.join(args.directory, 'generated', 'hxx', 'register.cpp')
  if not os.path.isfile(registercpp):
    return

  depfile = os.path.join(args.directory, 'generated', 'hxx', 'register.cpp.d')
  cachefile = os.path.join(args.directory, 'generated', 'craftr-depscache.txt')

  # Parse in the previous file list. The source processor only outputs the
  # files that it parses because they are new or changed, not the unchaged
  # ones.
  # We use a separate cache file as Ninja deletes the depfile after the
  # command was executed.
  if os.path.isfile(cachefile):
    with open(cachefile) as fp:
      for line in fp:
        line = line.strip()
        if line and line not in files:
          files.append(line)

  print('Writing dependencies file:', depfile)
  with open(depfile, 'w') as fp:
    fp.write('dependencies:')
    for x in files[:-1]:
      fp.write(' ' + escape(x) + ' \\\n')
    if files:
      fp.write(' ' + escape(files[-1]) + '\n')

  with open(cachefile, 'w') as fp:
    for x in files:
      fp.write(x + '\n')

  # If the register.cpp does not need to be updated, its timestamp will be
  # older than that of the files that were used to parse it. We touch the
  # register.cpp so the build system nows that the update has happened
  # (timestamp newer than the inputs).
  with open(registercpp, 'a'):
    os.utime(registercpp, None)

  return proc.returncode

if __name__ == '__main__':
  sys.exit(main())
