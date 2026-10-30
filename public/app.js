// The Mailbox Project — map of USPS post offices offering General Delivery.
//
// The Google Maps API key is NOT stored in this file. It is injected into
// index.html's script tag at deploy time (see .github/workflows/*.yml) and
// read back from that tag below for the Street View thumbnail.

const MAX_RANKED_RESULTS = 25; // Distance Matrix allows at most 25 destinations per request.

const mapStyle = [
  {featureType: 'administrative', elementType: 'all', stylers: [{visibility: 'on'}, {lightness: 33}]},
  {featureType: 'landscape', elementType: 'all', stylers: [{color: '#f2e5d4'}]},
  {featureType: 'poi.park', elementType: 'geometry', stylers: [{color: '#c5dac6'}]},
  {featureType: 'poi.park', elementType: 'labels', stylers: [{visibility: 'on'}, {lightness: 20}]},
  {featureType: 'road', elementType: 'all', stylers: [{lightness: 20}]},
  {featureType: 'road.highway', elementType: 'geometry', stylers: [{color: '#c5c6c6'}]},
  {featureType: 'road.arterial', elementType: 'geometry', stylers: [{color: '#e4d7c6'}]},
  {featureType: 'road.local', elementType: 'geometry', stylers: [{color: '#fbfaf7'}]},
  {featureType: 'water', elementType: 'all', stylers: [{visibility: 'on'}, {color: '#acbcc9'}]},
];

