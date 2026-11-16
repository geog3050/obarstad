# Assignment 3 - GEOG:3050
# Study Area: Des Moines; Polk County, Iowa
# 1% Flood Risk Mapping Analysis 
# Seeing what population within Des Moines, IA lives within floodplain of 
    # 100-year flood projected by FEMA data
# US Census Bureau provdided Iowa Block Group data and Polk County, IA population Data
# FEMA provided Des Moines, IA floodplain shapefiles and water polyline data
    # Using water polyine data vs road polyline data since it makes moree sense, water
        # polylines were provided in FEMA dataset plus it is on track with my final project
# Results printed @ bottom

# Optional code is titled OPTIONAL and is not intended for being part of the project but helped me along in the process of working through each problem

def hawkid():
    return ["Owen Barstad", "obarstad"]

# Problem 1: Prepare Data

# Import arcpy provides accecss to ArcGIS geoprocessing tools/data
# Import Pathlib and Import Path provides a way to create/manage file paths wihtout having to combine strings manually

import arcpy
from pathlib import Path

CLASS_FOLDER = Path(r"S:\2026_Fall\SEES-3050\STUDENT\obarstad\Assignment3\Assignment3_ArcPy\Assignment3")

DATA_FOLDER = CLASS_FOLDER / "hw3_data" / "dataIOWA"
OUTPUT_FOLDER = CLASS_FOLDER / "outputs"

# mkdir() creates the new output folder 'outputs'
# parents=True creates a missing parent folder
# esist_ok=True prevents an error if the folder already exists in the group 
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# setting up Iowa / Polk County data and naming those pathways to access the data
# Make sure they exists in the specified file paths

DATA_IOWA = CLASS_FOLDER / "hw3_data" / "dataIOWA"

iowa_blocks = DATA_IOWA / "tl_2022_19_bg.shp"
population_csv = DATA_IOWA / "polk_county_population.csv"

print(iowa_blocks.exists())
print(population_csv.exists())

# OPTIONAL

staging_gdb = OUTPUT_FOLDER / "polk_staging.gdb"

if not arcpy.Exists(str(staging_gdb)):
    arcpy.management.CreateFileGDB(
        str(OUTPUT_FOLDER),
        staging_gdb.name
    )

# Select Polk County block groups
arcpy.management.MakeFeatureLayer(
    str(iowa_blocks),
    "iowa_block_groups"
)

arcpy.management.SelectLayerByAttribute(
    "iowa_block_groups",
    "NEW_SELECTION",
    "COUNTYFP = '153'"
)

# Save selected polygons
polk_blocks = str(staging_gdb / "polk_block_groups")

arcpy.management.CopyFeatures(
    "iowa_block_groups",
    polk_blocks
)

print("Polk County block groups:", arcpy.management.GetCount(polk_blocks)[0])

# Import requests allows python to send requests to the Census API
# Import pandas as pd importd pandas for working with csv files/tabular data

import requests
import pandas as pd
from pathlib import Path

# Assigned Census API Key for accessing Polk County Block Group data (attribute tables/csv file)
api_key = "d8f7d03d1685b06996ccc0bd632f0d637bb02491"

url = "https://api.census.gov/data/2022/acs/acs5"

# The only fetures I want downlaoded from csv file (GEOID for the join and Population Totals for Block Groups)
# State ID code for Iowa is 19 and Pok County Code is 153
params = {
    "get": "NAME,B01003_001E",
    "for": "block group:*",
    "in": "state:19 county:153",
    "key": api_key
}

# Download the data from census 
response = requests.get(url, params=params)
response.raise_for_status()

# Converts API resposne to python data (.json)
data = response.json()

df = pd.DataFrame(data[1:], columns=data[0])

# build a GEOID that matches the census shapefile
df["GEOID"] = (
    df["state"] +
    df["county"] +
    df["tract"] +
    df["block group"]
)

# We want to keep only the GEOID and Population Total for each block group fron the CSV file
population = df[["GEOID", "B01003_001E"]].copy()

