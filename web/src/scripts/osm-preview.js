'use strict';
/* global $ mapCalc Backbone isNan _ ol THREE performance google ga fbq TRANSLATIONS i18next readCookie createCookie data mapDiameter */
/* eslint quotes:0, space-unary-ops:0, no-alert:0, no-unused-vars:0, no-shadow:0, no-extend-native:0, no-trailing-spaces:0 */

window.initOsmPreview = function(outputs) {
  var previewMapMarker1 = new ol.Overlay({
    element: $("#marker1-overlay")[0]
  });
  var osmDragPanInteraction = new ol.interaction.DragPan();
  var previewMap = new ol.Map({
    target: outputs.map[0],
    interactions: new ol.Collection([
      osmDragPanInteraction
    ]),
    controls: new ol.Collection([
      new ol.control.ScaleLine()
    ]),
    layers: [
      new ol.layer.Tile({
        source: new ol.source.OSM({
        })
      })
    ],
    view: new ol.View({
    }),
    overlays: new ol.Collection([
      previewMapMarker1
    ])
  });

  var previewMapShown = false;
  function updatePreview() {
    var view = previewMap.getView();
    var newCenter = ol.proj.fromLonLat(computeLonLat(data));
    var diameter = mapDiameter();
    var metersPerPixel = mapDiameter() / outputs.map.width();
    var metersPerPixel = mapDiameter() / outputs.map.width();
    var resolutionAtCoords = metersPerPixel / view.getProjection().getPointResolution(1, newCenter);
    view.setResolution(resolutionAtCoords);
    view.setCenter(newCenter);
    previewMapMarker1.setPosition(ol.proj.fromLonLat([ data.get("lon"), data.get("lat") ]));
    
    outputs.currentDiameterMeters.text(diameter.toFixed(0));
    outputs.currentDiameterYards.text((diameter * 1.0936133).toFixed(0));

    if (! previewMapShown) {
      previewMapShown = true;
      previewMap.updateSize();
    }
  }

  // removes duplicate entries from an array
  function removeDuplicates(a) {
    var uniqueArray = a.filter(function(item, pos) {
      return a.indexOf(item) === pos;
    });
    return uniqueArray;
  } 
 
  // Generates the contents of the List of Points of Interest in a Map
  // (based on the parsed osmPOIhtml Data file, picking out important nodes)
  function updatePointsOfInterestMapContent(url) {
    // Extract the names of tags from the html
    
    // The dictionary that will hold keys and values such that each key is a category
    // and each value is a list of features from that category
    var categories = {};
    
    // The list of elements from the body of the html file (we only care about the body)
    var elements = new DOMParser().parseFromString(osmPOIhtml, "text/html").body.childNodes;

    // A variable that will keep track of the most recent category seen so we know
    // which category each feature belongs to
    var currentCategory;

    // Loop through each element (some are blank, others are categories, and the rest are features)
    for (var i = 0; i < elements.length; i++) {
      var element = elements[i];

      if (element.nodeType === 1) { // Otherwise, this element is blank
        if (element.tagName === "H2") { // This element is a category  
          categories[element.innerHTML] = [];
          currentCategory = element.innerHTML;
        } else if (element.tagName === "P") { // This element is a feature
          if (currentCategory === undefined) {
            console.log("ERROR: The format of the provided html is unexpected. " + 
                        "Expected a category name to come before any feature name.");
            break;
          } else if (element.hasChildNodes()) {
            categories[currentCategory].push(element.firstChild.innerHTML); 
          }
        }
      }
    }

    // the HTML string
    var contentHTMLString = ""; 

    // Putting all the categories and their features in the HTML string
    for (var category in categories) {
      contentHTMLString += '<h3><u>' + category + ' Included in Map:</u></h3>';
      contentHTMLString += '<p><ul style="padding-left: 20px;">';
      
      var features = removeDuplicates(categories[category]);
      for (var i = 0; i < features.length; i++) {
        contentHTMLString += '<li><b>' + features[i] + '</b></li>';
      }

      contentHTMLString += '</ul><p><br>';
    }

    contentHTMLString += '<br><br><b>Current HTML Data (Remove):</b><br><br>' + osmPOIhtml; 
 
    // Update Points of Interes from Map Content as a list of Map Elements
    var elm = getElementInsideContainer('mainArea', 'pointsOfInterestMapContent');
    elm.innerHTML = contentHTMLString;
  }                                                              

  // Calculates the new bounded region and updates the OSM Data that 
  // matches this newly bounded region. Uses the OverPass API to grab 
  // the updated Points of Interest data as an HTML string. Updates 
  // osmPOIhtml variable with the HTML returned contents.
  // May need to fix to support Multipart Maps
  function getUpdatedOSMData() {
    var radius = mapDiameter() / 2;
    var metersPerDeg = mapCalc.metersPerDegree(data.get("lat"));
    var degreesLon = 1 / metersPerDeg.lon * radius;
    var degreesLat = 1 / metersPerDeg.lat * radius;
    var posLonLat = computeLonLat(data);

    var lonMin = posLonLat[0] - degreesLon;
    var lonMax = posLonLat[0] + degreesLon;
    var latMin = posLonLat[1] - degreesLat;
    var latMax = posLonLat[1] + degreesLat;

    // Calling Overpass API Popup Query
    var bbox = "" + latMin + "," + lonMin + "," + latMax + "," + lonMax;
    var url = "http://overpass-api.de/api/interpreter?data=[out:popup(\"Points of Interest\";[name][highway!~\".\"][railway!~\".\"][landuse!~\".\"][type!~\"route|network|associatedStreet\"][public_transport!~\".\"][route!~\"bus|ferry|railway|train|tram|trolleybus|subway|light_rail\"];\"name\";)(\"Streets\";[highway~\"primary|secondary|tertiary|residential|unclassified\"];\"name\";)(\"Public Transport Stops\";[name][highway~\"bus_stop|tram_stop\"];[name][railway~\"halt|station|tram_stop\"];\"name\";)(\"Public Transport Lines\";[route~\"bus|ferry|railway|train|tram|trolleybus|subway|light_rail|monorail\"];\"name\";)];(node(" + bbox + ");<;);out;";

    // JQuery GET request to grab OSM data from the url
    $.get(url, function( osmDataHTML ) {
       // Note: the variable osmPOIhtml lives in util.js (to make it more public); Look there for details
       osmPOIhtml = osmDataHTML; 
 
       console.log("\n### Successfully Loaded new OSM Data (as HTML String) ###\n" );

       // Update the Points of Interest Map Contents
       updatePointsOfInterestMapContent(url);        
     });
  }

  // Printings informaton about the bounding box of the currently
  // displayed map (used mostly for debugging purposes)
  function printMapRegionDimensions() {
    console.log("\n### Data Values ###");
    console.log('latitude : ' + data.get("lat"));
    console.log('longitude: ' + data.get("lon"));
    console.log('offsetX  : ' + data.get("offsetX"));
    console.log('offsetY  : ' + data.get("offsetY"));
    console.log('scale    : ' + data.get("scale"));
    console.log('size     : ' + data.get("size"));
    console.log('map diameter:   ' + mapDiameter());
    console.log('center point: ' + computeLonLat(data));  
    console.log('multipartXpc: ' + data.get("multipartXpc"));
    console.log('multipartYpc: ' + data.get("multipartYpc"));
  }

  // Update View & corresponding OSM Data when relevant parameters change
  data.on("change:lon change:lat change:size change:offsetX change:offsetY change:scale change:multipartXpc change:multipartYpc", function() {
    if (! (data.get("lat") && data.get("lon") && data.get("size"))) {
      return;
    }
    $("#map-area-preview-container").show();
    updatePreview();

    //printMapRegionDimensions();
    
    // Grab osm data for this map region centered at computeLonLat() with
    // offset X & Y from the latitude (lat) & longitude (lon) of the point of interest
    getUpdatedOSMData();
  }); // end of data.on

  // Map panning
  previewMap.on("moveend", function(ev){
    if (data.get("multipartMode")) {
        return;
    }

    var metersPerDeg = mapCalc.metersPerDegree(data.get("lat"));
    var newCenter = ol.proj.toLonLat(previewMap.getView().getCenter());
    var offsetX = Math.round((newCenter[0] - data.get("lon")) * metersPerDeg.lon);
    var offsetY = Math.round((newCenter[1] - data.get("lat")) * metersPerDeg.lat);
    var maxOffset = mapDiameter() / 2 * 0.9;
    var fixPreview = false;
    if (Math.abs(offsetX) > maxOffset) {
      fixPreview = true;
      offsetX = Math.round(Math.sign(offsetX) * maxOffset);
    }
    if (Math.abs(offsetY) > maxOffset) {
      fixPreview = true;
      offsetY = Math.round(Math.sign(offsetY) * maxOffset);
    }
    $("#x-offset-input").val(offsetX);
    $("#y-offset-input").val(offsetY);
    data.set("offsetX", offsetX, { silent: false }); // used to be true
    data.set("offsetY", offsetY, { silent: false }); // used to be true
    if (fixPreview) {
      updatePreview();
    }
  });

  // Show preview when user arrives via back button or browser wake-up.
  $(window).on('pageshow', function(){
    previewMapShown = false;
    updatePreview();
  });
  data.on("initdone", function(){
    previewMapShown = false;
    updatePreview();
  });

  return osmDragPanInteraction;
};
