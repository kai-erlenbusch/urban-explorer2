<div id="panel">
  <h4>Land Use</h4>
  <ul>
    <li><span style="background: #F9EDDB;"></span>One & Two Family Buildings</li>
    <li><span style="background: #F6D9CB;"></span>Multi-Family Buildings</li>
    <li><span style="background: #F1B89C;"></span>Mixed Residential & Commercial</li>
    <li><span style="background: #DF7649;"></span>Commercial & Office Buildings</li>
    <li><span style="background: #CF4F4F;"></span>Industrial & Manufacturing</li>
    <li><span style="background: #BEC6CC;"></span>Transportation & Utility</li>
    <li><span style="background: #BDE7F4;"></span>Public Facilities & Institutions</li>
    <li><span style="background: #A3D393;"></span>Open Space & Outdoor Recreation</li>
    <li><span style="background: #8DA2B4;"></span>Parking Facilities</li>
    <li><span style="background: #E4E4E4;"></span>Vacant Land</li>
    <li><span style="background: #F9F9F9; border: 1px solid #ccc; box-sizing: border-box;"></span>No Data</li>
  </ul>
</div>

<style>
  #panel {
    background: white;
    width: 300px; /* Adjusted to fit nicely */
    border: 1px solid rgba(0, 0, 0, 0.05);
    position: absolute;
    right: 16px;
    top: 16px;
    box-shadow: 0 0 4px 0 rgba(0, 0, 0, 0.1);
    color: rgba(0, 0, 0, 0.5);
    font-family: sans-serif;
    font-size: 14px;
    z-index: 10; /* Ensures it sits above the map */
  }
  h4 {
    text-transform: uppercase;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    margin: 0;
    padding: 16px;
  }
  ul {
    list-style-type: none;
    margin: 0;
    padding: 16px;
  }
  li {
    padding: 3px 0;
    display: flex;
    align-items: center;
  }
  span {
    width: 10px;
    height: 10px;
    display: inline-block;
    margin-right: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
</style>