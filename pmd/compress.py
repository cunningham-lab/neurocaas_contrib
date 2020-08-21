#!/usr/bin/env python
import os
import sys

import yaml
import scipy

import numpy as np
import trefide.pmd

from trefide.reformat import overlapping_component_reformat
from trefide.pmd import determine_thresholds
from trefide.pmd import batch_decompose
from trefide.pmd import overlapping_batch_decompose
from trefide.utils import psd_noise_estimate

import skimage
import skimage.io
import sklearn
from sklearn.utils.extmath import randomized_svd as svd

# Declare Constants
CONFIG_NAME = 'config'
CONFIG_EXT = 'yaml'
REQ_PARAM_KEYS = [
    'fov_height',
    'fov_width',
    'num_frames',
    'block_height',
    'block_width'
]
DEFAULT_PARAMS = {
    # Optional: Simulated
    'spatial_thresh': None,
    'temporal_thresh': None,
    # Optional: Preprocessing
    'center': False,
    'scale': False,
    'background_rank': 0,
    # Optional: Defaults
    'overlapping':True,
    'd_sub': 1,
    't_sub': 1, 
    'max_iters_init': 40,
    'max_iters_main': 10,
    'max_components': 50,
    'consec_failures': 3,
    'tol': 5e-3, 
    # Data Formatting
    'transpose': False
}


def print_and_flush(string):
    """ """
    print(string)
    sys.stdout.flush()


def load_params(filename, ext): 
    """ Read Config.yaml & merge with defaults """

    # Convert yaml file to python dict
    print_and_flush("Loading configuration file ({})...".format(filename + '.' + ext))
    with open(filename + '.' + ext, 'r') as stream:
        user_params = yaml.safe_load(stream)
    print_and_flush("Configuration file successfully loaded.")

    # Ensure That Required Arguments Have Been Provided
    print_and_flush('Checking required fields...')
    for key in REQ_PARAM_KEYS:
        if not key in user_params.keys():
            raise ValueError('Provided config missing required param: {}'.format(key))
    print_and_flush('All required fields have been provided.')

    # Plug In Defaults For Missing Optional Params
    print_and_flush('Inserting defaults for missing optional arguments')
    for key, val in DEFAULT_PARAMS.items():
        if not key in user_params.keys():
            user_params[key] = val 
    
    # Check To See If User Provided Anything Unused & Notify

    # Return Processed Param Dict
    return user_params


def write_params(filename, ext, params): 
    """ Read Config.yaml & merge with defaults """

    # Convert yaml file to python dict
    print_and_flush("Writing configuration file ({})...".format(filename + '.' + ext))
    with open(filename + '.' + ext, 'w') as stream:
        user_params = yaml.dump(params, stream, default_flow_style=False)
    print_and_flush("Configuration file written to outputs successfully.")


def simulate_missing_params(params):
    """ """
    # Check To See If We Need To Run Simulations
    missing_spatial_thresh = params['spatial_thresh'] is None
    missing_temporal_thresh = params['temporal_thresh'] is None
    simulate_thresholds = missing_spatial_thresh or missing_temporal_thresh

    # If Either Is Missing, Run Simulations & Overwrite
    if simulate_thresholds:
        print_and_flush("One or both thresholds were not provided, performing simulations...")
        st, tt = determine_thresholds( #TODO: Simplify Param Passing
            (params['fov_height'], params['fov_width'], params['num_frames']),
            (params['block_height'], params['block_width']),
            params['consec_failures'], params['max_iters_main'], 
            params['max_iters_init'], params['tol'], 
            params['d_sub'], params['t_sub'], 5, True
        )
        params['spatial_thresh'] = st.item()
        params['temporal_thresh'] = tt.item()
        print_and_flush("Simulations complete, determined thresholds are (spatial:{}, temporal:{})".format(st, tt))
    return simulate_thresholds


def load_data(filename, ext):
    """ Handle Loading Of Multiple File Formats """

    # Switch To Different Loading Functions Depending On Filetype
    print_and_flush("Loading dataset ({})...".format(filename + '.' + ext))
    if ext == 'npy':
        data = np.load(filename + '.' + ext)
    elif ext == 'tiff':
        data = skimage.io.imread(filename + '.' + ext)
    else:
        raise ValueError("Invalid file format '{}', please use ['npy', 'tiff'].")
    print_and_flush("Dataset of shape {} successfully loaded.".format(data.shape))

    # Rearrange Dimensions If Instructed
    # TODO modify params so transpose can be any sequence of dims
    if params['transpose']:
        print_and_flush("Transposing data to order (fov_height, fov_width, num_frames)...")
        data = np.transpose(data, (1,2,0))

    # TODO maybe add options for users to trim dimensions?
    return np.ascontiguousarray(data).astype(np.float64)


def validate_data(params, data):
    """ """
    expected_shape = (params['fov_height'], params['fov_width'], params['num_frames'])
    if not expected_shape == data.shape:
        raise ValueError('Data shape {} does not match provided config {}.'.format(data.shape, expected_shape))


