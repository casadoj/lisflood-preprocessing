import os
os.environ['USE_PYGEOS'] = '0'
import yaml
from pathlib import Path
from typing import Union, Dict
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import xarray as xr
import rioxarray
import logging

# set logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)



class Config:
    def __init__(self, config_file):
        """
        Reads the configuration from a YAML file and sets default values if not provided.

        Parameters:
        -----------
        config_file: string or pathlib.Path
            The path to the YAML configuration file.
        """
        
        # read configuration file
        with open(config_file, 'r', encoding='utf8') as ymlfile:
            config = yaml.load(ymlfile, Loader=yaml.FullLoader)
            
        # input
        self.POINTS = Path(config['input']['points'])
        self.LDD_FINE = Path(config['input']['ldd_fine'])
        self.UPSTREAM_FINE = Path(config['input']['upstream_fine'])
        self.LDD_COARSE = Path(config['input']['ldd_coarse'])
        self.UPSTREAM_COARSE = Path(config['input']['upstream_coarse'])
        
        # resolutions
        self.FINE_RESOLUTION = None
        self.COARSE_RESOLUTION = None
        
        # output
        self.OUTPUT_FOLDER = Path(config.get('output_folder', './shapefiles'))
        self.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # conditions
        self.MIN_AREA = config['conditions'].get('min_area', 10)
        self.ABS_ERROR = config['conditions'].get('abs_error', 50)
        self.PCT_ERROR = config['conditions'].get('pct_error', 1)
            
        
        
def read_input_files(
    cfg: Config
) -> Dict:
    """Reads the input files and saves them in a dictionary. It also updates attributes in the Config object based on the resolution of the input maps
    
    Parameters:
    -----------
    cfg: Config
        Configuration object containing file paths and parameters specified in the configuration file.
        
    Returns:
    --------
    inputs: dictionary
        * 'points': geopandas.GeoDataFrame of input points
        * 'ldd_fine': xarray.DataArray of local drainaige directions in the fine grid
        * 'upstream_fine': xarray.DataArray of upstream area (km2) in the fine grid
        * 'ldd_coarse': xarray.DataArray of local drainaige directions in the coarse grid
        * 'upstream_coarse': xarray.DataArray of upstream area (m2) in the coarse grid
    """
    
    # read upstream map with fine resolution
    upstream_fine = rioxarray.open_rasterio(cfg.UPSTREAM_FINE).squeeze(dim='band')
    logger.info(f'Map of upstream area in the finer grid corretly read: {cfg.UPSTREAM_FINE}')

    # read local drainage direction map
    ldd_fine = rioxarray.open_rasterio(cfg.LDD_FINE).squeeze(dim='band')
    logger.info(f'Map of local drainage directions in the finer grid corretly read: {cfg.LDD_FINE}')
    
    # read upstream area map of coarse grid
    upstream_coarse = rioxarray.open_rasterio(cfg.UPSTREAM_COARSE).squeeze(dim='band')
    logger.info(f'Map of upstream area in the coarser grid corretly read: {cfg.UPSTREAM_COARSE}')

    # read local drainage direction map
    ldd_coarse = rioxarray.open_rasterio(cfg.LDD_COARSE).squeeze(dim='band')
    logger.info(f'Map of local drainage directions in the coarser grid correctly read: {cfg.LDD_COARSE}')
    
    # read points text file
    points = pd.read_csv(cfg.POINTS, index_col='ID')
    points.columns = points.columns.str.lower()
    logger.info(f'Table of points correctly read: {cfg.POINTS}')
    # remove points with missing values
    mask = points.isnull().any(axis=1)
    if mask.sum() > 0:
        points = points[~mask]
        logger.warning(f'{mask.sum()} points were removed because of missing values')
    # convert to geopandas and export as shapefile
    points = gpd.GeoDataFrame(points,
                              geometry=[Point(xy) for xy in zip(points['lon'], points['lat'])],
                              crs=ldd_coarse.rio.crs)
    point_shp = cfg.OUTPUT_FOLDER / f'{cfg.POINTS.stem}.shp'
    points.to_file(point_shp)
    logger.info(f'The original points table has been exported to: {point_shp}')
    
    inputs = {
        'points': points,
        'ldd_fine': ldd_fine,
        'upstream_fine': upstream_fine,
        'ldd_coarse': ldd_coarse,
        'upstream_coarse': upstream_coarse,
    }
    
    # update Config
    update_config(cfg, ldd_fine, ldd_coarse)
    
    return inputs



def update_config(
    cfg: Config,
    fine_grid: xr.DataArray,
    coarse_grid: xr.DataArray
):
    """It extracts the resolution of the finer and coarser grid, updates the respective attributes in the configuration object, and it creates the necessary structure of directories
    
    Parameters:
    -----------
    cfg: Config
        Configuration object containing file paths and parameters specified in the configuration file.
    fine_grid: xarray.DataArray
        Any map in the fine grid
    coarse_grid: xarray.DataArray
        Any map in the coarse grid    
    """
    
    # resolution of the finer grid
    cellsize = np.mean(np.diff(fine_grid.x)) # degrees
    cellsize_arcsec = int(np.round(cellsize * 3600, 0)) # arcsec
    logger.info(f'The resolution of the finer grid is {cellsize_arcsec} arcseconds')
    cfg.FINE_RESOLUTION = f'{cellsize_arcsec}sec'
    
    # resolution of the input maps
    cellsize = np.round(np.mean(np.diff(coarse_grid.x)), 6) # degrees
    cellsize_arcmin = int(np.round(cellsize * 60, 0)) # arcmin
    logger.info(f'The resolution of the coarser grid is {cellsize_arcmin} arcminutes')
    cfg.COARSE_RESOLUTION = f'{cellsize_arcmin}min'