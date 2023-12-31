import warnings
from datetime import datetime
from netCDF4 import default_fillvals  # pylint: disable=no-name-in-module

import numpy as np
import xarray as xr
from conf.global_settings import OUTPUT_DIR
from glob import glob
import os

warnings.filterwarnings('ignore')

seas_ds = xr.open_dataset('ref_files/trnd_seas_simple_grid.nc')
seas_ds.coords['Longitude'] = (seas_ds.coords['Longitude']) % 360
seas_ds = seas_ds.sortby(seas_ds.Longitude)

front_seas_ds = seas_ds.isel(Month_grid=0)
back_seas_ds = seas_ds.isel(Month_grid=-1)
front_seas_ds = front_seas_ds.assign_coords({'Month_grid': front_seas_ds.Month_grid.values + (12/12)})
back_seas_ds = back_seas_ds.assign_coords({'Month_grid': back_seas_ds.Month_grid.values - (12/12)})
padded_seas_ds = xr.concat([back_seas_ds, seas_ds, front_seas_ds], dim='Month_grid')

hr_mask_ds = xr.open_dataset('ref_files/HR_GRID_MASK_latlon.nc')
hr_mask_ds.coords['longitude'] = hr_mask_ds.coords['longitude'] % 360
hr_mask_ds = hr_mask_ds.sortby(hr_mask_ds.longitude)

def get_decimal_year(dt: datetime):
    year_start = datetime(dt.year, 1, 1)
    year_end = year_start.replace(year=dt.year+1)
    return dt.year + ((dt - year_start).total_seconds() /  # seconds so far
        float((year_end - year_start).total_seconds()))  # seconds in year

def interp(ds: xr.Dataset) -> xr.Dataset:
    new_lats = np.arange(-89.875,90.125,0.25)
    new_lons = np.arange(-9.825,369.825, 0.25)
    interp_ds = ds.interp(longitude=new_lons, latitude=new_lats)
    return interp_ds


def smoothing(ds):
    # interpolation
    interp_ds = interp(ds)

    # Do boxcar averaging
    dsr = interp_ds.rolling({'longitude':38, 'latitude':16}, min_periods=1, center=True).mean()
    dsr = dsr.sel(longitude=slice(0,360))
    
    dsr.SSHA.values = np.where(hr_mask_ds.maskC.values == 0, np.nan, dsr.SSHA.values)
    filtered_ds = dsr.where(dsr.counts > 475, np.nan)
    filtered_ds.SSHA.values = np.where(hr_mask_ds.maskC.values == 0, np.nan, filtered_ds.SSHA.values)

    dsr_subset = filtered_ds.sel(latitude=slice(-82,82))

    return dsr_subset

def remove_trends(data, date):
    decimal_year = get_decimal_year(date)
    yr_fraction = decimal_year - date.year

    cycle_ds = padded_seas_ds.interp({'Month_grid': yr_fraction})
    removed_cycle_data = data - (cycle_ds.Seasonal_SSH.values * 10)
    trend = (decimal_year * seas_ds.SSH_Slope * 10) + (seas_ds.SSH_Offset * 10)
    removed_cycle_trend_data = removed_cycle_data - trend
    return removed_cycle_trend_data

def padding(ds):
    front = ds.sel(longitude=slice(0,10))
    back = ds.sel(longitude=slice(350,360))
    front = front.assign_coords({'longitude': front.longitude.values + 360})
    back = back.assign_coords({'longitude': back.longitude.values - 360})
    padded_ds = xr.merge([back, ds, front])
    return padded_ds

def cycle_ds_encoding(cycle_ds):
    """
    Generates encoding dictionary used for saving the cycle netCDF file.
    The measures gridded dataset (1812) has additional units encoding requirements.

    Params:
        cycle_ds (Dataset): the Dataset object
        ds_name (str): the name of the dataset (used to check if dataset is 1812)
        center_date (datetime): used to set the units encoding in the 1812 dataset

    Returns:
        encoding (dict): the encoding dictionary for the cycle_ds Dataset object
    """

    var_encoding = {'zlib': True,
                    'complevel': 5,
                    'dtype': 'float32',
                    'shuffle': True,
                    '_FillValue': default_fillvals['f8']}
    var_encodings = {var: var_encoding for var in cycle_ds.data_vars}

    coord_encoding = {}
    for coord in cycle_ds.coords:
        if 'Time' in coord:
            coord_encoding[coord] = {'_FillValue': None,
                                     'zlib': True,
                                     'contiguous': False,
                                     'shuffle': False}

        if 'Lat' in coord or 'Lon' in coord:
            coord_encoding[coord] = {'_FillValue': None, 'dtype': 'float32'}

    encoding = {**coord_encoding, **var_encodings}
    return encoding