# Renaming Block Group Population Totals to POP_TOTAL and then converts it to numeric form
population = population.rename(
    columns={"B01003_001E": "POP_TOTAL"}
)

# errors="coerce" converts NaN values into missing values instead of raising an error and stopping the program
population["POP_TOTAL"] = pd.to_numeric(
    population["POP_TOTAL"], errors="coerce"
)

# Save the CSV with organized GEOID and BG Pop. Data
output_csv = DATA_FOLDER / "polk_county_population.csv"
population.to_csv(output_csv, index=False)

print("Saved:", output_csv)
print(population.head())
print("Number of block groups in Polk County:", len(population))


# OPTIONAL
DATA_IOWA = CLASS_FOLDER / "hw3_data" / "dataIOWA"

population_csv = DATA_IOWA / "polk_county_population.csv"

# OPTIONAL
import pandas as pd

df = pd.read_csv(population_csv)

print(df.head())
print(df.columns.tolist())
print("Number of rows:", len(df))

def prepare_data(input_fc, output_geodatabase, out_coordinate_system,
                 join_table=None, join_field=None, value_field=None):

    try:
        # Converts paths to strings for arcpy
        input_fc = str(input_fc)
        output_geodatabase = Path(output_geodatabase)

        # Checks that the input exists
        if not arcpy.Exists(input_fc):
            raise FileNotFoundError(f"Input feature class not found: {input_fc}")

        # Create or reuse the output geodatabase
        if not arcpy.Exists(str(output_geodatabase)):
            arcpy.management.CreateFileGDB(
                str(output_geodatabase.parent),
                output_geodatabase.name
            )

        # Describes the input feature class
        desc = arcpy.Describe(input_fc)
        base_name = desc.baseName
        geometry_type = desc.shapeType

        # Sets the output feature class path
        output_fc = str(output_geodatabase / base_name)

        # Rejects an existing output
        if arcpy.Exists(output_fc):
            raise FileExistsError(f"Output already exists: {output_fc}")

        # Checks the output coordinate system
        out_sr = arcpy.SpatialReference(out_coordinate_system)

        if out_sr.type != "Projected" or out_sr.linearUnitName != "Meter":
            raise ValueError("Output coordinate system must be projected in meters.")

        # Projects the input feature class
        arcpy.management.Project(input_fc, output_fc, out_sr)

        # Checks whether join arguments were supplied
        join_arguments = [join_table, join_field, value_field]

        if any(arg is not None for arg in join_arguments):

            if not all(arg is not None for arg in join_arguments):
                raise ValueError("Supply all three join arguments together.")

            # Joins are only allowed for polygon feature classes
            if geometry_type != "Polygon":
                raise ValueError("Attribute joins are only allowed for polygons.")

            join_table = str(join_table)

            if not arcpy.Exists(join_table):
                raise FileNotFoundError(f"Join table not found: {join_table}")

            # Check that the required fields exist
            table_fields = {field.name: field for field in arcpy.ListFields(join_table)}
            polygon_fields = {field.name for field in arcpy.ListFields(output_fc)}

            if join_field not in table_fields or join_field not in polygon_fields:
                raise ValueError(f"Join field '{join_field}' was not found.")

            if value_field not in table_fields:
                raise ValueError(f"Value field '{value_field}' was not found.")

            # Check field types
            if table_fields[join_field].type not in ["String", "Integer", "BigInteger"]:
                raise ValueError("Join ID field must be text or an integer identifier.")

            if table_fields[value_field].type not in [
                "SmallInteger", "Integer", "BigInteger", "Single", "Double"
            ]:
                raise ValueError("Value field must be numeric.")

            # Import only the join ID and numeric value
            attributes_name = base_name + "_attributes"
            attributes_table = str(output_geodatabase / attributes_name)

            if arcpy.Exists(attributes_table):
                raise FileExistsError(
                    f"Attribute table already exists: {attributes_table}"
                )

            field_mappings = arcpy.FieldMappings()

            for field_name in [join_field, value_field]:
                field_map = arcpy.FieldMap()
                field_map.addInputField(join_table, field_name)
            
                output_field = field_map.outputField
                output_field.name = field_name
            
                if field_name == join_field:
                    output_field.type = "String"
                    output_field.length = 12
                else:
                    output_field.type = "Double"
            
                field_map.outputField = output_field
                field_mappings.addFieldMap(field_map)
            arcpy.conversion.TableToTable(
                join_table,
                str(output_geodatabase),
                attributes_name,
                field_mapping=field_mappings
            )

            # Join the numeric value to the projected polygons
            arcpy.management.JoinField(
                output_fc,
                join_field,
                attributes_table,
                join_field,
                [value_field]
            )

        return output_fc

    except Exception as e:
        print(f"Error preparing data: {e}")
        raise

