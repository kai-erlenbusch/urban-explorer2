import * as turf from '@turf/turf';
import RBush from 'rbush';

// Global cache for the index so we don't rebuild it every frame
let demographicsIndex = null;

/**
 * Builds the index. Call this ONCE when data is loaded.
 * @param {Array} features 
 */
export function buildDemographicsIndex(features) {
    const index = new RBush();
    const items = features.map(f => {
        // RBush expects {minX, minY, maxX, maxY, item}
        const coords = f.geometry.coordinates;
        return {
            minX: coords[0],
            minY: coords[1],
            maxX: coords[0],
            maxY: coords[1],
            feature: f
        };
    });
    index.load(items);
    demographicsIndex = index;
    return index;
}

/**
 * Calculates Land Use statistics based on features within a lens.
 * @param {Array} features - Array of GeoJSON features from 'pluto-fill'
 * @param {Object} lensGeo - The GeoJSON geometry of the analysis lens (circle)
 * @returns {Object} - { count, area, breakdown, entropy }
 */
export function calculateLandUse(features, lensGeo) {
    let totalArea = 0;
    let counts = {};
    const seenIds = new Set();

    features.forEach(f => {
        const uniqueId = f.id || f.properties.BBL || f.properties.LotArea;
        if (seenIds.has(uniqueId)) return;

        if (turf.booleanIntersects(f, lensGeo)) {
            seenIds.add(uniqueId);
            const rawLU = f.properties.LandUse;
            // Sq Meters to Acres conversion roughly
            const area = (f.properties.LotArea || turf.area(f)) * 0.000247105;

            if (rawLU) {
                const cleanKey = parseInt(String(rawLU), 10).toString();
                if (cleanKey && cleanKey !== "NaN") {
                    if (!counts[cleanKey]) counts[cleanKey] = 0;
                    counts[cleanKey] += area;
                    totalArea += area;
                }
            }
        }
    });

    let entropy = 0;
    if (totalArea > 0) {
        let H = 0;
        Object.values(counts).forEach(a => {
            const p = a / totalArea;
            if (p > 0) H -= p * Math.log(p);
        });
        entropy = H / Math.log(11);
    }

    return { count: seenIds.size, area: totalArea, breakdown: counts, entropy };
}

/**
 * Calculates Demographic statistics based on census dots (Optimized with RBush).
 * @param {Array} features - Array of GeoJSON features (or empty if using index)
 * @param {Object} centerPoint - Turf point of the lens center
 * @param {number} radiusMiles - Radius of the lens in miles
 * @returns {Object} - { totalPeople, density, ethnicityBreakdown, diversityIndex, percentFemale, ageBreakdown }
 */
export function calculateDemographics(features, centerPoint, radiusMiles) {
    let candidates = features;
    
    // 1. OPTIMIZATION: If we have an index, filter candidates first
    if (demographicsIndex) {
        const rDeg = radiusMiles / 60; // Approx degrees
        const [cx, cy] = centerPoint.geometry.coordinates;
        
        const results = demographicsIndex.search({
            minX: cx - rDeg,
            minY: cy - rDeg,
            maxX: cx + rDeg,
            maxY: cy + rDeg
        });
        candidates = results.map(r => r.feature);
    }

    // 2. Exact Distance Check & Stats Aggregation
    let totalPeople = 0;
    let ethnicityCounts = {};
    let femaleCount = 0;
    let ageCounts = { '0-4': 0, '5-17': 0, '18-34': 0, '35-59': 0, '60+': 0 };

    const radiusKm = radiusMiles * 1.60934;

    candidates.forEach(f => {
        const pt = turf.point(f.geometry.coordinates);
        if (turf.distance(centerPoint, pt, { units: 'kilometers' }) <= radiusKm) {
            const pop = f.properties.pop_est || 1;
            totalPeople += pop;

            // Ethnicity
            const eth = f.properties.ethnicity || 'Other';
            if (!ethnicityCounts[eth]) ethnicityCounts[eth] = 0;
            ethnicityCounts[eth] += pop;

            // Gender
            if (f.properties.sex === 'Female') femaleCount += pop;

            // Age
            const age = f.properties.age_group;
            if (age && ageCounts[age] !== undefined) ageCounts[age] += pop;
        }
    });

    let sumSquares = 0;
    if (totalPeople > 0) {
        Object.values(ethnicityCounts).forEach(count => {
            const p = count / totalPeople;
            sumSquares += p * p;
        });
    }

    return {
        totalPeople,
        density: totalPeople / (Math.PI * radiusMiles * radiusMiles * 640),
        ethnicityBreakdown: ethnicityCounts,
        diversityIndex: totalPeople > 0 ? (1 - sumSquares) : 0,
        percentFemale: totalPeople > 0 ? (femaleCount / totalPeople) * 100 : 0,
        ageBreakdown: ageCounts
    };
}

