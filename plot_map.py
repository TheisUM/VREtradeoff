#%% -- import packages and files
import pandas as pd
import numpy as np
from Functions import gdx_to_dict
from Functions import distance
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as clr
import plotly.graph_objects as go
from Dictionaries import fuel_colors
from Dictionaries import fuel_labels
from Dictionaries import area_to_region
from Dictionaries import region_to_country
from Dictionaries import df_color_tech
from Dictionaries import country_to_region
from Dictionaries import fuel_potential_high
from Dictionaries import fuel_potential_low
from Dictionaries import VRE_potential_high
from Dictionaries import VRE_potential_low
from Dictionaries import VRE_potential_high_noOffshore
from Dictionaries import VRE_potential_low_noOffshore
import geopandas as gpd
import cartopy.crs as ccrs
from pybalmorel import MainResults
import seaborn as sns
from geopy.geocoders import Nominatim

# Load data
scenarios = ['HHM','HLM','LHM','LLM']
symbolBal = ['G_CAP_YCRAF','CC_YCRAG','F_CONS_YCRA','OBJ_YCR','X_CAP_YCR','XH2_CAP_YCR','PRO_YCRAGF','XH2_FLOW_YCR','X_FLOW_YCR']
symbolOpti = ['VFLOWSOURCE_Opti_C','VFLOWTRANS_Opti_C','VFLOW_Opti_C','VFLOWCCU_C','VFLOW_Opti_A']

gams_directory = 'C:\\GAMS\\46'
file_path = 'C:\\Users\\tmad\\GitHub\\pap1-code\\Files'

GDXs = gdx_to_dict(symbolBal,symbolOpti,scenarios,gams_directory,file_path)

#%% -- add settings

scenario = 'LLM'
labels = {"HH":"i)","HL":"ii)","LH":"iii)","LL":"iv)"}
number = labels[scenario[:2]]
year = '2050'
map_path = 'C:\\Users\\tmad\\GitHub\\pap1-code\\map\\2022 BalmorelMap.geojson'

#%% -- prepare data

df_VFLOW = GDXs['VFLOW_Opti_A']
df_VFLOW.rename(columns={'level_0':'Year','level_1':'Area','level_2':'From','level_3':'To','level_4':'Flow'},inplace=True)
df_VFLOW['Area'] = df_VFLOW['Area'].map(area_to_region)
df_XH2cap = GDXs['XH2_CAP_YCR']
df_XH2cap.rename(columns={'level_0':'Year','level_1':'Country','level_2':'Region_Exp','level_3':'Region_Imp','level_4':'Unit'},inplace=True)
df_XH2flow = GDXs['XH2_FLOW_YCR']
df_XH2flow.rename(columns={'level_0':'Year','level_1':'Country','level_2':'Region_Exp','level_3':'Region_Imp','level_4':'Unit'},inplace=True)
df_FCON = GDXs['F_CONS_YCRA']
df_FCON.rename(columns={'level_0':'Year','level_1':'Country','level_2':'Region','level_3':'Area','level_4':'Generator','level_5':'Fuel','level_6':'Technology','level_7':'Unit'},inplace=True)
df_PROD = GDXs['PRO_YCRAGF']
df_PROD.rename(columns={'level_0':'Year','level_1':'Country','level_2':'Region','level_3':'Area','level_4':'Generator','level_5':'Fuel','level_6':'Commodity','level_7':'Technology','level_8':'Unit'},inplace=True)
df_CAP = GDXs['G_CAP_YCRAF']
df_CAP.rename(columns={'level_0':'Year','level_1':'Country','level_2':'Region','level_3':'Area','level_4':'Generator','level_5':'Fuel','level_6':'Commodity','level_7':'Technology','level_8':'Variable','level_9':'Unit'},inplace=True)
#%% -- reduce data
# Narrow down dataframes
fuels_production = df_VFLOW[(df_VFLOW['Year'] == year) & (df_VFLOW['To'].str.contains('_Eff')) & (df_VFLOW['Scenario'] == scenario) & (~df_VFLOW['From'].str.contains('Exim'))]
bfset = ['BIOJETFLOW','BIOGASOLINEFLOW','METHANOLFLOW']
emetset = ['EMETHANOLFLOW']
ammset = ['AMMONIA_FLOW']
emupgrset = ['EME_GASOLINEFLOW','EME_JETFLOW','EME_LPGFLOW']
fuels_production['Flow'] = fuels_production['Flow'].apply(lambda x: 'Bio FT' if x in bfset else ('E-ammonia' if x in ammset else ('E-Methanol' if x in emetset else 'Methanol upg.')))
fuels_production_agg = fuels_production.groupby(['Area','Flow'])['Value'].sum().unstack() / 3.6 # TWh
fuels_production_agg.fillna(0,inplace=True)
fuels_production_agg.reset_index(inplace=True)
hydrogen_links = df_XH2cap[(df_XH2cap['Year'] == year) & (df_XH2cap['Scenario'] == scenario)]
coordinates = pd.read_csv('C:\\Users\\tmad\\GitHub\\pap1-code\\data\\coordinates_RRR.csv')