# Prepare Polk County polygons and join population
# Creates a database for polk county whihc will contain Polk County Block groups, population attribute table with GEOID and Pop. Total and is in target coordinate system NAD83 / UTM Zone 16 (ESPG 26916)

polk_gdb = OUTPUT_FOLDER / "polk_county.gdb"

polk_census = prepare_data(
    polk_blocks,
    polk_gdb,
    26916,
    population_csv,
    "GEOID",
    "POP_TOTAL"
)

print(polk_census)

# OPTIONAL
with arcpy.da.SearchCursor(
    polk_census,
    ["GEOID", "POP_TOTAL"]
) as cursor:

    for row in cursor:
        print(row)

total_population = 0

# Search Cursor reads the values in the POP_TOTAL field wihtout hanging the original dataset and thenw e can print the Total Population for our study area (Polk County)
with arcpy.da.SearchCursor(
    polk_census,
    ["POP_TOTAL"]
) as cursor:

    for row in cursor:
        total_population += row[0]

print("Total Polk County population:", total_population)

# OPTIONAL

# Locate your FEMA download folder
FEMA_FOLDER = DATA_IOWA / "FEMA_Flood"

# List all files and folders inside
for item in FEMA_FOLDER.rglob("*"):
    print(item)

# FEMA flood hazard polygon layer fromd ataset (S_FLD_HAZ_AR.shp)
# Placing new data layer in specified data folder
fema_flood = DATA_IOWA / "FEMA_Flood" / "S_FLD_HAZ_AR.shp"

# Count features by flood zone


with arcpy.da.SearchCursor(
    str(fema_flood),
    ["FLD_ZONE"]
) as cursor:

# Zones = {} creates an empty dictionary
# row [0] pulls value from first requested field
    
    zones = {}

    for row in cursor:
        zone = row[0]
        zones[zone] = zones.get(zone, 0) + 1

for zone, count in sorted(zones.items()):
    print(zone, count)

# Select 1% annual-chance flood hazard areas

fema_layer = "fema_flood_layer"

arcpy.management.MakeFeatureLayer(
    str(fema_flood),
    fema_layer
)

arcpy.management.SelectLayerByAttribute(
    fema_layer,
    "NEW_SELECTION",
    "FLD_ZONE IN ('A', 'AE', 'AH', 'AO')"
)

print(
    "Selected floodplain polygons:",
    arcpy.management.GetCount(fema_layer)[0]
)

# Want to copy the selected floodplain polygon as separate dataset so we can have a specific floodplain dataset to use in population analysis
# name is Floodplain raw to look at only the floodplain in polk county, not the whole floodplain shapefile

floodplain_raw = str(staging_gdb / "polk_floodplain_raw")

arcpy.management.CopyFeatures(
    fema_layer,
    floodplain_raw
)

print("Floodplain saved:", floodplain_raw)

floodplain = prepare_data(
    floodplain_raw,
    polk_gdb,
    26916
)

print("Prepared floodplain:", floodplain)

# Problem 2: Estimate Population in Zone

