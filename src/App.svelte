<script>
  import Map from './lib/Map.svelte';
  import Sidebar from './lib/Sidebar.svelte';
  
  // No script logic needed! 
  // The components will talk to each other via the store.
</script>

<main>
  <div class="sidebar-container">
    <Sidebar />
  </div>
  <div class="map-container">
    <Map />
  </div>
</main>

<style>
  main {
    display: flex;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
  .sidebar-container {
    width: 350px;
    flex-shrink: 0;
    border-right: 1px solid #ddd;
    background: white;
    z-index: 10;
  }
  .map-container {
    flex-grow: 1;
    position: relative;
  }
</style>