hydrogen_trade = df_XH2flow[(df_XH2flow['Year'] == year) & (df_XH2flow['Scenario'] == scenario)]
hydrogen_export = hydrogen_trade.groupby(['Scenario','Region_Exp'])['Value'].sum().unstack()
hydrogen_import = hydrogen_trade.groupby(['Scenario','Region_Imp'])['Value'].sum().unstack()
hydrogen_export.rename(columns={'Region_Exp': 'Region'}, inplace=True)
hydrogen_import.rename(columns={'Region_Imp': 'Region'}, inplace=True)
hydrogen_export.fillna(0, inplace=True)
hydrogen_import.fillna(0, inplace=True)
hydrogen_export.columns.name = 'Region'
hydrogen_import.columns.name = 'Region'
hydrogen_export, hydrogen_import = hydrogen_export.align(hydrogen_import, fill_value=0)
hydrogen_netexport = hydrogen_export - hydrogen_import # TWh
hydrogen_netexport = hydrogen_netexport.transpose()
hydrogen_netexport.rename(columns={scenario: 'Values'}, inplace=True)
hydrogen_netexport = hydrogen_netexport.reset_index()


biomasses = ["STRAW","WOODCHIPS"]
fuel_consumption = df_FCON[(df_FCON['Year'] == year) & (df_FCON['Scenario'] == scenario) & (df_FCON['Fuel'].isin(biomasses))]
fuel_consumption = fuel_consumption.groupby('Country')['Value'].sum() * 3.6 * 1000000 # GJ
if scenario[0] == 'H':
    potential = fuel_potential_high
else:
    potential = fuel_potential_low
fuel_consumption = fuel_consumption / fuel_consumption.index.map(potential)

for country in fuel_consumption.index:
    if isinstance(country_to_region[country],str):
        fuel_consumption.rename(index={country: country_to_region[country]}, inplace=True)
    elif isinstance(country_to_region[country],list):
        for region in country_to_region[country]:
            fuel_consumption.loc[region] = fuel_consumption.loc[country]
        fuel_consumption.drop(index=country, inplace=True)

fuel_consumption_region = fuel_consumption.reset_index()
fuel_consumption_region.columns = ['Regions', 'Values']

electricity_production = df_PROD[(df_PROD['Year'] == year) & (df_PROD['Commodity'] == 'ELECTRICITY') & (df_PROD['Scenario'] == scenario)]
thermal = ['CONDENSING','CHP-EXTRACTION','CHP-BACK-PRESSURE']
hydro = ['HYDRO-RESERVOIRS','HYDRO-RUN-OF-RIVER']
#electricity_production.loc[electricity_production['Fuel'].str.contains('NUCLEAR'), 'Technology'] = 'NUCLEAR'
electricity_production['Technology'] = electricity_production['Technology'].apply(lambda x: 'THERMAL' if x in thermal else x)
electricity_production['Technology'] = electricity_production['Technology'].apply(lambda x: 'HYDRO' if x in hydro else x)
electricity_production = electricity_production.groupby(['Region','Technology'])['Value'].sum().unstack() # TWh
electricity_production.fillna(0, inplace=True)
electricity_production.drop(columns=['INTRASEASONAL-ELECT-STORAGE'], inplace=True, errors='ignore')
column_names = electricity_production.columns.tolist()
column_colors = [df_color_tech.get(tech, 'grey') for tech in column_names]
column_names = [name.capitalize() for name in column_names]
electricity_production.reset_index(inplace=True)

