class Parameters:
  def __init__(self):
    self.clustering_threshold = 10
    self.size_threshold = 5  # ONLY TRUE FOR PYTHON
    self.distance_threshold = 5  # ONLY TRUE FOR PYTHON
    self.hashing_depth = 1
    self.clusterize_using_dcup = False
    self.clusterize_using_hash = False
    self.report_unifiers = False
    self.force = False
    self.use_diff = False
