from glob import glob
import logging
import os
import warnings
from datetime import datetime
from shutil import copyfile

import numpy as np
import xarray as xr
from netCDF4 import default_fillvals # type: ignore
from conf.global_settings import OUTPUT_DIR

with warnings.catch_warnings():
    warnings.simplefilter('ignore', UserWarning)
    import pyresample as pr
    from pyresample.utils import check_and_wrap



def validate_counts(ds, threshold=0.9):
    '''
    Checks if counts average is above threshold value.
    '''
    counts = ds.sel(latitude=slice(-66, 66))['counts'].values
    mean = np.nanmean(counts)

    if mean > threshold * 500:
        return True

    return False


def calc_linear_trend(cycle_ds):
    trend_ds = xr.open_dataset('ref_files/BH_offset_and_trend_v0_new_grid.nc')

    cycle_time = cycle_ds.time.values.astype('datetime64[D]')

    time_diff = (cycle_time - np.datetime64('1992-10-02')).astype(np.int32) * 86400
    trend = time_diff * trend_ds['BH_sea_level_trend_meters_per_second'] + trend_ds['BH_sea_level_offset_meters']

    return trend


def calc_spatial_mean(global_dam, ecco_latlon_grid, ct):
    global_dam_slice = global_dam.sel(latitude=slice(-66, 66))
    ecco_latlon_grid_slice = ecco_latlon_grid.sel(latitude=slice(-66, 66))

    nzp = np.where(~np.isnan(global_dam_slice), 1, np.nan)
    area_nzp = np.sum(nzp * ecco_latlon_grid_slice.area)

    spatial_mean = float(np.nansum(global_dam_slice * ecco_latlon_grid_slice.area) / area_nzp)

    spatial_mean_da = xr.DataArray(spatial_mean, coords={'time': ct}, attrs=global_dam.attrs)

    spatial_mean_da.name = 'spatial_mean'
    spatial_mean_da.attrs['comment'] = 'Global SSHA spatial mean'
    return spatial_mean_da


def calc_climate_index(agg_ds, pattern, pattern_ds, ann_cyc_in_pattern):
    """

    Params:
        agg_ds (Dataset): the aggregated cycle Dataset object
        pattern (str): the name of the pattern
        pattern_ds (Dataset): the actual pattern object
        ann_cyc_in_pattern (Dict):
        weights_dir (Path): the Path to the directory containing the stored pattern weights
    Returns:
        LS_result (List[float]):
        center_time (Datetime):
    """

    center_time = agg_ds.time.values

    # determine its month
    agg_ds_center_mon = int(str(center_time)[5:7])

    pattern_field = pattern_ds[pattern][f'{pattern}_pattern'].values

    ssha_da = agg_ds[f'SSHA_{pattern}_removed_global_linear_trend']

    # remove the monthly mean pattern from the gridded ssha
    # now ssha_anom is w.r.t. seasonal cycle and MDT
    ssha_anom = ssha_da.values - ann_cyc_in_pattern[pattern].ann_pattern.sel(month=agg_ds_center_mon).values/1e3

    # set ssha_anom to nan wherever the original pattern is nan
    ssha_anom = np.where(~np.isnan(pattern_ds[pattern][f'{pattern}_pattern']), ssha_anom, np.nan)

    # extract out all non-nan values of ssha_anom, these are going to
    # be the points that we fit
    nonnans = ~np.isnan(ssha_anom)
    ssha_anom_to_fit = ssha_anom[nonnans]

    # do the same for the pattern
    pattern_to_fit = pattern_field[nonnans]/1e3

    # just for fun extract out same points from ssha, we'll see if
    # removing the monthly climatology makes much of a difference
    ssha_to_fit = ssha_da.copy(deep=True)
    ssha_to_fit = ssha_da.values[nonnans]

    X = np.vstack(np.array(pattern_to_fit))

    # Good old Gauss
    B_hat = np.matmul(np.matmul(np.linalg.inv(np.matmul(X.T, X)), X.T), ssha_anom_to_fit.T)
    offset = 0
    index = B_hat[0]

    # now minimize ssha_to_fit
    B_hat = np.matmul(np.matmul(np.linalg.inv(np.matmul(X.T, X)), X.T), ssha_to_fit.T)
    offset_b = 0
    index_b = B_hat[0]

    LS_result = [offset, index, offset_b, index_b]

    lats = ssha_da.latitude.values
    lons = ssha_da.longitude.values

    ssha_anom = xr.DataArray(ssha_anom, dims=['latitude', 'longitude'],
                             coords={'longitude': lons,
                                     'latitude': lats})

    return LS_result, center_time, ssha_anom


