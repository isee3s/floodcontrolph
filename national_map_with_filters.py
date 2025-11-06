import re
import pandas as pd
import folium
from bs4 import BeautifulSoup

# === File Settings ===
DOM_FILE = "resources/all_national_data.txt"
MAP_FILE = "index.html"
EXCEL_FILE = "output/national_projects_data.xlsx"

# === Function to extract coordinates from location string. ===
def extract_coordinates(location_string):
    match = re.search(r'\(([-+]?[0-9]*\.?[0-9]+)\s*,\s*([-+]?[0-9]*\.?[0-9]+)\)', location_string)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

# === Load HTML ===
with open(DOM_FILE, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# === Extract projects ===
rows = soup.select("tr td.desc-a a.load-project-card")
templates = {t["id"]: t for t in soup.select("template[id^='proj-card-']")}
projects = []

for row in rows:
    project_id = row.get("data-id")
    project_name = row.get_text(strip=True)
    template_tag = templates.get(f"proj-card-{project_id}")
    if not template_tag:
        continue

    template_soup = BeautifulSoup(template_tag.decode_contents(), "html.parser")
    location_tag = template_soup.select_one("div.longi span")
    location_string = location_tag.get_text(strip=True) if location_tag else "Unknown"
    latitude, longitude = extract_coordinates(location_string)

    contractor_tag = template_soup.select_one("div.contractor p")
    cost_tag = template_soup.select_one("div.const span")
    start_date_tag = template_soup.select_one("div.start-date span")

    contractor = contractor_tag.get_text(strip=True) if contractor_tag else "N/A"
    cost_str = cost_tag.get_text(strip=True).replace(",", "").replace("₱", "") if cost_tag else "0"
    cost = float(cost_str) if cost_str.replace(".", "", 1).isdigit() else 0
    start_date = start_date_tag.get_text(strip=True) if start_date_tag else "Unknown"

    if latitude is not None and longitude is not None:
        projects.append({
            "Title": project_name,
            "Contractor": contractor,
            "Start Date": start_date,
            "Cost": cost,
            "Latitude": latitude,
            "Longitude": longitude,
            "Location": location_string
        })

df = pd.DataFrame(projects)
print(f"✅ Total projects: {len(df)}")

# === Optional: export to Excel ===
df.to_excel(EXCEL_FILE, index=False)
print(f"✅ Projects exported to '{EXCEL_FILE}'")

# === Define color based on cost ===
def get_color(cost):
    if 50_000_000 <= cost < 100_000_000:
        return "yellow"
    elif 100_000_000 <= cost < 200_000_000:
        return "orange"
    elif 200_000_000 <= cost < 300_000_000:
        return "red"
    elif 300_000_000 <= cost < 400_000_000:
        return "brown"
    elif cost >= 400_000_000:
        return "black"
    else:
        return "lightgrey"

# === Create map ===
map_center = [11.5531, 124.7341]
project_map = folium.Map(location=map_center, zoom_start=6, control_scale=True)

# === Feature groups for checkboxes ===
groups = {
    "50M–100M": folium.FeatureGroup(name="50M–100M"),
    "100M–200M": folium.FeatureGroup(name="100M–200M"),
    "200M–300M": folium.FeatureGroup(name="200M–300M"),
    "300M–400M": folium.FeatureGroup(name="300M–400M"),
    "400M+": folium.FeatureGroup(name="400M+"),
}

# === Add pins to feature groups ===
for idx, row in df.iterrows():
    cost = row["Cost"]
    color = get_color(cost)
    popup_html = f"<b>{row['Title']}</b><br>Cost: ₱{cost:,.0f}"

    marker = folium.CircleMarker(
        location=[row["Latitude"], row["Longitude"]],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        tooltip=f"₱{cost:,.0f}"
    ).add_child(folium.Popup(popup_html, max_width=300))

    # Assign marker to proper group
    if 50_000_000 <= cost < 100_000_000:
        groups["50M–100M"].add_child(marker)
    elif 100_000_000 <= cost < 200_000_000:
        groups["100M–200M"].add_child(marker)
    elif 200_000_000 <= cost < 300_000_000:
        groups["200M–300M"].add_child(marker)
    elif 300_000_000 <= cost < 400_000_000:
        groups["300M–400M"].add_child(marker)
    elif cost >= 400_000_000:
        groups["400M+"].add_child(marker)

# Add all feature groups to map
for group in groups.values():
    group.add_to(project_map)

# === Add LayerControl for checkboxes ===
folium.LayerControl(collapsed=False).add_to(project_map)

# === Add legend ===
legend_html = """
<div style="position: fixed; bottom: 30px; left: 30px; width: 160px; height: 140px;
     background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
     padding: 10px; border-radius: 5px;">
<b>Cost Legend</b><br>
<i style="background: yellow; width: 12px; height: 12px; display:inline-block; margin-right:5px;"></i> 50M–100M<br>
<i style="background: orange; width: 12px; height: 12px; display:inline-block; margin-right:5px;"></i> 100M–200M<br>
<i style="background: red; width: 12px; height: 12px; display:inline-block; margin-right:5px;"></i> 200M–300M<br>
<i style="background: brown; width: 12px; height: 12px; display:inline-block; margin-right:5px;"></i> 300M–400M<br>
<i style="background: black; width: 12px; height: 12px; display:inline-block; margin-right:5px;"></i> 400M+<br>
</div>
"""
project_map.get_root().html.add_child(folium.Element(legend_html))

# === Save map ===
project_map.save(MAP_FILE)
print(f"✅ Map with colored pins and checkboxes saved as '{MAP_FILE}'")
