import csv,json
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="myGeocoder")
# open file2.csv
with open('file2.csv', 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    data = [row for row in reader]
    for j,row in enumerate(data):
        for i,elem in enumerate(row):
            row[i] = elem.replace('\n', ' ').replace("\u2122", ' ').replace("\u2014", ' ').replace(" STATE "," ").replace(" HIGHWAY ", " ").replace(" N "," ").replace(" S "," ").replace(" E "," ").replace(" W "," ").replace("    ", ' ').replace("   ", ' ').replace("  ", ' ').strip()
        try:
            location = geolocator.geocode(row[2])
            row[2] = location.address
            row.append((location.latitude, location.longitude))
            print(location.address)
        except:
            try:
                print("errored: " + row[2])
                del data[j]
            except:
                del data[j]

# 199 5TH ST W CHAMA, NM 87520-9998
with open('file.json', 'w') as f:
    json.dump(data, f)
