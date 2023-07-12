import warnings
from datetime import datetime
from glob import glob

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
import numpy as np
import xarray as xr
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER
from conf.global_settings import OUTPUT_DIR
from matplotlib import colors
from matplotlib import pyplot as plt

warnings.filterwarnings('ignore')


def make_akiko_cmap() -> colors.ListedColormap:
    '''
    Converts colorscale txt file to mpl 
    '''
    values = []
    with open('ref_files/akiko_colorscale.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            vals = line.split()
            row = [float(v)/256 for v in vals]
            row.append(1)
            values.append(row)
    return colors.ListedColormap(values, name='akiko_cmap')

akiko_cmap = make_akiko_cmap()

def date_sat_map(date: datetime.date) -> str:
    '''
    TOPEX/Poseidon -> Jason-1:  			14 May 2002
    Jason-1 -> Jason-2:						12 Jul 2008
    Jason-2 -> Jason-3:						18 Mar 2016
    Jason-3 -> Sentinel-6 Michael Freilich:	07 Apr 2022
    '''
    topex = (date(1992,1,1), date(2002,5,14))
    j1 = (date(2002,5,14), date(2008,7,12))
    j2 = (date(2008,7,12), date(2016,3,18))
    j3 = (date(2016,3,18), date(2022,4,7))
    s6 = (date(2022,4,7), date.today())
    
    if date >= topex[0] and date < topex[1]:
        return 'TOPEX/Poseidon'
    if date >= j1[0] and date < j1[1]:
        return 'Jason-1'
    if date >= j2[0] and date < j2[1]:
        return 'Jason-2'
    if date >= j3[0] and date < j3[1]:
        return 'Jason-3'
    if date >= s6[0] and date < s6[1]:
        return 'Sentinel-6 Michael Freilich'

def plot_orth(enso_ds, date, satellite, vmin=-180, vmax=180):
    date_str = datetime.strftime(date, '%b %d %Y').upper()
    fig = plt.figure(figsize=(10,10))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Orthographic(-150, 10))
    
    ax.pcolormesh(enso_ds.longitude, enso_ds.latitude, enso_ds.SSHA, transform=ccrs.PlateCarree(), vmin=vmin, vmax=vmax, cmap=akiko_cmap, shading='nearest')
    ax.add_feature(cfeature.OCEAN, facecolor='lightgrey')
    ax.add_feature(cfeature.LAND, facecolor='dimgrey', zorder=10)
    ax.coastlines(zorder=11)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), linewidth=2, color='black', alpha=0.75,zorder=12)
    
    gl.xlocator = mticker.FixedLocator([])
    gl.ylocator = mticker.FixedLocator([0])
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    fig.set_facecolor('black')
    
    fig.text(-.1, 1.02, date_str, color='white', ha='left', va='top', size=20, transform=ax.transAxes)
    if satellite == 'Sentinel-6 Michael Freilich':
        fig.text(1.1, 1.02, satellite.split(' ')[0], color='white', ha='right', va='top', 
                 size=20, transform=ax.transAxes, wrap=True)
        fig.text(1.1, 0.98, satellite.split('Sentinel-6 ')[-1], color='white', ha='right', va='top', 
                 size=20, transform=ax.transAxes, wrap=True)
    else:
        fig.text(1.1, 1.02, satellite, color='white', ha='right', va='top', size=20, 
                 transform=ax.transAxes, wrap=True)

    outpath = f'{OUTPUT_DIR}/ENSO_maps/ENSO_ortho/ENSO_ortho_{str(date).replace("-","")}.png'
    plt.savefig(outpath, bbox_inches='tight', pad_inches=0.5)

def plot_plate(enso_ds, date, satellite, vmin=-180, vmax=180):
    date_str = datetime.strftime(date, '%b %d %Y').upper()

    fig = plt.figure(figsize=(20,8))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree(-180))
    
    g = plt.pcolormesh(enso_ds.longitude, enso_ds.latitude, enso_ds.SSHA, transform=ccrs.PlateCarree(), 
                       vmin=vmin, vmax=vmax, cmap=akiko_cmap)
    
    ax.add_feature(cfeature.OCEAN, facecolor='lightgrey')
    ax.add_feature(cfeature.LAND, facecolor='dimgrey', zorder=10)
    ax.coastlines(zorder=11)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True, linewidth=1, color='gray', alpha=.5, linestyle='--', zorder=15)
    
    gl.xlabels_top = False
    gl.ylabels_right = False
    gl.xlocator = mticker.FixedLocator([40, 80, 120, 160, -160, -120, -80, -40])
    ax.xaxis.set_major_formatter(LONGITUDE_FORMATTER)
    ax.xaxis.set_minor_formatter(LONGITUDE_FORMATTER)
    gl.xlabel_style = {'size': 14}
    gl.ylabel_style = {'size': 14}

    plt.title(f'{satellite} Sea Level Residuals {date_str}', size=16)
    cb = plt.colorbar(g, orientation="horizontal", shrink=0.5, aspect=30, pad=0.1)
    cb.set_label('MM', fontsize=14)
    cb.ax.tick_params(labelsize=12) 
    fig.tight_layout()

    outpath = f'{OUTPUT_DIR}/ENSO_maps/ENSO_plate/ENSO_plate_{str(date).replace("-","")}.png'
    plt.savefig(outpath, bbox_inches='tight', pad_inches=0.5)

