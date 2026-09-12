// ═══════════════════════════════════════════════════════════════════
// Compiscript IDE — Frontend Logic
// ═══════════════════════════════════════════════════════════════════

"use strict";

// ── State ────────────────────────────────────────────────────────
let astScale = 1;
let lastResult = null;
let isCompiling = false;

// ── DOM Refs ─────────────────────────────────────────────────────
const editor      = () => document.getElementById("codeEditor");
const lineNums    = () => document.getElementById("lineNumbers");
const diagList    = () => document.getElementById("diagList");
const symbolTree  = () => document.getElementById("symbolTree");
const astCont     = () => document.getElementById("astContainer");
const runBtn      = () => document.getElementById("runBtn");
const statusDot   = () => document.querySelector(".status-dot");
const statusText  = () => document.getElementById("statusText");
const errorBadge  = () => document.getElementById("errorBadge");
const diagCount   = () => document.getElementById("diagCount");
const sbErrors    = () => document.getElementById("sbErrors");
const sbWarnings  = () => document.getElementById("sbWarnings");
const sbCursor    = () => document.getElementById("sbCursor");

// ── Examples ─────────────────────────────────────────────────────
const EXAMPLES = {
  variables: `// Variables, constantes y tipos básicos
let nombre: string = "Compiscript";
let version: integer = 1;
let precio: float = 3.14;
let activo: boolean = true;
let nada = null;

const MAX: integer = 100;
const PI: float = 3.14159;

print(nombre);
print(version);
print(activo);`,

  funciones: `// Funciones y recursión
function suma(a: integer, b: integer): integer {
  return a + b;
}

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function saludar(nombre: string): string {
  return "Hola, " + nombre + "!";
}

let r: integer = suma(10, 20);
let f: integer = factorial(6);
let msg: string = saludar("Mundo");

print(r);
print(f);
print(msg);`,

  clases: `// Clases, herencia y polimorfismo
class Animal {
  let nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }

  function hablar(): string {
    return this.nombre + " hace un ruido.";
  }

  function getNombre(): string {
    return this.nombre;
  }
}

class Perro : Animal {
  function hablar(): string {
    return this.nombre + " dice: ¡Guau!";
  }
}

class Gato : Animal {
  function hablar(): string {
    return this.nombre + " dice: ¡Miau!";
  }
}

let perro: Perro = new Perro("Rex");
let gato: Gato = new Gato("Luna");

print(perro.hablar());
print(gato.hablar());
print(perro.getNombre());`,

  arrays: `// Arreglos y estructuras de datos
let notas: integer[] = [95, 82, 78, 91, 88];
let primera: integer = notas[0];
print(primera);

// foreach sobre arreglo
foreach (nota in notas) {
  if (nota >= 90) {
    print("Nota excelente:");
    print(nota);
  }
}

// Matriz 2D
let matriz: integer[][] = [[1, 2, 3], [4, 5, 6], [7, 8, 9]];
let centro: integer = matriz[1][1];
print(centro);

// Arreglo de strings
let palabras: string[] = ["hola", "mundo", "compiladores"];
foreach (p in palabras) {
  print(p);
}`,

  errores: `// Código con errores semánticos intencionales
// Comenta o edita las líneas para ver cómo cambian los diagnósticos

// Error 1: Variable no declarada
print(variableNoExiste);

// Error 2: Operador '-' no aplica a strings
let a: string = "texto";
let b: string = "otro";
let c = a - b;

// Error 3: Condición no booleana
let x: integer = 5;
if (x) { print("error"); }

// Error 4: break fuera de un loop
break;

// Error 5: Tipo incorrecto en la declaración
let n: integer = "no soy un número";`,
};

// ── Initialization ────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const ed = editor();
  updateLineNumbers();
  ed.addEventListener("input", updateLineNumbers);
  ed.addEventListener("scroll", syncScroll);
  ed.addEventListener("keydown", handleEditorKey);
  ed.addEventListener("click", updateCursor);
  ed.addEventListener("keyup", updateCursor);

  // Ctrl+Enter to compile
  ed.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      compile();
    }
  });
});

// ── Line Numbers ──────────────────────────────────────────────────
function updateLineNumbers() {
  const ed = editor();
  const lines = ed.value.split("\n");
  lineNums().textContent = lines.map((_, i) => i + 1).join("\n");
}

function syncScroll() {
  lineNums().scrollTop = editor().scrollTop;
}

function updateCursor() {
  const ed = editor();
  const val = ed.value.substring(0, ed.selectionStart);
  const line = val.split("\n").length;
  const col = val.split("\n").pop().length + 1;
  sbCursor().textContent = `Ln ${line}, Col ${col}`;
}

