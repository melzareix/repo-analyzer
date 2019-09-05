import textwrap
import json

from parameters import Parameters


class Snippet:
  def __init__(self, filename, lines, text):
    def deindent(string):
      if string and string[0] == '\n':
        string = string[1:]
      return textwrap.dedent(string)
    self.filename = filename
    self.lines = lines
    self.text = deindent(text)

  @property
  def first_line(self):
    return min(self.lines)

  @property
  def last_line(self):
    return max(self.lines)

  @property
  def size(self):
    return len(self.lines)


# Minimal Clone Summary for serialization.
class CloneSummary:
  def __init__(self, name, snippets, distance):
    self.name = name
    self.snippets = snippets
    self.distance = distance

  @property
  def size(self):
    return sum([snippet.size for snippet in self.snippets]) / len(self.snippets)


class Report:
  def __init__(self, parameters, clones=[], filenames=[]):
    self._parameters = parameters
    self._clones = clones
    self._file_names = filenames
    self._mark_to_statement_hash = None

  @property
  def parameters(self):
    return self._parameters

  @property
  def clones(self):
    return self._clones

  @property
  def filenames(self):
    return self._file_names

  def setMarkToStatementHash(self, mark_to_statement_hash):  # TODO: Figure out what this is and if it belongs
    self._mark_to_statement_hash = mark_to_statement_hash

  def addFileName(self, file_name):
    self._file_names.append(file_name)

  def addClone(self, clone):
    self._clones.append(clone)

  def sortByCloneSize(self):
    def f(a, b):
      return cmp(b.size, a.size)
    self._clones.sort(f)


def save_report(filename, report):
  def serialize_parameters(parameters):
    return {
      'clustering_threshold': parameters.clustering_threshold,
      'size_threshold': parameters.size_threshold,
      'distance_threshold': parameters.distance_threshold,
      'hashing_depth': parameters.hashing_depth,
      'clusterize_using_dcup': parameters.clusterize_using_dcup,
      'clusterize_using_hash': parameters.clusterize_using_hash,
      'report_unifiers': parameters.report_unifiers,
      'force': parameters.force,
      'use_diff': parameters.use_diff,
    }

  def serialize_snippet(snippet):
    return {
      'filename': snippet.filename,
      'lines': list(snippet.lines),
      'text': snippet.text,
    }

  def serialize_clone(clone):
    return {
      'name': clone.name,
      'distance': clone.distance,
      'snippets': [serialize_snippet(snippet) for snippet in clone.snippets]
    }
  serialized_report = json.dumps({
    'parameters': serialize_parameters(report.parameters),
    'filenames': report.filenames,
    'clones': [serialize_clone(clone) for clone in report.clones],
  })
  with open(filename, "w") as f:
    f.write(serialized_report)


def load_report(filename):
  def load_parameters(json_parameters):
    parameters = Parameters()
    parameters.clustering_threshold = json_parameters['clustering_threshold']
    parameters.size_threshold = json_parameters['size_threshold']
    parameters.distance_threshold = json_parameters['distance_threshold']
    parameters.hashing_depth = json_parameters['hashing_depth']
    parameters.clusterize_using_dcup = json_parameters['clusterize_using_dcup']
    parameters.clusterize_using_hash = json_parameters['clusterize_using_hash']
    parameters.report_unifiers = json_parameters['report_unifiers']
    parameters.force = json_parameters['force']
    parameters.use_diff = json_parameters['use_diff']

  def load_snippet(json_snippet):
    return Snippet(
      json_snippet['filename'],
      set(json_snippet['lines']),
      json_snippet['text'])

  def load_clone(json_clone):
    return CloneSummary(
      json_clone['name'],
      [load_snippet(snippet) for snippet in json_clone['snippets']],
      json_clone['distance'])

  with open(filename) as f:
    json_report = json.load(f)
  return Report(
    load_parameters(json_report['parameters']),
    [load_clone(clone) for clone in json_report['clones']],
    json_report['filenames'])
