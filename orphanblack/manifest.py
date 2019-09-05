# Tool to provide fine grained file-lists.
# The syntax and commands are based on the MANIFEST.in files used by distutils.

# See the documentation for exact behavior, but the basic idea is that each line
import os
import sys
import fnmatch
import logging

# TODO: Explicit exclusion / inclusion.
# TODO: Explicit-* warnings.
# TODO: Use shlex?


class Pattern:
  def __init__(self, pattern):
    self.p_tokens = pattern.split(os.path.sep)

  # Note: This function only takes the filepath past the root directory!
  # Otherwise, */*.py might match ./myfile.py
  def matches(self, filename, lengths_must_match=False):
    f_tokens = filename.split(os.path.sep)

    if lengths_must_match and len(f_tokens) != len(self.p_tokens):
      return False

    if len(f_tokens) < len(self.p_tokens):
      return False
    for f_tok, p_tok in zip(reversed(f_tokens), reversed(self.p_tokens)):
      if not fnmatch.fnmatch(f_tok, p_tok):
        return False
    return True

  def __repr__(self):
    return "/".join(self.p_tokens)


def is_file(path):
  return os.path.isfile(path)


def is_dir(path):
  return os.path.isdir(path)


# Assumes that path and dir are both real paths
# Note that this function can fail on Windows if path and dir are on different
# drives. This is not a concern here because we only even encounter files from
# inside a single directory.
def is_subpath(path, dir):
    relative = os.path.relpath(path, dir)

    if relative.startswith(os.pardir):
        return False
    else:
        return True


class ManifestFilter:

  # There are three possible results returned:
  #
  # True means that the file is whitelisted
  #  as a result, this file should be added even if it's not present.
  #
  # False means that the file is blacklisted
  #  as a result, this file should be removed even if it was present.
  #
  # None means that the file is not referenced
  #  as a result, this file's status should not be changed.
  #
  def check(self, filepath):
    raise NotImplementedError("ManifestFilter Subclasses must be able to filter files.")

  @property
  def explicitly_included_files(self):
    return set()

  @property
  def explicitly_excluded_files(self):
    return set()


class CompositeFilter(ManifestFilter):
  def __init__(self, mfilters):
    self.mfilters = mfilters

  def check(self, filepath):
    # To preserve composite filtering properties if composites are composed
    # differently, this should be None.
    included = None
    for mfilter in self.mfilters:
      update = mfilter.check(filepath)
      if update is True:
        included = True
      if update is False:
        included = False
    return included

  def __repr__(self):
    return "COMPOSITE[\n" + "\n".join([repr(mfilter) for mfilter in self.mfilters]) + "\n]"

  @property
  def explicitly_included_files(self):
    return set.union(*[mfilter.explicitly_included_files for mfilter in self.mfilters])

  @property
  def explicitly_excluded_files(self):
    return set.union(*[mfilter.explicitly_excluded_files for mfilter in self.mfilters])


def build_CompositeFilter(mfilters, error_context):
  if len(mfilters) == 0:
    return None  # TODO: DEBUG level message?
  if len(mfilters) == 1:
    return mfilters[0]
  return CompositeFilter(mfilters)


# The logical inverse of whatever filter is passed in.
class NegatedFilter(ManifestFilter):
  def __init__(self, mfilter):
    self.mfilter = mfilter

  def check(self, filepath):
    inverse_result = self.mfilter.check(filepath)
    if inverse_result is None:
      return None
    return not inverse_result

  def __repr__(self):
    return "EXCLUDE " + repr(self.mfilter)

  @property
  def explicitly_included_files(self):
    return self.mfilter.explicitly_excluded_files

  @property
  def explicitly_excluded_files(self):
    return self.mfilter.explicitly_included_files


def negated_builder(builder):
  def f(args, rootdir, error_context):
    inverse_filter = builder(args, rootdir, error_context)
    if inverse_filter is None:
      return None
    return NegatedFilter(inverse_filter)
  return f


class PatternFilter(ManifestFilter):
  def __init__(self, pattern, rootdir, recursive=True):
    self.rootdir = rootdir
    self.pattern = pattern
    self.recursive = recursive

  def check(self, filepath):
    if not is_subpath(filepath, self.rootdir):
      return None
    filename = os.path.relpath(filepath, self.rootdir)
    if self.pattern.matches(filename, lengths_must_match=not self.recursive):
      return True
    return None

  def __repr__(self):
    s = "MATCH " + repr(self.pattern) + " from " + self.rootdir
    if self.recursive:
      s += " or a subdirectory"
    s += "."
    return s


def build_IncludeFilter(args, rootdir, error_context, recursive=False):
  if len(args) == 0:
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + "The \"" + error_context['command']
                 + "\" command requires at least one pattern.")
  mfilters = []
  for pattern_str in args:
    pattern = Pattern(pattern_str)
    mfilters.append(PatternFilter(pattern, rootdir, recursive=recursive))

  # Note that since PatternFilters don't return False, this is basically
  # an OR operation over the filters.
  return build_CompositeFilter(mfilters, error_context)

build_ExcludeFilter = negated_builder(build_IncludeFilter)


def build_RecursiveIncludeFilter(args, rootdir, error_context):
  if len(args) == 0:
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + "The \"" + error_context['command']
                 + "\" command requires at least a directory"
                 + " and a pattern as arguments.")
    return None
  dir = os.path.join(rootdir, args[0])
  if not is_dir(dir):
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + " " + dir + " is not a directory!"
                 + " This \"" + error_context['command']
                 + "\" will be ignored.")
    return None
  return build_IncludeFilter(args[1:], dir, error_context, recursive=True)

build_RecursiveExcludeFilter = negated_builder(build_RecursiveIncludeFilter)


