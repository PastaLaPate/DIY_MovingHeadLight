const host = new URLSearchParams(location.search).get("esp") ?? location.host;
let ws;
function connect() {
  ws = new WebSocket(`ws://${host}/ws`);
  ws.onclose = () => setTimeout(connect, 1000);   // survives reboots and OTA
}
connect();