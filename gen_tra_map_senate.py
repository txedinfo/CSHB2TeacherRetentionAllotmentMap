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

df_teacher_data = pd.read_excel("Campus Teacher Profile.xlsx")

df = pd.merge(df, df_teacher_data, how="right", on="School Number")

# keep only rows where Full_Site_Address is NOT exactly "TX,  "
df = df[df['Full_Site_Address'] != 'TX,  ']

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
    zoom_snap=0.25,
    zoom_delta=0.25,
    # prefer_canvas=True
)
# Fit map to cover all of Texas on initial load
minx, miny, maxx, maxy = senate.total_bounds
m.fit_bounds([[miny, minx], [maxy, maxx]])
m_name = m.get_name()

m.get_root().header.add_child(JavascriptLink(
    "https://unpkg.com/leaflet-image@0.4.0/leaflet-image.js"
))
m.get_root().header.add_child(Element('<title>CSHB 2: TRA Map - TX Senate</title>'))
og_meta = Element("""
    <!-- Open Graph / Twitter meta tags for link previews -->
    <meta property="og:title" content="CSHB 2: Teacher Retention Allotment Map - TX Senate" />
    <meta property="og:description" content="An interactive statewide map of Texas senate districts showing per-teacher retention allotments by experience." />
    <meta property="og:url" content="https://txedinfo.github.io/CSHB2TeacherRetentionAllotmentMap/" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="CSHB 2: Teacher Retention Allotment Map - TX Senate" />
    <meta name="twitter:description" content="An interactive statewide map of Texas senate districts showing per-teacher retention allotments by experience." />
""")
m.get_root().header.add_child(og_meta)

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
    CSHB 2: Teacher Retention Allotment Map - TX Senate
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
m_dropdown_checkbox = """
<label style="font-size:12px;">
  <input type="checkbox" id="isolateToggle" checked style="font-size: 12px"/>
    Isolate Small Charters/<br>
  <span style="display:block; text-align:right; width:100%;">Large Public Schools</span>
</label>
"""
new_dropdown_block = f"""
<style>
.district-selector {{
    background: white;
    padding: 10px;
    border: 1px solid gray;
    font-size: 12px;
}}
</style>
<script>
window.addEventListener('load', function() {{
    var map = {m_name};
    var container = L.DomUtil.create('div', 'district-selector');
    container.innerHTML = `
      <select id="districtDropdown" style="display:block; margin-bottom:4px; font-size:12px;">
        <option value="">All Senate Districts</option>
        {options_html}
      </select>
      {m_dropdown_checkbox}
    `;
    L.DomEvent.disableClickPropagation(container);

    var DistrictControl = L.Control.extend({{
        options: {{ position: 'topright' }},
        onAdd: function(map) {{
            return container;
        }}
    }});
    map.addControl(new DistrictControl());

    var distMap = {distmap_js};
    var boundsMap = {bounds_js};

    // build an object mapping each district to its markers
    var markerLayersByDistrict = {{}};
    for (var k in distMap) {{
        markerLayersByDistrict[k] = [];
    }}
    map.eachLayer(function(layer) {{
        if (layer instanceof L.CircleMarker || (layer.options && layer.options.numberOfSides === 4)) {{
            for (var d in distMap) {{
                if (distMap[d].hasLayer(layer)) {{
                    markerLayersByDistrict[d].push(layer);
                }}
            }}
        }}
    }});

    function applyFilter() {{
      var checked = document.getElementById('isolateToggle').checked;
      var sel = document.getElementById('districtDropdown').value;
      // hide everything first
      Object.values(markerLayersByDistrict).flat().forEach(layer => {{
        if (map.hasLayer(layer)) map.removeLayer(layer);
      }});
      if (!checked) {{
        // show all markers in selected district or all
        if (sel) {{
          markerLayersByDistrict[sel].forEach(layer => map.addLayer(layer));
        }} else {{
          Object.values(markerLayersByDistrict).flat().forEach(layer => map.addLayer(layer));
        }}
      }} else {{
        // isolate small charters / large public
        var targets = sel ? [sel] : Object.keys(markerLayersByDistrict);
        targets.forEach(d => {{
          markerLayersByDistrict[d].forEach(layer => {{
            var isCharterSmall = layer.options.numberOfSides === 4 && layer.options.fillColor === "#0D92F4";
            var isPublicLarge = layer.options.numberOfSides !== 4 && layer.options.fillColor === "#F95454";
            if (isCharterSmall || isPublicLarge) {{
              map.addLayer(layer);
            }}
          }});
        }});
      }}
    }}

    document.getElementById('isolateToggle').addEventListener('change', applyFilter);

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
        applyFilter();
    }});

    applyFilter();

    // check URL for district param or hash
    var hash = window.location.hash.substring(1);
    var params = new URLSearchParams(window.location.search);
    var param = params.get('district') || hash;
    if (param) {{
        var d = param.replace(/^SD/i, '');
        if (distMap.hasOwnProperty(d)) {{
            var dropdown = document.getElementById('districtDropdown');
            dropdown.value = d;
            dropdown.dispatchEvent(new Event('change'));
        }}
    }}

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
m.get_root().html.add_child(Element(new_dropdown_block))


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
            link.download = "CSHB2 Teacher Retention Allotment Map - TX Senate.png";
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
    # format base salary averages
    beg_base = r['Teacher Beginning Base Salary Average']
    if beg_base == 'MASKED' or beg_base is None or pd.isnull(beg_base):
        beg_base_fmt = beg_base
    else:
        beg_base_fmt = f"{int(beg_base):,}"

    mid_base = r['Teacher 1-5 Years Base Salary Average']
    if mid_base == 'MASKED' or mid_base is None or pd.isnull(mid_base):
        mid_base_fmt = mid_base
    else:
        mid_base_fmt = f"{int(mid_base):,}"

    sen_base = r['Teacher 5+ Years Base Salary Average']
    if sen_base == 'MASKED' or sen_base is None or pd.isnull(sen_base):
        sen_base_fmt = sen_base
    else:
        sen_base_fmt = f"{int(round(sen_base)):,}"

    # build popup
    allot_short = 5000 if enroll <= 5000 else 2500
    allot_long = 10000 if enroll <= 5000 else 5500
    # format 5+ years percent to one decimal unless masked or null
    perc = r['Teacher 5+ Years Full Time Equiv Percent']
    if perc == 'MASKED' or perc is None or pd.isnull(perc):
        perc_fmt = perc
    else:
        perc_fmt = f"{perc:.1f}"
        if ".0" in perc_fmt:
            perc_fmt = perc_fmt.replace(".0", "")

    # format 5+ years count to one decimal place unless masked or null
    cnt = r['Teacher 5+ Years Full Time Equiv Count']
    if cnt == 'MASKED' or cnt is None or pd.isnull(cnt):
        cnt_fmt = cnt
    else:
        cnt_fmt = f"{cnt:.1f}"
        if ".0" in cnt_fmt:
            cnt_fmt = cnt_fmt.replace(".0", "")

    # format beginning count display (mask entire cell if any part is MASKED)
    beg_cnt = r['Teacher Beginning Full Time Equiv Count']
    beg_perc_val = r['Teacher Beginning Full Time Equiv Percent']
    if beg_cnt == 'MASKED' or beg_perc_val == 'MASKED':
        beg_count_display = 'MASKED'
    else:
        beg_count_display = f"{beg_cnt} ({beg_perc_val}%)"

    # format mid count display (mask entire cell if any part is MASKED)
    mid_cnt = r['Teacher 1-5 Years Full Time Equiv Count']
    mid_perc_val = r['Teacher 1-5 Years Full Time Equiv Percent']
    if mid_cnt == 'MASKED' or mid_perc_val == 'MASKED':
        mid_count_display = 'MASKED'
    else:
        mid_count_display = f"{mid_cnt} ({mid_perc_val}%)"

    # format senior count display (mask entire cell if any part is MASKED)
    if cnt_fmt == 'MASKED' or perc_fmt == 'MASKED':
        sen_count_display = 'MASKED'
    else:
        sen_count_display = f"{cnt_fmt} ({perc_fmt}%)"

    popup_html = f"""
    Senate District {r['district_name']}<br>
    <b>{r['School Name']} – {r['District Name']}</b><br>
    <i>{r['District Type']}</i><br>
    School Enrollment (Oct 2023): {r['School Enrollment as of Oct 2023']:,}<br>
    District Enrollment (Oct 2023): {enroll:,}<br><br>
    <div>CSHB 2: Teacher Retention Allotment</div>
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
    <br>
    <div>2023-2024 Campus Staff</div>
    <table style="width:100%; text-align:center; border:1px solid black; border-collapse:collapse;">
      <tr>
        <th style="border:1px solid black; white-space:normal;">Years<br>Experience</th>
        <th style="border:1px solid black; white-space:normal;">Count (% of Total)</th>
        <th style="border:1px solid black; white-space:normal;">Base<br>Salary Avg.</th>
      </tr>
      <tr>
        <td style="border:1px solid black;">Beginning teachers</td>
        <td style="border:1px solid black;">{beg_count_display}</td>
        <td style="border:1px solid black;">{beg_base_fmt if beg_base_fmt=='MASKED' else f"${beg_base_fmt}"}</td>
      </tr>
      <tr>
        <td style="border:1px solid black;">1-5 years experience</td>
        <td style="border:1px solid black;">{mid_count_display}</td>
        <td style="border:1px solid black;">{mid_base_fmt if mid_base_fmt=='MASKED' else f"${mid_base_fmt}"}</td>
      </tr>
    <tr>
        <td style="border:1px solid black;">5+ years experience</td>
        <td style="border:1px solid black;">{sen_count_display}</td>
        <td style="border:1px solid black;">{sen_base_fmt if sen_base_fmt=='MASKED' else f"${sen_base_fmt}"}</td>
      </tr>
    </table>
    """
    popup_district = folium.Popup(popup_html, max_width=300, sticky=True)
    marker_district.add_child(popup_district)
    # add hover tooltip so popup shows temporarily on hover
    tooltip = folium.Tooltip(popup_html, sticky=False)
    marker_district.add_child(tooltip)
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
    font-size: 12px;
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
    <div style="max-width: 85%; margin: auto;">
        A visualization of data relevant to the Teacher Retention Allotment (Sec. 48.158) provision in CSHB 2. Click on a campus to see the pay raises that teachers at the campus would receive based on their years of experience and the district's/charter's student enrollment. This analysis was completed on May 15, 2025 using the <a href='https://tealprod.tea.state.tx.us/Tea.AskTed.Web/Forms/ArchivedSchoolAndDistrictDataFiles.aspx' target="blank">Spring 2024 AskTED school data</a> and <a href='https://rptsvr1.tea.texas.gov/perfreport/tapr/2024/index.html' target="blank">2023-2024 TAPR staff profile.</a>
    </div>
</div>
'''
m.get_root().html.add_child(Element(footer_html))


# === SAVE MAP ===
m.save(OUTPUT_MAP)
print("Map saved →", OUTPUT_MAP)
