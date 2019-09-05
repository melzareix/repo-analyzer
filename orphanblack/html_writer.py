#    Copyright 2008 Peter Bulychev
#    Copyright 2015 Will Oursler
#
#    This file is part of Clone Digger.
#
#    Clone Digger is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Clone Digger is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Clone Digger.  If not, see <http://www.gnu.org/licenses/>.
import os
from jinja2 import Environment, FileSystemLoader

path = os.path.dirname(os.path.abspath(__file__))
env = Environment(
  autoescape=False,
  loader=FileSystemLoader(os.path.join(path, 'templates')),
  trim_blocks=False)
template = env.get_template('template.html')


def write(report, file_name):
  percent_source_line_clones = (not report.all_source_lines_count and 100) or 100*report.covered_source_lines_count/float(report.all_source_lines_count)
  # TODO: Make a lot of these properties of report...
  html_text = template.render(
    report=report,
    percent_source_line_clones=percent_source_line_clones)
  f = open(file_name, 'w')
  f.write(html_text)
  f.close()
