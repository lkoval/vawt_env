from os import listdir
from os.path import isfile, join
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# class Polar:
#
#     def __init__(self):
#         pass
#
#     def load_from_directory(self, dir_path):
#         # make a list of all files in given directory
#         dir_path = '/home/aa/vawt_env/learn/AeroDyn polars/cp10'
#         files_list = [f for f in listdir(dir_path) if isfile(join(dir_path, f))]


# make a list of all files in given directory
dir_path = '/learn/AeroDyn polars/cp10_xfoil'
files_list = [f for f in listdir(dir_path) if isfile(join(dir_path, f))]
# print(files_list)

cl_df = pd.DataFrame()

# load each files as pandas DataFrame
# nedds to be xfoil type file
for file in files_list:
    # open file
    fh = open(dir_path + '/' + file, 'r')
    lines = fh.readlines()
    # get Reynolds number line
    line = lines[7]
    words = line.split()
    Re_base = words[5]
    Re_degree = words[7]
    Re_number = float(Re_base) * math.pow(10, int(Re_degree))
    # get pandas DataFrame
    columns_names = lines[9].split()[:5]
    data = [line.split()[:5] for line in lines[11:-2]]
    df = pd.DataFrame(data, columns=columns_names)
    # change columns datatypes
    df = df.astype({'alpha': float, 'CL': float})
    df.set_index(df['alpha'], inplace=True)
    if cl_df.empty:
        cl_df = pd.DataFrame(index=df['alpha'])
    cl_df[Re_number] = df['CL']
    # close
    fh.close()
cl_df = cl_df.reindex(sorted(cl_df.columns), axis=1)


fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

for i, model in enumerate(cl_df.columns):
    ax.plot(np.full(cl_df.index.size, i), cl_df.index.values, cl_df[model])

plt.xticks(np.arange(cl_df.columns.size), cl_df.columns.values, rotation=90)
plt.show()


