import streamlit as st

import folium
from streamlit_folium import st_folium

import os
import geopandas as gpd
from geopy.geocoders import GoogleV3
from shapely.geometry import Point

from pathlib import Path

root = Path(__file__).parent

class Verifier:
  def __init__(self, api_key, address):
    # Geocode the location
    self.location = GoogleV3(user_agent="MUW-Verify", api_key=api_key).geocode(address)
    # Format address as Point
    addr_point = Point(self.location.longitude, self.location.latitude)
    self.addr_point = gpd.GeoSeries(addr_point, crs='EPSG:4326')
    if self.location:
      st.write('Found location: %s' % self.location.address)
    else:
      st.write('Address not found - check that your formatting is correct.')
    # Load the burn scar polygons
    self.burn_scar = gpd.read_file(root / "burn-area.geojson")
    # Load building damage polygons
    self.bld_dmg = gpd.read_file(root / "lahaina-building-damage.geojson").to_crs('EPSG:4326')

  def check_in_burn_scar(self):
    # Check if address is contained within burn scar
    if self.burn_scar.iloc[1].geometry.contains(self.addr_point).any():
      st.write('Address %s is inside South Maui/Upcountry burn scar area' % self.location.address)
    elif self.burn_scar.iloc[0].geometry.contains(self.addr_point).any():
      st.write('Address %s is inside Lahaina burn scar area' % self.location.address)
    else:
      st.write('Address %s is NOT inside either burn scar area' % self.location.address)

  def check_in_building_damage(self):
    st.write("NOTE: Building damage detection and damage levels based on imagery from August 9. Further damage may have occurred that is not shown here.\nSee NOAA website for latest high-res imagery: https://storms.ngs.noaa.gov/storms/2023_hawaii/index.html")
    # Check if the address matches a building and if so what the damage level is
    bldg_match = False
    for idx, row in self.bld_dmg.iterrows():
      if row.geometry.contains(self.addr_point).any():
        bldg_match = True
        st.write('Address %s matches building in building damage detection database' % self.location.address)
        st.write('Estimated damage level: %f percent' % (float(row['damage_pct'])*100))
        break
    if not bldg_match:
      st.write('Address %s does not match any buildings in building damage detection database' % self.location.address)

  def display_map(self):
    # Display the map
    addr_centroid = (self.addr_point.y.values[0], self.addr_point.x.values[0])
    y, x = addr_centroid

    map = folium.Map(location=[y, x], zoom_start=14)

    folium.TileLayer(
        tiles="http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}",
        name='Google Satellite Layer (before)',
        attr="Google Maps"
    ).add_to(map)

    folium.TileLayer(
        tiles="https://geospatialvisualizer.z13.web.core.windows.net/tiles/10300100EB592000_tiles/{z}/{x}/{y}.png",
        name='SkySat post-fire August 9',
        attr="SkySat"
    ).add_to(map)

    geo_j = self.burn_scar.to_json()
    geo_j = folium.GeoJson(data=geo_j,
                           style_function=lambda x: {'color': 'black', 'fillColor': '#a76f45', 'opacity':0.5, 'fillOpacity':0.4},
                           name="Burn scar")
    geo_j.add_to(map)

    builds_geo_j =  self.bld_dmg[self.bld_dmg['damaged']==1].to_json()
    builds_geo_j = folium.GeoJson(data=builds_geo_j,
                                  style_function=lambda x: {'color': 'black', 'fillColor': 'red', 'opacity':0.5, 'fillOpacity':0.6},
                                  name="Damaged buildings")
    builds_geo_j.add_to(map)

    folium.Marker(location=addr_centroid, name='Verification address').add_to(map)

    folium.LayerControl().add_to(map)

    return map

api_key = os.environ.get("api_key", None)

with st.form("inputs"):
  st.write("Input the following:")
  if api_key is None:
    api_key = st.text_input("Input your google maps key")
  address = st.text_input("Input your address")

   # Every form must have a submit button.
  submitted = st.form_submit_button("Submit")
  if submitted:
      st.write("Address:", address)
      v = Verifier(api_key, address)
      v.check_in_burn_scar()
      v.check_in_building_damage()

      map = v.display_map()
      st_data = st_folium(map, width=500)