def save_files(date, indicator_ds, globals_ds, pattern_and_anom_das):
    ds_and_paths = []

    fp_date = date.replace('-', '_')
    cycle_indicators_path = f'{OUTPUT_DIR}/indicator/daily/cycle_indicators'
    os.makedirs(cycle_indicators_path, exist_ok=True)
    os.chmod(cycle_indicators_path, 0o777)
    
    indicator_output_path = f'{cycle_indicators_path}/{fp_date}_indicator.nc'
    ds_and_paths.append((indicator_ds, indicator_output_path))

    cycle_globals_path = f'{OUTPUT_DIR}/indicator/daily/cycle_globals'
    os.makedirs(cycle_globals_path, exist_ok=True)
    os.chmod(cycle_globals_path, 0o777)
    
    global_output_path = f'{cycle_globals_path}/{fp_date}_globals.nc'
    ds_and_paths.append((globals_ds, global_output_path))

    for pattern in pattern_and_anom_das.keys():
        pattern_anom_ds = pattern_and_anom_das[pattern]
        pattern_anom_ds = pattern_anom_ds.expand_dims(time=[pattern_anom_ds.time.values])

        os.makedirs(f'{OUTPUT_DIR}/indicator/daily/cycle_pattern_anoms/', exist_ok=True)
        os.chmod(cycle_pattern_anoms_path, 0o777)

        cycle_pattern_anoms_path = f'{OUTPUT_DIR}/indicator/daily/cycle_pattern_anoms/{pattern}'
        os.makedirs(cycle_pattern_anoms_path, exist_ok=True)
        os.chmod(cycle_pattern_anoms_path, 0o777)
        
        pattern_anoms_output_path = f'{cycle_pattern_anoms_path}/{fp_date}_{pattern}_ssha_anoms.nc'
        ds_and_paths.append((pattern_anom_ds, pattern_anoms_output_path))

    encoding_each = {'zlib': True,
                     'complevel': 5,
                     'dtype': 'float32',
                     'shuffle': True,
                     '_FillValue': default_fillvals['f8']}

    for ds, path in ds_and_paths:

        coord_encoding = {}
        for coord in ds.coords:
            coord_encoding[coord] = {'_FillValue': None,
                                     'dtype': 'float32',
                                     'complevel': 6}

        var_encoding = {var: encoding_each for var in ds.data_vars}

        encoding = {**coord_encoding, **var_encoding}

        ds.to_netcdf(path, encoding=encoding)
        ds.close()

    return


def concat_files(indicator_dir, type, pattern=''):
    # Glob daily indicators
    daily_path = f'{indicator_dir}/daily/cycle_{type}s/{pattern}'
    daily_files = [x for x in glob(f'{daily_path}/*.nc') if os.path.isfile(x)]
    daily_files.sort()

    files = daily_files

    if pattern:
        print(f' - Reading {pattern} files')
    else:
        print(f' - Reading {type} files')

    all_ds = []
    for c in files:
        all_ds.append(xr.open_dataset(c))

    print(f' - Concatenating {type} files')
    concat_ds = xr.concat(all_ds, dim='time')
    all_ds = []

    return concat_ds


