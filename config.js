// Frontend API override for the deployed Netlify site.
// Local/Render same-origin runs keep this empty and call the API on the same host.
const MBWR_RENDER_BACKEND_URL = "https://mood-based-watch-recommender.onrender.com";
const MBWR_NETLIFY_HOSTS = new Set(["mood-based-watch-recommender.netlify.app"]);

window.MBWR_API_BASE_URL =
  window.MBWR_API_BASE_URL ||
  (MBWR_NETLIFY_HOSTS.has(window.location.hostname) ? MBWR_RENDER_BACKEND_URL : "");
