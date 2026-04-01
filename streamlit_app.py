import streamlit as st

import folium
from streamlit_folium import st_folium

import os
import geopandas as gpd
import pandas as pd
from geopy.geocoders import GoogleV3
from shapely.geometry import Point

from pathlib import Path

root = Path(__file__).parent

QUIET = False

class Verifier:
  def __init__(self, api_key, address):
    # Geocode the location
    try:
      self.location = GoogleV3(user_agent="MUW-Verify", api_key=api_key).geocode(address)
      # Format address as Point
      addr_point = Point(self.location.longitude, self.location.latitude)
      self.addr_point = gpd.GeoSeries(addr_point, crs='EPSG:4326')
      if self.location:
        if not QUIET:
          st.write('Found location: %s' % self.location.address)
      else:
        if not QUIET:
          st.write('Address not found - check that your formatting is correct.')
      # Load the burn scar polygons
      self.burn_scar = gpd.read_file(root / "burn-area.geojson")
      # Load building damage polygons
      lh_bld_dmg = gpd.read_file(root / "lahaina-building-damage.geojson")
      lh_bld_dmg.crs = 32604
      ku_bld_dmg = gpd.read_file(root / "kula-building-damage.geojson")
      ku_bld_dmg.crs = 32604
      ku_bld_dmg['damaged'] = 1
      ku_bld_dmg = ku_bld_dmg[['fid','OBJECTID','damaged','geometry']]
      ku_bld_dmg.columns = ['fid','id','damaged','geometry']
      bld_dmg = pd.concat([ku_bld_dmg, lh_bld_dmg])
      self.bld_dmg = bld_dmg.to_crs(epsg=4326)
    except:
      if not QUIET:
        st.write('Address %s not found by geocoder' % address)
      self.location = None
      self.addr_point = None
      self.burn_scar = None
      self.bld_dmg = None

  def check_in_burn_scar(self):
    # Check if address is contained within burn scar
    if self.addr_point.geometry.within(self.burn_scar.iloc[1].geometry).any():
      if not QUIET:
        st.write("Address %s is inside South Maui/Upcountry burn scar area" % self.location.address)
      return True
    elif self.addr_point.geometry.within(self.burn_scar.iloc[0].geometry).any():
      if not QUIET:
        st.write("Address %s is inside Lahaina burn scar area" % self.location.address)
      return True
    else:
      if not QUIET:
        st.write("Address %s is NOT inside either burn scar area" % self.location.address)
      return False

  def check_in_building_damage(self):
    bldg_warning = """NOTE: Building damage detection and damage levels based on imagery from August 9
                      provided by Microsoft AI for Good Geospatial (POC: Caleb Robinson).
                      Further damage may have occurred that is not shown here.\nSee NOAA website for
                      latest high-res imagery: https://storms.ngs.noaa.gov/storms/2023_hawaii/index.html"""
    # Check if the address matches a building and if so what the damage level is
    bldg_match = False
    for idx, row in self.bld_dmg.iterrows():
      if self.addr_point.geometry.within(row.geometry).any():
        bldg_match = True
        if not QUIET:
          st.write('Address %s matches building in building damage detection database' % self.location.address)
        if row['damage_pct'] > 0:
          if not QUIET:
            st.write('Estimated damage level: {0:.2f}%'.format(float(row['damage_pct'])*100))
            st.write(bldg_warning)
          return float(row['damage_pct'])*100
    if not bldg_match:
      if not QUIET:
        st.write('Address %s does not match any buildings in building damage detection database' % self.location.address)
        st.write(bldg_warning)
      return False

  def display_map(self):
    # Display the map
    addr_centroid = (self.addr_point.y.values[0], self.addr_point.x.values[0])
    y, x = addr_centroid

    map = folium.Map(location=[y, x], zoom_start=18)

    folium.TileLayer(
        tiles="http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}",
        name='Google Satellite Layer (before)',
        attr="Google Maps"
    ).add_to(map)

    folium.TileLayer(
        tiles="https://geospatialvisualizer.z13.web.core.windows.net/tiles/skysat_maui_8_10_2023_rgb_tiles/{z}/{x}/{y}.png",
        name='SkySat Lahaina post-fire August 9',
        attr="SkySat Lahaina"
    ).add_to(map)

    folium.TileLayer(
      tiles="https://geospatialvisualizer.z13.web.core.windows.net/tiles/10300100EB592000_tiles/{z}/{x}/{y}.png",
      name='Maxar Lahaina post-fire August 9',
      attr="Maxar Lahaina"
    ).add_to(map)

    folium.TileLayer(
      tiles="https://geospatialvisualizer.z13.web.core.windows.net/tiles/105001003590C300_tiles/{z}/{x}/{y}.png",
      name='Maxar Kula post-fire August 12',
      attr="Maxar Kula"
    ).add_to(map)

    geo_j = self.burn_scar.to_json()
    geo_j = folium.GeoJson(data=geo_j,
                           style_function=lambda x: {'color': 'black', 'fillColor': '#a76f45', 'opacity':0.5, 'fillOpacity':0.4},
                           name="Burn scar")
    geo_j.add_to(map)

    builds_geo_j =  self.bld_dmg[self.bld_dmg['damaged']==1].to_json()
    builds_geo_j = folium.GeoJson(data=builds_geo_j,
                                  style_function=lambda x: {'color': 'black', 'fillColor': 'red', 'opacity':0.5, 'fillOpacity':0.4},
                                  name="Damaged buildings")
    builds_geo_j.add_to(map)

    intact_geo_j =  self.bld_dmg[self.bld_dmg['damaged']==0].to_json()
    intact_geo_j = folium.GeoJson(data=intact_geo_j,
                                  style_function=lambda x: {'color': 'black', 'fillColor': 'green', 'opacity':0.5, 'fillOpacity':0.4},
                                  name="Intact buildings")
    intact_geo_j.add_to(map)

    folium.Marker(location=addr_centroid, name='Verification address').add_to(map)

    folium.LayerControl().add_to(map)

    return map