// ── Tab handling in editor ────────────────────────────────────────
function handleEditorKey(e) {
  if (e.key === "Tab") {
    e.preventDefault();
    const ed = editor();
    const start = ed.selectionStart;
    const end = ed.selectionEnd;
    ed.value = ed.value.substring(0, start) + "  " + ed.value.substring(end);
    ed.selectionStart = ed.selectionEnd = start + 2;
    updateLineNumbers();
  }
}

// ── Tab navigation ────────────────────────────────────────────────
function switchTab(tab) {
  // Update nav buttons
  document.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById("btnEditor").classList.toggle("active", tab === "editor");
  document.getElementById("btnSymbols").classList.toggle("active", tab === "symbols");
  document.getElementById("btnAst").classList.toggle("active", tab === "ast");

  // Show the right panel
  document.getElementById("tabErrors").classList.toggle("hidden", tab !== "editor");
  document.getElementById("tabSymbols").classList.toggle("hidden", tab !== "symbols");
  document.getElementById("tabAst").classList.toggle("hidden", tab !== "ast");
}

// ── Examples ──────────────────────────────────────────────────────
function loadExample() {
  const sel = document.getElementById("exampleSelect");
  const key = sel.value;
  if (!key) return;
  editor().value = EXAMPLES[key] || "";
  updateLineNumbers();
  sel.value = "";
}

function clearEditor() {
  editor().value = "";
  updateLineNumbers();
  clearDiagnostics();
}

// ── Compile ───────────────────────────────────────────────────────
async function compile() {
  if (isCompiling) return;
  isCompiling = true;

  const btn = runBtn();
  btn.disabled = true;
  btn.classList.add("loading");
  btn.querySelector(".run-icon").textContent = "⟳";

  setStatus("running", "Compilando…");

  const code = editor().value;

  try {
    const resp = await fetch("/compile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, ast: true }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const result = await resp.json();
    lastResult = result;

    renderDiagnostics(result.errors || [], result.warnings || []);
    renderSymbolTable(result.symbol_table || {});
    renderAst(result.ast_svg || null);

    const errCount = (result.errors || []).length;
    const warnCount = (result.warnings || []).length;

    if (errCount === 0) {
      setStatus("ok", "Sin errores");
      document.querySelector(".statusbar").classList.remove("has-errors");
    } else {
      setStatus("error", `${errCount} error(es)`);
      document.querySelector(".statusbar").classList.add("has-errors");
    }

    sbErrors().textContent = `${errCount} error(es)`;
    sbWarnings().textContent = `${warnCount} advertencia(s)`;

  } catch (err) {
    setStatus("error", "Error de conexión");
    renderDiagnostics([{
      message: "No se pudo conectar con el servidor. ¿Está corriendo ide/server.py?",
      line: 0, column: 0, severity: "error", phase: "network"
    }], []);
  } finally {
    isCompiling = false;
    btn.disabled = false;
    btn.classList.remove("loading");
    btn.querySelector(".run-icon").textContent = "▶";
  }
}

function setStatus(kind, text) {
  statusDot().className = `status-dot ${kind}`;
  statusText().textContent = text;
}

// ── Diagnostics Rendering ─────────────────────────────────────────
function clearDiagnostics() {
  diagList().innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🔬</div>
      <p>Los errores y advertencias aparecerán aquí.</p>
    </div>`;
  errorBadge().textContent = "0";
  errorBadge().classList.remove("has-errors");
  diagCount().textContent = "Presiona Compilar para analizar";
  sbErrors().textContent = "0 errores";
  sbWarnings().textContent = "0 advertencias";
}

function renderDiagnostics(errors, warnings) {
  const all = [...errors, ...warnings].sort((a, b) => (a.line - b.line) || (a.column - b.column));
  const total = all.length;

  errorBadge().textContent = total;
  if (errors.length > 0) {
    errorBadge().classList.add("has-errors");
  } else {
    errorBadge().classList.remove("has-errors");
  }

  diagCount().textContent = total === 0
    ? "✓ Sin problemas"
    : `${errors.length} error(es) · ${warnings.length} advertencia(s)`;

  if (total === 0) {
    diagList().innerHTML = `
      <div class="empty-state" style="color: var(--green)">
        <div class="empty-icon">✅</div>
        <p style="color:var(--green)">¡Sin errores semánticos!</p>
      </div>`;
    return;
  }

  diagList().innerHTML = all.map(issue => {
    const isErr = issue.severity === "error";
    const icon = isErr ? "🔴" : "🟡";
    const phase = issue.phase ? `[${issue.phase}]` : "";
    const loc = issue.line > 0 ? `Línea ${issue.line}:${issue.column}` : "";
    return `
      <div class="diag-item ${isErr ? "error" : "warning"}"
           onclick="goToLine(${issue.line})"
           title="${escHtml(issue.message)}">
        <div class="diag-icon">${icon}</div>
        <div class="diag-body">
          <div class="diag-msg">${escHtml(issue.message)}</div>
          <div class="diag-meta">${phase} ${loc}</div>
        </div>
      </div>`;
  }).join("");
}

function goToLine(line) {
  if (line <= 0) return;
  const ed = editor();
  const lines = ed.value.split("\n");
  let pos = 0;
  for (let i = 0; i < Math.min(line - 1, lines.length); i++) {
    pos += lines[i].length + 1;
  }
  ed.focus();
  ed.setSelectionRange(pos, pos + (lines[line - 1] || "").length);
  // Scroll into view
  const lineH = 13 * 1.6;
  ed.scrollTop = (line - 5) * lineH;
  updateCursor();
}

// ── Symbol Table Rendering ────────────────────────────────────────
function renderSymbolTable(scope) {
  if (!scope || !scope.name) {
    symbolTree().innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <p>No hay símbolos aún.</p>
      </div>`;
    return;
  }
  symbolTree().innerHTML = renderScope(scope);
}