def make_grid(ds):
    # ds.coords['longitude'] = (ds.coords['longitude']) % 360
    # ds = ds.sortby(ds.longitude)
    # data = ds.SSHA.values * 1000
    # date = datetime.strptime(str(ds.time.values)[:10], '%Y-%m-%d')
    # date_str = datetime.strftime(date, '%Y%m%d')

    # removed_cycle_trend_data = remove_trends(data, date)
    # ds.SSHA.values = removed_cycle_trend_data

    # padded_ds = padding(ds)

    # smooth_ds = smoothing(padded_ds)
    # smooth_ds = smooth_ds.drop_vars(['counts', 'mask'])
    # smooth_ds.SSHA.attrs = ds.SSHA.attrs
    # smooth_ds.SSHA.attrs['units'] = 'mm'
    # smooth_ds.SSHA.attrs['valid_min'] = np.nanmin(smooth_ds.SSHA.values)
    # smooth_ds.SSHA.attrs['valid_max'] = np.nanmax(smooth_ds.SSHA.values)
    # smooth_ds.SSHA.attrs['summary'] = 'Data gridded to 0.25 degree grid with boxcar smoothing applied'

    # smooth_ds.latitude.attrs = {'long_name': 'latitude', 'standard_name': 'latitude'}
    # smooth_ds.longitude.attrs = {'long_name': 'longitude', 'standard_name': 'longitude'}

    # encoding = cycle_ds_encoding(smooth_ds)

    # fname = f'ssha_enso_{date_str}.nc'
    # smooth_ds.to_netcdf(f'{OUTPUT_DIR}/ENSO_grids/{fname}', encoding=encoding)
    fname = f'ssha_enso_{datetime.strftime(date, "%Y%m%d")}.nc'
    if os.path.exists(f'{OUTPUT_DIR}/ENSO_grids/{fname}'):
        print('ENSO grid already exists. Skipping.')
        return
    
    ds.coords['longitude'] = (ds.coords['longitude']) % 360
    ds = ds.sortby(ds.longitude)
    ds = ds.where(ds.counts > 475, np.nan)

    lats = ds.latitude.values
    lons = ds.longitude.values
    data = ds.SSHA.values * 1000
    counts = ds.counts.values
    date = datetime.utcfromtimestamp(ds.time.values.tolist()/1e9)

    date_str = datetime.strftime(date, '%b %d %Y')

    decimal_year = get_decimal_year(date)
    yr_fraction = decimal_year - date.year
    cycle_ds = padded_seas_ds.interp({'Month_grid': yr_fraction})

    removed_cycle_data = data - (cycle_ds.Seasonal_SSH.values * 10)
    trend = (decimal_year * seas_ds.SSH_Slope * 10) + (seas_ds.SSH_Offset * 10)
    removed_cycle_trend_data = removed_cycle_data - trend
    ds.SSHA.values = removed_cycle_trend_data

    front = ds.sel(longitude=slice(0,10))
    back = ds.sel(longitude=slice(350,360))
    front = front.assign_coords({'longitude': front.longitude.values + 360})
    back = back.assign_coords({'longitude': back.longitude.values - 360})
    padded_ds = xr.merge([back, ds, front])

    smooth_ds = smoothing(padded_ds)
    filtered_ds = smooth_ds.drop_vars(['counts', 'mask'])

    filtered_ds.SSHA.attrs = ds.SSHA.attrs
    filtered_ds.SSHA.attrs['units'] = 'mm'
    filtered_ds.SSHA.attrs['valid_min'] = np.nanmin(filtered_ds.SSHA.values)
    filtered_ds.SSHA.attrs['valid_max'] = np.nanmax(filtered_ds.SSHA.values)
    filtered_ds.SSHA.attrs['summary'] = 'Data gridded to 0.25 degree grid with boxcar smoothing applied'

    filtered_ds.time.attrs = {'long_name': 'time', 'standard_name': 'time'}

    filtered_ds.latitude.attrs = {'long_name': 'latitude', 'standard_name': 'latitude'}
    filtered_ds.longitude.attrs = {'long_name': 'longitude', 'standard_name': 'longitude'}
    encoding = cycle_ds_encoding(filtered_ds)

    filtered_ds.to_netcdf(f'{OUTPUT_DIR}/ENSO_grids/{fname}', encoding=encoding)
    
def check_update(cycle_filename):
    '''
    Check if ENSO grid needs to be generated
    '''
    date = cycle_filename.split('_')[-1].split('.')[0]
    enso_filename = f'ssha_enso_{date}.nc'

    if not os.path.exists(f'{OUTPUT_DIR}/ENSO_grids/{enso_filename}'):
        return True

    cycle_mod_time = datetime.fromtimestamp(os.path.getmtime(f'{OUTPUT_DIR}/gridded_cycles/{cycle_filename}'))
    enso_mod_time = datetime.fromtimestamp(os.path.getmtime(f'{OUTPUT_DIR}/ENSO_grids/{enso_filename}'))

    if cycle_mod_time > enso_mod_time:
        return True
    return False
    
def enso_gridding():
    os.makedirs(f'{OUTPUT_DIR}/ENSO_grids/', exist_ok=True)
    os.chmod(f'{OUTPUT_DIR}/ENSO_grids/', 0o777)
    
    simple_grid_paths = glob(f'{OUTPUT_DIR}/gridded_cycles/*.nc')
    simple_grid_paths.sort()
    for f in simple_grid_paths:
        filename = f.split('/')[-1]
        if check_update(filename):
            print(f'Making ENSO grid for {filename}')
            ds = xr.open_dataset(f)
            make_grid(ds)
