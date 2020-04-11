"""

Module defining methods and classes needed to manage results produced.

"""

from abc import abstractmethod

import numpy as np
import pickle
from pathlib import Path
from neuropredict import config as cfg
from neuropredict.utils import is_iterable_but_not_str


class CVResults(object):
    """
    Class to store and organize the results for a CV run.
    """


    def __init__(self,
                 metric_set=(cfg.default_scoring_metric,),
                 num_rep=cfg.default_num_repetitions,
                 dataset_ids='dataset1'):
        "Constructor."

        if num_rep < 1 or not np.isfinite(num_rep):
            raise ValueError('num_rep must be a finite integer.')
        self.num_rep = np.int64(num_rep)

        if dataset_ids is not None:
            if is_iterable_but_not_str(dataset_ids):
                self._dataset_ids = tuple(dataset_ids)
            else:
                self._dataset_ids = (dataset_ids,)
        else:
            # assuming only one feature/dataset
            self._dataset_ids = ('dataset1',)

        if is_iterable_but_not_str(metric_set):
            self.metric_set = {func.__name__: func for func in metric_set}
            self.metric_val = dict()
        else:
            raise ValueError('metric_set must be a list of predefined metric names')

        # initializing arrays
        for m_name in self.metric_set.keys():
            self._init_new_metric(m_name)

        self._count = 0
        self.attr = dict()
        self.meta = dict()

        # sharing the target values
        self.true_targets = dict()
        self.predicted_targets = dict()

        # pretty print options
        self._max_width_metric = max([len(mt) for mt in self.metric_set.keys()]) + 1
        self._max_width_ds_ids = max([len(str(ds)) for ds in self._dataset_ids]) + 1


    def _init_new_metric(self, name):
        """Initializes a new metric with an array for all datasets"""

        if name not in self.metric_val:
            self.metric_val[name] = {ds_id: np.full((self.num_rep,), np.NaN)
                                     for ds_id in self._dataset_ids}


    def add(self, run_id, dataset_id, predicted, true_targets):
        """
        Method to populate the CVResults class with predictions/accuracies,
         coming from different repetitions of CV.
        """

        # TODO should we ensure dataset_id exists already in self._dataset_ids?
        #   what do when run_id > self.num_reps
        self.true_targets[(dataset_id, run_id)] = true_targets
        self.predicted_targets[(dataset_id, run_id)] = predicted

        msgs = list()
        msgs.append('CV run {:<3} dataset {did:<{dlen}} :'
                    ''.format(run_id, did=dataset_id, dlen=self._max_width_ds_ids))
        for name, score_func in self.metric_set.items():
            score = score_func(true_targets, predicted)
            self.metric_val[name][dataset_id][run_id] = score
            msgs.append(' {:>20} {:8.3f}'.format(name, score))

        # quick summary print
        print(' '.join(msgs))

        # counting
        self._count += 1


    def add_metric(self, run_id, dataset_id, name, value):
        """Helper to add a metric directly"""

        if name not in self.metric_val:
            self._init_new_metric(name)

        self.metric_val[name][dataset_id][run_id] = value


    def add_attr(self, run_id, dataset_id, name, value):
        """
        Method to store miscellaneous attributes for post-hoc analyses,
        """

        if name not in self.attr:
            self.attr[name] = dict()

        self.attr[name][(dataset_id, run_id)] = value


    def add_meta(self, name, value):
        """
        Method to store experiment-wise meta data (for all runs and datasets).

        Examples include class_set, model and optimization strategies
        """

        self.meta[name] = value


    def _metric_summary(self):
        """for FYI"""

        if self._count > 0:
            summary = list()
            for metric, mdict in self.metric_val.items():
                summary.append('\n{metric:<{mmw}}'
                               ''.format(metric=metric, mmw=self._max_width_metric))
                for ds, distr in mdict.items():
                    median = np.nanmedian(distr)
                    SD = np.nanstd(distr)
                    summary.append('\t{ds:>{mds}} '
                                   ' : median {median:<7.4f} SD {SD:<7.4f}'
                                   ''.format(ds=ds, median=median,
                                             SD=SD, mds=self._max_width_ds_ids))
            return '\n'.join(summary)
        else:
            return 'No results added so far!'


    def __str__(self):
        """Simple summary"""

        return '\n\nMetrics : {}\n # runs : {}, # datasets : {}\n{}' \
               ''.format(', '.join(self.metric_val.keys()), self._count,
                         len(self._dataset_ids), self._metric_summary())


    def __repr__(self):
        return self.__str__()


    def __format__(self, format_spec):
        return self.__str__()


    def save(self):
        "Method to persist the results to disk."

    @abstractmethod
    def load(self, path):
        "Method to load previously saved results e.g. to redo visualizations"


    def to_array(self, metric, ds_ids=None):
        """
        Consolidates a given metric into a flat array

        Parameters
        -----------
        metric : str
            name of the metric whose values are to be returned

        ds_ids : Iterable
            List of datasets ids to be queried. This is helpful to return only a
            desired subset needed, or to control the desired order.

        Returns
        --------
        result : ndarray
            An array of dimensions num_rep_CV X num_datasets

        ds_ids : Iterable
            List of datasets ids

        Raises
        ------
        ValueError
            If metric, one of the ids in ds_ids, is not recognized or invalid
        """

        metric = metric.lower()
        if metric not in self.metric_val:
            raise ValueError('Unrecognized metric: {}\n\tMust be one of {}'
                             ''.format(metric, tuple(self.metric_val.keys())))

        if ds_ids is None:
            ds_ids = self._dataset_ids
        else:
            for did in ds_ids:
                if did not in self._dataset_ids:
                    raise ValueError('{} not recognized! Choose a dataset from: {}'
                                     ''.format(did, self._dataset_ids))

        m_data = self.metric_val[metric]
        consolidated = np.empty((self.num_rep, len(m_data)))
        for index, ds_id in enumerate(ds_ids):
            consolidated[:, index] = m_data[ds_id]

        return consolidated, ds_ids


    @abstractmethod
    def dump(self, out_dir):
        """Method for quick dump, for checkpointing purposes"""


    @abstractmethod
    def export(self):
        "Method to export the results to different formats (e.g. pyradigm or CSV)"


