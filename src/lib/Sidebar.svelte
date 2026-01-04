<script>
  import { onMount } from 'svelte';
  import { analysisData, demographicsData, transitData, radius, activeLayer } from './stores.js';

  // --- CONFIGURATION ---
  const LU_CATEGORIES = [
    { code: '1', label: 'One & Two Family Buildings', color: '#F9EDDB' },
    { code: '2', label: 'Multi-Family Walk-Up Buildings', color: '#F6D9CB' },
    { code: '3', label: 'Multi-Family Elevator Buildings', color: '#F6D9CB' },
    { code: '4', label: 'Residential & Commercial Mix', color: '#F1B89C' },
    { code: '5', label: 'Commercial & Office', color: '#DF7649' },
    { code: '6', label: 'Industrial & Manufacturing', color: '#CF4F4F' },
    { code: '7', label: 'Transportation & Utility', color: '#BEC6CC' },
    { code: '8', label: 'Public Facilities & Institutions', color: '#BDE7F4' },
    { code: '9', label: 'Open Space & Outdoor Recreation', color: '#A3D393' },
    { code: '10', label: 'Parking Facilities', color: '#8DA2B4' },
    { code: '11', label: 'Vacant Land', color: '#E4E4E4' },
  ];

  const ETH_COLORS = { 'Asian': '#eeae9f', 'Black': '#68c582', 'Hispanic': '#f0ba5e', 'White': '#4674ea', 'Other': '#b1b1b1' };
  const AGE_LABELS = ['0-4', '5-17', '18-34', '35-59', '60+'];
  const R = 18;
  const CIRCUMFERENCE = 2 * Math.PI * R;

  // --- SUBWAY COLORS (Requested) ---
  const SUBWAY_COLORS = {
      'A': '#2953ad', 'C': '#2953ad', 'E': '#2953ad',
      'B': '#fd621a', 'D': '#fd621a', 'F': '#fd621a', 'M': '#fd621a',
      '1': '#ec352e', '2': '#ec352e', '3': '#ec352e',
      '4': '#00933a', '5': '#00933a', '6': '#00933a',
      'S': '#7e8283',
      '7': '#b934ad',
      'J': '#986535', 'Z': '#986535',
      'L': '#a8a9ac',
      'N': '#feca08', 'Q': '#feca08', 'R': '#feca08', 'W': '#feca08'
  };

  let donutSegments = [];
  let indicatorData = [];
  let ethSegments = [];
  let waffleDots = [];
  let maxAgeVal = 0;

  let sectionRefs = {}; 

  onMount(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          activeLayer.set(entry.target.id);
        }
      });
    }, { root: null, rootMargin: '-40% 0px -40% 0px', threshold: 0 });

    ['landuse', 'demographics', 'transit'].forEach(id => {
        if (sectionRefs[id]) observer.observe(sectionRefs[id]);
    });

    return () => observer.disconnect();
  });

  $: {
    // Land Use & Demo Logic
    const luData = $analysisData;
    const dData = $demographicsData;
    let accumulatedPercent = 0;
    const rawSegments = LU_CATEGORIES.map(cat => {
        const key = cat.code; 
        const altKey = parseInt(cat.code).toString();
        const categoryAcres = luData.breakdown ? (luData.breakdown[key] || luData.breakdown[altKey] || 0) : 0;
        const pct = (luData.area > 0) ? (categoryAcres / luData.area) : 0;
        return { ...cat, pct, categoryAcres };
    });
    donutSegments = rawSegments.map(seg => {
        const segmentLength = seg.pct * CIRCUMFERENCE;
        const rotation = (accumulatedPercent * 360) - 90;
        accumulatedPercent += seg.pct;
        return { ...seg, dashArray: `${segmentLength} ${CIRCUMFERENCE}`, rotation: rotation, displayPct: (seg.pct * 100).toFixed(1) };
    });
    indicatorData = rawSegments.filter(seg => ['9', '11'].includes(seg.code)).map(seg => {
        const segmentLength = seg.pct * CIRCUMFERENCE;
        return { label: seg.label, color: seg.color, displayPct: (seg.pct * 100).toFixed(1), dashArray: `${segmentLength} ${CIRCUMFERENCE}` };
    });
    const total = dData.totalPeople || 1; 
    const entries = Object.keys(dData.ethnicityBreakdown || {}).length > 0 ? Object.entries(dData.ethnicityBreakdown) : [['No Data', 0]];
    entries.sort((a, b) => b[1] - a[1]); 
    ethSegments = entries.map(([label, count]) => {
        const pct = count / total;
        return { label, count, color: ETH_COLORS[label] || '#ccc', displayPct: (pct * 100).toFixed(1) };
    });
    waffleDots = [];
    ethSegments.forEach(seg => {
        const numDots = Math.round(parseFloat(seg.displayPct)); 
        for (let i = 0; i < numDots; i++) { if (waffleDots.length < 100) waffleDots.push({ color: seg.color }); }
    });
    while (waffleDots.length < 100) waffleDots.push({ color: '#eee' }); 
    const ageVals = Object.values(dData.ageBreakdown || {});
    maxAgeVal = Math.max(...ageVals, 1); 
  }
