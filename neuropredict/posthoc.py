from __future__ import print_function
import os
import sys
import warnings
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.colors as mcolors
from matplotlib.backends.backend_pdf import PdfPages
import itertools
from collections import Counter

common_fig_size=[9, 9]

def display_confusion_matrix(cfmat_array, class_labels,
                             method_names, base_output_path,
                             title='Confusion matrix',
                             cmap=plt.cm.Greens):
    """
    Display routine for the confusion matrix.
    Entries in confusin matrix can be turned into percentages with `display_perc=True`.

    Use a separate method to iteratve over multiple datasets.
    confusion_matrix dime: [num_classes, num_classes, num_repetitions, num_datasets]

    """

    num_datasets = cfmat_array.shape[3]
    num_classes  = cfmat_array.shape[0]
    assert num_classes==cfmat_array.shape[1], \
        "Invalid dimensions of confusion matrix. " \
        "Need [num_classes, num_classes, num_repetitions, num_datasets]"

    np.set_printoptions(2)
    for dd in range(num_datasets):
        output_path = base_output_path + '_' + method_names[dd]
        output_path.replace(' ', '_')

        # mean confusion over CV trials
        avg_cfmat = np.mean(cfmat_array[:, :, :, dd], 2)

        # percentage confusion relative to class size
        clsiz_elemwise = np.transpose(np.matlib.repmat(np.sum(avg_cfmat, axis=1), num_classes, 1))
        cfmat = np.divide(avg_cfmat, clsiz_elemwise)
        # human readable in 0-100%, 3 deciamls
        cfmat = 100*np.around(cfmat, decimals=3)

        fig, ax = plt.subplots(figsize=common_fig_size)

        im = plt.imshow(cfmat, interpolation='nearest', cmap=cmap)
        plt.title(title)
        plt.colorbar(im, fraction=0.046, pad=0.04)
        tick_marks = np.arange(len(class_labels))
        plt.xticks(tick_marks, class_labels, rotation=45)
        plt.yticks(tick_marks, class_labels)

        # trick from sklearn
        thresh = 100.0 / num_classes # cfmat.max() / 2.
        for i, j in itertools.product(range(num_classes), range(num_classes)):
            plt.text(j, i, "{}%".format(cfmat[i, j]),
                     horizontalalignment="center", fontsize = 14,
                     color="tomato" if cfmat[i, j] > thresh else "teal")

        plt.tight_layout()
        plt.ylabel('True class')
        plt.xlabel('Predicted class')

        fig.tight_layout()

        pp1 = PdfPages(output_path + '.pdf')
        pp1.savefig()
        pp1.close()

    return


def summarize_misclassifications(misclf_stats):
    "Summary of most/least frequently mislcassified subjects for further analysis"

    pass


def visualize_metrics(metric, labels, output_path, num_classes = 2, metric_label = 'balanced accuracy'):
    """

    Distribution plots of various metrics such as balanced accuracy!

    metric is expected to be ndarray of size [num_repetitions, num_datasets]

    """

    num_repetitions = metric.shape[0]
    num_datasets = metric.shape[1]
    assert len(labels)==num_datasets, "Differing number of features and labels!"
    method_ticks = 1.0+np.arange(num_datasets)

    fig, ax = plt.subplots(figsize=common_fig_size)
    line_coll = ax.violinplot(metric, widths=0.8, bw_method=0.2,
                              showmedians=True, showextrema=False,
                              positions=method_ticks)

    jet = cm.get_cmap('hsv', num_datasets)
    for cc, ln in enumerate(line_coll['bodies']):
        ln.set_facecolor(jet(cc))
        ln.set_label(labels[cc])

    plt.legend(loc=2, ncol=num_datasets)

    ax.tick_params(axis='both', which='major', labelsize=15)
    ax.grid(axis='y', which='major')

    lower_lim = np.float64(0.9/num_classes)
    upper_lim = 1.01
    step_tick = 0.1
    ax.set_ylim(lower_lim, upper_lim)

    ax.set_xticks(method_ticks)
    ax.set_xlim(np.min(method_ticks) - 1, np.max(method_ticks) + 1)
    ax.set_xticklabels(labels, rotation=45) # 'vertical'

    ax.set_yticks(np.arange(lower_lim, upper_lim, step_tick))
    ax.set_yticklabels(np.arange(lower_lim, upper_lim, step_tick))
    # plt.xlabel(xlabel, fontsize=16)
    plt.ylabel(metric_label, fontsize=16)

    fig.tight_layout()

    pp1 = PdfPages(output_path + '.pdf')
    pp1.savefig()
    pp1.close()

    return


def stat_comparison(clf_results):
    "Non-parametric statistical comparison of different feature sets"

    pass



if __name__ == '__main__':
    pass