class ClassifyCVResults(CVResults):
    """Custom CVResults class to accommodate classification-specific evaluation."""


    def __init__(self,
                 metric_set=cfg.default_metric_set_classification,
                 num_rep=cfg.default_num_repetitions,
                 dataset_ids=None,
                 path=None):
        "Constructor."

        if path is not None:
            path = Path(path)
            if not path.exists():
                raise IOError('Path to load the results from does not exist:\n{}'
                              ''.format(path))
            self.load(path)
        else:
            super().__init__(metric_set=metric_set, num_rep=num_rep,
                             dataset_ids=dataset_ids)

        self.confusion_mat = dict()  # confusion matrix
        self.misclfd_samplets = dict()  # list of misclassified samplets


    def add_diagnostics(self, run_id, dataset_id, conf_mat, misclfd_ids):
        """Method to save the confusion matrix from each prediction run"""

        self.confusion_mat[(dataset_id, run_id)] = conf_mat
        self.misclfd_samplets[(dataset_id, run_id)] = misclfd_ids


    def export(self):
        """Method to export the results in portable formats reusable outside this
        library"""

        raise NotImplementedError()


    def dump(self, out_dir):
        """Method for quick dump, for checkpointing purposes"""

        from os.path import join as pjoin, exists
        from neuropredict.utils import make_time_stamp
        import pickle
        out_path = pjoin(out_dir, '{}_{}.pkl'
                                  ''.format(cfg.prefix_dump, make_time_stamp()))
        if exists(out_path):
            from os import remove
            remove(out_path)
        with open(out_path, 'wb') as df:
            to_save = [self.metric_set, self.metric_val, self.attr, self.meta,
                       self.confusion_mat, self.misclfd_samplets]
            pickle.dump(to_save, df)


    def load(self, path):
        "Method to load previously saved results e.g. to redo visualizations"

        try:
            with open(path, 'rb') as res_fid:
                full_results = pickle.load(res_fid)
        except:
            raise IOError()
        else:
            results = full_results['results']
            for var in cfg.clf_results_class_variables_to_load:
                setattr(self, var, getattr(results, var))

            # dynamically computing whats needed
            self._max_width_metric = max(
                    [len(mt) for mt in self.metric_set.keys()]) + 1
            self._max_width_ds_ids = max(
                    [len(str(ds)) for ds in self._dataset_ids]) + 1

        print()

        return self


class RegressCVResults(CVResults):
    """Custom CVResults class to accommodate classification-specific evaluation."""


    def __init__(self,
                 metric_set=cfg.default_metric_set_regression,
                 num_rep=cfg.default_num_repetitions,
                 dataset_ids=None,
                 path=None):
        "Constructor."

        if path is not None:
            path = Path(path)
            if not path.exists():
                raise IOError('Path to load the results from does not exist:\n{}'
                              ''.format(path))
            self.load(path)
        else:
            super().__init__(metric_set=metric_set, num_rep=num_rep,
                             dataset_ids=dataset_ids)

        self.residuals = dict()


    def add_diagnostics(self, run_id, dataset_id, true_targets, predicted):
        """Method to save the confusion matrix from each prediction run"""

        residuals = predicted - true_targets
        self.residuals[(dataset_id, run_id)] = residuals


    def dump(self, out_dir):
        """Method for quick dump, for checkpointing purposes"""

        from os.path import join as pjoin, exists
        from neuropredict.utils import make_time_stamp
        import pickle
        out_path = pjoin(out_dir, '{}_{}.pkl'
                                  ''.format(cfg.prefix_dump, make_time_stamp()))
        if exists(out_path):
            from os import remove
            remove(out_path)
        with open(out_path, 'wb') as df:
            to_save = [self.metric_set, self.metric_val, self.attr, self.meta]
            pickle.dump(to_save, df)

    def load(self, path):
        "Method to load previously saved results e.g. to redo visualizations"

        try:
            with open(path, 'rb') as res_fid:
                full_results = pickle.load(res_fid)
        except:
            raise IOError()
        else:
            results = full_results['results']
            for var in cfg.regr_results_class_variables_to_load:
                setattr(self, var, getattr(results, var))

            # dynamically computing whats needed
            self._max_width_metric = max(
                    [len(mt) for mt in self.metric_set.keys()]) + 1
            self._max_width_ds_ids = max(
                    [len(str(ds)) for ds in self._dataset_ids]) + 1

        return self