def estimatePopulationInZone(source_polygons, population_field, study_zone,
                             output_fc):

    try:
        # Converts paths to strings
        source_polygons = str(source_polygons)
        study_zone = str(study_zone)
        output_fc = str(output_fc)

        # Checks that inputs exist
        if not arcpy.Exists(source_polygons):
            raise FileNotFoundError("Source polygons not found.")

        if not arcpy.Exists(study_zone):
            raise FileNotFoundError("Study zone not found.")

        # Describes inputs
        source_desc = arcpy.Describe(source_polygons)
        zone_desc = arcpy.Describe(study_zone)

        # Checks geometry types
        if source_desc.shapeType != "Polygon":
            raise ValueError("Source data must contain polygons.")

        if zone_desc.shapeType != "Polygon":
            raise ValueError("Study zone must contain polygons.")

        # Checks coordinate systems
        source_sr = source_desc.spatialReference
        zone_sr = zone_desc.spatialReference

        # Make sure the coordiante prjoection EPSG 26916 is projected correctly, otherwise it will raise an error
        if (source_sr.type != "Projected" or
                zone_sr.type != "Projected" or
                source_sr.linearUnitName != "Meter" or
                zone_sr.linearUnitName != "Meter"):
            raise ValueError("Inputs must use a projected coordinate system in meters.")
            
        
        if source_sr.factoryCode and zone_sr.factoryCode:
            if source_sr.factoryCode != zone_sr.factoryCode:
                raise ValueError("Incorrect Coordinate System: Inputs must use the same coordinate system.")
        elif source_sr.name != zone_sr.name:
            raise ValueError("Incorrect Coordinate System: Inputs must use the same coordinate system.")

        # Checks population field and raises error if fiel dis not found or incorrect
        source_fields = {f.name: f for f in arcpy.ListFields(source_polygons)}

        if population_field not in source_fields:
            raise ValueError("Population field error: Not Found.")

        if source_fields[population_field].type not in [
            "SmallInteger", "Integer", "BigInteger", "Single", "Double"
        ]:
            raise ValueError("Population field must be numeric.")

        # Checks population values and ensures they are not negative / null
        with arcpy.da.SearchCursor(source_polygons, [population_field]) as cursor:
            for row in cursor:
                if row[0] is None or row[0] < 0:
                    raise ValueError("Population values are <0 or NaN")

        # Check output and make sure it exists in our database, otherwise an error is raised
        if arcpy.Exists(output_fc):
            raise FileExistsError(f"Output already exists: {output_fc}")

        if not arcpy.Exists(str(Path(output_fc).parent)):
            raise FileNotFoundError("Output geodatabase does not exist.")

        # Check for existing area fields
        reserved_fields = ["SRC_KM2", "PART_KM2", "EST_POP"]

        if any(field in source_fields for field in reserved_fields):
            raise ValueError("Source polygons already contain a reserved output field.")

        # Temporary datasets in memory
        source_copy = r"memory\source_copy"
        dissolved_zone = r"memory\dissolved_zone"

        # Copy source polygons so original data remain unchanged
        arcpy.management.CopyFeatures(source_polygons, source_copy)

        # Calculate original polygon area in square kilometers
        arcpy.management.AddField(source_copy, "SRC_KM2", "DOUBLE")

        arcpy.management.CalculateField(
            source_copy,
            "SRC_KM2",
            "!shape.area@SQUAREKILOMETERS!",
            "PYTHON3"
        )

        # Dissolve study zone to combine overlapping polygons
        arcpy.management.Dissolve(study_zone, dissolved_zone)

        # Intersect source polygons with the dissolved study zone
        arcpy.analysis.Intersect(
            [source_copy, dissolved_zone],
            output_fc,
            "ALL",
            output_type="INPUT"
        )

        # Calculate overlapping area of floopldain and block groups of polk county
        arcpy.management.AddField(output_fc, "PART_KM2", "DOUBLE")

        arcpy.management.CalculateField(
            output_fc,
            "PART_KM2",
            "!shape.area@SQUAREKILOMETERS!",
            "PYTHON3"
        )

        # Calculate area-weighted population
        arcpy.management.AddField(output_fc, "EST_POP", "DOUBLE")

        arcpy.management.CalculateField(
            output_fc,
            "EST_POP",
            f"!{population_field}! * !PART_KM2! / !SRC_KM2!",
            "PYTHON3"
        )

        # Calculate total estimated population within floodplain
        total_population = 0

        with arcpy.da.SearchCursor(output_fc, ["EST_POP"]) as cursor:
            for row in cursor:
                total_population += row[0]

        return total_population

    except Exception as e:
        print(f"Error estimating population: {e}")
        raise

    finally:
        # Remove temporary datasets
        for temp in [r"memory\source_copy", r"memory\dissolved_zone"]:
            if arcpy.Exists(temp):
                arcpy.management.Delete(temp)


