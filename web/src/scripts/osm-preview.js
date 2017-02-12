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

  // Calculates the new bounded region and updates the OSM Data that 
  // matches this newly bounded region. Uses the OverPass API to grab 
  // the updated data in the form of an XML file. Updates osmDataXMLString 
  // variable with the String representation of this XML file.
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

    // Specifically calling Overpass API for testing...
    var bbox = "" + lonMin + "," + latMin + "," + lonMax + "," + latMax;
    var url = "http://overpass.osm.rambler.ru/cgi/xapi?map?bbox=" + bbox;

    // JQuery GET request to grab OSM data from the url
    $.get(url, function( osmDataXML ) {
       // Note: the variable osmDataXMLString lives in util.js (to make it more public); Look there for details
       osmDataXMLString = new XMLSerializer().serializeToString(osmDataXML.documentElement); // XML file with OSM tags & nodes
 
       console.log("\n### Successfully Loaded new OSM Data (as XML String) ###\n" );
    });
  }

  // Printings informaton about the bounding box of the currently
  // displayed map (used mostly for debugging purposes)
  function printMapRegionDimensions() {
    console.log('latitude : ' + data.get("lat"));
    console.log('longitude: ' + data.get("lon"));
    console.log('offsetX  : ' + data.get("offsetX"));
    console.log('offsetY  : ' + data.get("offsetY"));
    console.log('scale    : ' + data.get("scale"));
    console.log('size     : ' + data.get("size"));
    console.log('map diameter:   ' + mapDiameter());
    console.log('center point: ' + computeLonLat(data) + '\n');  
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
