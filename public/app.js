const mapStyle = [{
  'featureType': 'administrative',
  'elementType': 'all',
  'stylers': [{
    'visibility': 'on',
  },
  {
    'lightness': 33,
  },
  ],
},
{
  'featureType': 'landscape',
  'elementType': 'all',
  'stylers': [{
    'color': '#f2e5d4',
  }],
},
{
  'featureType': 'poi.park',
  'elementType': 'geometry',
  'stylers': [{
    'color': '#c5dac6',
  }],
},
{
  'featureType': 'poi.park',
  'elementType': 'labels',
  'stylers': [{
    'visibility': 'on',
  },
  {
    'lightness': 20,
  },
  ],
},
{
  'featureType': 'road',
  'elementType': 'all',
  'stylers': [{
    'lightness': 20,
  }],
},
{
  'featureType': 'road.highway',
  'elementType': 'geometry',
  'stylers': [{
    'color': '#c5c6c6',
  }],
},
{
  'featureType': 'road.arterial',
  'elementType': 'geometry',
  'stylers': [{
    'color': '#e4d7c6',
  }],
},
{
  'featureType': 'road.local',
  'elementType': 'geometry',
  'stylers': [{
    'color': '#fbfaf7',
  }],
},
{
  'featureType': 'water',
  'elementType': 'all',
  'stylers': [{
    'visibility': 'on',
  },
  {
    'color': '#acbcc9',
  },
  ],
},
];

function initMap() {
    const map = new google.maps.Map(document.getElementById('map'), {
        zoom: 4.61,
        center: {lat: 38.2284531, lng: -95.166094},
        styles: mapStyle
    });

    map.data.loadGeoJson('file.json', {idPropertyName: 'store_id'});

    map.data.setStyle((feature) => {
        return {
          icon: {
            url: `images/mail_icon.svg`,
            scaledSize: new google.maps.Size(32, 32),
          },
        };
      });

    const apiKey = 'AIzaSyDcU7vPIAONsO5GZnOnip7SOI4ElZcGKcE';
    const infoWindow = new google.maps.InfoWindow();

    // Show the information for a store when its marker is clicked.
    map.data.addListener('click', (event) => {
      const name = event.feature.getProperty('name');
      const url = event.feature.getProperty('url');
      const address = event.feature.getProperty('address');
      const position = event.feature.getGeometry().get();
      const content = `
      <img style="float:left; width:80px; margin-top:30px" src="images/mail_icon.svg">
      <div style="margin-left:100px; margin-bottom:20px; margin-top: 20px">
        <h2>${name}</h2>
        <br/>
        <p>
        <b>Details:</b> 
        <br/>
        <a href=${url} >${url}</a><br/><b>Address:</b> ${address}</p>
        <p><img src="https://maps.googleapis.com/maps/api/streetview?size=350x120&location=${position.lat()},${position.lng()}&key=${apiKey}&solution_channel=GMP_codelabs_simplestorelocator_v1_a"></p>
      </div>
      `;
  
      infoWindow.setContent(content);
      infoWindow.setPosition(position);
      infoWindow.setOptions({pixelOffset: new google.maps.Size(0, -30)});
      infoWindow.open(map);
    });

    const card = document.createElement('div');
    const titleBar = document.createElement('div');
    const title = document.createElement('div');
    const container = document.createElement('div');
    const input = document.createElement('input');
    const options = {
        types: ['address'],
        componentRestrictions: {country: 'us'},
    };

    card.setAttribute('id', 'pac-card');
    title.setAttribute('id','pac_title');
    title.textContent = 'Search for Nearby GMAs:';
    titleBar.appendChild(title);
    container.setAttribute('id', 'pac-container');
    input.setAttribute('id', 'pac-input');
    input.setAttribute('type', 'text');
    input.setAttribute('placeholder','Enter an address here...');
    container.appendChild(input);
    card.appendChild(titleBar);
    card.appendChild(container);
    map.controls[google.maps.ControlPosition.TOP_RIGHT].push(card);

    const autocomplete = new google.maps.places.Autocomplete(input,options);
    autocomplete.setFields(
      ['address_components', 'geometry', 'name']
    );
}