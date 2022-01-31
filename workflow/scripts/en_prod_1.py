# Import relevant packages
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

economies = ind_prod_long['economy'].unique()                              

# Define a new function that will add a column to ind_prod_long that can then be used to match to IEA_industry_long

def item_match(dataframe):
    if dataframe['item'] == 'steel_production':
        x = 'Iron and steel'
    
    elif dataframe['item'] == 'cement_production':
        x = 'Non-metallic minerals'

    else:
        pass

    return x

ind_prod_long['flow'] = ind_prod_long.apply(item_match, axis = 1)

enprod_long = IEA_industry_long.merge(ind_prod_long, how = 'left', on = ['economy', 'year', 'flow'])

enprod_long.rename(columns = {'unit_x': 'unit_energy', 
                              'unit_y': 'unit_production'}, inplace = True)

enprod_long = enprod_long[['economy', 'year', 'flow', 'product', 'unit_energy', 'energy', 'unit_production', 'production']]



# Charts

Aus_steel = ind_prod_long[(ind_prod_long['economy'] == '01_AUS') & (ind_prod_long['item'] == 'steel_production')]
Aus_cement = ind_prod_long[(ind_prod_long['economy'] == '01_AUS') & (ind_prod_long['item'] == 'cement_production')]
# Now make some plots of production

fig, [ax1, ax2] = plt.subplots(2, 1, figsize = (8,5))
 
ax1.plot('year', 'production', data = Aus_steel)
ax2.plot('year', 'production', data = Aus_cement)

plt.show()