# gives total population estimate of polk county residents that live within FEMA projoected 1% floodplain

total_floodplain_population = estimatePopulationInZone(
    polk_census,
    "POP_TOTAL",
    floodplain,
    str(polk_gdb / "floodplain_population")
)

print(
    "Estimated population in 1% floodplain:",
    round(total_floodplain_population)
)

# Problem 3: Summarize Length

# OPTIONAL
for item in FEMA_FOLDER.rglob("*.shp"):
    print(item.name)

water_lines = FEMA_FOLDER / "S_WTR_LN.shp"

polk_water_lines = prepare_data(
    water_lines,
    polk_gdb,
    26916
)

def summarizeLineLength(lines, polygons, polygon_id_field, output_fc):

    try:
        # Converts paths to strings
        lines = str(lines)
        polygons = str(polygons)
        output_fc = str(output_fc)

        # Checks that inputs exist
        if not arcpy.Exists(lines):
            raise FileNotFoundError("Line feature class not found.")

        if not arcpy.Exists(polygons):
            raise FileNotFoundError("Polygon feature class not found.")

        # Describes inputs
        line_desc = arcpy.Describe(lines)
        polygon_desc = arcpy.Describe(polygons)

        # Checks geometry types
        if line_desc.shapeType != "Polyline":
            raise ValueError("Line input must contain polylines.")

        if polygon_desc.shapeType != "Polygon":
            raise ValueError("Polygon input must contain polygons.")

        # Checks coordinate systems
        line_sr = line_desc.spatialReference
        polygon_sr = polygon_desc.spatialReference

        if (line_sr.type != "Projected" or
                polygon_sr.type != "Projected" or
                line_sr.linearUnitName != "Meter" or
                polygon_sr.linearUnitName != "Meter"):
            raise ValueError("Inputs must use a projected coordinate system in meters.")

        if line_sr.factoryCode and polygon_sr.factoryCode:
            if line_sr.factoryCode != polygon_sr.factoryCode:
                raise ValueError("Inputs must use the same coordinate system.")
        elif line_sr.name != polygon_sr.name:
            raise ValueError("Inputs must use the same coordinate system.")

        # Checks polygon ID field
        polygon_fields = {
            field.name for field in arcpy.ListFields(polygons)
        }

        if polygon_id_field not in polygon_fields:
            raise ValueError("Polygon ID field not found.")

        if "LINE_KM" in polygon_fields:
            raise ValueError("Polygon input already contains LINE_KM.")

        # Checks output and makes sure it exists, otherwise error is raised
        if arcpy.Exists(output_fc):
            raise FileExistsError(f"Output already exists: {output_fc}")

        if not arcpy.Exists(str(Path(output_fc).parent)):
            raise FileNotFoundError("Output geodatabase does not exist.")

        # Temporary datasets
        intersect_fc = r"memory\line_intersect"
        summary_table = r"memory\line_summary"

        # Removes extra temp datasets if there are any
        for temp in [intersect_fc, summary_table]:
            if arcpy.Exists(temp):
                arcpy.management.Delete(temp)

        # Intersect lines with polygons
        arcpy.analysis.Intersect(
            [lines, polygons],
            intersect_fc,
            "ALL",
            output_type="LINE"
        )

        # Calculate line lengths in kilometers
        arcpy.management.AddField(
            intersect_fc,
            "LENGTH_KM",
            "DOUBLE"
        )

        arcpy.management.CalculateField(
            intersect_fc,
            "LENGTH_KM",
            "!shape.length@KILOMETERS!",
            "PYTHON3"
        )

        # Summarize line lengths by polygon ID
        arcpy.analysis.Statistics(
            intersect_fc,
            summary_table,
            [["LENGTH_KM", "SUM"]],
            polygon_id_field
        )

        # Copy all polygons to the output
        arcpy.management.CopyFeatures(polygons, output_fc)

        # Add LINE_KM field
        arcpy.management.AddField(
            output_fc,
            "LINE_KM",
            "DOUBLE"
        )

        # Join summarized line lengths to polygons
        if int(arcpy.management.GetCount(intersect_fc)[0]) > 0:

            arcpy.management.JoinField(
                output_fc,
                polygon_id_field,
                summary_table,
                polygon_id_field,
                ["SUM_LENGTH_KM"]
            )

            # Replace null values with zero
            arcpy.management.CalculateField(
                output_fc,
                "LINE_KM",
                "!SUM_LENGTH_KM! if !SUM_LENGTH_KM! is not None else 0",
                "PYTHON3"
            )

            # Remove temporary joined field
            arcpy.management.DeleteField(
                output_fc,
                ["SUM_LENGTH_KM"]
            )

        else:
            # No lines intersected any polygons
            arcpy.management.CalculateField(
                output_fc,
                "LINE_KM",
                "0",
                "PYTHON3"
            )

        return output_fc

    except Exception as e:
        print(f"Error summarizing line lengths: {e}")
        raise

    finally:
        # Remove temporary datasets
        for temp in [r"memory\line_intersect", r"memory\line_summary"]:
            if arcpy.Exists(temp):
                arcpy.management.Delete(temp)

