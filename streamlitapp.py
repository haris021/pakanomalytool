import pandas as pd
import geopandas as gpd 
import os 
import math 
import numpy as np
from shapely import Point
import pickle
import xarray as xr
import rioxarray as rio
from shapely.geometry import mapping
import matplotlib.pyplot as plt
import pickle
import geemap
import ee
import json
import wxee
import plotly.express as px
import datetime
from datetime import timedelta
import streamlit as st
import calendar


# Access the service account key data from Streamlit Secrets
service_account_key_data = st.secrets["private_key_id"]

# Load the key data as a JSON object
key_data = json.loads(service_account_key_data)

# Initialize Earth Engine with the service account key data
credentials = ee.ServiceAccountCredentials("", key_data=key_data)
ee.Initialize(credentials)

end_date = datetime.datetime.now() - datetime.timedelta(days = 10) 
start_date = datetime.datetime.now() - datetime.timedelta(days = 15) 



st.title("Pakistan Temperature Anomaly")
st.divider()

# Create a date filter
start_date_api = f'{start_date.year}-{start_date.month}-{start_date.day}'
end_date_api = f'{end_date.year}-{end_date.month}-{end_date.day}'
#ee.Authenticate()
#ee.Initialize()

@st.cache_data
def get_data_from_gee(start_date, end_date):
    pakistan_bbox = ee.Geometry.Polygon([
    [60.88, 37.27], 
    [77.84, 37.27],  
    [77.84, 23.62],  
    [60.88, 23.62],  
    [60.88, 37.27]])
    dataset = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR') \
    .filterDate(ee.Date(start_date_api), ee.Date(end_date_api)) \
    .filterBounds(pakistan_bbox).select(['temperature_2m'])
    downloaded_dataset = dataset.wx.to_xarray(scale =  11132, region = pakistan_bbox, crs = "epsg:4326")
    downloaded_dataset['temperature_2m'] = (downloaded_dataset['temperature_2m'] - 273.15) 
    return downloaded_dataset





file = open('divisions_historical_data.pkl', 'rb') 
shapefile = pickle.load(file)

downloading_data_state = st.text("Downloading data...")
downloaded_dataset = get_data_from_gee(start_date_api, end_date_api)
downloading_data_state.text("Data Downloaded!")
# print(downloaded_dataset.time)

option = st.selectbox(
    'Date',
    tuple(downloaded_dataset.time.values))


selected_option_month_name = calendar.month_name[pd.to_datetime(option).month]


shapefile["current_tmean"] = ""
for division in shapefile["Division"]: 
    division_geometry = shapefile.loc[shapefile["Division"] == division].geometry

    shapefile.loc[shapefile["Division"] == division, "current_tmean"] = downloaded_dataset.sel(time = option).temperature_2m.rio.clip(division_geometry).mean().values
    # print(downloaded_dataset.temperature_2m.rio.clip(division_geometry).mean().values)

shapefile['anomaly'] = shapefile['current_tmean'] - shapefile[f'{selected_option_month_name}_historic_tmean']
shapefile['anomaly'] = shapefile['anomaly'] .astype(float)

geojson_file = json.loads(shapefile.to_json())
# Define your custom color scale for positive and negative values
color_scale = [
    (0, 'white'), 
    (-1,'blue'),
    (-2,'blue'),
    (-3,'blue'),
    (1, 'red'), # Middle value (0) in white
    (2, 'red'),
    (3, 'red'),     # Positive values in red
]

fig = px.choropleth(shapefile, geojson=geojson_file, color="anomaly",
                    locations="Division", featureidkey="properties.Division",
                    projection="mercator", color_continuous_scale= 'rdylbu_r', height = 800
                   )

fig.update_geos(fitbounds="locations", visible=False)


# import streamlit as st 

st.plotly_chart(fig)

# st.dataframe(shapefile.drop(['geometry'], axis = 1))

downloading_data_state.text("")
