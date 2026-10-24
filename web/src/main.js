import "./style.css";
import $ from "jquery";

let ws;
function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => $("#status").text("online").removeClass("text-red-400").addClass("text-green-400");
  ws.onclose = () => {
    $("#status").text("offline").removeClass("text-green-400").addClass("text-red-400");
    setTimeout(connect, 1000);
  };
}
connect();

function throttle(fn, ms) {
  let last = 0, timer;
  return (...args) => {
    const wait = ms - (Date.now() - last);
    clearTimeout(timer);
    if (wait <= 0) { last = Date.now(); fn(...args); }
    else timer = setTimeout(() => { last = Date.now(); fn(...args); }, wait);
  };
}
const send = throttle((msg) => {
  if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
}, 40);

$("#pan").on("input", function () {
  const pan = Number(this.value);
  $("#pan-val").text(pan);
  send({ pan });            // placeholder: use whatever your /ws handler expects
});