line_summary = str(polk_gdb / "polk_block_group_water_length")

summarizeLineLength(
    polk_water_lines,
    polk_census,
    "GEOID",
    line_summary
)

# OPTIONAL
fields = ["GEOID", "POP_TOTAL", "LINE_KM"]

with arcpy.da.SearchCursor(line_summary, fields) as cursor:
    for i, row in enumerate(cursor):
        if i == 10:
            break
        print(row)

# FINAL RESULTS
# added percentage of people affected to understand the scale of polk counties population affected and not just have a number

percent_floodplain = (
    total_floodplain_population / total_population
) * 100

print("Total Polk County population:", round(total_population))
print("Estimated floodplain population:", round(total_floodplain_population))
print("Percentage of population in floodplain:", round(percent_floodplain, 2), "%")

# given code from README txt doc
combined_floodplain = str(polk_gdb / "combined_floodplain")

arcpy.management.Dissolve(
    floodplain,
    combined_floodplain
)

# given code from README txt doc
clipped_water_lines = str(polk_gdb / "clipped_water_lines")

arcpy.analysis.Clip(
    polk_water_lines,
    combined_floodplain,
    clipped_water_lines
)

# OPTIONAL
print(
    "Original water polylines:",
    arcpy.management.GetCount(polk_water_lines)[0]
)

print(
    "Clipped water polylines:",
    arcpy.management.GetCount(clipped_water_lines)[0]
)

arcpy.management.AddField(
    clipped_water_lines,
    "LENGTH_KM",
    "DOUBLE"
)

arcpy.management.CalculateField(
    clipped_water_lines,
    "LENGTH_KM",
    "!shape.length@KILOMETERS!",
    "PYTHON3"
)

# OPTIONAL
with arcpy.da.SearchCursor(
    clipped_water_lines,
    ["LENGTH_KM"]
) as cursor:
    total_length = sum(row[0] for row in cursor)

print("Total clipped water-polyline length (km):", round(total_length, 2))


