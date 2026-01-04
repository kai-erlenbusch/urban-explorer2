<script>
  import { onMount, onDestroy } from 'svelte';
  import { activeLayer, analysisData, demographicsData, transitData, radius } from './stores.js';
  import maplibregl from 'maplibre-gl';
  import * as turf from '@turf/turf';
  import 'maplibre-gl/dist/maplibre-gl.css';
  
  // IMPORT THE NEW LOGIC
  import { calculateLandUse, calculateDemographics, calculateTransit } from './analysis.js';

  /** @type {maplibregl.Map} */
  let map;
  let mapContainer;
  let currentRadius;
  let cursorPosition = null;
  let currentMode = 'landuse';
  
  // Performance Throttling
  let animationFrameId;
  let isUpdating = false;
  let analysisTimeout; // Timer for debouncing

  // --- CONFIGURATION ---
  // ⚠️ ACTION REQUIRED: Use an environment variable in production!
  const MAPBOX_TOKEN = 'pk.eyJ1Ijoia2FpLWVybGVuYnVzY2giLCJhIjoiY21qZzM5Z3FnMHk3MTNkcHNrcDJ0ajFpNyJ9.X4SxJOFBNAxGo8G5qHLKXA';
  
  const LANDUSE_TILESET_ID = 'mapbox://kai-erlenbusch.9a769cf2';
  const LANDUSE_SOURCE_LAYER = 'mn_mappluto-d8n2zk';
  const CENSUS_TILESET_ID = 'mapbox://kai-erlenbusch.0ua9vbjj';
  const CENSUS_SOURCE_LAYER = 'census_dots_full';
  const TRANSIT_TILESET_ID = 'mapbox://kai-erlenbusch.ydqfgcin';

  // 60fps Masking: The outer boundary of the "world"
  const WORLD_RING = [
    [-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]
  ];

  // --- STORES ---
  const unsubscribeRadius = radius.subscribe(value => {
    currentRadius = value;
    if (map && cursorPosition) triggerUpdate(cursorPosition);
  });

  const unsubscribeLayer = activeLayer.subscribe(value => {
    currentMode = value;
    if (!map || !map.isStyleLoaded()) return;
    
    const isLandUse = value === 'landuse';
    const isDemo = value === 'demographics';
    const isTransit = value === 'transit';

    // 1. Toggle Data Layers
    if (map.getLayer('pluto-fill')) map.setLayoutProperty('pluto-fill', 'visibility', isLandUse ? 'visible' : 'none');
    if (map.getLayer('pluto-lines')) map.setLayoutProperty('pluto-lines', 'visibility', isLandUse ? 'visible' : 'none');
    if (map.getLayer('census-dots')) map.setLayoutProperty('census-dots', 'visibility', isDemo ? 'visible' : 'none');

    const transitIds = [
        'transit-bus-lines', 'transit-bus-stops', 'transit-subway-lines', 'transit-subway-stations',
        'transit-rail-lines-rail_lirr_routes', 'transit-rail-lines-rail_mnr_routes', 
        'transit-rail-lines-rail_njt_routes', 'transit-rail-lines-rail_amtrak_routes', 'transit-rail-lines-rail_path_routes',
        'transit-rail-stations-rail_lirr_stops', 'transit-rail-stations-rail_mnr_stops', 
        'transit-rail-stations-rail_njt_stops', 'transit-rail-stations-rail_amtrak_stops', 'transit-rail-stations-rail_path_stops'
    ];

    transitIds.forEach(id => {
        if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', isTransit ? 'visible' : 'none');
    });

    // 2. TOGGLE MASKS & WATER
    if (map.getLayer('mask-layer-top')) {
         map.setLayoutProperty('mask-layer-top', 'visibility', isTransit ? 'visible' : 'none');
    }
    if (map.getLayer('mask-layer-bottom')) {
         map.setLayoutProperty('mask-layer-bottom', 'visibility', isTransit ? 'none' : 'visible');
    }
    if (map.getLayer('water-rescue')) {
         map.setLayoutProperty('water-rescue', 'visibility', isTransit ? 'visible' : 'none');
    }

    setTimeout(() => {
        if (cursorPosition) triggerUpdate(cursorPosition);
    }, 100);
  });

  // --- OPTIMIZED ENGINE ---
  function triggerUpdate(lngLat) {
      cursorPosition = lngLat;
      if (!isUpdating) {
          isUpdating = true;
          animationFrameId = requestAnimationFrame(() => {
              updateMapState(lngLat);
              isUpdating = false;
          });
      }
  }

  function updateMapState(lngLat) {
    if (!map) return;

    // --- 1. VISUAL UPDATES (RUNS EVERY FRAME - 60FPS) ---
    // These operations are cheap and keep the UI feeling snappy
    const centerPoint = turf.point([lngLat.lng, lngLat.lat]);
    const circleGeo = turf.circle(centerPoint, currentRadius, { steps: 64, units: 'miles' });

    // Update Mask Geometry
    if (map.getSource('mask-source')) {
        const maskGeometry = turf.polygon([
            WORLD_RING, // Outer
            circleGeo.geometry.coordinates[0] // Inner
        ]);
        /** @type {maplibregl.GeoJSONSource} */
        const maskSource = map.getSource('mask-source');
        if (maskSource) maskSource.setData(maskGeometry);
    }

    // Update Lens Outline
    if (map.getSource('lens-source')) {
        /** @type {maplibregl.GeoJSONSource} */
        const lensSource = map.getSource('lens-source');
        if (lensSource) lensSource.setData(circleGeo);
    }

    // --- 2. DATA ANALYSIS (DEBOUNCED) ---
    // We delay the heavy math until the user STOPS moving the mouse for 100ms
    if (analysisTimeout) clearTimeout(analysisTimeout);
    
    analysisTimeout = setTimeout(() => {
        triggerAnalysis(centerPoint, circleGeo);
    }, 100); // Wait 100ms before crunching numbers
  }

  // New function to handle the heavy lifting separately
  function triggerAnalysis(centerPoint, circleGeo) {
    if (currentMode === 'landuse') performLandUseAnalysis(circleGeo);
    else if (currentMode === 'demographics') performDemographicsAnalysis(centerPoint);
    else if (currentMode === 'transit') performTransitAnalysis(centerPoint, circleGeo);
  }

  // --- ANALYSIS WRAPPER FUNCTIONS ---
  
  function performLandUseAnalysis(circleGeo) {
    if (!map) return;
    
    const bbox = turf.bbox(circleGeo);
    const southWest = map.project([bbox[0], bbox[1]]);
    const northEast = map.project([bbox[2], bbox[3]]);
    
    const features = map.queryRenderedFeatures([southWest, northEast], { layers: ['pluto-fill'] });
    const result = calculateLandUse(features, circleGeo);
    analysisData.set(result);
  }

  function performDemographicsAnalysis(centerPoint) {
    if (!map) return;

    // Use queryRenderedFeatures for visual consistency
    const circleGeo = turf.circle(centerPoint, currentRadius, { steps: 10, units: 'miles' });
    const bbox = turf.bbox(circleGeo);
    const p1 = map.project([bbox[0], bbox[1]]);
    const p2 = map.project([bbox[2], bbox[3]]);

    /** @type {[maplibregl.PointLike, maplibregl.PointLike]} */
    const bboxPixels = [p1, p2];

    const features = map.queryRenderedFeatures(bboxPixels, { layers: ['census-dots'] });
    const result = calculateDemographics(features, centerPoint, currentRadius);
    demographicsData.set(result);
  }

  function performTransitAnalysis(centerPoint, circleGeo) {
    if (!map) return;

    const bbox = turf.bbox(circleGeo);
    const p1 = map.project([bbox[0], bbox[1]]);
    const p2 = map.project([bbox[2], bbox[3]]);
    
    /** @type {[maplibregl.PointLike, maplibregl.PointLike]} */
    const bboxPixels = [p1, p2];

    const featureSets = {
        subStations: map.queryRenderedFeatures({ layers: ['transit-subway-stations'] }),
        subTracks: map.queryRenderedFeatures(bboxPixels, { layers: ['transit-subway-lines'] }),
        railStations: map.queryRenderedFeatures({ 
            layers: [
                'transit-rail-stations-rail_lirr_stops', 
                'transit-rail-stations-rail_mnr_stops', 
                'transit-rail-stations-rail_njt_stops', 
                'transit-rail-stations-rail_amtrak_stops', 
                'transit-rail-stations-rail_path_stops'
            ] 
        }),
        railTracks: map.queryRenderedFeatures(bboxPixels, { 
            layers: [
                'transit-rail-lines-rail_lirr_routes', 
                'transit-rail-lines-rail_mnr_routes', 
                'transit-rail-lines-rail_njt_routes', 
                'transit-rail-lines-rail_amtrak_routes', 
                'transit-rail-lines-rail_path_routes'
            ] 
        }),
        busStops: map.queryRenderedFeatures({ layers: ['transit-bus-stops'] }),
        busLines: map.queryRenderedFeatures(bboxPixels, { layers: ['transit-bus-lines'] })
    };

    const result = calculateTransit(featureSets, centerPoint, currentRadius);
    transitData.set(result);
  }

  // --- INITIALIZATION ---
  onMount(async () => {
    // 1. INIT MAP
    map = new maplibregl.Map({
      container: mapContainer,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-73.985, 40.748], 
      zoom: 13,
      minZoom: 9, 
      transformRequest: (url) => {
        if (url.startsWith("mapbox://")) {
          return {
            url: url.replace("mapbox://", "https://api.mapbox.com/v4/") + `.json?access_token=${MAPBOX_TOKEN}`,
            headers: { "Content-Type": "application/json" }
          };
        }
        return { url };
      }
    });

    map.on('load', () => {
      const layers = map.getStyle().layers;

      // 1. HIDE BUILDINGS
      layers.forEach(layer => {
          if (layer.id.includes('building')) {
            map.setLayoutProperty(layer.id, 'visibility', 'none');
          }
      });

      // 2. FIND INSERTION POINT
      let insertionLayerId;
      for (const layer of layers) {
        if (layer.id.includes('water') && layer.type === 'fill') {
          insertionLayerId = layer.id;
          break; 
        }
      }
      if (!insertionLayerId) {
         for (const layer of layers) {
            if (layer.id.includes('road') || layer.type === 'symbol') {
              insertionLayerId = layer.id;
                break;
            }
         }
      }

      // 3. DYNAMIC WATER DETECTION
      let waterSource = null;
      let waterSourceLayer = null;
      let waterColor = '#e0e0e0'; 
      
      /** @type {maplibregl.FillLayerSpecification} */
      // @ts-ignore
      const waterRef = layers.find(l => l.id.includes('water') && l.type === 'fill');

      if (waterRef) {
          waterSource = waterRef.source;
          waterSourceLayer = waterRef['source-layer'];
          if (waterRef.paint && waterRef.paint['fill-color']) {
             if (typeof waterRef.paint['fill-color'] === 'string') {
                waterColor = waterRef.paint['fill-color'];
             }
          }
      }

      // 4. ADD DATA LAYERS
      map.addSource('pluto-data', { type: 'vector', url: LANDUSE_TILESET_ID });
      map.addLayer({
        'id': 'pluto-fill', 'type': 'fill', 'source': 'pluto-data', 'source-layer': LANDUSE_SOURCE_LAYER, 'minzoom': 10,
        'paint': { 
            'fill-color': [
                'match', ['to-string', ['get', 'LandUse']], 
                '01', '#F9EDDB', '1', '#F9EDDB', '02', '#F6D9CB', '2', '#F6D9CB',
                '03', '#F6D9CB', '3', '#F6D9CB', '04', '#F1B89C', '4', '#F1B89C',
                '05', '#DF7649', '5', '#DF7649', '06', '#CF4F4F', '6', '#CF4F4F',
                '07', '#BEC6CC', '7', '#BEC6CC', '08', '#BDE7F4', '8', '#BDE7F4',
                '09', '#A3D393', '9', '#A3D393', '10', '#8DA2B4', '11', '#E4E4E4', '#cccccc'
            ],
            'fill-opacity': 1 
        },
        'layout': { 'visibility': 'visible' }
      }, insertionLayerId);
      
      map.addLayer({
        'id': 'pluto-lines', 'type': 'line', 'source': 'pluto-data', 'source-layer': LANDUSE_SOURCE_LAYER,
        'paint': { 'line-width': 0.5, 'line-opacity': ['interpolate', ['linear'], ['zoom'], 11, 0, 13, 0.6], 'line-color': '#cccccc' },
        'layout': { 'visibility': 'visible' }
      }, insertionLayerId);

      map.addSource('census-source', { type: 'vector', url: CENSUS_TILESET_ID });
      map.addLayer({
        id: 'census-dots', type: 'circle', source: 'census-source', 'source-layer': CENSUS_SOURCE_LAYER, minzoom: 8, 
        paint: {
          'circle-radius': ['interpolate', ['exponential', 1.5], ['zoom'], 8, 1, 16, 4],
          'circle-color': [ 'match', ['get', 'ethnicity'], 'Asian', '#eeae9f', 'Black', '#68c582', 'Hispanic', '#f0ba5e', 'White', '#4674ea', '#b1b1b1' ],
          'circle-opacity': 0.8
        },
        'layout': { 'visibility': 'none' }
      }, insertionLayerId);

      // 5. MASK A: BOTTOM
      map.addSource('mask-source', { 
        type: 'geojson', 
        data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [WORLD_RING] } } 
      });
      
      map.addLayer({
        id: 'mask-layer-bottom', type: 'fill', source: 'mask-source',
        paint: { 'fill-color': '#ffffff', 'fill-opacity': 0.85 },
        layout: { 'visibility': 'visible' }
      }, insertionLayerId);

      // 6. TRANSIT LAYERS
      map.addSource('transit-source', { type: 'vector', url: TRANSIT_TILESET_ID });
      map.addLayer({
        id: 'transit-bus-lines', type: 'line', source: 'transit-source', 'source-layer': 'bus_routes',
        paint: { 'line-color': '#0245ef', 'line-width': 1, 'line-opacity': 0.8 },
        layout: { 'visibility': 'none' }
      });
      map.addLayer({
        id: 'transit-bus-stops', type: 'circle', source: 'transit-source', 'source-layer': 'bus_stops',
        paint: { 'circle-color': '#0245ef', 'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 1, 15, 2.5], 'circle-opacity': 0.6 },
        layout: { 'visibility': 'none' }
      });
      map.addLayer({
        id: 'transit-subway-lines', type: 'line', source: 'transit-source', 'source-layer': 'subway_lines',
        paint: { 'line-width': 2.5, 'line-color': '#ffd73e' },
        layout: { 'visibility': 'none' }
      });
      ['rail_lirr', 'rail_mnr', 'rail_njt', 'rail_amtrak', 'rail_path'].forEach(agency => {
          map.addLayer({
            id: `transit-rail-lines-${agency}_routes`, type: 'line', source: 'transit-source', 'source-layer': `${agency}_routes`,
            paint: { 'line-color': '#ff98ab', 'line-width': 1.5 }, layout: { 'visibility': 'none' }
          });
      });
      map.addLayer({
        id: 'transit-subway-stations', type: 'circle', source: 'transit-source', 'source-layer': 'subway_stations',
        paint: { 'circle-radius': 3.5, 'circle-color': '#ffffff', 'circle-stroke-width': 2, 'circle-stroke-color': '#ffd73e' },
        layout: { 'visibility': 'none' }
      });
      ['rail_lirr', 'rail_mnr', 'rail_njt', 'rail_amtrak', 'rail_path'].forEach(agency => {
          map.addLayer({
            id: `transit-rail-stations-${agency}_stops`, type: 'circle', source: 'transit-source', 'source-layer': `${agency}_stops`,
            paint: { 'circle-radius': 3, 'circle-color': '#ff98ab', 'circle-stroke-width': 1, 'circle-stroke-color': '#fff' }, layout: { 'visibility': 'none' }
          });
      });

      // 7. MASK B: TOP
      map.addLayer({
        id: 'mask-layer-top', type: 'fill', source: 'mask-source',
        paint: { 'fill-color': '#ffffff', 'fill-opacity': 0.85 },
        layout: { 'visibility': 'none' } 
      });

      // 8. WATER RESCUE OVERLAY
      if (waterSource && waterSourceLayer) {
        map.addLayer({
            'id': 'water-rescue',
            'type': 'fill',
            'source': waterSource,
            'source-layer': waterSourceLayer,
            'paint': {
                'fill-color': waterColor,
                'fill-opacity': 1
            },
            'layout': { 'visibility': 'none' } 
        });
      }

      // 9. LENS OUTLINE
      map.addSource('lens-source', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({
        id: 'lens-outline', type: 'line', source: 'lens-source',
        paint: { 'line-color': '#333333', 'line-width': 1.5, 'line-dasharray': [2, 3] }
      });

      map.on('mousemove', (e) => triggerUpdate(e.lngLat));
      updateMapState(map.getCenter());
    });
  });

  onDestroy(() => {
    unsubscribeRadius();
    unsubscribeLayer();
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    if (analysisTimeout) clearTimeout(analysisTimeout);
    if (map) map.remove();
  });
</script>

<div class="map-wrap" bind:this={mapContainer}></div>

<style>
  .map-wrap { width: 100%; height: 100%; position: relative; }
</style>