</script>

<div class="sidebar">
  <div class="header-container">
      <div class="header-content">
        <h1>{#if $activeLayer === 'landuse'}Land Use{:else if $activeLayer === 'demographics'}Demographics{:else}Transit Network{/if}</h1>
        <div class="control-group">
            <label for="radius">Pedshed Radius: <strong>{$radius} mi</strong></label>
            <input id="radius" type="range" min="0.1" max="1.0" step="0.05" bind:value={$radius} />
        </div>
      </div>
  </div>

  <div class="scroll-content">
      <section id="landuse" bind:this={sectionRefs['landuse']}>
        <div class="section-label">01. Land Use</div>
        <div class="metrics-grid">
            <div class="metric"><span class="value">{$analysisData.count.toLocaleString()}</span><span class="label">Lots</span></div>
            <div class="metric"><span class="value">{$analysisData.area ? $analysisData.area.toFixed(1) : '0.0'} <small>ac</small></span><span class="label">Lot Area</span></div>
            <div class="metric entropy-metric">
                <div class="donut-wrapper">
                    <svg width="50" height="50" viewBox="0 0 40 40">
                        <circle cx="20" cy="20" r={R} fill="none" stroke="#eee" stroke-width="4" />
                        {#each donutSegments as seg}
                            <circle cx="20" cy="20" r={R} fill="none" stroke={seg.color} stroke-width="4" stroke-dasharray={seg.dashArray} transform="rotate({seg.rotation} 20 20)" />
                        {/each}
                    </svg>
                    <span class="value centered">{$analysisData.entropy ? $analysisData.entropy.toFixed(2) : '0.00'}</span>
                </div>
                <span class="label">Entropy Score</span>
            </div>
        </div>
        <div class="category-list">
            <h3>Categories</h3>
            {#each donutSegments as cat} <div class="category-row"><div class="cat-info"><span class="cat-name">{cat.label}</span><span class="cat-val">{cat.displayPct}%</span></div><div class="progress-bar-bg"><div class="progress-bar-fill" style:width="{cat.displayPct}%" style:background-color={cat.color}></div></div></div>{/each}
        </div>
        <div class="indicators-section">
            <h3>Key Indicators</h3>
            <div class="indicator-grid">
              {#each indicatorData as ind}
                <div class="indicator-card">
                  <div class="donut-mini">
                    <svg width="60" height="60" viewBox="0 0 40 40">
                      <circle cx="20" cy="20" r={R} fill="none" stroke="#eee" stroke-width="4" />
                      <circle cx="20" cy="20" r={R} fill="none" stroke={ind.color} stroke-width="4" stroke-dasharray={ind.dashArray} transform="rotate(-90 20 20)" />
                      <text x="50%" y="55%" text-anchor="middle" font-size="8" font-weight="bold" fill="#333">{ind.displayPct}%</text>
                    </svg>
                  </div>
                  <span class="label">{ind.label}</span>
                </div>
              {/each}
            </div>
        </div>
      </section>

      <hr class="section-divider" />

      <section id="demographics" bind:this={sectionRefs['demographics']}>
        <div class="section-label">02. Demographics</div>
        <div class="metrics-grid">
            <div class="metric"><span class="value">{$demographicsData.totalPeople.toLocaleString()}</span><span class="label">People</span></div>
            <div class="metric"><span class="value">{$demographicsData.density.toFixed(1)}</span><span class="label">People / Acre</span></div>
        </div>
        <div class="section-container">
            <h3>Race / Ethnicity</h3>
            <div class="race-layout">
                <div class="waffle-chart">{#each waffleDots as dot}<div class="waffle-dot" style:background-color={dot.color}></div>{/each}</div>
                <div class="race-list">{#each ethSegments as cat} <div class="race-row"><span class="race-dot" style:background-color={cat.color}></span><span class="race-name">{cat.label}</span><span class="race-val">{cat.displayPct}%</span></div>{/each}</div>
            </div>
        </div>
        <div class="section-container">
            <h3>Age Distribution</h3>
            <div class="age-chart">
                {#each AGE_LABELS as label}
                    {@const count = $demographicsData.ageBreakdown[label] || 0}
                    {@const heightPct = maxAgeVal > 0 ? (count / maxAgeVal) * 100 : 0}
                    <div class="age-col"><div class="bar-container"><div class="bar-fill" style:height="{heightPct}%"></div></div><span class="age-label">{label}</span><span class="age-val">{count}</span></div>
                {/each}
            </div>
        </div>
        <div class="indicators-section">
            <div class="indicator-grid">
                <div class="indicator-card"><div class="donut-mini"><svg width="60" height="60" viewBox="0 0 40 40"><circle cx="20" cy="20" r={R} fill="none" stroke="#eee" stroke-width="4" /><circle cx="20" cy="20" r={R} fill="none" stroke="#333" stroke-width="4" stroke-dasharray="{($demographicsData.percentFemale / 100) * CIRCUMFERENCE} {CIRCUMFERENCE}" transform="rotate(-90 20 20)" /><text x="50%" y="55%" text-anchor="middle" font-size="8" font-weight="bold" fill="#333">{$demographicsData.percentFemale.toFixed(1)}%</text></svg></div><span class="label">Percent Female</span></div>
                <div class="indicator-card"><div class="donut-mini"><svg width="60" height="60" viewBox="0 0 40 40"><circle cx="20" cy="20" r={R} fill="none" stroke="#eee" stroke-width="4" /><circle cx="20" cy="20" r={R} fill="none" stroke="#4674ea" stroke-width="4" stroke-dasharray="{$demographicsData.diversityIndex * CIRCUMFERENCE} {CIRCUMFERENCE}" transform="rotate(-90 20 20)" /><text x="50%" y="55%" text-anchor="middle" font-size="8" font-weight="bold" fill="#333">{$demographicsData.diversityIndex.toFixed(2)}</text></svg></div><span class="label">Diversity Index</span></div>
            </div>
        </div>
      </section>

      <hr class="section-divider" />

      <section id="transit" bind:this={sectionRefs['transit']}>
        <div class="section-label">03. Transit Network</div>
        
        <div class="transit-groups">
            <div class="transit-group">
                <div class="group-header">
                    <span class="indicator-dot subway"></span>
                    <h4>Subway Network</h4>
                </div>
                <div class="pill-container">
                    {#if $transitData.subwayLines.length === 0}
                        <span class="empty-state">No lines nearby</span>
                    {:else}
                        {#each $transitData.subwayLines as line}
                            {@const bg = SUBWAY_COLORS[line] || '#333'}
                            {@const isYellow = ['N','Q','R','W'].includes(line)}
                            <span class="line-pill" 
                                  style:background-color={bg} 
                                  style:color={isYellow ? '#000' : '#fff'}>
                                {line}
                            </span>
                        {/each}
                    {/if}
                </div>
                <div class="metric-row">
                    <span class="label">Stations within radius</span>
                    <span class="value-small">{$transitData.subwayStationCount}</span>
                </div>
            </div>

            <div class="transit-group">
                <div class="group-header">
                    <span class="indicator-dot rail"></span>
                    <h4>Railroads</h4>
                </div>
                <div class="pill-container">
                     {#if $transitData.railLines.length === 0}
                        <span class="empty-state">No rail nearby</span>
                    {:else}
                        {#each $transitData.railLines as line}
                            <span class="rail-pill active">{line}</span>
                        {/each}
                    {/if}
                </div>
                 <div class="metric-row">
                    <span class="label">Stations within radius</span>
                    <span class="value-small">{$transitData.railStationCount}</span>
                </div>
            </div>

            <div class="transit-group">
                <div class="group-header">
                    <span class="indicator-dot bus"></span>
                    <h4>Bus Network</h4>
                </div>
                 <div class="pill-container">
                    {#if $transitData.busLines.length === 0}
                        <span class="empty-state">No bus stops nearby</span>
                    {:else}
                        {#each $transitData.busLines.slice(0, 20) as line}
                            <span class="bus-pill">{line}</span>
                        {/each}
                        {#if $transitData.busLines.length > 20}
                            <span class="bus-pill">+{ $transitData.busLines.length - 20 }</span>
                        {/if}
                    {/if}
                </div>
                 <div class="metric-row">
                    <span class="label">Stops within radius</span>
                    <span class="value-small">{$transitData.busStopCount}</span>
                </div>
            </div>

        </div>
      </section>

      <div style="height: 200px;"></div>
  </div>
</div>

<style>
  /* Base styles */
  .sidebar { height: 100%; display: flex; flex-direction: column; font-family: 'Inter', sans-serif; color: #333; overflow: hidden; }
  .header-container { background: white; padding: 2rem 2rem 1rem 2rem; border-bottom: 1px solid #eee; box-shadow: 0 4px 6px -4px rgba(0,0,0,0.05); z-index: 20; }
  .control-group { margin-top: 1rem; padding: 1rem; background: #f9f9f9; border-radius: 4px; }
  label { display: block; font-size: 0.85rem; margin-bottom: 0.5rem; color: #555; }
  input[type=range] { width: 100%; cursor: pointer; }
  h1 { font-size: 1.5rem; margin: 0; font-weight: 700; transition: color 0.3s; }
  .scroll-content { flex: 1; overflow-y: auto; padding: 2rem; scroll-behavior: smooth; }
  section { min-height: 80vh; padding-bottom: 4rem; }
  .section-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #aaa; margin-bottom: 2rem; font-weight: 700; }
  .section-divider { border: 0; border-top: 1px dashed #ddd; margin: 4rem 0; }
  h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 1rem; margin-top: 2rem; }
  .metrics-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem; padding-bottom: 2rem; border-bottom: 1px solid #eee; }
  .metric { display: flex; flex-direction: column; justify-content: flex-start; }
  .entropy-metric { align-items: center; }
  .donut-wrapper { position: relative; width: 50px; height: 50px; display: flex; justify-content: center; align-items: center; margin-bottom: 0.25rem; }
  .donut-wrapper svg { position: absolute; top: 0; left: 0; }
  circle { transition: all 0.3s ease; } 
  .value { font-size: 1.5rem; font-weight: 700; color: #111; line-height: 1.2; }
  .value.centered { font-size: 0.9rem; } 
  .value small { font-size: 1rem; color: #666; font-weight: 400; }
  .label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-top: 0.25rem; text-align: center;}
  .category-row { margin-bottom: 1rem; }
  .cat-info { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.25rem; }
  .progress-bar-bg { width: 100%; height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
  .progress-bar-fill { height: 100%; transition: width 0.3s ease; }
  .race-layout { display: flex; gap: 1.5rem; align-items: flex-start; }
  .waffle-chart { display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px; width: 100px; }
  .waffle-dot { width: 6px; height: 6px; border-radius: 50%; background-color: #eee; }
  .race-list { flex: 1; }
  .race-row { display: flex; align-items: center; margin-bottom: 6px; font-size: 0.8rem; }
  .race-dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
  .race-name { flex: 1; color: #555; }
  .race-val { font-weight: 600; color: #333; }
  .age-chart { display: flex; justify-content: space-between; height: 120px; align-items: flex-end; gap: 8px; }
  .age-col { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; justify-content: flex-end; }
  .bar-container { width: 100%; flex: 1; display: flex; align-items: flex-end; background: rgba(0,0,0,0.03); border-radius: 2px; overflow: hidden; }
  .bar-fill { width: 100%; background: #444; transition: height 0.3s ease; }
  .age-label { font-size: 0.7rem; color: #888; margin-top: 6px; }
  .age-val { font-size: 0.7rem; font-weight: 600; color: #333; margin-top: 2px; }
  .indicators-section { margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #eee; }
  .indicator-grid { display: flex; gap: 2rem; justify-content: flex-start; }
  .indicator-card { display: flex; flex-direction: column; align-items: center; width: 80px; text-align: center; }
  .donut-mini { margin-bottom: 0.5rem; }
  
  /* TRANSIT */
  .transit-group { margin-bottom: 3rem; }
  .group-header { display: flex; align-items: center; margin-bottom: 1rem; }
  .indicator-dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; }
  .indicator-dot.subway { background-color: #ffd73e; } 
  .indicator-dot.rail { background-color: #ff98ab; }   
  .indicator-dot.bus { background-color: #0245ef; }    
  h4 { margin: 0; font-size: 1rem; font-weight: 600; }
  .pill-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 1rem; }
  
  .line-pill { 
      width: 24px; height: 24px; 
      border-radius: 50%; 
      display: flex; align-items: center; justify-content: center; 
      font-size: 0.7rem; font-weight: bold; 
      /* Color defined inline now */
  }
  
  /* RAIL & BUS: Use same styling */
  .rail-pill, .bus-pill {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      background: #333; 
      color: white;
  }
  
  .metric-row { display: flex; justify-content: space-between; align-items: baseline; font-size: 0.85rem; border-top: 1px solid #eee; padding-top: 0.5rem; }
  .value-small { font-weight: 700; font-size: 1rem; }
  .empty-state { font-size: 0.75rem; color: #999; font-style: italic; }
</style>