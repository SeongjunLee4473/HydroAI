import os
import sys
import platform
import importlib
from multiprocessing import Pool
import numpy as np
import netCDF4 as nc
from scipy.spatial import cKDTree
from tqdm import tqdm
import matplotlib.pyplot as plt

# Check the platform to set file paths
if platform.system() == 'Darwin':  # macOS
    base_FP = '/Users/hyunglokkim/Insync/hkim@geol.sc.edu/Google_Drive'
    cpuserver_data_FP = '/Users/hyunglokkim/cpuserver_data'
else:
    base_FP = '/data'
    cpuserver_data_FP = '/data'

# Add Python modules path and import
sys.path.append(base_FP + '/python_modules')
import HydroAI.Grid as hGrid
import HydroAI.Data as hData
importlib.reload(hGrid)

def process_files(file_names, ref_points, data_shape):
    local_data_count = np.zeros(data_shape, dtype=int)
    tree = cKDTree(ref_points)
    
    for file_name in tqdm(file_names, desc="Processing Files", leave=False):
        dataset = nc.Dataset(file_name)
        sp_lat = dataset.variables['sp_lat'][:].flatten().compressed()
        sp_lon = dataset.variables['sp_lon'][:].flatten().compressed() - 180
        sat_points = np.column_stack((sp_lat, sp_lon))
        _, indices = tree.query(sat_points)
        rows, cols = np.unravel_index(indices, data_shape)
        np.add.at(local_data_count, (rows, cols), 1)
    
    return local_data_count

def main():
    base_dir = cpuserver_data_FP+"/CYGNSS/L1_V21"
    nc_file_list = hData.get_file_list(base_dir, 'nc4')
    #nc_file_list = nc_file_list[:5000]
    resol = '3km'
    ref_lon, ref_lat = hGrid.generate_lat_lon_e2grid(resol)
    
    data_shape = ref_lat.shape
    ref_points = np.column_stack((ref_lat.flatten(), ref_lon.flatten()))

    num_processes = 180
    chunk_size = len(nc_file_list) // num_processes + (len(nc_file_list) % num_processes > 0)
    
    pool = Pool(processes=num_processes)
    results = pool.starmap(process_files, [(nc_file_list[i:i + chunk_size], ref_points, data_shape) for i in range(0, len(nc_file_list), chunk_size)])
    pool.close()
    pool.join()
    
    # Aggregate results
    final_data_count = np.sum(results, axis=0)

    # Save to CSV
    save_path = "./CYGNSS_data_count_"+resol+".csv"  # Specify your path and filename
    np.savetxt(save_path, final_data_count, delimiter=',')    

    # Plotting the results
    plt.figure(figsize=(10, 6))
    im = plt.imshow(final_data_count, cmap='viridis')
    plt.colorbar(im)
    plt.title("Visualization of Data Count")
    plt.xlabel("Longitude Index")
    plt.ylabel("Latitude Index")
    plt.show()

    print("Processing complete. Data count shape:", final_data_count.shape)

if __name__ == '__main__':
    main()

