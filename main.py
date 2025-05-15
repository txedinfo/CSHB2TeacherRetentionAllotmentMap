import os
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium import Element
from branca.element import JavascriptLink, CssLink

# === LOAD EASYPRINT PLUGIN ===
# (Add JS plugin after map creation)

# === CONFIGURATION ===
SHP_DIR = "PLANS2168"
SHP_NAME = "PLANS2168.shp"
EXCEL_PATH = "AskTED Geocoded_Spring 2024.xlsx"
OUTPUT_MAP = "index.html"

# === LOAD SCHOOL DATA ===
df = pd.read_excel(EXCEL_PATH, sheet_name="School Data")
def resolve_coords(r):
    lat = r['Census_Latitude'] if pd.notnull(r['Census_Latitude']) else r['Latitude']
    lon = r['Census_Longitude'] if pd.notnull(r['Census_Longitude']) else r['Longitude']
    if pd.isnull(lat) or pd.isnull(lon):
        print(f"Missing coords for {r['School Name']} – {r['District Name']}")
        return None
    return Point(lon, lat)
df['geometry'] = df.apply(resolve_coords, axis=1)
df = df[df.geometry.notnull()]
gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")

# === LOAD SENATE DISTRICTS ===
senate = gpd.read_file(os.path.join(SHP_DIR, SHP_NAME)).to_crs("EPSG:4326")
senate['district_name'] = senate['District'].astype(str)

# === SPATIAL JOIN ===
gdf = gpd.sjoin(
    gdf,
    senate[['district_name', 'geometry']],
    how='left',
    predicate='within'
).drop(columns=['index_right'])

# === BUILD BASE MAP ===
m = folium.Map(
    location=[31.0, -99.0],
    zoom_start=6,
    tiles="CartoDB positron",
    control_scale=True,
    # prefer_canvas=True
)
m_name = m.get_name()

m.get_root().header.add_child(JavascriptLink(
    "https://unpkg.com/leaflet-image@0.4.0/leaflet-image.js"
))

# === CREATE CUSTOM MARKER PANE ===
pane_script = Element(f"""
<script>
window.addEventListener('load', function() {{
    var map = {m_name};
    map.createPane('markerPane');
    map.getPane('markerPane').style.zIndex = 650;
}});
</script>
""")
m.get_root().html.add_child(pane_script)


# === ADD MAP TITLE ===
title_html = '''
<style>
    html, body {
        display: flex;
        flex-direction: column;
        height: 100%;
        margin: 0;
    }
    .map-title {
        flex: none;
        font-family: Helvetica, sans-serif;
        font-weight: bold;
        text-align: center;
        background-color: white;
        padding: 15px;
        z-index: 9998;
        font-size: 16px;
    }
    .folium-map {
        flex: 1;
    }
    .map-footer {
        flex: none;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        background-color: #f8f9fa;
    }
    .leaflet-control-layers {
        display: none !important;
    }
</style>
<div class="map-title">
    CSHB 2: Teacher Retention Allotment Map
</div>
'''
m.get_root().html.add_child(Element(title_html))

# === CREATE FEATURE GROUPS ===
district_groups = {}
for d in sorted(senate['district_name'].unique(), key=lambda x: int(x)):
    fg = folium.FeatureGroup(name=f"Senate District {d}", show=True)
    fg.add_to(m)
    # add the polygon for this district
    sel = senate[senate['district_name'] == d]
    folium.GeoJson(
        sel,
        name=f"District {d}",
        smooth_factor=0,
        style_function=lambda f: {'color': 'black', 'weight': 1, 'fillOpacity': 0.1},
        highlight_function=lambda f: {'weight': 3, 'fillOpacity': 0.3},
        tooltip=folium.GeoJsonTooltip(fields=['district_name'], aliases=['Senate District'])
    ).add_to(fg)
    district_groups[d] = fg

# === COMPUTE DISTRICT BOUNDS FOR ZOOM ===
bounds_dict = {}
for d, fg in district_groups.items():
    sel = senate[senate['district_name'] == d]
    minx, miny, maxx, maxy = sel.total_bounds
    bounds_dict[d] = [[float(miny), float(minx)], [float(maxy), float(maxx)]]

# === DROPDOWN SCRIPT ===
options_html = "".join(
    f'<option value="{d}">Senate District {d}</option>'
    for d in sorted(senate['district_name'].unique(), key=lambda x: int(x))
)
distmap_js = "{" + ",".join(
    f'"{d}": {district_groups[d].get_name()}'
    for d in district_groups
) + "}"
bounds_js = json.dumps(bounds_dict)
dropdown = f"""
<div style="position: fixed; top: 10px; right: 10px; z-index:9999; background: none; padding: 0;">  
    <select id="districtDropdown">
    <option value="">All Schools</option>
    {options_html}
  </select>
</div>
<script>
window.addEventListener('load', function() {{
    var map = {m_name};
    var distMap = {distmap_js};
    var boundsMap = {bounds_js};

    document.getElementById('districtDropdown').addEventListener('change', function(e) {{
        var sel = e.target.value;
        // remove every district layer first
        for (var k in distMap) {{
            if (map.hasLayer(distMap[k])) {{
                map.removeLayer(distMap[k]);
            }}
        }}
        if (sel) {{
            // show only selected district
            map.addLayer(distMap[sel]);
            map.fitBounds(boundsMap[sel]);
            // bring all markers to front so popups work
            distMap[sel].eachLayer(function(layer) {{
                if (layer instanceof L.Marker || layer instanceof L.CircleMarker) {{
                    layer.bringToFront();
                    layer.on('click', function() {{ this.openPopup(); }});
                }}
            }});
        }} else {{
            // show all districts
            for (var k in distMap) {{
                map.addLayer(distMap[k]);
            }}
            map.setView([31.0, -99.0], 6);
        }}
    }});

    // bind marker click to open their popups
    map.eachLayer(function(layer) {{
      if (layer instanceof L.Marker || layer instanceof L.CircleMarker) {{
        layer.on('click', function() {{
          this.openPopup();
        }});
      }}
    }});
}});
</script>
"""
m.get_root().html.add_child(Element(dropdown))