def build_GlobalIncludeFilter(args, rootdir, error_context):
  return build_IncludeFilter(args, rootdir, error_context, recursive=True)

build_GlobalExcludeFilter = negated_builder(build_GlobalIncludeFilter)


class ExplictMatchFilter(ManifestFilter):
  def __init__(self, filepath):
    self.filepath = filepath

  def check(self, filepath):
    if filepath == self.filepath:
      return True
    return None

  def __repr__(self):
    return "EXPLICITLY INCLUDE " + self.filepath + " ."

  @property
  def explicitly_included_files(self):
    return set([self.filepath])


def build_ExplicitIncludeFilter(args, rootdir, error_context):
  if len(args) == 0:
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + "The \"" + error_context['command']
                 + "\" command requires at least one filename.")
  mfilters = []
  for filename in args:
    filepath = os.path.join(rootdir, filename)
    # TODO: Ensure this file exists, if not issue warning.
    if not is_file(filepath):
      logging.warn("In File Manifest \"" + error_context['filename']
                   + "\" on line " + str(error_context['line_number']) + " : "
                   + " " + filename + " is not a file!"
                   + " This \"" + error_context['command']
                   + "\" will be ignored.")
      continue
    mfilters.append(ExplictMatchFilter(filepath))

  # Note that since PatternFilters don't return False, this is basically
  # an OR operation over the filters.
  return build_CompositeFilter(mfilters, error_context)

build_ExplicitExcludeFilter = negated_builder(build_ExplicitIncludeFilter)


class GraftFilter(ManifestFilter):
  def __init__(self, dir):
    self.dir = dir

  def check(self, filepath):
    if is_subpath(filepath, self.dir):
      return True
    return None

  def __repr__(self):
    return "everything below " + self.dir + " ."


def build_GraftFilter(args, rootdir, error_context):
  if len(args) == 0:
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + " A \"" + error_context['command']
                 + "\" command requires a single directory as an argument.")
    return None
  if len(args) > 1:
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + " Received too many arguments "
                 + str(args)
                 + " for a \""
                 + error_context['command']
                 + "\" command. It requires a single directory as an argument.")
    return None
  dir = os.path.join(rootdir, args[0])
  if not is_dir(dir):
    logging.warn("In File Manifest \"" + error_context['filename']
                 + "\" on line " + str(error_context['line_number']) + " : "
                 + " " + dir + " is not a directory!"
                 + " This \"" + error_context['command']
                 + "\" will be ignored.")
    return None
  return GraftFilter(dir)


build_PruneFilter = negated_builder(build_GraftFilter)

command_builders = {
  'include': build_IncludeFilter,
  'exclude': build_ExcludeFilter,
  'explicit-include': build_ExplicitIncludeFilter,
  'explicit-exclude': build_ExplicitExcludeFilter,
  'recursive-include': build_RecursiveIncludeFilter,
  'recursive-exclude': build_RecursiveExcludeFilter,
  'global-include': build_GlobalIncludeFilter,
  'global-exclude': build_GlobalExcludeFilter,
  'graft': build_GraftFilter,
  'prune': build_PruneFilter,
}


def parse_manifest(filename, rootdir):
  try:
    with open(filename, 'r') as f:
      filters = []
      for line_number, line in enumerate(f, 1):

        # Also convienently trims leading and trailing spaces.
        tokens = line.split()

        # Ignore blank lines.
        if len(tokens) == 0:
          continue

        # Ignore comments.
        if tokens[0][0] == '#':
          continue

        command = tokens[0]
        rest = tokens[1:]
        if command not in command_builders:
          logging.error("Invalid command \"" + command + "\" in file manifest.")
          sys.exit(1)

        error_context = {
          'filename': filename,
          'line_number': line_number,
          'command': command,
        }

        manifest_filter = command_builders[command](rest, rootdir, error_context)

        # If the builder aborted building, try to continue without the filter.
        if manifest_filter is None:
          continue

        # Otherwise, add it to the queue of filters files will pass through.
        # Notice that this preseves the order of the lines in the file.
        filters.append(manifest_filter)

    return build_CompositeFilter(filters, None)

  except IOError:
    logging.error("Unable to open file manifest from \"" + filename + "\".")
    sys.exit(1)


def contents(manifest_filename, rootdir=None):
  if rootdir is None:
    rootdir = os.getcwd()
  else:
    rootdir = os.path.realpath(rootdir)
    if not is_dir(rootdir):
      logging.error("Tried to apply a manifest to a non-directory: " + rootdir)
      sys.exit(1)

  manifest_filter = parse_manifest(manifest_filename, rootdir)

  for root, dirnames, filenames in os.walk(rootdir):
    for filename in filenames:
      filepath = os.path.join(root, filename)
      # Note that this is either True, None, or False
      # None implies that no filter cares about the file, so this makes
      # the default non-inclusion.
      if manifest_filter.check(filepath):
        yield filepath


def default_manifest(language):
  defaults = {
    'python': 'PYTHON',
    'javascript': 'JAVASCRIPT'
  }
  manifest_filename = defaults[language]
  dir, _ = os.path.split(__file__)
  return os.path.join(dir, "default_manifests", manifest_filename)

if __name__ == '__main__':
  for filepath in contents("ORPHAN_BLACK_MANIFEST"):
    print os.path.relpath(filepath, os.getcwd())
  # TODO: Should be tests
  # pattern = Pattern("*/b/*.txt")
  # print pattern.matches('a/b/c.txt')
  # print pattern.matches('z/a/b/c.txt')
  # print pattern.matches('z/a/b/c.txt', lengths_must_match=True)
  # print pattern.matches('a/g/c.txt')
  # print pattern.matches('toshort.txt')
