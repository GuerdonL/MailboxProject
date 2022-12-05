from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="myGeocoder")
location = geolocator.geocode("1 Hanover St Fl 1, New York, NY 10005")
print(location.address)
print((location.latitude, location.longitude))