VRE = ['WIND-ON','WIND-OFF','SOLAR-PV']
capacity = df_CAP[(df_CAP['Year'] == year) & (df_CAP['Commodity'] == 'ELECTRICITY') & (df_CAP['Scenario'] == scenario) & (df_CAP['Technology'].isin(VRE))]
capacity = capacity.groupby('Region')['Value'].sum() # GW
capacity.fillna(0, inplace=True)
if scenario[1] == 'H':
    potential = capacity.index.map(VRE_potential_high) / 1000 # GW
else:
    potential = capacity.index.map(VRE_potential_low) / 1000 # GW
capacity_utilization = capacity / potential
capacity_utilization = capacity_utilization.reset_index()
capacity_utilization.columns = ['Regions', 'Values']

#%% -- prepare map
plt.rcParams["font.family"] = "serif"
europe_map = gpd.read_file(map_path)
europe_map_H2 = europe_map.merge(capacity_utilization, left_on='id', right_on='Regions', how='left')
#europe_map_H2 = europe_map.merge(hydrogen_netexport, left_on='id', right_on='Region', how='left')
eu0 = europe_map_H2
eu0 = eu0[eu0['Values'].isna()]
eu0['Values'].fillna(0, inplace=True)
# initialize geolocator
geolocator = Nominatim(user_agent="fuel_production_map")
# make the figure
fig = plt.figure(figsize=(8, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_xlim(-12,30)      
ax.set_ylim(36,72)
colmap = clr.LinearSegmentedColormap.from_list('custom greenes', ['lightyellow',(125/255, 159/255, 72/255,1)], N=256)
eu0.plot(ax=ax, legend=True, color='lightgrey', edgecolor='black', linewidth=0.25, transform=ccrs.PlateCarree())
europe_map_H2.plot(column='Values',ax=ax, cmap=colmap,legend=False, edgecolor='black', linewidth=0.5, transform=ccrs.PlateCarree(),vmax = 1, vmin = 0, legend_kwds={'shrink': 0.65,'label': 'TWh'})

ax.set_title(number, fontsize=12, loc='left')

# Plot hydrogen links
for i,row in hydrogen_links.iterrows():
    region_exp = row['Region_Exp']
    region_imp = row['Region_Imp']
    lat_exp = coordinates[coordinates['RRR'] == region_exp]['Lat'].values[0]
    lon_exp = coordinates[coordinates['RRR'] == region_exp]['Lon'].values[0]
    lat_imp = coordinates[coordinates['RRR'] == region_imp]['Lat'].values[0]
    lon_imp = coordinates[coordinates['RRR'] == region_imp]['Lon'].values[0]
    if region_exp == 'NL':
        lat_exp += 2
    if region_imp == 'NL':
        lat_imp += 2
    if region_exp == 'BE':
        lon_exp -= 1
    if region_imp == 'BE':
        lon_imp -= 1
    cap = row['Value']
    width = cap/2.5
    if width > 10:
        width = 10
    elif width < 0.4:
        width = 0.4
    else:
        width = width
    # size is defined for 25 GW or more, smallest for 1 GW or less
    ax.plot([lon_exp,lon_imp],[lat_exp,lat_imp],color='midnightblue',linewidth=width+1,transform=ccrs.PlateCarree(),zorder=1, solid_capstyle='round')
    ax.plot([lon_exp,lon_imp],[lat_exp,lat_imp],color='cornflowerblue',linewidth=width,transform=ccrs.PlateCarree(),zorder=1, solid_capstyle='round')
    

# loop over countries
#enumerate(df_prod['Country'].unique(), 1):
for i,row in fuels_production_agg.iterrows():
#for i,row in electricity_production.iterrows():    
    # Get country coordinates
    region = row['Area']
    #region = row['Region']
    lat = coordinates[coordinates['RRR'] == region]['Lat'].values[0]
    lon = coordinates[coordinates['RRR'] == region]['Lon'].values[0]
    if region == 'NL':
        lat += 2 
    if region == 'BE':
        lon -= 1
        
    # Country data
    region_production = fuels_production_agg[fuels_production_agg['Area'] == region]
    #region_production = electricity_production[electricity_production['Region'] == region]    
    bioft = row['Bio FT']
    emeth = row['E-Methanol']
    ammonia = row['E-ammonia']
    methupg = row['Methanol upg.']
    pie_values = [bioft,emeth,ammonia,methupg]
    #pie_values = region_production.iloc[0,1:]
    prod = (bioft + emeth + ammonia + methupg)
    #prod = pie_values.sum()
    size = prod/50 #(size bounds 2 and 0.2)
    if size > 2:
        size = 2
    elif 0 < size < 0.5:
        size = 0.5
    else:
        size = size
    #if prod >= 600:
    #    size = 2
    #elif 300 <= prod < 600:
    #    size = prod/250
    #elif 100 <= prod < 300:
    #    size = prod/200
    #else:
    #    size = 0.25
    
    # Largest size is defined for 100 TWh or more, smallest for 10 TWh or less
    #print(str(region) + ": " + str(round(prod,1)) + " -- size: " + str(round(size,2)))
    # Plot pie chart
    ax.pie(pie_values, startangle=90, radius=size, center=(lon,lat), frame=True, colors=['forestgreen','goldenrod','indianred','palegoldenrod'], wedgeprops=dict(edgecolor='black',linewidth=0.5))

# Add legend
legend_circle_1 = plt.Line2D([0], [0], marker='o', color='none', markerfacecolor='grey', markersize=2*15, label=' 100 TWh')
legend_circle_2 = plt.Line2D([0], [0], marker='o', color='none', markerfacecolor='grey', markersize=1.5*15, label='50 TWh')
#legend_circle_3 = plt.Line2D([0], [0], marker='o', color='none', markerfacecolor='grey', markersize=1*10, label='100 TWh')
legend_circle_4 = plt.Line2D([0], [0], marker='o', color='none', markerfacecolor='grey', markersize=0.2*15, label='10 TWh')
first_legend = ax.legend(handles=[legend_circle_1,legend_circle_2,legend_circle_4], loc='upper left',frameon=False ,labelspacing=.5,columnspacing=0.5,fontsize=11,bbox_to_anchor=(0.01, 0.98),ncol=4)
ax.add_artist(first_legend)
colors = ['forestgreen','goldenrod','indianred','palegoldenrod']
labels = ['Bio FT','E-Methanol','E-ammonia','Methanol upg.']
#labels = column_names
#colors = column_colors
legend_patches = [mpatches.Patch(color=color, label=label) for color, label in zip(colors, labels)]
second_legend = ax.legend(handles=legend_patches, loc='upper left',frameon=False ,labelspacing=.5,fontsize=11,bbox_to_anchor=(0.01, 0.9),ncol=2,columnspacing=0.5)
ax.add_artist(second_legend)
legend_line_1 = plt.Line2D([0], [0], color='cornflowerblue', label=' 25 GW',linewidth=8)
legend_line_2 = plt.Line2D([0], [0], color='cornflowerblue', label=' 10 GW',linewidth=4)
#legend_line_3 = plt.Line2D([0], [0], color='cornflowerblue', label='5 GW',linewidth=2)
legend_line_4 = plt.Line2D([0], [0], color='cornflowerblue', label='   1 GW',linewidth=1.1)
third_legend = ax.legend(handles=[legend_line_1,legend_line_2,legend_line_4], loc='upper left',frameon=False ,labelspacing=0.5,fontsize=11,bbox_to_anchor=(0.01, 0.8))
ax.add_artist(third_legend)

map_name = 'map' + scenario + year
plt.savefig('C:\\Users\\tmad\\OneDrive - Danmarks Tekniske Universitet\\11 BioLim PtX\\Figures\\' +  map_name + '.png', dpi=300, bbox_inches='tight')

plt.show()
# %% new colorbar

fig = plt.figure(figsize=(15, 0.25))
#cmap = plt.cm.Spectral
cmap = colmap
norm = plt.Normalize(vmin=0, vmax=1)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ticks=[0,.25,.50,.75,1], orientation='horizontal',cax=fig.add_axes([0.05, 0.05, 0.9, 0.9]))
cbar.ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
cbar.set_label('VRE utilization (%)', fontsize=12)

plt.savefig('C:\\Users\\tmad\\OneDrive - Danmarks Tekniske Universitet\\11 BioLim PtX\\Figures\\colorbar.png', dpi=300, bbox_inches='tight')
plt.show()
# %%