def plot_orth_enso(enso_ds, date, vmin=-180, vmax=180):
    date_str = datetime.strftime(date, '%d %b %Y')
    fig = plt.figure(figsize=(14,10))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Orthographic(-150, 10))
    ax.pcolormesh(enso_ds.longitude, enso_ds.latitude, enso_ds.SSHA, transform=ccrs.PlateCarree(), vmin=vmin, vmax=vmax, cmap=my_cmap, shading='nearest')
    ax.add_feature(cfeature.OCEAN, facecolor='lightgrey')
    ax.add_feature(cfeature.LAND, facecolor='dimgrey', zorder=10)
    ax.coastlines(zorder=11)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), linewidth=2, color='black', alpha=0.75,zorder=12)
    gl.xlocator = mticker.FixedLocator([])
    gl.ylocator = mticker.FixedLocator([0])
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    fig.set_facecolor('black')
    fig.text(.6375, 1, date_str, color='white', ha='right', va='bottom', transform=ax.transAxes, fontname='Arial', fontsize=52)
    
    ax.set_ylim(-3000000,2000000)
    fig.tight_layout()

    outpath = f'{OUTPUT_DIR}/ENSO_maps/ENSO_ortho_zoom/ENSO_ortho_zoom{str(date).replace("-","")}.png'
    plt.savefig(outpath, bbox_inches='tight', pad_inches=.75)


def indicator_plots():
    vars = ['enso_index', 'pdo_index', 'iod_index', 'spatial_mean']
    ds = xr.open_dataset(f'{OUTPUT_DIR}/indicator/indicators.nc')
    end_time = ds.time.values[-1]
    start_time = end_time - np.timedelta64(365*5, 'D')
    pdo_start_time = end_time - np.timedelta64(365*10, 'D')
    spatial_start_time = end_time - np.timedelta64(365*7, 'D')

    slice_start = None

    output_path = f'{OUTPUT_DIR}/indicator/plots'
    output_path.mkdir(parents=True, exist_ok=True)

    for var in vars:

        if 'pdo' in var:
            var_ds = ds[var].sel(time=slice(pdo_start_time, end_time))
            delta = np.timedelta64(120, 'D')
        elif 'spatial' in var:
            var_ds = ds[var].sel(time=slice(spatial_start_time, end_time))
            delta = np.timedelta64(90, 'D')
        else:
            var_ds = ds[var].sel(time=slice(start_time, end_time))
            delta = np.timedelta64(60, 'D')

        plt.rcParams.update({'font.size': 16})
        plt.figure(figsize=(10, 5))

        if 'spatial_mean' not in var:
            plt.hlines(
                y=0, xmin=var_ds.time[0]-delta, xmax=var_ds.time[-1]+delta, color='black', linestyle='-')
            max_val = max(var_ds.values)
            plt.ylim(0-max_val-.25, max_val+.25)
            plt.xlim(var_ds.time[0]-delta, var_ds.time[-1]+delta)
        else:
            var_ds = var_ds * 100
            plt.ylabel('cm')

        plt.plot(var_ds.time, var_ds, label='Indicator', linewidth=3)

        if slice_start:
            var_slice_ds = ds[var].sel(time=slice(slice_start, end_time))

            if 'spatial_mean' in var:
                var_slice_ds = var_slice_ds * 100

            plt.plot(var_slice_ds.time, var_slice_ds,
                     label='New Indicator Data', linewidth=3)

        plt.grid()
        plt.title(var)
        plt.legend()
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        plt.savefig(f'{output_path}/{var}.png', dpi=150)
        plt.cla()


def enso_maps():
    enso_grid_paths = glob(f'{OUTPUT_DIR}/ENSO_grids/*.nc')
    enso_grid_paths.sort()
    
    for f in enso_grid_paths:
        file_name = f.split('/')[-1]
        ds = xr.open_dataset(f)
        date_dt = datetime.strptime(str(ds.time.values)[:10], '%Y-%m-%d').date()
        print(date_dt)
        satellite = date_sat_map(date_dt)
        
        plot_orth(ds, date_dt, satellite)
        plot_plate(ds, date_dt, satellite)
        plot_orth_enso(ds, date_dt, -130, 130)