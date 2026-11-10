const owlImg = document.querySelector("#owlImage");
const speech = document.querySelector("#owlSpeech");
const burmalda = document.querySelector("#burmalda");
const feedZone = document.querySelector(".feed-zone");

// сохранённый цвет совы из гардероба
const savedOwl = localStorage.getItem("owlColorImage");
if (savedOwl) {
  owlImg.onerror = () => { owlImg.onerror = null; owlImg.src = "assets/sova_roz.png"; };
  owlImg.src = savedOwl;
}

let dragging = false, fed = false, offsetX = 0, offsetY = 0;

function overOwl(x, y) {
  const r = owlImg.getBoundingClientRect();
  return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
}

burmalda.addEventListener("pointerdown", (e) => {
  if (fed) return;
  const r = burmalda.getBoundingClientRect();
  offsetX = e.clientX - r.left;
  offsetY = e.clientY - r.top;
  dragging = true;
  burmalda.setPointerCapture(e.pointerId);
  burmalda.style.width = `${r.width}px`;
  burmalda.style.height = `${r.height}px`;
  burmalda.style.left = `${r.left}px`;
  burmalda.style.top = `${r.top}px`;
  burmalda.classList.add("dragging");
});

burmalda.addEventListener("pointermove", (e) => {
  if (!dragging) return;
  burmalda.style.left = `${e.clientX - offsetX}px`;
  burmalda.style.top = `${e.clientY - offsetY}px`;
});

burmalda.addEventListener("pointerup", (e) => {
  if (!dragging) return;
  dragging = false;
  if (overOwl(e.clientX, e.clientY)) {
    fed = true;
    burmalda.style.display = "none";
    feedZone.classList.add("done");
    owlImg.classList.add("stretched");
    speech.textContent = "Ням-ням, вась! Спасибо за бурмалду!";
  } else {
    // вернуть на место
    burmalda.classList.remove("dragging");
    burmalda.style.left = burmalda.style.top = burmalda.style.width = burmalda.style.height = "";
  }
});
