import logging
from argparse import ArgumentParser

import txt_engine
import yaml
from conf.global_settings import OUTPUT_DIR
from cycle_gridding import cycle_gridding
from indicators import indicators
from logs.logconfig import configure_logging
import plotting
import enso_grids


configure_logging(file_timestamp=False)

logging.debug(f'\nUsing output directory: {OUTPUT_DIR}')


def create_parser():
    """
    Creates command line argument parser

    Returns:
        parser (ArgumentParser): the ArgumentParser object
    """
    parser = ArgumentParser()

    parser.add_argument('--options_menu', default=False, action='store_true',
                        help='Display option menu to select which steps in the pipeline to run.')

    # parser.add_argument('-gc', '--grid_cycles', type=str, default='', dest='grid_cycles',
    #                 help='Dataset to harvest')

    return parser


def show_menu():
    """
    Prints the optional navigation menu

    Returns:
        selection (str): the menu number of the selection
    """
    while True:
        print(f'\n{" OPTIONS ":-^35}')
        print('1) Run pipeline on all')
        print('2) Perform gridding')
        print('3) Calculate index values and generate txt output and plots')
        print('4) Generate txt output and plots')
        selection = input('Enter option number: ')

        if selection in ['1', '2', '3', '4']:
            return selection
        print(f'Unknown option entered, "{selection}", please enter a valid option\n')


def run_cycle_gridding():
    try:
        cycle_gridding()
        logging.info('Cycle gridding complete.')
    except Exception as e:
        logging.exception(f'Cycle gridding failed. {e}')


def run_indexing() -> bool:
    success = False
    try:
        success = indicators()
        logging.info('Index calculation complete.')
    except Exception as e:
        logging.error(f'Index calculation failed: {e}')
    
    if not success:
        return success
    
    try:
        plotting.indicator_plots()
    except Exception as e:
        logging.error(f'Plot generation failed: {e}')

    try:
        txt_engine.generate_txt()
        logging.info('Index txt file creation complete.')
    except Exception as e:
        logging.error(f'Index txt file creation failed: {e}')

    return success

def run_enso():
    try: 
        enso_grids.enso_gridding()
        logging.info('ENSO gridding complete.')
    except Exception as e:
        logging.error(f'ENSO gridding failed: {e}')

if __name__ == '__main__':

    print(' SEA LEVEL INDICATORS PIPELINE '.center(57, '='))

    PARSER = create_parser()
    args = PARSER.parse_args()

    # --------------------- Run pipeline ---------------------

    with open(f'conf/datasets.yaml', "r") as stream:
        config = yaml.load(stream, yaml.Loader)
    configs = {c['ds_name']: c for c in config}    

    DATASET_NAMES = list(configs.keys())

    CHOSEN_OPTION = show_menu() if args.options_menu else '1'

    # Run harvesting, gridding, indexing, post processing
    if CHOSEN_OPTION == '1':
        run_cycle_gridding()
        run_indexing()
        run_enso()

    # Run gridding
    elif CHOSEN_OPTION == '2':
        run_cycle_gridding()

    # Run indexing (and post processing)
    elif CHOSEN_OPTION == '3':
        run_indexing()
        
    # Run ENSO
    elif CHOSEN_OPTION == '4':
        run_enso()