def center_and_scale(params, data):
    """ """

    # Center With Pixelwise Median
    if params['center']:
        print_and_flush('Computing pixelwise median...')
        baseline = np.median(data.reshape((-1, data.shape[-1])), axis=-1)
        print_and_flush('Performing pixelwise offset...')
        data = (data.reshape((-1, data.shape[-1])) - baseline[:,None]).reshape(data.shape)
        print_and_flush('Centering complete.')
    else:
        baseline = np.zeros((data.shape[0], data.shape[1]))

    # Scale To Have Unit Standard Deviation
    if params['scale']:
        print_and_flush('Estimating pixelwise noise variance...')
        scale = np.asarray(psd_noise_estimate(data.reshape((-1, data.shape[-1]))))
        print_and_flush('Performing pixelwise normalization...')
        data = (data.reshape((-1, data.shape[-1])) / scale[:,None]).reshape(data.shape)
        print_and_flush('Scaling complete.')
    else: 
        scale = np.ones((data.shape[0], data.shape[1]))

    return data, baseline, scale


def extract_background(params, data):
    """ """
    if params['background_rank'] > 0:
        print_and_flush('Fitting low-rank background...')
        U, s, Vt = svd(M=data.reshape((-1, data.shape[-1])), 
                       n_components=params['background_rank'])
        U = np.reshape(U * s[None, :], data.shape[:2] + U.shape[-1:])
        print_and_flush('Removing background from dataset...')
        data = data - np.dot(U, Vt)
        print_and_flush('Background successfully extracted.')
        return data, (U, Vt)
    return data, (None, None)


def run_pmd(params, data):
    """ Perform Compression """
    if not params['overlapping']:    # Blockwise Parallel, Single Tiling
        print_and_flush("Performing decomposition...")
        results = batch_decompose(
            params['fov_height'], params['fov_width'], params['num_frames'],
            data, params['block_height'], params['block_width'],
            params['spatial_thresh'], params['temporal_thresh'],
            params['max_components'], params['consec_failures'],
            params['max_iters_main'], params['max_iters_init'], params['tol'],
            params['d_sub'], params['t_sub']
        )
    else:    # Blockwise Parallel, 4x Overlapping Tiling
        print_and_flush("Performing overlapping decomposition...")
        results = overlapping_batch_decompose(
            params['fov_height'], params['fov_width'], params['num_frames'],
            data, params['block_height'], params['block_width'],
            params['spatial_thresh'], params['temporal_thresh'],
            params['max_components'], params['consec_failures'],
            params['max_iters_main'], params['max_iters_init'], params['tol'],
            params['d_sub'], params['t_sub']
        )
    print_and_flush("decomposition completed successfully.")
    return results


def process_results(params, results, baseline, scale, background, filename):
    """ """
    # Generate Summary Figs & Diagnostic Video
    #TODO

    # Reformat Results For Compact Writing
    if not params['overlapping']:    # Blockwise Parallel, Single Tiling
        #U, V = component_reformat( #TODO
        #        params['fov_height'], params['fov_width'], params['num_frames'],
        #        params['block_height'], params['block_width'],
        #        results[0], results[1], results[2], results[3]
        #)
        U, V = results[0], results[1]
    else:    # Blockwise Parallel, 4x Overlapping Tiling
        print_and_flush("Expanding spatial matrices...")
        U, V = overlapping_component_reformat(
                params['fov_height'], params['fov_width'], params['num_frames'],
                params['block_height'], params['block_width'],
                results[0], results[1], results[2], results[3], results[4]
        )
        print_and_flush("Overlapping reformat completed successfully.")

    # Write Results To Outdir
    print_and_flush("Writing denoised results file ({})...".format(filename))
    np.savez(filename, 
             U=U, V=V, 
             ranks=results[2], indices=results[3],
             baseline=baseline, scale=scale, 
             U_bg=background[0], V_bg=background[1], 
             allow_pickle=True)
    print_and_flush("Denoised results file successfully written.")


if __name__ == "__main__":
    
    # Get Command Line Args
    filename, ext = sys.argv[1].split('.')
    indir = sys.argv[2]
    outdir = sys.argv[3]

    # Read & Process Params
    params = load_params(os.path.join(indir, CONFIG_NAME), CONFIG_EXT)
    config_was_modified = simulate_missing_params(params)

    #  Load Data, Run PMD, & Format + Write Results
    data = load_data(os.path.join(indir, filename), ext)
    validate_data(params, data)

    # Perform Required Preprocessing...
    data, baseline, scale = center_and_scale(params, data)
    data, background = extract_background(params, data)

    # Perform Compression
    results = run_pmd(params, data)

    # Write Results to output
    process_results(params, results, 
                    baseline, scale, 
                    background,
                    os.path.join(outdir, filename + '_denoised.npz'))
    write_params(os.path.join(outdir, CONFIG_NAME), CONFIG_EXT, params)
    print('Done! Shutting Down Instance...')
