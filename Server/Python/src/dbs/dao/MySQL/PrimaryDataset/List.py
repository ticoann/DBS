#!/usr/bin/env python
"""
This module provides PrimaryDataset.List data access object.
"""
__revision__ = "$Id: List.py,v 1.2 2010/02/11 19:39:34 afaq Exp $"
__version__ = "$Revision: 1.2 $"

from dbs.dao.Oracle.PrimaryDataset.List import List as OraPrimaryDatasetList

class List(OraPrimaryDatasetList):
        pass

