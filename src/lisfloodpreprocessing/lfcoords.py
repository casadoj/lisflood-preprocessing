import numpy as np
import pandas as pd
import argparse
import logging
from datetime import datetime

from lisfloodpreprocessing import Config, read_input_files
from lisfloodpreprocessing.utils import find_conflicts
from lisfloodpreprocessing.finer_grid import coordinates_fine
from lisfloodpreprocessing.coarser_grid import coordinates_coarse

def main():
    
    parser = argparse.ArgumentParser(
        description="""
        Correct the coordinates of a set of points to match the river network in the
        LISFLOOD static map.
        First, it uses a reference value of catchment area to find the most accurate 
        pixel in a high-resolution map.
        Second, it finds the pixel in the low-resolution map that better matches the 
        catchment shape derived from the high-resolution map.
        """
    )
    parser.add_argument('-c', '--config-file', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('-r', '--reservoirs', action='store_true', default=False,
                        help='Define the points in the input CSV file as reservoirs')
    args = parser.parse_args()
    
    # create logger
    logger = logging.getLogger('lfcoords')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_format = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # console handler
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(log_format)
    c_handler.setLevel(logging.INFO)
    logger.addHandler(c_handler)
    # File handler
    f_handler = logging.FileHandler(f'lfcoords_{datetime.now():%Y%m%d%H%M}.log')
    f_handler.setFormatter(log_format)
    f_handler.setLevel(logging.INFO)
    logger.addHandler(f_handler)
        
    # read configuration
    cfg = Config(args.config_file)
    
    # read input files
    inputs = read_input_files(cfg)
    
    # find coordinates in high resolution
    points_HR, polygons_HR = coordinates_fine(cfg,
                                              points=inputs['points'],
                                              ldd_fine=inputs['ldd_fine'],
                                              upstream_fine=inputs['upstream_fine'],
                                              save=True)
    
    # find conflicts in high resolution
    find_conflicts(points_HR,
                   columns=[f'{var}_{cfg.FINE_RESOLUTION}' for var in ['lat', 'lon']],
                   save=cfg.OUTPUT_FOLDER / f'conflicts_{cfg.FINE_RESOLUTION}.shp')
    
    # find coordinates in LISFLOOD
    points_LR, polygons_LR = coordinates_coarse(cfg,
                                                points_fine=points_HR,
                                                polygons_fine=polygons_HR,
                                                ldd_coarse=inputs['ldd_coarse'],
                                                upstream_coarse=inputs['upstream_coarse'],
                                                reservoirs=args.reservoirs,
                                                save=True)
    
    # find conflicts in LISFLOOD
    find_conflicts(points_LR,
                   columns=[f'{var}_{cfg.COARSE_RESOLUTION}' for var in ['lat', 'lon']],
                   save=cfg.OUTPUT_FOLDER / f'conflicts_{cfg.COARSE_RESOLUTION}.shp')

if __name__ == "__main__":
    main()