const boardEl = document.querySelector("#board");
const speech = document.querySelector("#owlSpeech");
const owlImg = document.querySelector("#owlImage");
const burmalda = document.querySelector("#burmalda");
const betLabel = document.querySelector("#betLabel");
const restartBtn = document.querySelector("#restartBtn");

// сохранённый цвет совы из гардероба
const savedOwl = localStorage.getItem("owlColorImage");
if (savedOwl) {
  owlImg.onerror = () => { owlImg.onerror = null; owlImg.src = "assets/sova_roz.png"; };
  owlImg.src = savedOwl;
}

const LINES = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
const HUMAN = "O", OWL = "X";

const MOVE_PHRASES = [
  "Обалдеть ты играешь, вась!",
  "Ну ты даёшь, вась!",
  "Хороший ход, вась, но я хитрее.",
  "Хм, смело, вась.",
  "Думаешь, обыграешь сову, вась?",
  "Ого, вась, а ты не промах!",
  "Ходи-ходи, вась, всё равно я выиграю."
];
const LOSE_PHRASES = [
  "Ахахаха, проиграл сове, вась! Умора!",
  "Ухохочешься, вась! Сова тебя уделала!",
  "Ой не могу, вась, это было слабо! Хахаха!",
  "Бурмалда осталась у меня, вась! Ха-ха-ха!"
];
const WIN_PHRASES = [
  "Респект, вась! Ты меня уделал, забирай бурмалду!",
  "Уважаю, вась! Бурмалда твоя!",
  "Вот это игра, вась! Респект тебе!"
];
const DRAW_PHRASES = [
  "Ничья, вась! Бурмалда остаётся на кону, давай ещё."
];

let cells, over;
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
function say(text) { speech.textContent = text; }

function winner(b) {
  for (const [a, c, d] of LINES) {
    if (b[a] && b[a] === b[c] && b[a] === b[d]) return { who: b[a], line: [a, c, d] };
  }
  return null;
}

function render() {
  boardEl.replaceChildren();
  cells.forEach((value, i) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cell" + (value ? ` ${value.toLowerCase()}` : "");
    btn.textContent = value || "";
    btn.disabled = over || !!value;
    btn.setAttribute("aria-label", `Клетка ${i + 1}`);
    btn.addEventListener("click", () => humanMove(i));
    boardEl.appendChild(btn);
  });
}

function owlChoice() {
  const free = cells.map((v, i) => v ? null : i).filter((i) => i !== null);
  const tryLine = (mark) => {
    for (const line of LINES) {
      const marks = line.filter((i) => cells[i] === mark).length;
      const empty = line.find((i) => !cells[i]);
      if (marks === 2 && empty !== undefined) return empty;
    }
    return null;
  };
  let move = tryLine(OWL);
  if (move === null) move = tryLine(HUMAN);
  if (move === null && !cells[4]) move = 4;
  if (move === null) move = pick(free);
  return move;
}

function finish(result) {
  over = true;
  render();
  if (result && result.line) {
    boardEl.querySelectorAll(".cell").forEach((el, i) => el.classList.toggle("win", result.line.includes(i)));
  }
  if (result && result.who === HUMAN) {
    say(pick(WIN_PHRASES));
    owlImg.classList.add("respect");
    burmalda.classList.add("won");
    betLabel.textContent = "Бурмалда досталась тебе!";
  } else if (result && result.who === OWL) {
    say(pick(LOSE_PHRASES));
    owlImg.classList.add("laugh");
    burmalda.classList.add("lost");
    betLabel.textContent = "Бурмалда у совы...";
  } else {
    say(pick(DRAW_PHRASES));
  }
}

function humanMove(i) {
  if (over || cells[i]) return;
  cells[i] = HUMAN;
  let result = winner(cells);
  if (result) return finish(result);
  if (cells.every(Boolean)) return finish(null);

  cells[owlChoice()] = OWL;
  result = winner(cells);
  if (result) return finish(result);
  if (cells.every(Boolean)) return finish(null);

  render();
  say(pick(MOVE_PHRASES));
}

function newGame() {
  cells = Array(9).fill(null);
  over = false;
  owlImg.classList.remove("laugh", "respect");
  burmalda.classList.remove("won", "lost");
  betLabel.textContent = "Бурмалда — ставка на игру";
  say("Сыграем в крестики-нолики, вась? На кону бурмалда!");
  render();
}

restartBtn.addEventListener("click", newGame);
newGame();