function getMapsApiKey() {
  const script = document.querySelector('script[src*="maps.googleapis.com/maps/api/js"]');
  if (!script) return '';
  try {
    return new URL(script.src).searchParams.get('key') || '';
  } catch (e) {
    return '';
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Great-circle distance in metres between two google.maps.LatLng objects.
function haversineMetres(a, b) {
  const toRad = (deg) => deg * Math.PI / 180;
  const R = 6371000;
  const dLat = toRad(b.lat() - a.lat());
  const dLng = toRad(b.lng() - a.lng());
  const lat1 = toRad(a.lat());
  const lat2 = toRad(b.lat());
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function formatMiles(metres) {
  const miles = metres / 1609.344;
  return miles < 10 ? `${miles.toFixed(1)} mi` : `${Math.round(miles)} mi`;
}

function initMap() {
  const map = new google.maps.Map(document.getElementById('map'), {
    zoom: 4.6,
    center: {lat: 38.2284531, lng: -95.166094},
    styles: mapStyle,
    mapTypeControl: false,
    streetViewControl: false,
  });

  map.data.loadGeoJson('file.json', {idPropertyName: 'store_id'});
  map.data.setStyle({
    icon: {url: 'images/mail_icon.svg', scaledSize: new google.maps.Size(32, 32)},
  });

  const apiKey = getMapsApiKey();
  const infoWindow = new google.maps.InfoWindow();

  function openInfoWindow(feature) {
    const name = feature.getProperty('name');
    const url = feature.getProperty('url');
    const address = feature.getProperty('address');
    const position = feature.getGeometry().get();
    const streetView = apiKey
      ? `<p><img alt="Street view of ${escapeHtml(name)}" src="https://maps.googleapis.com/maps/api/streetview?size=350x120&location=${position.lat()},${position.lng()}&key=${encodeURIComponent(apiKey)}"></p>`
      : '';
    infoWindow.setContent(`
      <div class="info_window">
        <h2>${escapeHtml(name)}</h2>
        <p><b>Address:</b> ${escapeHtml(address)}</p>
        <p><a href="${escapeHtml(url)}" target="_blank" rel="noopener">USPS location details</a></p>
        ${streetView}
      </div>`);
    infoWindow.setPosition(position);
    infoWindow.setOptions({pixelOffset: new google.maps.Size(0, -30)});
    infoWindow.open(map);
  }

  map.data.addListener('click', (event) => openInfoWindow(event.feature));

  // Search card (top right of the map).
  const card = document.createElement('div');
  card.id = 'pac-card';
  const title = document.createElement('div');
  title.id = 'pac_title';
  title.textContent = 'Search for Nearby GMAs:';
  const container = document.createElement('div');
  container.id = 'pac-container';
  const input = document.createElement('input');
  input.id = 'pac-input';
  input.type = 'text';
  input.placeholder = 'Enter an address here...';
  container.appendChild(input);
  card.appendChild(title);
  card.appendChild(container);
  map.controls[google.maps.ControlPosition.TOP_RIGHT].push(card);

  // Results panel (top left of the map).
  const panel = document.createElement('div');
  panel.id = 'panel';
  map.controls[google.maps.ControlPosition.LEFT_TOP].push(panel);

  const autocomplete = new google.maps.places.Autocomplete(input, {
    types: ['address'],
    componentRestrictions: {country: 'us'},
    fields: ['geometry', 'name'],
  });

  const originMarker = new google.maps.Marker({map: map, visible: false});

  autocomplete.addListener('place_changed', async () => {
    const place = autocomplete.getPlace();
    if (!place.geometry || !place.geometry.location) {
      window.alert(`No address found for "${place.name}". Please pick a suggestion from the list.`);
      return;
    }
    const origin = place.geometry.location;
    map.setCenter(origin);
    map.setZoom(9);
    originMarker.setPosition(origin);
    originMarker.setVisible(true);

    renderPanel(panel, [], 'Finding nearby General Delivery locations…');
    const ranked = await rankLocations(map.data, origin);
    renderPanel(panel, ranked, ranked.length ? '' : 'No locations found.', (store) => {
      const feature = map.data.getFeatureById(store.storeId);
      map.panTo(feature.getGeometry().get());
      map.setZoom(13);
      openInfoWindow(feature);
    });
  });
}

// Rank every location by straight-line distance, keep the closest
// MAX_RANKED_RESULTS, then ask the Distance Matrix API for driving distances
// to those. Falls back to straight-line distances if that call fails.
async function rankLocations(data, origin) {
  const candidates = [];
  data.forEach((feature) => {
    const location = feature.getGeometry().get();
    candidates.push({
      storeId: feature.getProperty('store_id'),
      name: feature.getProperty('name'),
      address: feature.getProperty('address'),
      location: location,
      distanceVal: haversineMetres(origin, location),
    });
  });
  candidates.sort((a, b) => a.distanceVal - b.distanceVal);
  const nearest = candidates.slice(0, MAX_RANKED_RESULTS);
  if (nearest.length === 0) return [];

  try {
    const service = new google.maps.DistanceMatrixService();
    const response = await new Promise((resolve, reject) => {
      service.getDistanceMatrix({
        origins: [origin],
        destinations: nearest.map((c) => c.location),
        travelMode: google.maps.TravelMode.DRIVING,
        unitSystem: google.maps.UnitSystem.IMPERIAL,
      }, (result, status) => {
        if (status === google.maps.DistanceMatrixStatus.OK) resolve(result);
        else reject(new Error(`Distance Matrix failed: ${status}`));
      });
    });
    const elements = response.rows[0].elements;
    nearest.forEach((c, i) => {
      const el = elements[i];
      if (el && el.status === 'OK') {
        c.distanceVal = el.distance.value;
        c.distanceText = `${el.distance.text} driving`;
      } else {
        c.distanceText = `${formatMiles(c.distanceVal)} (straight line)`;
      }
    });
    nearest.sort((a, b) => a.distanceVal - b.distanceVal);
  } catch (err) {
    console.warn(err);
    nearest.forEach((c) => { c.distanceText = `${formatMiles(c.distanceVal)} (straight line)`; });
  }
  return nearest;
}

function renderPanel(panel, stores, message, onSelect) {
  panel.replaceChildren();
  if (message) {
    const p = document.createElement('p');
    p.className = 'panel_message';
    p.textContent = message;
    panel.appendChild(p);
  }
  stores.forEach((store) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'place';
    const name = document.createElement('span');
    name.className = 'place_name';
    name.textContent = store.name;
    const distance = document.createElement('span');
    distance.className = 'distanceText';
    distance.textContent = store.distanceText;
    item.append(name, distance);
    if (onSelect) item.addEventListener('click', () => onSelect(store));
    panel.appendChild(item);
  });
  panel.classList.toggle('open', stores.length > 0 || Boolean(message));
}

window.initMap = initMap;