def indicators():
    """
    This function calculates indicator values for each regridded cycle. Those are
    saved locally to avoid overloading memory. All locally saved indicator files 
    are combined into a single netcdf spanning the entire 1992 - NOW time period.
    """
    # Get all gridded cycles
    grids = glob(f'{OUTPUT_DIR}/gridded_cycles/*.nc')
    grids.sort()

    update = False

    os.makedirs(f'{OUTPUT_DIR}/indicator/', exist_ok=True)
    os.chmod(f'{OUTPUT_DIR}/indicator/', 0o777)

    # Check if we need to recalculate indicators
    data_path = f'{OUTPUT_DIR}/indicator/indicators.nc'
    if os.path.exists(data_path):
        ind_mod_time = datetime.fromtimestamp(os.path.getmtime(data_path))
        for grid in grids:
            grid_mod_time = datetime.fromtimestamp(os.path.getmtime(grid))

            if grid_mod_time >= ind_mod_time:
                update = True

                backup_dir = f'{OUTPUT_DIR}/indicator/backups'
                os.makedirs(backup_dir, exist_ok=True)
                os.chmod(backup_dir, 0o777)

                # Copy old indicator file as backup
                try:
                    print('Making backup of existing indicator file.\n')
                    backup_path = f'{backup_dir}/indicator_{ind_mod_time}.nc'
                    copyfile(data_path, backup_path)
                except Exception as e:
                    logging.exception(f'Error creating indicator backup: {e}')
                break
    else:
        update = True
    
    # ONLY PROCEED IF THERE ARE CYCLES NEEDING CALCULATING
    if not update:
        logging.info('No regridded cycles modified since last index calculation.')
        return True

    logging.info('Calculating new index values for cycles.')

    # ==============================================
    # Pattern preparation
    # ==============================================

    patterns = ['enso', 'pdo', 'iod']

    pattern_ds = dict()
    pattern_geo_bnds = dict()
    ann_cyc_in_pattern = dict()
    pattern_area_defs = dict()

    # Global grid
    ecco_latlon_grid = xr.open_dataset('ref_files/GRID_GEOMETRY_ECCO_V4r4_latlon_0p50deg.nc')

    global_lon = ecco_latlon_grid.longitude.values
    global_lat = ecco_latlon_grid.latitude.values
    global_lon_m, global_lat_m = np.meshgrid(global_lon, global_lat)

    pattern_area_defs['global'] = pr.geometry.SwathDefinition(lons=global_lon_m,
                                                              lats=global_lat_m)

    # load the monthly global sla climatology
    ann_ds = xr.open_dataset('ref_files/ann_pattern.nc')

    # load patterns and select out the monthly climatology of sla variation
    # in each pattern
    for pattern in patterns:
        # load each pattern
        pattern_fname = f'{pattern}_pattern_and_index.nc'
        pattern_ds[pattern] = xr.open_dataset(f'ref_files/{pattern_fname}')

        # get the geographic bounds of each sla pattern
        pattern_geo_bnds[pattern] = [float(pattern_ds[pattern].Latitude[0].values),
                                     float(pattern_ds[pattern].Latitude[-1].values),
                                     float(pattern_ds[pattern].Longitude[0].values),
                                     float(pattern_ds[pattern].Longitude[-1].values)]

        # extract the sla annual cycle in the region of each pattern
        ann_cyc_in_pattern[pattern] = ann_ds.sel(Latitude=slice(pattern_geo_bnds[pattern][0],
                                                                pattern_geo_bnds[pattern][1]),
                                                 Longitude=slice(pattern_geo_bnds[pattern][2],
                                                                 pattern_geo_bnds[pattern][3]))

        # Individual Patterns
        lon_m, lat_m = np.meshgrid(pattern_ds[pattern].Longitude.values,
                                   pattern_ds[pattern].Latitude.values)
        tmp_lon, tmp_lat = check_and_wrap(lon_m, lat_m)
        pattern_area_defs[pattern] = pr.geometry.SwathDefinition(lons=tmp_lon,
                                                                 lats=tmp_lat)

    # ==============================================
    # Calculate indicators for each updated (re)gridded cycle
    # ==============================================

    os.makedirs(f'{OUTPUT_DIR}/indicator/daily', exist_ok=True)
    os.chmod(f'{OUTPUT_DIR}/indicator/daily', 0o777)

    for cycle in grids:

        try:
            cycle_ds = xr.open_dataset(cycle)
            cycle_ds.close()

            date = cycle.split('_')[-1][:8]
            date = f'{date[:4]}-{date[4:6]}-{date[6:8]}'

            # Skip this grid if it's missing too much data
            if not validate_counts(cycle_ds):
                logging.exception(f'Too much data missing from {date} cycle. Skipping.')
                continue

            print(f' - Calculating index values for {date}')

            ct = np.datetime64(date)

            # Area mask the cycle data
            global_dam = cycle_ds.where(
                ecco_latlon_grid.maskC.isel(Z=0) > 0)['SSHA']
            global_dam = global_dam.where(global_dam)

            global_dam.name = 'SSHA_GLOBAL'
            global_dam.attrs['comment'] = 'Global SSHA land masked'
            global_dsm = global_dam.to_dataset()

            # Spatial Mean
            mean_da = calc_spatial_mean(global_dam, ecco_latlon_grid, ct)

            global_dam_removed_mean = global_dam - mean_da.values
            global_dam_removed_mean.attrs['comment'] = 'Global SSHA with global spatial mean removed'
            global_dsm['SSHA_GLOBAL_removed_global_spatial_mean'] = global_dam_removed_mean

            # Linear Trend
            trend = calc_linear_trend(cycle_ds)
            global_dsm['SSHA_GLOBAL_linear_trend'] = trend

            global_dam_detrended = global_dam - trend
            global_dam_detrended.attrs['comment'] = 'Global SSHA with linear trend removed'
            global_dsm['SSHA_GLOBAL_removed_linear_trend'] = global_dam_detrended

            if 'Z' in global_dsm.data_vars:
                global_dsm = global_dsm.drop_vars('Z')

            pattern_and_anom_das = {}

            all_indicators = []

            # Do the actual index calculation per pattern
            for pattern in patterns:
                pattern_lats = pattern_ds[pattern]['Latitude']
                pattern_lats = pattern_lats.rename({'Latitude': 'latitude'})
                pattern_lons = pattern_ds[pattern]['Longitude']
                pattern_lons = pattern_lons.rename({'Longitude': 'longitude'})
                pattern_lons, pattern_lats = check_and_wrap(pattern_lons, pattern_lats)

                agg_da = global_dsm['SSHA_GLOBAL_removed_linear_trend'].sel(longitude=pattern_lons, 
                                                                            latitude=pattern_lats)
                agg_da.name = f'SSHA_{pattern}_removed_global_linear_trend'

                agg_ds = agg_da.to_dataset()
                agg_ds.attrs = cycle_ds.attrs

                index_calc, ct, ssha_anom = calc_climate_index(agg_ds, pattern,
                                                            pattern_ds, ann_cyc_in_pattern)

                anom_name = f'SSHA_{pattern}_removed_global_linear_trend_and_seasonal_cycle'
                ssha_anom.name = anom_name

                agg_ds[anom_name] = ssha_anom

                # Handle patterns and anoms
                pattern_and_anom_das[pattern] = agg_ds

                # Handle indicators and offsets
                indicator_da = xr.DataArray(index_calc[1], coords={'time': ct})
                indicator_da.name = f'{pattern}_index'
                all_indicators.append(indicator_da)

                offsets_da = xr.DataArray(index_calc[0], coords={'time': ct})
                offsets_da.name = f'{pattern}_offset'
                all_indicators.append(offsets_da)

            # Merge pattern indicators, offsets, and global spatial mean
            all_indicators.append(mean_da)
            indicator_ds = xr.merge(all_indicators)
            indicator_ds = indicator_ds.expand_dims(time=[indicator_ds.time.values])

            globals_ds = global_dsm
            globals_ds = globals_ds.expand_dims(time=[globals_ds.time.values])

            # Save indicators ds, global ds, and individual pattern ds for this one cycle
            save_files(date, indicator_ds, globals_ds, pattern_and_anom_das)

        except Exception as e:
            logging.exception(e)

    print('\nCycle index calculation complete. ')
    print('Merging and saving final indicator products.\n')

    # ==============================================
    # Combine daily indicator files
    # ==============================================

    try:
        indicator_dir = f'{OUTPUT_DIR}/indicator'

        # open_mfdataset is too slow so we glob instead
        indicators = concat_files(indicator_dir, 'indicator')
        print(' - Saving indicator file\n')
        indicators.to_netcdf(f'{indicator_dir}/indicators.nc')

        for pattern in patterns:
            pattern_anoms = concat_files(
                indicator_dir, 'pattern_anom', pattern)
            print(f' - Saving {pattern} anom file\n')
            pattern_anoms.to_netcdf(f'{indicator_dir}/{pattern}_anoms.nc')
            pattern_anoms = None

        globals_ds = concat_files(indicator_dir, 'global')
        print(' - Saving global file\n')
        globals_ds.to_netcdf(f'{indicator_dir}/globals.nc')
        globals_ds = None

    except Exception as e:
        logging.exception(e)
        return False

    return True