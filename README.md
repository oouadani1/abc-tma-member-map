# ABC TMA Organization Map

This map shows where A Better City and Allston-Brighton's Transportation Management Association member organizations (hospitals, institutions, large employers, developers, etc.) are and their access relationship to transit and sustainable mobility. It does so by incorporating all MBTA Subway (RL, OL, BL, GL and SL), Commuter Rail, Bus, and Ferry routes and stops, Bluebikes stations, bike lanes, and shared-use paths/trails. Four summary tiles calculate the proportion of organizations within 50, 250, 500, or 1,000 meters of each kind of transit mode. Distances are measured along actual streets and paths using a network analysis.

Clicking an organization maps its walk or bike network within 5, 10, or 15 minutes. Walking is assumed to be 80 meters per minute (4.8 km/h, or about 3.0 mph, the average human walking speed). Biking is 250 meters per minute (15 km/h, or about 9.3 mph, an average commuting or leisure pace). The bike network uses any street or path that allows bikes, including roads without bike lanes. A glossary in the map explains the data sources. 

Organization data comes from Airtable and updates every 6 hours. GTFS data is integrated through the MBTA's V3 API, and consists of live route changes, stops, and departures, and updates every 24 hours. Live Bluebikes data comes from Bluebikes's GBFS. Bike lanes and trails are overlayed as images, not dynamic layers, and are sourced from MAPC. Streets are rendered by OpenStreetMap. The map is built on MapLibre GL JS. 

See map: https://oouadani1.github.io/abc-tma-member-map/
