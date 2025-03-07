
import gams
import pandas as pd
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from Dictionaries import fuel_colors
from Dictionaries import fuel_labels
from Dictionaries import area_to_region

def symbol_to_df(db, symbol, cols='None'):
    """
    Loads a symbol from a GDX database into a pandas dataframe

    Args:
        db (GamsDatabase): The loaded gdx file
        symbol (string): The wanted symbol in the gdx file
        cols (list): The columns
    """   
    df = dict( (tuple(rec.keys), rec.value) for rec in db[symbol] )
    df = pd.DataFrame(df, index=['Value']).T.reset_index() # Convert to dataframe
    if cols != 'None':
        try:
            df.columns = cols
        except:
            pass
    return df 

def gdx_to_dict(symbolBal,symbolOpti,scenarios,system_directory,file_path):
    """
    create dictionary of balmorel & optiflow parameters
    input:
    1) strings of parameters to read from Balmorel
    2) strings of parameters to read from OptiFlow
    3) strings of scenarios to read in the format ..MainResults_SCENARIO.gdx 
    output:
    1) a dictionary of dataframes for the chosen parameters
    """
    # open gams workspace
    #gams_sys_dir = "C:\\GAMS\\46"
    gams_sys_dir = system_directory
    ws = gams.GamsWorkspace(system_directory=gams_sys_dir)
    # location of GDX files
    #gdx_file_path = "C:\\Users\\tmad\\OneDrive - Danmarks Tekniske Universitet\\05 Python tools\\BalOpti_fuelmaps\\GDXfiles"
    gdx_file_path = file_path
    # make room for dataframes
    dfsBal = {symbol : pd.DataFrame({}) for symbol in symbolBal}
    dfsOpti = {symbol : pd.DataFrame({}) for symbol in symbolOpti}

    for scenario in scenarios:
        # Fetch gdx files
        file1 = gdx_file_path + "\\MainResults_" + scenario + ".gdx"
        file2 = gdx_file_path + "\\Optiflow_MainResults_" + scenario + ".gdx"
        gdx_file1 = ws.add_database_from_gdx(file1)
        gdx_file2 = ws.add_database_from_gdx(file2)
        # Converting to dataframes and putting in dictionary
        for symbol in symbolBal:
            temp = symbol_to_df(gdx_file1, symbol)
            temp["Scenario"] = scenario
            dfsBal[symbol] = pd.concat((dfsBal[symbol],temp))
        for symbol in symbolOpti:
            temp = symbol_to_df(gdx_file2, symbol)
            temp["Scenario"] = scenario
            dfsOpti[symbol] = pd.concat((dfsOpti[symbol],temp))
        dfs = dfsBal | dfsOpti
    print("Finished, making dictionary of dataframes.")
    print("")
    return dfs

def distance(regions,map_path):
    """
    calculate the distance between two balmorel regions:
    1) list of regions
    2) path to the shapefile
    output:
    1) the distance matrix
    """
    # Initialize geography
    europe_map = gpd.read_file(map_path)
    europe_map.crs
    # Get centroids
    centroids = {}
    for region in regions:
        centroid = europe_map[europe_map['id'] == region]['geometry'].iloc[0].centroid
        centroids[region] = centroid
    # Calculate distance
    dist = {}
    for region1 in centroids:
        for region2 in centroids:
            if region1 != region2:
                dist[region1,region2] = geodesic((centroids[region1].x,centroids[region1].y), (centroids[region2].x,centroids[region2].y)).km

    return dist