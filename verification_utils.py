import geopandas as gpd
import matplotlib.pyplot as plt
from geopy.geocoders import GoogleV3
from shapely.geometry import Point

class Verifier:
  def __init__(self, api_key, address):
    # Geocode the location
    self.location = GoogleV3(user_agent="MUW-Verify", api_key=api_key).geocode(address)
    # Format address as Point
    addr_point = Point(location.longitude, location.latitude)
    self.addr_point = gpd.GeoSeries(addr_point, crs='EPSG:4326')
    if location:
      print('Found location: %s' % geolocator.geocode(address))
    else:
      print('Address not found - check that your formatting is correct.')
    # Load the burn scar polygons
    burn_scar_url = "https://drive.google.com/file/d/1Ukn9UnGtTz69JrfTBYLQ1UpEi9vQ7VU6/view?usp=drive_link"
    burn_scar_url = "https://drive.google.com/uc?id=" + burn_scar_url.split('/')[-2] 
    self.burn_scar = gpd.read_file(burn_scar_url)
    # Load building damage polygons
    bldg_dmg_url = "https://drive.google.com/file/d/1tCGqAsrWB0lHRvQFNyk25w7_sKO40lTm/view?usp=drive_link"
    bldg_dmg_url = "https://drive.google.com/uc?id=" + bldg_dmg_url.split('/')[-2] 
    self.bld_dmg = gpd.read_file(bldg_dmg_url).to_crs('EPSG:4326')

  def check_in_burn_scar():
    # Check if address is contained within burn scar
    if burn_scar.iloc[1].geometry.contains(self.addr_point).any():
      print('Address %s is inside South Maui/Upcountry burn scar area' % self.location.address)
    elif burn_scar.iloc[0].geometry.contains(self.addr_point).any():
      print('Address %s is inside Lahaina burn scar area' % self.location.address)
    else:
      print('Address %s is NOT inside either burn scar area' % self.location.address)

  def check_in_building_damage():
    # Check if the address matches a building and if so what the damage level is
    bldg_match = False
    for idx, row in self.bld_dmg.iterrows():
      if row.geometry.contains(self.addr_point).any():
        bldg_match = True
        print('Address %s matches building in building damage detection database' % self.location.address)
        print('Estimated damage level: %f percent' % (float(row['damage_pct'])*100))
        break
    if not bldg_match:
      print('Address %s does not match any buildings in building damage detection database' % self.location.address)

  def display_map():
    # Display the map
    addr_centroid = (addr_point.y.values[0], addr_point.x.values[0])
    
    m = Map(
        zoom=18, # only defined between 12 and 18
        scroll_wheel_zoom=True,
        center=addr_centroid)
    
    google_layer = TileLayer(url="http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}", name="Google Satellite Layer (before)")
    m.add_layer(google_layer)
    
    maxar_lahaina_tiles = ("https://geospatialvisualizer.z13.web.core.windows.net/tiles/10300100EB592000_tiles/{z}/{x}/{y}.png")
    maxar_layer=TileLayer(url=maxar_lahaina_tiles, name='Maxar post-fire August 9')
    m.add_layer(maxar_layer)
    
    skysat_lahaina_tiles = ("https://geospatialvisualizer.z13.web.core.windows.net/tiles/skysat_maui_8_10_2023_rgb_tiles/{z}/{x}/{y}.png")
    skysat_layer=TileLayer(url=skysat_lahaina_tiles, name='SkySat post-fire August 9')
    m.add_layer(skysat_layer)
    
    burnscar = GeoData(geo_dataframe = burn_scar, style={'color': 'black', 'fillColor': '#a76f45', 'opacity':0.5, 'fillOpacity':0.4},
                       name='Burn scar')
    m.add_layer(burnscar)
    
    buildings = GeoData(geo_dataframe = bld_dmg[bld_dmg['damaged']==1], style={'color': 'black', 'fillColor': 'red', 'opacity':0.5, 'fillOpacity':0.6},
                        name='Damaged buildings')
    m.add_layer(buildings)
    
    buildings = GeoData(geo_dataframe = bld_dmg[bld_dmg['damaged']==0], style={'color': 'black', 'fillColor': 'green', 'opacity':0.5, 'fillOpacity':0.6},
                        name='Intact buildings')
    m.add_layer(buildings)
    
    mark = Marker(location=addr_centroid, name='Verification address')
    m.add_layer(mark)
    m.add_control(LayersControl())
    m
