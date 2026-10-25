import "./style.css";
import $ from "jquery";
import { mountConfigPanel } from "./components/config-panel.js";
mountConfigPanel("#config-panel");

let packet_id = 0;

let ws;
function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () =>
    $("#status")
      .text("online")
      .removeClass("text-red-400")
      .addClass("text-green-400");
  ws.onclose = () => {
    $("#status")
      .text("offline")
      .removeClass("text-green-400")
      .addClass("text-red-400");
    setTimeout(connect, 1000);
  };
}
connect();

function throttle(fn, ms) {
  let last = 0,
    timer;
  return (...args) => {
    const wait = ms - (Date.now() - last);
    clearTimeout(timer);
    if (wait <= 0) {
      last = Date.now();
      fn(...args);
    } else
      timer = setTimeout(() => {
        last = Date.now();
        fn(...args);
      }, wait);
  };
}

const send = throttle((msg) => {
  packet_id += 1;
  if (ws?.readyState === WebSocket.OPEN) ws.send(`${packet_id};${msg}`);
}, 40);

$("#top_servo").on("input", function () {
  const angle = Number(this.value);
  $("#top-val").text(angle);
  send(`tS=${angle}`);
});

$("#base_servo").on("input", function () {
  const angle = Number(this.value);
  $("#base-val").text(angle);
  send(`bS=${angle}`);
});

let currentR = 90;
let currentG = 90;
let currentB = 90;

$("#r_led").on("input", function () {
  const brightness = Number(this.value);
  currentR = brightness;
  $("#r-val").text(brightness);
  send(`r=${currentR};g=${currentG};b=${currentB}`);
});

$("#g_led").on("input", function () {
  const brightness = Number(this.value);
  currentG = brightness;
  $("#g-val").text(brightness);
  send(`r=${currentR};g=${currentG};b=${currentB}`);
});

$("#b_led").on("input", function () {
  const brightness = Number(this.value);
  $("#b-val").text(brightness);
  currentB = brightness;
  send(`r=${currentR};g=${currentG};b=${currentB}`);
});