/**
 * Calculates Transit connectivity statistics.
 * @param {Object} featureSets - Object containing arrays of features for different layers
 * @param {Object} centerPoint - Turf point of the lens center
 * @param {number} radiusMiles - Radius of the lens in miles
 * @returns {Object} - { subwayStationCount, subwayLines, railStationCount, railLines, busStopCount, busLines }
 */
export function calculateTransit(featureSets, centerPoint, radiusMiles) {
    const radiusKm = radiusMiles * 1.60934;
    const { subStations, subTracks, railStations, railTracks, busStops, busLines } = featureSets;

    // --- Subway ---
    const foundSubLines = new Set();
    let subCount = 0;

    subStations.forEach(f => {
        const pt = turf.point(f.geometry.coordinates);
        if (turf.distance(centerPoint, pt, { units: 'kilometers' }) <= radiusKm) {
            subCount++;
            const linesStr = f.properties.trains || f.properties.lines || f.properties.name || "";
            const parts = linesStr.split(/[\s-]+/);
            parts.forEach(p => {
                if (/^[A-Z0-9]+$/.test(p) && p.length <= 2) foundSubLines.add(p);
            });
        }
    });

    subTracks.forEach(f => {
        const line = f.properties.route_id || f.properties.route_shor || f.properties.name;
        if (line) foundSubLines.add(line);
    });

    // --- Rail ---
    const foundRailLines = new Set();
    let railCount = 0;

    const identifyAgency = (layerId) => {
        if (!layerId) return null;
        if (layerId.includes("lirr")) return "LIRR";
        if (layerId.includes("mnr")) return "Metro-North";
        if (layerId.includes("njt")) return "NJ Transit";
        if (layerId.includes("amtrak")) return "Amtrak";
        if (layerId.includes("path")) return "PATH";
        return null;
    };

    railStations.forEach(f => {
        const pt = turf.point(f.geometry.coordinates);
        if (turf.distance(centerPoint, pt, { units: 'kilometers' }) <= radiusKm) {
            railCount++;
            const agency = identifyAgency(f.layer.id);
            if (agency) foundRailLines.add(agency);
        }
    });

    railTracks.forEach(f => {
        const agency = identifyAgency(f.layer.id);
        if (agency) foundRailLines.add(agency);
    });

    // --- Bus ---
    let busStopCount = 0;
    busStops.forEach(f => {
        const pt = turf.point(f.geometry.coordinates);
        if (turf.distance(centerPoint, pt, { units: 'kilometers' }) <= radiusKm) busStopCount++;
    });

    const foundBusLines = new Set();
    busLines.forEach(f => {
        const props = f.properties;
        const name = props.route_id || props.route_short_name || props.route_short || props.ref || props.name;
        if (name) {
            const cleanName = name.split(' ')[0];
            if (cleanName.length > 0 && cleanName.length < 6) foundBusLines.add(cleanName);
            else foundBusLines.add(name);
        }
    });

    return {
        subwayStationCount: subCount,
        subwayLines: Array.from(foundSubLines).sort(),
        railStationCount: railCount,
        railLines: Array.from(foundRailLines).sort(),
        busStopCount: busStopCount,
        busLines: Array.from(foundBusLines).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    };
}