function renderScope(scope) {
  const kindClass = scope.kind || "block";
  const symbols = (scope.symbols || []).filter(s => !s.name.startsWith("__"));
  const children = scope.children || [];

  const symRows = symbols.map(s => {
    const icon = {
      variable: "𝑥", constant: "𝐶", function: "𝑓", parameter: "𝑝",
      class: "◈", loop_variable: "↻"
    }[s.kind] || "·";
    return `
      <div class="symbol-row" title="${s.name}: ${s.type} at ${s.line}:${s.column}">
        <span class="sym-kind-icon">${icon}</span>
        <span class="sym-name">${escHtml(s.name)}</span>
        <span class="sym-type">${escHtml(s.type)}</span>
        <span class="sym-loc">${s.line}:${s.column}</span>
      </div>`;
  }).join("");

  const childrenHtml = children.map(c => renderScope(c)).join("");

  // A scope with no declarations of its own would otherwise render as a blank
  // box — say so explicitly instead of looking broken.
  const emptyRow = (symbols.length === 0 && children.length === 0)
    ? `<div class="scope-empty">Sin símbolos declarados en este ámbito</div>`
    : "";

  return `
    <div class="scope-node">
      <div class="scope-header" onclick="toggleScope(this)">
        <span class="scope-kind-badge ${kindClass}">${kindClass}</span>
        <span class="scope-name">${escHtml(scope.name)}</span>
        <span class="scope-chevron open">▶</span>
      </div>
      <div class="scope-body">
        ${symRows}${emptyRow}
        ${children.length > 0 ? `<div class="scope-children">${childrenHtml}</div>` : ""}
      </div>
    </div>`;
}

function toggleScope(header) {
  const body = header.nextElementSibling;
  const chevron = header.querySelector(".scope-chevron");
  body.classList.toggle("collapsed");
  chevron.classList.toggle("open");
}

function expandAllScopes() {
  document.querySelectorAll(".scope-body").forEach(b => b.classList.remove("collapsed"));
  document.querySelectorAll(".scope-chevron").forEach(c => c.classList.add("open"));
}

// ── AST Rendering ────────────────────────────────────────────────
function renderAst(svg) {
  const container = astCont();
  if (!svg) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🌲</div>
        <p>El AST requiere Graphviz instalado en el servidor.</p>
        <p style="font-size:11px;color:var(--text-2);margin-top:4px">pip install graphviz + apt/brew install graphviz</p>
      </div>`;
    return;
  }
  astScale = 1;
  container.innerHTML = `<div id="astSvgWrapper">${svg}</div>`;
  // Make SVG responsive
  const svgEl = container.querySelector("svg");
  if (svgEl) {
    svgEl.style.maxWidth = "none";
    svgEl.style.width = "auto";
    svgEl.style.height = "auto";
  }
}

function zoomAst(factor) {
  astScale = Math.max(0.1, Math.min(4, astScale * factor));
  const wrapper = document.getElementById("astSvgWrapper");
  if (wrapper) wrapper.style.transform = `scale(${astScale})`;
  const svgEl = astCont().querySelector("svg");
  if (svgEl) svgEl.style.transform = `scale(${astScale})`;
}

function resetAstZoom() {
  astScale = 1;
  const svgEl = astCont().querySelector("svg");
  if (svgEl) svgEl.style.transform = "scale(1)";
}

// ── Utilities ─────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
