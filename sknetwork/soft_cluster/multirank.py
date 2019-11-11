#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Nov, 2019
@author: Nathan de Lara <ndelara@enst.fr>
"""

from typing import Union

import numpy as np
from scipy import sparse

from sknetwork.ranking import PageRank, BiPageRank
from sknetwork.utils.algorithm_base_class import Algorithm


class MultiRank(Algorithm):
    """Semi-Supervised clustering based on personalized PageRank.

    Parameters
    ----------
    damping_factor:
        Damping factor for personalized PageRank.
    solver:
        Which solver to use for PageRank.
    rtol:
        Relative tolerance parameter.
        Values lower than rtol / n_nodes in each personalized PageRank are set to 0.
    sparse_output:
        If ``True``, returns the membership as a sparse CSR matrix.
        Otherwise, returns a dense ndarray.

    Attributes
    ----------
    membership_: CSR matrix or ndarray
        Component (i, k) indicates the level of membership of node i in the k-th cluster.
        If the provided labels are not consecutive integers starting from 0,
        the k-th column of the membership corresponds to the k-th label in ascending order.
        The rows are normalized to sum to 1.

    References
    ----------
    Lin, F., & Cohen, W. W. (2010, August). `Semi-supervised classification of network data using very few labels.
    <https://lti.cs.cmu.edu/sites/default/files/research/reports/2009/cmulti09017.pdf>`_
    In 2010 International Conference on Advances in Social Networks Analysis and Mining (pp. 192-199). IEEE.

    """
    def __init__(self, damping_factor: float = 0.85, solver: str = 'lanczos', rtol: float = 1e-4,
                 sparse_output: bool = True):
        self.damping_factor = damping_factor
        self.solver = solver
        self.rtol = rtol
        self.sparse_output = sparse_output
        self.bipartite = False

        self.membership_ = None

    def fit(self, adjacency: Union[sparse.csr_matrix, np.ndarray], seeds: Union[np.ndarray, dict]) -> 'MultiRank':
        """Compute personalized PageRank using each given labels as seed set.

        Parameters
        ----------
        adjacency:
            Adjacency matrix of the graph.
        seeds: Dict or ndarray,
            If dict, ``(key, val)`` indicates that node ``key`` has label ``val``.
            If ndarray, ``seeds[i] = val`` indicates that node ``i`` has label ``val``.
            Negative values are treated has no label.

        Returns
        -------
        self: :class:`MultiRank`

        """
        if self.bipartite:
            pagerank = BiPageRank(self.damping_factor, self.solver)
        else:
            pagerank = PageRank(self.damping_factor, self.solver)

        n: int = adjacency.shape[0]
        if isinstance(seeds, np.ndarray):
            if seeds.shape[0] != n:
                raise ValueError('Dimensions mismatch between adjacency and seeds vector.')
        elif isinstance(seeds, dict):
            tmp = -np.ones(n)
            for key, val in seeds.items():
                tmp[key] = val
            seeds = tmp
        else:
            raise TypeError('"seeds" must be a dictionary or a one-dimensional array.')

        unique_labels: np.ndarray = np.unique(seeds[seeds >= 0])
        n_labels: int = len(unique_labels)
        if n_labels < 2:
            raise ValueError('There must be at least to distinct labels.')
        membership = np.zeros((n, n_labels))

        for i, label in enumerate(unique_labels):
            personalization = np.zeros(n)
            personalization[seeds == label] = 1.
            pagerank.fit(adjacency, personalization)
            score = pagerank.score_.copy()
            score[score <= self.rtol / n] = 0

            membership[:, i] = score

        norm = np.sum(membership, axis=1)
        membership[norm > 0] /= norm[norm > 0, np.newaxis]

        if self.sparse_output:
            self.membership_ = sparse.csr_matrix(membership)
        else:
            self.membership_ = membership

        return self


class BiMultiRank(MultiRank):
    """Semi-Supervised clustering based on personalized PageRank for bipartite graphs.
    See :class:`sknetwork.ranking.BiPageRank`
    """

    def __init__(self, damping_factor: float = 0.85, solver: str = 'lanczos', rtol: float = 1e-4,
                 sparse_output: bool = True):
        MultiRank.__init__(self, damping_factor, solver, rtol, sparse_output)
        self.bipartite = True