import csv,json
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="myGeocoder")
 
# open file2.csv, a file with store data pulled from the url list in file.csv
with open("scraping/scraped_info.csv", 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    # create a data object that holds each store object of data as a seperate list in a list of the form [placename, url, address]
    data = [row for row in reader]

    #iterate through and clean each row
    for j,row in enumerate(data):
        for i,elem in enumerate(row):
            row[i] = elem.replace('\n', ' ').replace("\u2122", ' ').replace("\u2014", ' ').replace(" STATE "," ").replace(" HIGHWAY ", " ").replace(" N "," ").replace(" S "," ").replace(" E "," ").replace(" W "," ").replace("    ", ' ').replace("   ", ' ').replace("  ", ' ').strip()
    error_count = 0    
    #iterate through and geocode each row, geocoding the address, and replacing the address with the geocoded address, and appending the lat/long to the end of the store object
    for j,row in enumerate(data):
        try:
            # geocode the address
            location = geolocator.geocode(row[2])
            # replace the address with the geocoded address
            row[2] = location.address
            # append the lat/long to the end of the store object
            row.append((location.latitude, location.longitude))
            # print the progress
            print(str(j) + " of " + str(len(data)) + " geocoded")
        except:
            error_count+=1
            try:
                print("errored: " + row[2])
                del data[j]
            except:
                del data[j]
                print("double error")
                continue
    # we will format the data into a list of dictionaries, where each dictionary is a store object of the form: {"geometry": {"type": "Point", "coordinates": [LAT,LONG]},"type": "Feature","properties": {"name": NAME,"url": URL,"address": ADDRESS}}
    # iterate through the data and create a dictionary for each store object
    for j,row in enumerate(data):
        try:
            data[j] = {"geometry": {"type": "Point", "coordinates": [row[3][1],row[3][0]]},"type": "Feature","properties": {"name": row[0],"url": row[1],"address": row[2],"store_id": j}}
        except:
            print(data[j])
    # finally we place the data into a dictionary of the form: {"type": "FeatureCollection","features": [STORE1,STORE2,STORE3,...]}
    data = {"type": "FeatureCollection","features": data}

with open('scraping/file.json', 'w') as f:
    json.dump(data, f)
    print("done")
    print(error_count)