api_key = os.environ.get("api_key", None)

with st.form("inputs"):
  info_text = """This app is used to check if a user-specified address is inside
                 the Lahaina or Kula/South Maui burn scars and if the
                 address matches a building in the building damage detection
                 database. The address will be plotted on a map with geospatial and
                 satellite data layers showing impacts of the wildfires."""
  st.write(info_text)
  st.write("""If you experience any issues with the app, please contact Hannah
              Kerner at hkerner@asu.edu.""")

  if api_key is None:
    api_key = st.text_input("Input your google maps key")
  address = st.text_input("Input your address")

  st.write("""Instead of entering a single address above, you can upload
              a .xlsx/.csv file containing an address in each row.""")

  uploaded_file = st.file_uploader('Address file',type=['xlsx'],
                                    help='Must be xslx file type')
  columns = st.text_input("Enter the column names to use for addresses. If multiple columns should be used, separate the column names with commas (e.g.: col1, col2)")

  # Every form must have a submit button.
  submitted = st.form_submit_button("Submit")

  if submitted and address:
    st.write("Address:", address)
    v = Verifier(api_key, address)
    if v:
      v.check_in_burn_scar()
      v.check_in_building_damage()

      map = v.display_map()
      st_data = st_folium(map, width=500)

  elif submitted and uploaded_file:
    QUIET = True
    df = pd.read_excel(uploaded_file)
    colnames = [colname.strip() for colname in columns.split(',')]
    st.write('Processing bulk addresses from file...')
    progress_bar = st.progress(0)
    for idx, row in df.iterrows():
      address = ','.join([str(row[c]) for c in colnames if not pd.isnull(row[c])])
      # st.write("Address:", address)
      v = Verifier(api_key, address)
      if v.location == None:
        df.loc[idx, 'geocoder_address'] = 'ERROR: incorrect formatting or address not found'
      else:
        df.loc[idx, 'geocoder_address'] = v.location.address
        df.loc[idx, 'geocoder_long'] = v.location.longitude
        df.loc[idx, 'geocoder_lat'] = v.location.latitude
        if v.check_in_burn_scar():
          df.loc[idx, 'in_burn_scar'] = True
        else:
          df.loc[idx, 'in_burn_scar'] = False
        building_damage = v.check_in_building_damage()
        if building_damage:
          df.loc[idx, 'building_damage'] = building_damage
        else:
          df.loc[idx, 'building_damage'] = False
      progress_bar.progress((idx+1)/df.shape[0])

    st.write('Results shown in table below and saved in Excel file in Downloads folder')
    st.write(df)
    df.to_excel('~/Downloads/bulk-verification-results.xlsx')

