import os
from pathlib import Path

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = 'alongtrack-delivery'
OUTPUT_DIR = 'pipeline_output/'
Path.mkdir(OUTPUT_DIR, parents=True, exist_ok=True)

FILE_FORMAT = '.h5'

os.chdir(ROOT_DIR)
