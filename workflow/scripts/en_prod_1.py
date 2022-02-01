# Import relevant packages
import matplotlib as mpl
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from openpyxl import Workbook
import xlsxwriter
import pandas.io.formats.excel
import glob
from pandas import ExcelWriter 
import seaborn as sns

# Path mapping to data folder
data_folder = '../../data'

# Results folder
results_folder = '../../results'

# Read in industry production sheets
industry_prod_sheets = list(pd.read_excel(data_folder + '/heavy_industry_production.xlsx', sheet_name = None).keys())

# Now read in the data from those sheets and save in a consolidated dataframe
ind_dfs_list = list()

for sheet in industry_prod_sheets:
    ind_dfs_list.append(pd.read_excel(data_folder + '/heavy_industry_production.xlsx', sheet_name = sheet))

ind_prod = pd.concat(ind_dfs_list).reset_index(drop = True)

# Now read in IEA data
# First, in order to quickly extract sheet names for the for loop below
IEA_temp = pd.ExcelFile(data_folder + '/IEA2021_link.xlsx')

IEA_dfs_list = list()

for sheet in IEA_temp.sheet_names[:-2]:
    interim_df = pd.read_excel(data_folder + '/IEA2021_link.xlsx', 
                               sheet_name = sheet, 
                               header = 1, 
                               na_values = ['', '..', '-', 'x'])
    interim_df['ECONOMY'] = sheet
    interim_df['UNIT'] = 'TJ'
    IEA_dfs_list.append(interim_df)

IEA_df = pd.concat(IEA_dfs_list).reset_index(drop = True)

# Now, reorder the datafram columns and only keep 1990 onwards
IEA_df = IEA_df[['ECONOMY', 'FLOW', 'PRODUCT', 'UNIT'] + list(IEA_df.loc[:, 1990:2020])].reset_index(drop = True)

# Clean up variable by removing spaces from the beginning of strings

IEA_df['FLOW'] = IEA_df['FLOW'].str.lstrip()
IEA_df['PRODUCT'] = IEA_df['PRODUCT'].str.lstrip()

# Change heading names to lower case
IEA_df = IEA_df.rename(columns = {'ECONOMY': 'economy', 
                                  'FLOW': 'flow', 
                                  'PRODUCT': 'product', 
                                  'UNIT': 'unit'})

# Now just grab industry data 

industry_selection = ['Iron and steel', 'Chemical and petrochemical', 'Non-ferrous metals', 'Non-metallic minerals']

IEA_industry = IEA_df[IEA_df['flow'].isin(industry_selection)].copy().reset_index(drop = True)

# Transform dataframe to long format

IEA_industry_long = IEA_industry.melt(id_vars = ['economy', 'flow', 'product', 'unit'], 
                                      var_name = 'year', 
                                      value_name = 'energy')

# IEA_industry_long.iloc[:, -1:] = IEA_industry_long.iloc[:, -1:].apply(pd.to_numeric, errors = 'coerce')

# Now get industry production in long format

ind_prod_long = ind_prod.melt(id_vars = ['economy', 'item', 'unit'], 
                              var_name = 'year', 
                              value_name = 'production')

economy_codes = ind_prod_long['economy'].unique()                              

# Define a new function that will add a column to ind_prod_long that can then be used to match to IEA_industry_long

def item_match(dataframe):
    if dataframe['item'] == 'steel_production':
        x = 'Iron and steel'
    
    elif dataframe['item'] == 'cement_production':
        x = 'Non-metallic minerals'

    else:
        pass

    return x

# Now create a new variable that is the same as that in IEA_industry_long (from above function)

ind_prod_long['flow'] = ind_prod_long.apply(item_match, axis = 1)

# Change year datatype in both production and energy data frames
ind_prod_long['year'] = pd.to_datetime(ind_prod_long['year'], format = '%Y').dt.year
IEA_industry_long['year'] = pd.to_datetime(IEA_industry_long['year'], format = '%Y').dt.year

# Create new dataframe with all relevant data for energy productivity
enprod_long = IEA_industry_long.merge(ind_prod_long, how = 'outer', on = ['economy', 'year', 'flow'])

enprod_long.rename(columns = {'unit_x': 'unit_energy', 
                              'unit_y': 'unit_production'}, inplace = True)

enprod_long = enprod_long[['economy', 'year', 'flow', 'product', 'unit_energy', 'energy', 'unit_production', 'production']]\
    .reset_index(drop = True)

# There are some alpha vairables in 'energy' column; change to float (coerce errors to NaN)
enprod_long['energy'] = pd.to_numeric(enprod_long['energy'], errors = 'coerce')
enprod_long['economy'] = enprod_long['economy'].astype('str')

# Replace zeroes in energy and production column with np.nan
zero_cols = ['energy', 'production']

enprod_long[zero_cols] = enprod_long[zero_cols].replace({0: np.nan})

# Now create energy productivity column
# Energy productivity is output/energy
# Which is the inverse of energy intensity: energy/output
# General improvements will see EP trend up while EI will trend down

enprod_long['energy_productivity'] = enprod_long['production'] / enprod_long['energy']
enprod_long['energy_intensity'] = enprod_long['energy'] / enprod_long['production']

# Charts

# overwrite
# economy_codes = ['01_AUS']

# Read in economy dictionary for charting

economy_dict = pd.read_csv(data_folder + '/economy_dict.csv', header = 0, index_col = 0)\
    .squeeze('columns').to_dict()

# APEC economies for analysis (economies defined above)

for economy in economy_codes:
    steel_df = enprod_long[(enprod_long['economy'] == economy) &
                           (enprod_long['product'] == 'Total') &
                           (enprod_long['flow'] == 'Iron and steel')].copy().reset_index(drop = True)

    plt.style.use('seaborn-whitegrid')

    # Grab economy name rather than code for charts 
    location = pd.Series(economy).map(economy_dict).index[0]
    economy_name = pd.Series(economy).map(economy_dict).loc[location]

    fig, axs = plt.subplots(3, 1, figsize = (8, 10))

    axs[0].plot('year', 'energy', data = steel_df)
    axs[1].plot('year', 'production', data = steel_df)
    axs[2].plot('year', 'energy_productivity', data = steel_df)

    # labels
    axs[0].set_title(economy_name + ' iron and steel energy consumption')
    axs[0].yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))
    axs[0].set_xlabel('Year')
    axs[0].set_ylabel('Energy consumption (TJ)')
    axs[0].margins(x = 0)
    axs[0].set_ylim(bottom = 0)

    axs[1].set_title(economy_name + ' steel production')
    axs[1].yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))
    axs[1].set_xlabel('Year')
    axs[1].set_ylabel('Steel production (thousand tonnes)')
    axs[1].margins(x = 0)
    axs[1].set_ylim(bottom = 0)

    axs[2].set_title(economy_name + ' steel energy productivity')
    axs[2].set_xlabel('Year')
    axs[2].margins(x = 0)
    axs[2].set_ylabel('Energy productivity')
    axs[2].set_ylim(bottom = 0)

    plt.tight_layout()

    plt.savefig(results_folder + '/steel/' + economy + '_steel.png', dpi = 600)