# === SCREENSHOT BUTTON VIA leaflet-image ===
screenshot_html = f'''
<div style="
    position: fixed; top: 10px; left: 10px;
    z-index: 9999; background: none; padding: 0;
">
  <button id="downloadMapBtn" style="
      background: white;
      border: 1px solid gray;
      padding: 5px;
      font-size: 14px;
      cursor: pointer;
      display: none;
  ">Download PNG</button>
</div>
<script>
window.addEventListener('load', function() {{
    document.getElementById('downloadMapBtn').addEventListener('click', function() {{
        leafletImage({m_name}, function(err, canvas) {{
            if (err) console.error(err);
            var imgData = canvas.toDataURL("image/png");
            var link = document.createElement("a");
            link.href = imgData;
            link.download = "CSHB2 Permanent Teacher Retention Allotment Map.png";
            link.click();
        }});
    }});
}});
</script>
'''
m.get_root().html.add_child(Element(screenshot_html))


# === ADD SCHOOLS MARKERS ===
for _, r in gdf.iterrows():
    lat, lon = r.geometry.y, r.geometry.x
    enroll = r["District Enrollment as of Oct 2023"]
    color = "#0D92F4" if enroll <= 5000 else "#F95454"
    # smaller, semi-transparent markers with black border
    if r["District Type"] == "CHARTER":
        marker_district = folium.RegularPolygonMarker(
            location=(lat, lon),
            number_of_sides=4,
            radius=4,
            pane='markerPane',
            color='black', weight=1,
            fill=True, fill_color=color, fill_opacity=0.6
        )
    else:
        marker_district = folium.CircleMarker(
            location=(lat, lon),
            radius=4,
            pane='markerPane',
            color='black', weight=1,
            fill=True, fill_color=color, fill_opacity=0.6
        )
    # build popup
    allot_short = 5000 if enroll <= 5000 else 2500
    allot_long = 10000 if enroll <= 5000 else 5500
    popup_html = f"""
    Senate District {r['district_name']}<br>
    <b>{r['School Name']} – {r['District Name']}</b><br>
    <i>{r['District Type']}</i><br>
    District Enrollment (Oct 2023): {enroll:,}<br><br>
    <table style="width:100%; text-align:center; border:1px solid black; border-collapse:collapse;">
      <tr>
        <th style="border:1px solid black; white-space:normal;">Years Experience</th>
        <th style="border:1px solid black; white-space:normal;">Teacher<br>Retention Allotment</th>
      </tr>
      <tr>
        <td style="border:1px solid black;">3–4 years experience</td>
        <td style="border:1px solid black;">${allot_short:,}</td>
      </tr>
      <tr>
        <td style="border:1px solid black;">5+ years experience</td>
        <td style="border:1px solid black;">${allot_long:,}</td>
      </tr>
    </table>
    """
    popup_district = folium.Popup(popup_html, max_width=300, sticky=True)
    marker_district.add_child(popup_district)
    # add to district groups
    dname = r.get('district_name')
    if pd.notnull(dname) and dname in district_groups:
        district_groups[dname].add_child(marker_district)

# === LAYER CONTROL ===
folium.LayerControl().add_to(m)



# === ADD LEGEND ===
legend_html = """
<div style="
    position: fixed;
    bottom: 10px;
    right: 10px;
    background: white;
    padding: 10px;
    border: 1px solid gray;
    z-index: 9999;
    font-size: 14px;
">
    <div>
        <svg width="12" height="12">
            <circle cx="6" cy="6" r="5" fill="#0D92F4" stroke="black" stroke-width="1"></circle>
        </svg>
        Enrollment ≤ 5,000 (Public School)
    </div>
    <div>
        <svg width="12" height="12">
            <circle cx="6" cy="6" r="5" fill="#F95454" stroke="black" stroke-width="1"></circle>
        </svg>
        Enrollment > 5,000 (Public School)
    </div>
    <div>
        <svg width="12" height="12">
            <rect x="1" y="1" width="10" height="10" fill="#0D92F4" stroke="black" stroke-width="1"></rect>
        </svg>
        Enrollment ≤ 5,000 (Charter)
    </div>
    <div>
        <svg width="12" height="12">
            <rect x="1" y="1" width="10" height="10" fill="#F95454" stroke="black" stroke-width="1"></rect>
        </svg>
        Enrollment > 5,000 (Charter)
    </div>
</div>
"""
m.get_root().html.add_child(Element(legend_html))

# === ADD FOOTER ===
footer_html = '''
<div class="map-footer">
    <div style="max-width: 75%; margin: auto;">
        A visualization of data relevant to the Teacher Retention Allotment (Sec. 48.158) provision in CSHB 2. Click on an individual campus to see the amounts that teachers at the campus would receive based on their years of experience and the district's/charter's student enrollment. This analysis was completed on May 15, 2025 using the <a href='https://tealprod.tea.state.tx.us/Tea.AskTed.Web/Forms/ArchivedSchoolAndDistrictDataFiles.aspx' target="blank">Spring 2024 AskTED school data.</a>
    </div>
</div>
'''
m.get_root().html.add_child(Element(footer_html))


# === SAVE MAP ===
m.save(OUTPUT_MAP)
print("Map saved →", OUTPUT_MAP)
