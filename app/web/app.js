const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const ESTADO = {aceptado: "Aceptado", rechazado: "Rechazado", pendiente: "Por confirmar"};
const TIPO = {suelto: "Ejercicio suelto", bloque: "Bloque de lectura", parte: "Parte de Inglés"};
const GRADO = {"33": "3°", "44": "4°", "55": "5°", "66": "6°", "77": "7°", "88": "8°", "99": "9°", "10": "10°", "11": "11°", "13": "ICFES"};
const ORDEN_GRADOS = ["33", "44", "55", "66", "77", "88", "99", "10", "11", "13"];   // un objeto JS ordenaría 10 antes que 33
const VISTAS = ["panel", "cargar", "banco", "simulacros", "formatos", "catalogos"];
const NIVELES = ["Básico", "Medio", "Avanzado"];
const api = async (url, opt) => { const r = await fetch(url, opt); if (!r.ok) throw new Error((await r.text()) || r.status); return r.json(); };

/* ================================================================ navegación */
function mostrar(vista) {
  if (vista === "validar") vista = "cargar";
  if (!VISTAS.includes(vista)) vista = "cargar";
  document.querySelectorAll(".vista").forEach(v => v.hidden = v.id !== "v-" + vista);
  document.querySelectorAll("nav a").forEach(a => a.dataset.vista === vista ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
  ({panel: cargarPanel, cargar: cargarPendientes, banco: abrirBanco, simulacros: simulacros,
    formatos: cargarFormatos, catalogos: cargarCatalogos})[vista]();
}
window.addEventListener("hashchange", () => mostrar(location.hash.slice(1)));

/* ================================================================ cargar */
const zona = $("#zona"), entrada = $("#entrada");
["dragenter", "dragover"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add("encima"); }));
["dragleave", "drop"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.remove("encima"); }));
zona.addEventListener("drop", e => enviar([...e.dataTransfer.files]));
entrada.addEventListener("change", () => { enviar([...entrada.files]); entrada.value = ""; });

let REVISADOS = [];        // lo revisado en esta tanda, esperando que la persona pulse «Guardar»

async function enviar(archivos) {
  if (!archivos.length) return;
  const estado = $("#estado-carga");
  estado.textContent = `Revisando ${archivos.length} archivo${archivos.length > 1 ? "s" : ""}…`;
  const datos = new FormData();
  archivos.forEach(a => datos.append("archivos", a));
  try {
    const res = await api("/api/revisar", {method: "POST", body: datos});
    estado.textContent = "";
    REVISADOS = REVISADOS.concat(res);
    pintarResultados();
    cargarPendientes();
  } catch (e) {
    estado.textContent = "No se pudo revisar: " + e.message;
  }
}

function guardables() {
  return REVISADOS.filter(r => r.pendiente_id && !r.guardado && r.estado === "aceptado");
}

function pintarResultados() {
  const cuenta = {aceptado: 0, rechazado: 0, pendiente: 0, guardado: 0};
  REVISADOS.forEach(r => r.guardado ? cuenta.guardado++ : cuenta[r.estado]++);
  const resumen = $("#resumen");
  resumen.hidden = !REVISADOS.length;
  const nombres = {aceptado: n => n > 1 ? "listos para guardar" : "listo para guardar",
                   rechazado: n => n > 1 ? "rechazados" : "rechazado",
                   pendiente: n => n > 1 ? "por confirmar" : "por confirmar",
                   guardado: n => n > 1 ? "guardados en el banco" : "guardado en el banco"};
  resumen.innerHTML = Object.entries(cuenta).filter(([, n]) => n)
    .map(([k, n]) => `<span class="chip ${k === "guardado" ? "aceptado" : k}">${n} ${nombres[k](n)}</span>`).join("");
  $("#resultados").innerHTML = REVISADOS.map(tarjeta).join("");
  const listos = guardables().length;
  $("#barra-guardar").hidden = !REVISADOS.some(r => r.pendiente_id && !r.guardado);
  $("#btn-guardar-todos").disabled = !listos;
  $("#btn-guardar-todos").textContent = listos > 1 ? `Guardar los ${listos} en el banco` : "Guardar en el banco";
  $("#msg-guardar").textContent = listos ? "Nada entra al banco hasta que pulses Guardar." : "";
}

async function guardarRevisados(ids) {
  const boton = $("#btn-guardar-todos");
  boton.disabled = true;
  $("#msg-guardar").textContent = "Guardando…";
  try {
    const res = await api("/api/pendientes/guardar", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ids})});
    res.forEach(nuevo => {
      const i = REVISADOS.findIndex(r => r.pendiente_id === nuevo.pendiente_id || r.archivo === nuevo.archivo);
      if (i >= 0) REVISADOS[i] = nuevo; else REVISADOS.push(nuevo);
    });
    const guardados = res.filter(r => r.guardado).length;
    pintarResultados();
    $("#msg-guardar").textContent = guardados ? `${guardados} archivo(s) en el banco. Ya se pueden usar para armar cartillas.` : "";
    refrescarDatos();
    cargarPendientes();
  } catch (e) {
    $("#msg-guardar").textContent = "No se pudo guardar: " + e.message;
    boton.disabled = false;
  }
}

/* el banco cambió: que las demás pantallas vuelvan a pedir sus datos */
function refrescarDatos() {
  OPC = null;
  panelCargado = false;
  // bancoListo NO se toca: solo marca que los escuchadores de la pantalla ya están puestos, y
  // volver a ponerlos haría que cada filtro buscara dos veces. Los datos se recargan igual en abrirBanco.
  if (CART) api("/api/cartillas/" + CART.id).then(c => { CART = c; if (!$("#v-simulacros").hidden) pintarEditor(); }).catch(() => {});
}

function tarjeta(r) {
  const f = r.filas[0] || {};
  const meta = [r.tipo && TIPO[r.tipo], r.preguntas ? `${r.preguntas} pregunta${r.preguntas > 1 ? "s" : ""}` : "",
                f.grado && GRADO[f.grado], f.materia, f.submateria].filter(Boolean).join(" · ");
  const grupos = {};
  r.errores.forEach(m => (grupos[m.donde] ??= []).push(m));
  const errores = Object.entries(grupos).map(([donde, ms]) => `
    <div class="grupo"><h3>${esc(donde)}</h3>
      ${ms.map(m => `<div class="motivo"><span class="regla" title="Regla del Estándar 2.12">${m.regla ? "Regla " + m.regla : "Archivo"}</span><span>${esc(m.mensaje)}</span></div>`).join("")}
    </div>`).join("");
  const similares = r.similitudes.length ? `<div class="grupo decidir" data-pid="${r.pendiente_id ?? ""}"><h3>Confirma estos valores</h3>
    ${r.similitudes.map(s => `<div class="similar" data-clave="${esc(s.campo + "|" + s.valor)}">
      <span>${esc(s.campo)} «<b>${esc(s.valor)}</b>» se parece a «<b>${esc(s.parecido_a)}</b>», que ya está registrada.</span>
      <span class="botones"><button type="button" data-d="misma">Es la misma: usar «${esc(s.parecido_a)}»</button><button type="button" data-d="nueva">Es nueva</button></span></div>`).join("")}
    ${r.pendiente_id ? `<button type="button" class="boton guardar-pendiente" disabled>Confirmar y cargar</button>` : `<p class="nota">Desmarca «Solo revisar» para cargarlo y confirmar.</p>`}</div>` : "";
  const avisos = r.avisos.map(a => `<div class="aviso">ℹ ${esc(a.donde)}: ${esc(a.mensaje)}</div>`).join("");
  const guardado = r.guardado ? `<div class="guardado">Entró al banco${r.guardado.bloque ? ` como ${r.tipo === "parte" ? "parte" : "bloque"} <b class="mono">${esc(r.guardado.bloque)}</b>` : ""}: ${r.guardado.codigos.map(c => `<b class="mono">${esc(c)}</b>`).join(", ")}</div>` : "";
  const datos = r.estado !== "rechazado" && r.filas.length ? `
    <div class="grupo"><h3>Datos leídos de la TABLA DE EXCEL</h3><div class="tabla-scroll"><table class="datos">
      <tr><th>#</th><th>Correcta</th><th>Grado</th><th>Materia</th><th>Submateria</th><th>Pensamiento</th><th>Competencia</th><th>DBA</th><th>Temática</th><th>Nivel</th></tr>
      ${r.filas.map((x, i) => `<tr><td>${i + 1}</td><td>${esc(x.correcta)}</td><td>${esc(GRADO[x.grado] || x.grado)}</td><td>${esc(x.materia)}</td><td>${esc(x.submateria)}</td><td>${esc(x.pensamiento)}</td><td>${esc(x.competencia)}</td><td>${esc(x.dba)}</td><td>${esc(x.tematica)}</td><td>${esc(x.nivel)}</td></tr>`).join("")}
    </table></div></div>` : "";
  const glos = (r.glosarios || []).map((g, i) => g.map(t => [i + 1, t])).flat();
  const glosario = r.estado !== "rechazado" && glos.length ? `
    <div class="grupo"><h3>Glosario leído (se imprime solo si la cartilla lo incluye)</h3><div class="tabla-scroll"><table class="datos">
      <tr><th>Pregunta</th><th>Término</th><th>Significado</th></tr>
      ${glos.map(([k, t]) => `<tr><td>${k}</td><td>${esc(t.termino)}</td><td>${esc(t.significado)}</td></tr>`).join("")}
    </table></div></div>` : "";
  const n = r.errores.length;
  const titulo = r.estado === "rechazado" ? `${n} motivo${n > 1 ? "s" : ""} por corregir` : r.estado === "pendiente" ? "Falta confirmar un valor" : r.guardado ? "Guardado en el banco" : "Cumple el estándar · falta guardar";
  const acciones = r.pendiente_id && !r.guardado ? `<div class="bar-acciones" style="margin:12px 0 0">
      ${r.estado === "aceptado" ? `<button type="button" class="boton" data-guardar="${r.pendiente_id}">Guardar este en el banco</button>` : ""}
      <button type="button" class="boton claro" data-descartar="${r.pendiente_id}">Descartar</button></div>` : "";
  return `<details class="tarjeta ${r.guardado ? "aceptado" : r.estado}" ${r.estado !== "aceptado" || r.guardado ? "open" : ""}>
    <summary><span class="chip ${r.guardado ? "aceptado" : r.estado}">${r.guardado ? "Guardado" : ESTADO[r.estado]}</span><span class="nombre">${esc(r.archivo)}</span><span class="meta">${esc(meta)} · ${titulo}</span></summary>
    <div class="cuerpo">${guardado}${errores}${similares}${avisos}${datos}${glosario}${acciones}</div>
  </details>`;
}

// decisiones sobre valores parecidos
document.addEventListener("click", async e => {
  const guardarUno = e.target.closest("[data-guardar]");
  if (guardarUno) return guardarRevisados([+guardarUno.dataset.guardar]);
  if (e.target.closest("#btn-guardar-todos")) return guardarRevisados(guardables().map(r => r.pendiente_id));
  const descartarUno = e.target.closest("[data-descartar]");
  if (descartarUno) {
    const id = +descartarUno.dataset.descartar;
    await api("/api/pendientes/" + id, {method: "DELETE"});
    REVISADOS = REVISADOS.filter(r => r.pendiente_id !== id);
    pintarResultados();
    return cargarPendientes();
  }
  if (e.target.closest("#btn-descartar-todos")) {
    const ids = REVISADOS.filter(r => r.pendiente_id && !r.guardado).map(r => r.pendiente_id);
    for (const id of ids) await api("/api/pendientes/" + id, {method: "DELETE"});
    REVISADOS = REVISADOS.filter(r => r.guardado);
    pintarResultados();
    return cargarPendientes();
  }
  const b = e.target.closest(".similar button");
  if (b) {
    const fila = b.closest(".similar");
    fila.dataset.decision = b.dataset.d;
    fila.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
    const grupo = b.closest(".decidir");
    const boton = grupo.querySelector(".guardar-pendiente");
    if (boton) boton.disabled = [...grupo.querySelectorAll(".similar")].some(x => !x.dataset.decision);
    return;
  }
  const g = e.target.closest(".guardar-pendiente");
  if (g) {
    const grupo = g.closest(".decidir");
    const decisiones = Object.fromEntries([...grupo.querySelectorAll(".similar")].map(x => [x.dataset.clave, x.dataset.decision]));
    g.disabled = true;
    try {
      const r = await api(`/api/pendientes/${grupo.dataset.pid}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({decisiones})});
      const i = REVISADOS.findIndex(x => x.pendiente_id === +grupo.dataset.pid);
      if (i >= 0) REVISADOS[i] = r;
      pintarResultados();
      refrescarDatos();
      cargarPendientes();
    } catch (err) { g.disabled = false; alert("No se pudo cargar: " + err.message); }
  }
});

async function cargarPendientes() {
  const lista = await api("/api/pendientes");
  const enPantalla = new Set(REVISADOS.filter(r => !r.guardado).map(r => r.pendiente_id));
  const otros = lista.filter(p => !enPantalla.has(p.id));
  const cont = $("#pendientes");
  if (!otros.length) { cont.innerHTML = ""; return; }
  cont.innerHTML = `<div class="pendientes"><b>${otros.length} archivo${otros.length > 1 ? "s revisados esperan" : " revisado espera"} que decidas</b>
    <small class="nota">Quedaron de una carga anterior: se guardan o se descartan.</small>
    ${otros.map(p => `<span class="pend">${esc(p.nombre)} <small>${esc(p.creado)}</small>
      <button type="button" data-guardar="${p.id}">Guardar</button><button type="button" data-descartar="${p.id}">Descartar</button></span>`).join("")}</div>`;
}
document.addEventListener("click", async e => {
  const rev = e.target.closest("[data-revisar]"), des = e.target.closest("[data-descartar]");
  if (rev) {
    const r = await api(`/api/pendientes/${rev.dataset.revisar}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
    $("#resultados").insertAdjacentHTML("afterbegin", tarjeta(r));
  }
  if (des && confirm("¿Descartar este archivo? Tendrás que volver a subirlo.")) {
    await api(`/api/pendientes/${des.dataset.descartar}`, {method: "DELETE"});
    cargarPendientes();
  }
});

/* ================================================================ banco */
let bancoListo = false, temporizador;
async function abrirBanco() {
  const res = await api("/api/banco/resumen");
  $("#banco-resumen").textContent = res.total
    ? `${res.total} pregunta${res.total > 1 ? "s" : ""} en el banco${res.bloques ? `, contando las de ${res.bloques} bloque${res.bloques > 1 ? "s" : ""} de lectura o partes de Inglés` : ""}.${res.pendientes ? ` ${res.pendientes} archivo(s) esperan confirmación en «Cargar ejercicios».` : ""}`
    : "El banco está vacío. Carga los primeros ejercicios en «Cargar ejercicios».";
  if (!bancoListo) {
    const g = $("#f-grado");
    ORDEN_GRADOS.forEach(c => g.insertAdjacentHTML("beforeend", `<option value="${c}">${GRADO[c]}</option>`));
    $("#filtros").addEventListener("change", e => { if (e.target.id === "f-grado") llenarOpciones(); buscar(); });
    $("#f-texto").addEventListener("input", () => { clearTimeout(temporizador); temporizador = setTimeout(buscar, 300); });
    $("#filtros").addEventListener("submit", e => e.preventDefault());
    $("#banco-lista").addEventListener("change", e => { if (e.target.classList.contains("marca")) contarMarcados(); });
    $("#marcar-todos").addEventListener("change", e => {
      marcas().forEach(c => { c.checked = e.target.checked; });
      contarMarcados();
    });
    $("#btn-borrar-marcados").addEventListener("click", () => borrarLote({ids: marcados()}, marcados().length > 20));
    $("#btn-borrar-filtro").addEventListener("click", () => borrarLote({filtro: filtrosActuales()}, true));
    bancoListo = true;
  }
  await llenarOpciones();
  buscar();
}

async function llenarOpciones() {
  const op = await api("/api/banco/opciones?grado=" + encodeURIComponent($("#f-grado").value));
  for (const [id, lista] of [["f-tematica", op.tematicas], ["f-materia", op.materias], ["f-submateria", op.submaterias]]) {
    const sel = $("#" + id), actual = sel.value, primera = sel.options[0].outerHTML;
    sel.innerHTML = primera + lista.map(v => `<option${v === actual ? " selected" : ""}>${esc(v)}</option>`).join("");
  }
}

async function buscar() {
  const params = new URLSearchParams(new FormData($("#filtros")));
  [...params.keys()].forEach(k => { if (!params.get(k)) params.delete(k); });
  const res = await api("/api/banco?" + params);
  $("#banco-total").textContent = res.total ? `${res.total} resultado${res.total > 1 ? "s" : ""}${res.total > res.items.length ? ` (se muestran ${res.items.length})` : ""}` : "Ningún ejercicio coincide con los filtros.";
  $("#banco-lista").innerHTML = res.items.map(x => `
    <div class="item" data-id="${x.id}">
      <label class="item-marca" title="Marcar ${esc(x.codigo)} para eliminarlo">
        <input type="checkbox" class="marca" value="${x.id}" aria-label="Marcar ${esc(x.codigo)} para eliminarlo">
      </label>
      <button type="button" class="item-ver" data-id="${x.id}">
        <span class="item-cod mono">${esc(x.codigo)}</span>
        <span class="item-meta">${esc(GRADO[x.grado])} · ${esc(x.submateria || x.materia)} · ${esc(x.tematica)}${x.nivel ? " · " + esc(x.nivel) : ""}</span>
        <span class="item-texto">${esc(x.texto)}</span>
        <span class="item-tags">${x.bloque ? `<span>${x.tipo === "parte" ? "Parte" : "Bloque"} ${esc(x.bloque)} · pregunta ${x.orden}</span>` : ""}${x.imagen ? "<span>Imagen</span>" : ""}${x.tabla ? "<span>Tabla</span>" : ""}${x.glosario ? "<span>Glosario</span>" : ""}<span>Usado ${x.veces_usado}</span></span>
      </button>
    </div>`).join("");
  TOTAL_FILTRO = res.total;
  VISIBLES = res.items.length;
  $("#lote").hidden = !res.total;
  $("#marcar-todos").checked = false;
  contarMarcados();
}

$("#banco-lista").addEventListener("click", async e => {
  const b = e.target.closest(".item-ver");
  if (!b) return;
  document.querySelectorAll("#banco-lista .item").forEach(x => x.classList.toggle("activo", x.contains(b)));
  const d = await api("/api/banco/" + b.dataset.id);
  $("#detalle").innerHTML = `
    <div class="det-cab"><b class="mono">${esc(d.codigo)}</b>${d.bloque ? ` <span class="nota">· ${d.tipo === "parte" ? "parte" : "bloque"} ${esc(d.bloque)} con ${d.hermanos} preguntas</span>` : ""}</div>
    <div class="hoja">${d.html}</div>
    <dl class="ficha-datos">
      <dt>Clave original</dt><dd>${esc(d.clave)} <small class="nota">(la plantilla la cambia al armar la cartilla)</small></dd>
      <dt>Grado</dt><dd>${esc(GRADO[d.grado])}</dd><dt>Materia</dt><dd>${esc(d.materia)}${d.submateria ? " · " + esc(d.submateria) : ""}</dd>
      ${d.pensamiento ? `<dt>Pensamiento</dt><dd>${esc(d.pensamiento)}</dd>` : ""}${d.competencia ? `<dt>Competencia</dt><dd>${esc(d.competencia)}</dd>` : ""}
      ${d.dba ? `<dt>DBA</dt><dd>${esc(d.dba)}</dd>` : ""}<dt>Temática</dt><dd>${esc(d.tematica)}</dd>${d.nivel ? `<dt>Nivel</dt><dd>${esc(d.nivel)}</dd>` : ""}
      <dt>Justificación</dt><dd>${esc(d.justificacion)}</dd>
      <dt>Archivo</dt><dd>${esc(d.archivo)} · ${esc(d.creado)}</dd><dt>Usado</dt><dd>${d.veces_usado} ${d.veces_usado === 1 ? "vez" : "veces"}</dd>
    </dl>
    <div class="det-botones"><a class="boton" href="/api/banco/${d.id}/original">Descargar Word original</a><button type="button" class="boton peligro" data-eliminar="${d.id}">Eliminar</button></div>`;
});

/* ---------------------------------------------------------------- eliminar en lote */
let TOTAL_FILTRO = 0, VISIBLES = 0;

const marcas = () => [...document.querySelectorAll("#banco-lista .marca")];
const marcados = () => marcas().filter(c => c.checked).map(c => Number(c.value));

function contarMarcados() {
  const n = marcados().length;
  marcas().forEach(c => c.closest(".item").classList.toggle("marcado", c.checked));
  $("#lote-cuenta").textContent = n
    ? `${n} marcado${n > 1 ? "s" : ""} de ${VISIBLES} en la lista.`
    : "Ninguno marcado. Usa las casillas para elegir cuáles eliminar.";
  $("#btn-borrar-marcados").disabled = !n;
  $("#btn-borrar-marcados").textContent = n > 1 ? `Eliminar los ${n} marcados` : "Eliminar marcado";
  // borrar todo lo que coincide solo tiene sentido si hay más de lo que cabe en la lista
  const filtro = $("#btn-borrar-filtro");
  filtro.hidden = TOTAL_FILTRO <= VISIBLES;
  filtro.textContent = `Eliminar los ${TOTAL_FILTRO} del filtro`;
}

function filtrosActuales() {
  const f = {};
  new FormData($("#filtros")).forEach((v, k) => { if (v) f[k] = v; });
  return f;
}

/** Lo que se va a borrar, contado por el servidor, en palabras. */
function resumenBorrado(p) {
  const n = p.eliminados.length;
  const partes = [`Se eliminará${n > 1 ? "n" : ""} ${n} pregunta${n > 1 ? "s" : ""} del banco`
    + (p.unidades !== n ? ` (${p.unidades} archivo${p.unidades > 1 ? "s" : ""} de carga)` : "") + "."];
  if (p.arrastrados) partes.push(`${p.arrastrados} entra${p.arrastrados > 1 ? "n" : ""} porque pertenece${p.arrastrados > 1 ? "n" : ""} a un bloque de lectura o a una parte de Inglés que no se puede partir.`);
  if (p.cartillas.length) {
    partes.push(`Atención: ${p.cartillas.length} cartilla${p.cartillas.length > 1 ? "s las usan" : " las usa"} y se les quitarán esas preguntas, renumerando las demás:`);
    partes.push(p.cartillas.map(c => `   · ${c.codigo} ${c.nombre || ""}${c.estado === "generada" ? " (ya generada: pierde su Word y su Excel)" : ""}`).join("\n"));
  } else if (p.usos) {
    partes.push(`Se han usado ${p.usos} ve${p.usos > 1 ? "ces" : "z"} en cartillas anteriores.`);
  }
  partes.push("\nEsto no se puede deshacer. Haz primero una copia de seguridad si no estás seguro.");
  return partes.join("\n");
}

async function borrarLote(cuerpo, pedirPalabra) {
  let previo;
  try {
    previo = await api("/api/banco/eliminar", {method: "POST", headers: {"Content-Type": "application/json"},
                                               body: JSON.stringify({...cuerpo, solo_ver: true})});
  } catch (err) { alert("No se pudo consultar qué se eliminaría: " + err.message); return; }
  if (!previo.eliminados.length) { alert("No hay nada que eliminar."); return; }
  if (!confirm(resumenBorrado(previo) + "\n\n¿Eliminar?")) return;
  if (pedirPalabra && (prompt(`Son ${previo.eliminados.length} preguntas. Escribe BORRAR para confirmar:`) || "").trim().toUpperCase() !== "BORRAR") {
    alert("No se eliminó nada.");
    return;
  }
  try {
    const r = await api("/api/banco/eliminar", {method: "POST", headers: {"Content-Type": "application/json"},
                                                body: JSON.stringify(cuerpo)});
    $("#detalle").innerHTML = `<p class="nota">Se eliminaron ${r.eliminados.length} pregunta(s) del banco.${r.cartillas.length ? ` Se actualizaron ${r.cartillas.length} cartilla(s).` : ""}</p>`;
    refrescarDatos();
    abrirBanco();
  } catch (err) { alert("No se pudo eliminar: " + err.message); }
}

document.addEventListener("click", async e => {
  const b = e.target.closest("[data-eliminar]");
  if (!b) return;
  const u = await api(`/api/banco/${b.dataset.eliminar}/usos`);
  const varios = u.codigos.length > 1;
  const msg = `${varios ? `Este ejercicio es parte de una unidad de ${u.codigos.length} preguntas y se eliminarán todas:\n${u.codigos.join(", ")}` : `Se eliminará ${u.codigos[0]}.`}\n\n${u.usos ? `Se ha usado ${u.usos} vez/veces en cartillas. Las cartillas ya generadas no cambian, pero dejará de protegerse al excluir cartillas anteriores.` : "No se ha usado en ninguna cartilla."}\n\nPara corregirlo: elimínalo, corrige el Word y vuelve a subirlo. ¿Eliminar?`;
  if (!confirm(msg)) return;
  await api(`/api/banco/${b.dataset.eliminar}`, {method: "DELETE"});
  $("#detalle").innerHTML = `<p class="nota">Eliminado: ${esc(u.codigos.join(", "))}.</p>`;
  abrirBanco();
});


/* ================================================================ panel */
let panelCargado = false, EST = null;

function barra(valor, total, clase = "") {
  const pct = total ? Math.round(100 * Math.min(valor, total) / total) : 0;
  return `<span class="progreso ${clase}" title="${valor} de ${total}"><span style="width:${pct}%"></span></span>`;
}

async function cargarPanel() {
  if (panelCargado) { pintarPanel(); return; }
  $("#panel-cargando").hidden = false;
  try {
    EST = await api("/api/estadisticas");
    panelCargado = true;
    pintarPanel();
  } catch (e) {
    $("#panel-cargando").textContent = "No se pudo cargar el panel: " + e.message;
  }
}

function pintarPanel() {
  const b = EST.banco;
  $("#panel-cargando").hidden = true;
  const panel = $("#panel");
  panel.hidden = false;
  const fichas = [
    ["Preguntas en el banco", b.total, ""],
    ["Sin usar todavía", b.sin_usar, `${b.usados} ya usadas en cartillas`],
    ["Bloques y partes", b.unidades, "se usan completos"],
    ["Temáticas distintas", b.tematicas_distintas, ""],
    ["Con imagen · tabla · glosario", `${b.con_imagen} · ${b.con_tabla} · ${b.con_glosario}`, ""],
    ["Cartillas generadas", b.cartillas_generadas, b.pendientes ? `${b.pendientes} archivo(s) por guardar` : ""],
  ];
  const maxMateria = Math.max(1, ...b.por_materia.map(x => x.n));
  const niveles = {};
  b.por_nivel.forEach(x => { niveles[x.nivel] = (niveles[x.nivel] || 0) + x.n; });
  panel.innerHTML = `
    <div class="cifras">${fichas.map(([t, v, sub]) => `<div class="cifra"><span class="cifra-n">${esc(v)}</span>
      <span class="cifra-t">${esc(t)}</span>${sub ? `<small class="nota">${esc(sub)}</small>` : ""}</div>`).join("")}</div>

    <section class="grupo-panel"><h2>Preguntas por materia</h2>
      <table class="tabla-panel"><thead><tr><th>Grado</th><th>Materia</th><th>Submateria</th><th>Preguntas</th><th></th></tr></thead>
      <tbody>${b.por_materia.map(x => `<tr><td>${esc(x.nombre_grado)}</td><td>${esc(x.materia)}</td>
        <td class="nota">${esc(x.submateria || "—")}</td><td class="num">${x.n}</td><td class="ancho-barra">${barra(x.n, maxMateria)}</td></tr>`).join("")
        || `<tr><td colspan="5" class="nota">El banco está vacío.</td></tr>`}</tbody></table>
    </section>

    <section class="grupo-panel"><h2>Reparto por nivel y por tipo</h2>
      <div class="dos-columnas">
        <table class="tabla-panel"><thead><tr><th>Nivel</th><th>Preguntas</th><th></th></tr></thead><tbody>
          ${NIVELES.concat(Object.keys(niveles).filter(n => !NIVELES.includes(n))).filter(n => niveles[n]).map(n =>
            `<tr><td>${esc(n)}</td><td class="num">${niveles[n]}</td><td class="ancho-barra">${barra(niveles[n], b.total)}</td></tr>`).join("")}
        </tbody></table>
        <table class="tabla-panel"><thead><tr><th>Tipo</th><th>Preguntas</th><th></th></tr></thead><tbody>
          ${[["suelto", "Sueltos"], ["bloque", "De bloques de lectura"], ["parte", "De partes de Inglés"]].map(([k, t]) =>
            `<tr><td>${t}</td><td class="num">${b.por_tipo[k] || 0}</td><td class="ancho-barra">${barra(b.por_tipo[k] || 0, b.total)}</td></tr>`).join("")}
        </tbody></table>
      </div>
    </section>

    <section class="grupo-panel"><h2>Pasar un simulacro al formato de carga</h2>
      <p class="nota">Copia este texto, pégalo en Claude (o en otra inteligencia artificial) y detrás pégale el
        simulacro. Te lo devuelve en el formato exacto que acepta la página, con sus tablas de respuestas, de
        Excel y de glosario. El texto se arma solo con los grados, materias y valores que hay ahora mismo en el
        sistema, así que siempre está al día.</p>
      <p class="nota">Trae las reglas completas de calidad: las <b>matemáticas con el editor de ecuaciones</b>
        (fracciones apiladas y raíces, como en un libro), cómo escribir la <b>temática</b> para que agrupe y el
        buscador sirva, y cómo deben venir las imágenes y las tablas para que se impriman bien en blanco y negro.</p>
      <div class="caja-prompt">
        <div class="bar-acciones" style="margin:0 0 8px">
          <button type="button" class="boton" id="btn-copiar-prompt">Copiar el texto</button>
          <button type="button" class="boton claro" id="btn-ver-prompt">Ver el texto</button>
          <span class="nota" id="msg-prompt"></span>
        </div>
        <pre id="texto-prompt" class="prompt" hidden></pre>
      </div>
    </section>

    <section class="grupo-panel"><h2>Qué falta para armar cada cartilla</h2>
      <p class="nota">Compara lo que hay en el banco con las secciones de cada estructura, por grado.</p>
      ${EST.cobertura.map((x, i) => `<details class="cobertura" ${i === 0 ? "open" : ""}>
        <summary><b>${esc(x.nombre_grado)} · ${esc(x.estructura)}</b> <span class="nota">${esc(x.nombre)}</span>
          ${barra(x.hay, x.necesita, x.faltan ? "" : "ok")}
          <span class="${x.faltan ? "no" : "si"}">${x.faltan ? `faltan ${x.faltan}` : "completa"}</span></summary>
        <table class="tabla-panel"><thead><tr><th>Sección</th><th>Necesita</th><th>Hay</th><th>Faltan</th></tr></thead><tbody>
          ${x.secciones.map(sec => `<tr class="${sec.faltan ? "falta" : ""}"><td>${esc(sec.titulo)}</td>
            <td class="num">${sec.necesita}</td><td class="num">${sec.hay}</td>
            <td class="num">${sec.faltan || "—"}</td></tr>`).join("")}
        </tbody></table></details>`).join("") || `<p class="nota">Cuando haya ejercicios aparecerá aquí qué falta.</p>`}
    </section>

    <section class="grupo-panel"><h2>Temáticas <span class="nota">(${b.tematicas.length})</span></h2>
      <label class="nota">Buscar temática<input type="search" id="panel-buscar" placeholder="fracciones, células…" style="width:100%;max-width:420px;font:inherit;padding:6px 8px;border:1px solid var(--linea-2);border-radius:8px"></label>
      <div class="tabla-scroll" style="max-height:420px"><table class="tabla-panel" id="tabla-tematicas"><thead>
        <tr><th>Grado</th><th>Materia</th><th>Temática</th><th>Preguntas</th><th>Sin usar</th></tr></thead><tbody>
        ${b.tematicas.map(t => `<tr data-busca="${esc((t.tematica + " " + t.materia + " " + t.submateria).toLowerCase())}">
          <td>${esc(GRADO[t.grado] || t.grado)}</td><td class="nota">${esc(t.submateria || t.materia)}</td>
          <td>${esc(t.tematica)}</td><td class="num">${t.n}</td><td class="num">${t.sin_usar}</td></tr>`).join("")}
      </tbody></table></div>
    </section>`;
}

document.addEventListener("input", e => {
  if (e.target.id !== "panel-buscar") return;
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll("#tabla-tematicas tbody tr").forEach(tr => {
    tr.hidden = q && !tr.dataset.busca.includes(q);
  });
});

/* ================================================================ crear simulacro */
let OPC = null, CART = null, PASO = 1, SECCION = null;

async function simulacros() {
  if (!OPC) {
    OPC = await api("/api/cartillas/opciones");
    $("#n-grado").innerHTML = OPC.grados.map(g => `<option value="${g.codigo}">${esc(g.nombre)}</option>`).join("");
    $("#n-tipo").innerHTML = OPC.tipos.map(t => `<option value="${t.codigo}">${t.codigo} · ${esc(t.nombre)}</option>`).join("");
    $("#n-dificultad").innerHTML = OPC.mezclas.map(m => `<option value="${m.clave}">${esc(m.nombre)}</option>`).join("");
    $("#n-materia").innerHTML = OPC.agrupaciones.map(a => `<option value="${a.codigo}">${a.codigo} · ${esc(a.nombre)}</option>`).join("");
    ["n-grado", "n-estructura", "n-tipo", "n-materia", "n-plantilla", "n-version"].forEach(id => $("#" + id).addEventListener("change", codigoVivo));
    $("#n-grado").addEventListener("change", estructurasDeGrado);
    $("#n-version").addEventListener("input", codigoVivo);
    estructurasDeGrado();
  }
  if (CART) return pintarEditor();
  $("#sim-editor").hidden = true;
  $("#sim-inicio").hidden = false;
  const lista = await api("/api/cartillas");
  CARTILLAS = lista;
  $("#sim-lista").innerHTML = lista.length ? lista.map(x => `
    <div class="cartilla">
      ${x.estado === "generada"
        ? `<label class="cuad-marca" title="Incluir ${esc(x.codigo)} en un cuadernillo de varias sesiones"><input type="checkbox" class="cuad" value="${x.id}"></label>`
        : `<span class="cuad-marca"></span>`}
      <div class="cartilla-info"><b>${esc(x.codigo)}</b> · ${esc(x.nombre)}<br><small class="nota">${esc(x.institucion)} · ${esc(x.estructura)} · ${GRADO[x.grado]} · creada el ${esc(x.creada)}</small></div>
      <div class="avance" title="${x.elegidos} de ${x.total}"><span style="width:${x.total ? Math.round(100 * x.elegidos / x.total) : 0}%"></span></div>
      <div class="acciones"><span class="nota">${x.elegidos} de ${x.total}</span>
        <button type="button" class="mini" data-abrir="${x.id}">Abrir</button>
        <button type="button" class="mini quitar" data-borrar="${x.id}" data-codigo="${esc(x.codigo)}"
                data-generada="${x.estado === "generada" ? 1 : 0}">Eliminar</button></div></div>`).join("")
    : `<p class="nota">No hay cartillas todavía. Crea la primera con «Nueva cartilla».</p>`;
  ELEGIDAS = ELEGIDAS.filter(id => lista.some(x => x.id === id && x.estado === "generada"));
  pintarCuadernillo();
}


/* ---------------------------------------------------------------- cuadernillo de varias sesiones */
let CARTILLAS = [], ELEGIDAS = [];      // ELEGIDAS guarda el ORDEN en que se marcaron: son las sesiones

function pintarCuadernillo() {
  document.querySelectorAll("#sim-lista .cuad").forEach(c => { c.checked = ELEGIDAS.includes(Number(c.value)); });
  const panel = $("#cuadernillo");
  panel.hidden = CARTILLAS.filter(x => x.estado === "generada").length < 2;
  if (panel.hidden) return;
  const sesiones = ELEGIDAS.map(id => CARTILLAS.find(x => x.id === id)).filter(Boolean);
  $("#cuad-orden").innerHTML = sesiones.length
    ? sesiones.map((x, i) => `<li><b>${esc(x.codigo)}</b> · ${esc(x.nombre)} · ${x.elegidos} preguntas
        <span class="nota">${i === 0 ? "portada entera" : "media portada, abre en hoja derecha"}</span></li>`).join("")
    : `<li class="nota">Ninguna marcada todavía.</li>`;
  const listo = sesiones.length >= 2;
  $("#btn-cuadernillo").disabled = !listo;
  $("#cuad-aviso").textContent = listo
    ? `${sesiones.length} sesiones · ${sesiones.reduce((n, x) => n + x.elegidos, 0)} preguntas en total.`
    : "Marca al menos dos cartillas generadas, del mismo grado.";
}

document.addEventListener("change", e => {
  if (!e.target.classList.contains("cuad")) return;
  const id = Number(e.target.value);
  ELEGIDAS = e.target.checked ? [...ELEGIDAS.filter(x => x !== id), id] : ELEGIDAS.filter(x => x !== id);
  pintarCuadernillo();
});

async function descargarCuadernillo() {
  const boton = $("#btn-cuadernillo"), aviso = $("#cuad-aviso");
  boton.disabled = true;
  aviso.textContent = "Armando el cuadernillo y comprobándolo con Word…";
  try {
    const r = await fetch("/api/cuadernillo/generar", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({cartillas: ELEGIDAS, nombre: $("#cuad-nombre").value.trim() || null})});
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      aviso.textContent = d.detail || "No se pudo armar el cuadernillo.";
      return;
    }
    const nombre = decodeURIComponent((r.headers.get("content-disposition") || "").split("''")[1] || "cuadernillo.docx");
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement("a"), {href: url, download: nombre});
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    const paginas = r.headers.get("X-Praxis-Paginas"), faltan = r.headers.get("X-Praxis-Faltan");
    aviso.textContent = `Descargado: ${nombre}.` + (paginas
      ? ` ${paginas} páginas${faltan && faltan !== "0" ? `, faltan ${faltan} para el múltiplo de 4.` : ", múltiplo de 4."}`
      : " No se pudieron contar las páginas (Word no estaba disponible).");
  } catch (err) {
    aviso.textContent = "No se pudo armar el cuadernillo: " + err.message;
  } finally {
    boton.disabled = ELEGIDAS.length < 2;
  }
}

function estructurasDeGrado() {
  // solo las estructuras que se pueden llenar con ejercicios del grado (E1 y E2 no sirven para 3° a 5°; E5 y E6 son de ICFES)
  const grado = $("#n-grado").value;
  const lista = OPC.estructuras.filter(e => e.grados.includes(grado));
  $("#n-estructura").innerHTML = lista.map(e => `<option value="${e.clave}">${e.clave} · ${esc(e.nombre)}${e.total ? ` · ${e.total} preguntas` : ""}</option>`).join("");
  codigoVivo();
}

function codigoVivo() {
  const est = OPC.estructuras.find(e => e.clave === $("#n-estructura").value) || {};
  const libre = !est.codigo_materia;
  $("#n-materia").closest("label").style.opacity = libre ? 1 : .5;
  $("#n-materia").disabled = !libre;
  if (!libre) $("#n-materia").value = est.codigo_materia;
  const pares = [$("#n-grado").value, $("#n-materia").value, $("#n-tipo").value,
                 String($("#n-plantilla").value).padStart(2, "0"), String($("#n-version").value || 1).padStart(2, "0")];
  const nombres = ["grado", "materia", "tipo", "plantilla", "versión"];
  $("#n-codigo").innerHTML = pares.join("") + "<small>" + pares.map((p, i) => `${p} ${nombres[i]}`).join(" · ") + "</small>";
}

$("#btn-nueva").addEventListener("click", () => { $("#form-nueva").hidden = false; codigoVivo(); });
$("#btn-cancelar").addEventListener("click", () => { $("#form-nueva").hidden = true; $("#n-error").textContent = ""; });
$("#btn-cuadernillo").addEventListener("click", descargarCuadernillo);
$("#form-nueva").addEventListener("submit", async e => {
  e.preventDefault();
  const datos = Object.fromEntries(new FormData(e.target));
  try {
    CART = await api("/api/cartillas", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(datos)});
    $("#form-nueva").hidden = true;
    e.target.reset();
    PASO = 2;
    pintarEditor();
  } catch (err) { $("#n-error").textContent = (JSON.parse(err.message).detail || err.message); }
});

document.addEventListener("click", async e => {
  const abrir = e.target.closest("[data-abrir]"), borrar = e.target.closest("[data-borrar]");
  if (abrir) { CART = await api("/api/cartillas/" + abrir.dataset.abrir); PASO = 2; SECCION = null; pintarEditor(); }
  if (borrar) {
    const generada = borrar.dataset.generada === "1";
    const aviso = generada
      ? `Esta cartilla ya está generada (${borrar.dataset.codigo}).

Si la eliminas se borran también su Word y su Excel, y se descuenta el uso que sumó a sus ejercicios. Los ejercicios del banco no se tocan.

¿Eliminarla?`
      : `¿Eliminar el borrador ${borrar.dataset.codigo}? Los ejercicios del banco no se tocan.`;
    if (!confirm(aviso)) return;
    try {
      await api("/api/cartillas/" + borrar.dataset.borrar, {method: "DELETE"});
    } catch (err) {
      alert("No se pudo eliminar: " + (JSON.parse(err.message).detail || err.message));
    }
    simulacros();
  }
});

function pintarEditor() {
  const c = CART;
  $("#sim-inicio").hidden = true;
  const ed = $("#sim-editor");
  ed.hidden = false;
  const pares = [c.grado, c.codigo_materia, c.tipo_material, String(c.plantilla).padStart(2, "0"), c.version];
  const cabecera = `<div class="bar-acciones">
      <button type="button" class="boton claro" id="btn-volver">← Cartillas</button>
      <div class="codigo-vivo">${esc(c.codigo)}<small>${esc(c.nombre)} · ${esc(c.institucion)} · ${esc(c.estructura)} · ${GRADO[c.grado]} · plantilla ${c.plantilla} · ${esc(c.tiempo)}</small></div>
      <span class="chip ${c.elegidos === c.total ? "aceptado" : "pendiente"}">${c.elegidos} de ${c.total} preguntas</span>
    </div>
    ${c.excluidas.length ? `<p class="nota">No repite ejercicios de: ${c.excluidas.map(x => `<b class="mono">${esc(x.codigo)}</b> (${esc(x.nombre)})`).join(", ")}</p>` : ""}
    <div class="pasos">
      ${[[2, "Secciones"], [3, "Elegir ejercicios"], [4, "Vista previa y revisión"]].map(([n, t]) =>
        `<button type="button" data-paso="${n}" aria-selected="${PASO === n}">${n - 1}. ${t}</button>`).join("")}
    </div>`;
  ed.innerHTML = cabecera + (PASO === 2 ? vistaSecciones(c) : PASO === 3 ? vistaSeleccion(c) : vistaRevision(c));
  if (PASO === 3) cargarCandidatos();
  if (PASO === 4) cargarVistaPrevia();
}

function seccionesLibres(c) {
  const est = OPC.estructuras.find(e => e.clave === c.estructura) || {};
  return !!est.editable || c.codigo_materia === "93";
}

function opcionesSubmateria(materia, grado) {
  const m = OPC.materias.find(x => x.nombre === materia);
  if (!m) return "";
  const regla = m.reglas[grado];           // true obligatoria · null opcional · false va vacía
  const sin = regla === true ? [] : [`<option value="">(sin submateria)</option>`];
  const subs = regla === false ? [] : m.submaterias.map(x => `<option>${esc(x)}</option>`);
  // una sola sección que tome toda la materia: una prueba general de Matemáticas usa I y II
  const todas = (regla !== false && m.submaterias.length > 1)
    ? [`<option value="*">Todas las de ${esc(materia)} (mezcladas)</option>`] : [];
  return todas.concat(sin, subs).join("");
}

function vistaSecciones(c) {
  const libre = seccionesLibres(c);
  const grupos = (OPC.grupos || []).map(g =>
    `<option value="grupo:${esc(g.nombre)}">${esc(g.nombre)} (${esc(g.materias.join(" + "))})</option>`).join("");
  const materias = grupos + OPC.materias.map(m => `<option>${esc(m.nombre)}</option>`).join("");
  return `<table class="sec-tabla"><thead><tr><th>Orden</th><th>Sección</th><th>Materia</th><th>Preguntas</th><th>Rango</th><th>Dificultad</th><th>Elegidos</th>${libre ? "<th></th>" : ""}</tr></thead><tbody>
    ${c.secciones.map((s, i) => `<tr class="${s.elegidos === s.cantidad && s.cantidad ? "completa" : ""}" data-sec="${s.id}">
      <td><div class="acciones"><button type="button" class="mini" data-mover="${i},-1" ${i === 0 ? "disabled" : ""}>↑</button><button type="button" class="mini" data-mover="${i},1" ${i === c.secciones.length - 1 ? "disabled" : ""}>↓</button></div></td>
      <td>${esc(s.titulo)}</td>
      <td class="nota">${esc(s.materia)}${s.submateria ? " · " + esc(s.submateria) : ""}${s.mezclada ? " · mezclada" : ""}</td>
      <td><input type="number" min="0" max="140" value="${s.cantidad}" data-cantidad="${s.id}"></td>
      <td class="mono">${s.cantidad ? s.rango.join("–") : "—"}</td>
      <td><select data-dificultad="${s.id}">${[["=", "Igual a la cartilla"]].concat(OPC.mezclas.map(m => [m.clave, m.nombre]))
            .map(([v, t]) => `<option value="${v}" ${s.dificultad === v ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></td>
      <td>${s.elegidos}</td>${libre ? `<td>${s.elegidos ? "" : `<button type="button" class="mini quitar" data-quitar-sec="${s.id}">Quitar</button>`}</td>` : ""}</tr>`).join("")
      || `<tr><td colspan="${libre ? 8 : 7}" class="nota">Sin secciones todavía. Agrégalas abajo, en el orden en que se imprimen.</td></tr>`}
    </tbody></table>
    ${libre ? `<div class="panel-form" style="margin-top:14px">
      <h3 class="nota" style="margin-top:0">Agregar sección</h3>
      <div class="filtros" style="grid-template-columns:repeat(auto-fill,minmax(170px,1fr))">
        <label>Materia<select id="ns-materia">${materias}</select></label>
        <label>Submateria<select id="ns-sub">${opcionesSubmateria(OPC.materias[0]?.nombre, c.grado)}</select></label>
        <label>Título impreso<input type="text" id="ns-titulo" value="${esc((OPC.materias[0]?.nombre || "").toUpperCase())}"></label>
        <label>Preguntas<input type="number" id="ns-cantidad" min="1" max="140" value="10"></label>
      </div>
      <button type="button" class="boton" id="btn-agregar-sec">Agregar sección</button>
      <span class="nota">${c.grado && OPC.primaria.includes(c.grado)
        ? "En 3° a 5°, Matemáticas y Lengua Castellana van sin submateria."
        : "«Todas las de…» hace una sección que acepta las dos submaterias, por ejemplo una prueba general de Matemáticas con preguntas de Matemáticas I y II."}</span>
    </div>` : ""}
    <div class="bar-acciones" style="margin-top:14px"><button type="button" class="boton" id="btn-guardar-sec">Guardar secciones</button>
      <span class="nota">Total: <b id="sec-total">${c.total}</b> preguntas · el tiempo se recalcula solo.</span></div>
    <p class="err" id="sec-error" role="alert"></p>`;
}

let FILTROS = {}, CANDIDATOS = null, VISTO = null, PESTANA = "previa", BUSCA_TEM = "", ENCONTRADO = null;
let PROMPT = null;                 // el texto para la inteligencia artificial, se pide una sola vez

function chips(nombre, lista, seleccion, etiqueta = x => x.valor) {
  return lista.map(x => `<button type="button" class="chip-f ${seleccion.includes(x.valor) ? "on" : ""}"
    data-filtro="${nombre}" data-valor="${esc(x.valor)}">${esc(etiqueta(x))} <small>${x.n}</small></button>`).join("");
}

function vistaSeleccion(c) {
  SECCION = SECCION || (c.secciones.find(s => s.elegidos < s.cantidad) || c.secciones[0] || {}).id;
  const s = c.secciones.find(x => x.id === SECCION) || {};
  const faltan = Math.max(0, (s.cantidad || 0) - (s.elegidos || 0));
  return `<div class="bar-acciones">
      <label class="nota">Sección
        <select id="sel-seccion">${c.secciones.map(x => `<option value="${x.id}" ${x.id === SECCION ? "selected" : ""}>${esc(x.titulo)} · ${x.elegidos}/${x.cantidad}</option>`).join("")}</select>
      </label>
      <span class="chip ${faltan ? "pendiente" : "aceptado"}">${s.elegidos || 0} de ${s.cantidad || 0}${faltan ? ` · faltan ${faltan}` : " · completa"}</span>
      <button type="button" class="boton" id="btn-auto">Selección automática</button>
      <span class="nota" id="msg-auto"></span>
    </div>
    <div class="buscador-ej">
      <label class="busca-grande">
        <span class="lupa" aria-hidden="true">🔎</span>
        <input type="search" id="c-texto" value="${esc(FILTROS.texto || "")}" autocomplete="off"
               placeholder="Escribe los temas que buscas: fracciones, diagrama circular, senos y cosenos…">
      </label>
      <p class="nota ayuda-busca">Separa los temas con comas. No hacen falta tildes y sirve el singular o el plural.</p>
      <div id="c-donde"></div>
      <div class="filtros-din" id="filtros-din"></div>
    </div>
    <div class="elegir">
      <div class="col-filtros" id="filtros-ej"></div>
      <div class="col-lista">
        <div class="activos" id="c-activos" hidden></div>
        <p class="nota" id="c-total"></p>
        <div class="lista" id="c-lista"></div>
      </div>
      <div class="col-previa">
        <div class="pestanas-col" role="tablist">
          <button type="button" data-pest="previa" role="tab" aria-selected="${PESTANA === "previa"}">Vista previa</button>
          <button type="button" data-pest="elegidos" role="tab" aria-selected="${PESTANA === "elegidos"}">Elegidos <span class="nota">(${s.elegidos || 0}/${s.cantidad || 0})</span></button>
        </div>
        <div id="previa-ej" class="previa-ej" ${PESTANA === "previa" ? "" : "hidden"}>
          <p class="nota">Elige una temática a la izquierda y pulsa un ejercicio de la lista para verlo completo antes de agregarlo.</p>
        </div>
        <div id="caja-elegidos" class="elegidos" ${PESTANA === "elegidos" ? "" : "hidden"}>${(s.items || []).map((it, i) => `
          <div class="elegido ${it.bloque_id ? "bloque" : ""}">
            <span class="num">${it.numero}</span><span class="letra" title="Letra que asigna la plantilla">${it.letra}</span>
            <span style="flex:1;min-width:0"><button type="button" class="enlace-ej" data-ver="${it.ejercicio_id}"><b class="mono">${esc(it.codigo)}</b></button> · ${esc(it.tematica)}${it.nivel ? " · " + esc(it.nivel) : ""}${it.glosario ? ' · <span class="etq">glosario</span>' : ""}<br><small class="nota">${esc(it.texto)}</small></span>
            <span class="acciones"><button type="button" class="mini" data-subir="${i}" ${i === 0 ? "disabled" : ""}>↑</button>
              <button type="button" class="mini" data-bajar="${i}" ${i === (s.items || []).length - 1 ? "disabled" : ""}>↓</button>
              <button type="button" class="mini quitar" data-quitar="${it.ejercicio_id}">Quitar</button></span>
          </div>`).join("") || '<p class="nota">Todavía no hay ejercicios en esta sección.</p>'}</div>
      </div>
    </div>`;
}

function cambiarPestana(cual) {
  PESTANA = cual;
  document.querySelectorAll(".pestanas-col button").forEach(b => b.setAttribute("aria-selected", b.dataset.pest === cual));
  const previa = $("#previa-ej"), elegidos = $("#caja-elegidos");
  if (previa) previa.hidden = cual !== "previa";
  if (elegidos) elegidos.hidden = cual !== "elegidos";
}

/** Vuelve a dejar el cursor donde estaba: la columna se repinta en cada búsqueda. */
function conFoco(pintar) {
  const a = document.activeElement;
  const id = a && a.id, pos = a && a.selectionStart;
  pintar();
  if (!id) return;
  const nuevo = document.getElementById(id);
  if (!nuevo) return;
  nuevo.focus();
  if (pos != null && nuevo.setSelectionRange) { try { nuevo.setSelectionRange(pos, pos); } catch (e) { /* no es campo de texto */ } }
}

/** Quita la tilde y las mayúsculas: buscar "division" encuentra "División". */
function normal(t) {
  return (t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

/** Lista de temáticas de la sección: las elegidas primero, luego las que tienen ejercicios y al final las agotadas. */
function filasTematica(lista) {
  const sel = FILTROS.tematicas || [];
  const busca = normal(BUSCA_TEM);
  if (!lista.length) return `<p class="nota vacio-tem">Esta sección todavía no tiene ejercicios en el banco. Sube ejercicios de esa materia y grado.</p>`;
  // con una búsqueda escrita arriba, solo se ofrecen las temáticas que tienen resultados
  const conResultado = FILTROS.texto && CANDIDATOS ? new Set(CANDIDATOS.items.map(x => x.tematica)) : null;
  let vistas = lista.filter(x => !busca || normal(x.valor).includes(busca));
  if (conResultado) vistas = vistas.filter(x => conResultado.has(x.valor) || sel.includes(x.valor));
  if (!vistas.length) return `<p class="nota vacio-tem">Ninguna de las ${lista.length} temáticas dice «${esc(BUSCA_TEM)}».
    <button type="button" class="enlace-ej" id="tem-limpiar-busca">Ver todas</button></p>`;
  const peso = x => (sel.includes(x.valor) ? 0 : x.n ? 1 : 2);
  vistas.sort((a, b) => peso(a) - peso(b) || a.valor.localeCompare(b.valor, "es"));
  return vistas.map(x => `<button type="button" class="fila-tem ${sel.includes(x.valor) ? "on" : ""} ${x.n ? "" : "agotada"}"
      data-filtro="tematicas" data-valor="${esc(x.valor)}" ${x.n ? "" : 'disabled title="No quedan ejercicios libres de esta temática para esta sección"'}>
      <span class="tem-check" aria-hidden="true">${sel.includes(x.valor) ? "✓" : ""}</span>
      <span class="tem-nom">${esc(x.valor)}</span>
      ${x.elegidos ? `<span class="tem-ya" title="${x.elegidos} de esta temática ya están en la sección">✓${x.elegidos}</span>` : ""}
      <span class="tem-n" title="${x.n} disponibles para elegir">${x.n}</span>
    </button>`).join("");
}

const ETIQUETA_FILTRO = {tematicas: "Temática", niveles: "Nivel", competencias: "Competencia", pensamientos: "Pensamiento",
                         dba: "DBA", materias: "Materia", submaterias: "Submateria", tipos: "Tipo", recurso: "Recurso"};
const NOMBRE_TIPO = {suelto: "Suelto", bloque: "Bloque", parte: "Parte"};
const NOMBRE_RECURSO = {imagen: "Con imagen", tabla: "Con tabla", glosario: "Con glosario", sin_imagen: "Sin imagen"};

function nombreValor(nombre, v) {
  return nombre === "tipos" ? (NOMBRE_TIPO[v] || v) : nombre === "recurso" ? (NOMBRE_RECURSO[v] || v) : v;
}

function pintarFiltros(r) {
  const f = FILTROS;
  const sel = k => f[k] || [];
  const tem = r.facetas.tematicas;
  // los grupos secundarios se muestran siempre que tengan algo, aunque sea un solo valor
  const opciones = (nombre, lista) => lista.length ? `<details class="filtro" ${sel(nombre).length ? "open" : ""}>
      <summary>${ETIQUETA_FILTRO[nombre]}
        <span class="nota">${sel(nombre).length ? sel(nombre).length + " de " + lista.length : lista.length}</span></summary>
      <div class="chips">${chips(nombre, lista, sel(nombre), x => nombreValor(nombre, x.valor))}</div></details>` : "";
  $("#filtros-ej").innerHTML = `
    <section class="caja-tem">
      <div class="tem-cab">
        <b>Temáticas</b>
        <span class="nota">${tem.length} en la sección${sel("tematicas").length ? ` · ${sel("tematicas").length} elegida${sel("tematicas").length === 1 ? "" : "s"}` : ""}</span>
        ${sel("tematicas").length ? `<button type="button" class="mini" id="tem-todas">Ver todas</button>` : ""}
      </div>
      <input type="search" id="tem-busca" class="busca-chip" placeholder="buscar temática…" value="${esc(BUSCA_TEM)}"
             aria-label="Buscar temática" ${tem.length > 6 ? "" : "hidden"}>
      <div class="filas-tem" id="filas-tem">${filasTematica(tem)}</div>
      ${tem.length ? `<p class="tem-pie">✓ ya en la sección · nº disponibles</p>` : ""}
    </section>
    `;
  // los demás filtros van arriba, en menús que solo aparecen si hay de dónde escoger
  const menu = (nombre, lista) => lista.length ? `<details class="menu-f" ${sel(nombre).length ? "open" : ""}>
      <summary>${ETIQUETA_FILTRO[nombre]}${sel(nombre).length ? ` <b>${sel(nombre).length}</b>` : ""} <span class="flecha" aria-hidden="true">▾</span></summary>
      <div class="chips">${chips(nombre, lista, sel(nombre), x => nombreValor(nombre, x.valor))}</div></details>` : "";
  $("#filtros-din").innerHTML = `
    ${menu("materias", (r.facetas.materias || []).length > 1 ? r.facetas.materias : [])}
    ${menu("niveles", r.facetas.niveles)}
    ${menu("competencias", r.facetas.competencias)}
    ${menu("pensamientos", r.facetas.pensamientos)}
    ${menu("dba", r.facetas.dba)}
    ${menu("submaterias", r.facetas.submaterias)}
    ${menu("tipos", r.facetas.tipos)}
    <details class="menu-f" ${(f.recurso || []).length ? "open" : ""}>
      <summary>Recurso${(f.recurso || []).length ? ` <b>${f.recurso.length}</b>` : ""} <span class="flecha" aria-hidden="true">▾</span></summary>
      <div class="chips">
        ${Object.keys(NOMBRE_RECURSO).map(v => `<button type="button" class="chip-f ${(f.recurso || []).includes(v) ? "on" : ""}" data-filtro="recurso" data-valor="${v}">${NOMBRE_RECURSO[v]}</button>`).join("")}
      </div></details>
    <button type="button" class="chip-f ${f.sin_usar ? "on" : ""}" data-sin-usar>Sin usar</button>
    <button type="button" class="chip-f ${f.ocultar_excluidos ? "on" : ""}" data-ocultar>Ocultar los de la otra sesión</button>
    <label class="orden-f">Orden
      <select id="c-orden">
        ${[["menos_usados", "Menos usados primero"], ["tematica", "Por temática"], ["nivel", "Por nivel"], ["recientes", "Más recientes"]]
          .map(([v, t]) => `<option value="${v}" ${f.orden === v ? "selected" : ""}>${t}</option>`).join("")}</select></label>`;
}

/** Lo que está filtrando ahora mismo, para verlo y quitarlo de uno en uno. */
function pintarActivos() {
  const f = FILTROS, trozos = [];
  Object.keys(ETIQUETA_FILTRO).forEach(k => (f[k] || []).forEach(v => trozos.push(
    `<button type="button" class="chip-quitar" data-filtro="${k}" data-valor="${esc(v)}" title="Quitar este filtro">${
      ETIQUETA_FILTRO[k]}: ${esc(nombreValor(k, v))}<span aria-hidden="true">✕</span></button>`)));
  if (f.texto) trozos.push(`<button type="button" class="chip-quitar" data-quitar-texto title="Quitar este filtro">Texto: ${esc(f.texto)}<span aria-hidden="true">✕</span></button>`);
  if (f.sin_usar) trozos.push(`<button type="button" class="chip-quitar" data-sin-usar title="Quitar este filtro">Sin usar<span aria-hidden="true">✕</span></button>`);
  if (f.ocultar_excluidos) trozos.push(`<button type="button" class="chip-quitar" data-ocultar title="Quitar este filtro">Ocultar los de la otra sesión<span aria-hidden="true">✕</span></button>`);
  const caja = $("#c-activos");
  caja.innerHTML = trozos.length
    ? `<span class="nota">Filtros:</span>${trozos.join("")}<button type="button" class="boton claro mini" id="c-limpiar">Quitar todos</button>` : "";
  caja.hidden = !trozos.length;
}

/** La búsqueda de temáticas es al instante: no vuelve a preguntar al servidor, solo filtra la lista que ya está. */
function pintarTematicas() {
  if (!CANDIDATOS) return;
  const caja = $("#filas-tem");
  if (caja) caja.innerHTML = filasTematica(CANDIDATOS.facetas.tematicas);
}

/** Si el tema buscado está en otra sección de la cartilla, lo dice y deja saltar allá. */
async function dondeEsta() {
  const caja = $("#c-donde");
  if (!caja) return;
  if (!FILTROS.texto) { caja.innerHTML = ""; ENCONTRADO = null; return; }
  try {
    ENCONTRADO = await api(`/api/cartillas/${CART.id}/buscar?texto=` + encodeURIComponent(FILTROS.texto));
  } catch (e) { caja.innerHTML = ""; return; }
  const otras = ENCONTRADO.secciones.filter(x => x.encontrados && x.id !== SECCION);
  const aqui = ENCONTRADO.secciones.find(x => x.id === SECCION);
  if (!ENCONTRADO.total) {
    caja.innerHTML = `<p class="aviso-busca vacío">No hay ningún ejercicio libre sobre eso en toda la cartilla.
      Revisa cómo está escrito el tema o sube ejercicios nuevos.</p>`;
    return;
  }
  caja.innerHTML = `<p class="aviso-busca">
    <b>${ENCONTRADO.total}</b> ejercicio${ENCONTRADO.total === 1 ? "" : "s"} sobre eso en la cartilla:
    ${aqui && aqui.encontrados ? `<span class="aqui">${aqui.encontrados} aquí</span>` : '<span class="aqui no">ninguno en esta sección</span>'}
    ${otras.map(x => `<button type="button" class="ir-seccion" data-ir="${x.id}"
        title="Ir a ${esc(x.titulo)} para agregarlos desde allí">
        ir a ${esc(x.titulo)} <b>${x.encontrados}</b>${x.faltan > 0 ? `<small> · faltan ${x.faltan}</small>` : ""}</button>`).join("")}
  </p>`;
}

async function cargarCandidatos() {
  const s = CART.secciones.find(x => x.id === SECCION);
  if (!s) return;
  const params = new URLSearchParams({seccion: SECCION});
  Object.entries(FILTROS).forEach(([k, v]) => {
    if (Array.isArray(v) && v.length) params.set({tematicas: "tematica", niveles: "nivel", competencias: "competencia",
      pensamientos: "pensamiento", materias: "materia", submaterias: "submateria", tipos: "tipo", dba: "dba",
      recurso: "recurso"}[k] || k, v.join(";"));
    else if (!Array.isArray(v) && v) params.set(k, v);
  });
  const r = await api(`/api/cartillas/${CART.id}/candidatos?` + params);
  CANDIDATOS = r;
  dondeEsta();
  conFoco(() => pintarFiltros(r));
  pintarActivos();
  const filtrado = !$("#c-activos").hidden;
  $("#c-total").innerHTML = `<b>${r.total}</b> ${filtrado ? `de ${r.disponibles} disponibles` : `ejercicio${r.total === 1 ? " disponible" : "s disponibles"}`}
    · faltan <b>${r.faltan}</b> para completar la sección${r.total > r.items.length ? ` · se muestran los primeros ${r.items.length}` : ""}`;
  $("#c-lista").innerHTML = r.items.map(x => `
    <div class="item-ej ${x.excluido ? "excluido" : ""} ${VISTO === x.id ? "activo" : ""}" data-ej="${x.id}">
      <button type="button" class="item-ver" data-ver="${x.id}">
        <span class="item-tem">${esc(x.tematica)}${x.en_seccion ? `<span class="item-ya" title="Ya hay ${x.en_seccion} de esta temática en la sección">×${x.en_seccion} en la sección</span>` : ""}</span>
        <span class="item-meta"><b class="mono">${esc(x.codigo)}</b>${x.nivel ? " · " + esc(x.nivel) : ""}${
          (r.facetas.materias || []).length > 1 ? " · " + esc(x.materia) : ""}</span>
        <span class="item-texto">${esc(x.texto)}</span>
        <span class="item-tags">${x.bloque ? `<span>${x.tipo === "parte" ? "Parte" : "Bloque"} de ${x.hermanos}</span>` : ""}
          ${x.imagen ? "<span>Imagen</span>" : ""}${x.tabla ? "<span>Tabla</span>" : ""}${x.glosario ? "<span>Glosario</span>" : ""}
          ${x.competencia ? `<span>${esc(x.competencia)}</span>` : ""}${x.dba ? `<span>${esc(x.dba)}</span>` : ""}
          <span>Usado ${x.veces_usado}</span>${x.excluido ? "<span class='aviso-tag'>Ya va en la otra sesión</span>" : ""}</span>
      </button>
      <button type="button" class="mini agregar" data-agregar="${x.id}"
              title="Agregar este ejercicio a ${esc((CART.secciones.find(s => s.id === SECCION) || {}).titulo || "la sección")}">+ Agregar</button>
    </div>`).join("") || `<p class="nota">${filtrado
      ? "Ningún ejercicio coincide con esos filtros. Quita alguno de los de arriba."
      : "No quedan ejercicios libres para esta sección: los del banco ya están elegidos aquí o en otra sección. Sube más ejercicios de esta materia."}</p>`;
}

async function verEjercicio(id) {
  VISTO = +id;
  cambiarPestana("previa");
  document.querySelectorAll(".item-ej").forEach(x => x.classList.toggle("activo", +x.dataset.ej === VISTO));
  const caja = $("#previa-ej");
  if (!caja) return;
  caja.innerHTML = '<p class="nota">Cargando…</p>';
  try {
    const d = await api("/api/banco/" + VISTO);
    const enSeccion = (CART.secciones.find(x => x.id === SECCION)?.items || []).some(i => i.ejercicio_id === VISTO);
    caja.innerHTML = `<div class="previa-cab"><b class="mono">${esc(d.codigo)}</b> · ${esc(d.tematica)}${d.nivel ? " · " + esc(d.nivel) : ""}
        ${d.bloque ? `<span class="etq">${d.tipo === "parte" ? "parte" : "bloque"} de ${d.hermanos} preguntas</span>` : ""}
        ${enSeccion ? '<span class="etq">ya está en la sección</span>' : `<button type="button" class="mini" data-agregar="${d.id}">+ Agregar a la sección</button>`}</div>
      <div class="hoja">${d.html}</div>
      <dl class="ficha-datos"><dt>Clave original</dt><dd>${esc(d.clave)}</dd>
        ${d.competencia ? `<dt>Competencia</dt><dd>${esc(d.competencia)}</dd>` : ""}
        ${d.pensamiento ? `<dt>Pensamiento</dt><dd>${esc(d.pensamiento)}</dd>` : ""}
        ${d.dba ? `<dt>DBA</dt><dd>${esc(d.dba)}</dd>` : ""}
        <dt>Usado</dt><dd>${d.veces_usado} ${d.veces_usado === 1 ? "vez" : "veces"}</dd>
        <dt>Justificación</dt><dd>${esc(d.justificacion)}</dd></dl>`;
  } catch (e) {
    caja.innerHTML = `<p class="err">No se pudo abrir el ejercicio: ${esc(e.message)}</p>`;
  }
}

function vistaRevision(c) {
  const listo = c.verificacion.every(p => p.ok);
  const generada = c.estado === "generada";
  return `<div class="dos-columnas">
    <div>
      <h3 class="nota">Revisión antes de generar</h3>
      <div class="verif">${c.verificacion.map(p => `<div><span class="${p.ok ? "si" : "no"}">${p.ok ? "✓" : "✗"}</span><span>${esc(p.texto)}</span></div>`).join("")}</div>
      <div class="panel-form portada" style="margin-top:14px">
        <h3 class="nota" style="margin:0">Portada</h3>
        <div class="tipos-portada">
          ${[["completa", "Portada completa", "Ocupa toda la primera página, con la tabla de áreas."],
             ["media", "Media portada", "Título, ilustración y datos arriba; las preguntas arrancan debajo, en la misma página."]]
            .map(([v, t, ayuda]) => `<label class="tipo-portada ${c.portada === v ? "on" : ""}">
              <input type="radio" name="portada" value="${v}" ${c.portada === v ? "checked" : ""}>
              <span><b>${t}</b><br><small class="nota">${ayuda}</small></span></label>`).join("")}
        </div>
        <label class="nota" style="display:block">Título impreso en la portada
          <input type="text" id="p-titulo" value="${esc(c.titulo_portada || "")}" placeholder="${esc(c.titulo_sugerido || "")}">
        </label>
        <div class="ilustracion">
          <div class="muestra-ilu">${c.imagen
            ? `<img src="/api/cartillas/${c.id}/imagen?v=${Date.now()}" alt="Ilustración de la portada">`
            : '<span class="nota">La de la plantilla</span>'}</div>
          <div>
            <p class="nota" style="margin:0 0 6px">Ilustración de la portada${c.imagen_nombre ? ` · <b>${esc(c.imagen_nombre)}</b>` : ""}</p>
            <label class="boton claro" for="p-imagen">Cambiar imagen</label>
            <input type="file" id="p-imagen" accept="image/png,image/jpeg,image/webp" hidden>
            ${c.imagen ? '<button type="button" class="boton claro" id="p-quitar-imagen">Volver a la de la plantilla</button>' : ""}
            <p class="nota" id="p-msg" role="status" style="margin:6px 0 0">PNG, JPG o WEBP, hasta 6 MB. Se usa en las dos portadas.</p>
          </div>
        </div>
      </div>
      <div class="panel-form" style="margin-top:14px">
        <label class="casilla"><input type="checkbox" id="g-glosario" ${c.glosario ? "checked" : ""} ${c.con_glosario ? "" : "disabled"}>
          <span><b>Incluir glosario</b><br><small class="nota">${c.con_glosario
            ? `${c.con_glosario} de ${c.elegidos} preguntas tienen glosario. Va al final de cada una, en letra pequeña.`
            : "Ninguna pregunta elegida tiene glosario."}${generada ? " Si lo cambias, genera de nuevo." : ""}</small></span>
        </label>
        <label class="nota" style="display:block">Nombre del archivo
          <input type="text" id="g-nombre" style="width:100%;font:inherit;padding:6px 8px;border:1px solid var(--linea-2);border-radius:8px"
                 value="${esc(c.codigo + " - " + c.nombre)}" ${generada ? "disabled" : ""}>
        </label>
        <p class="nota" id="g-archivos">El Word y el Excel salen con ese mismo nombre.</p>
        <div class="maquetacion">
          <button type="button" class="boton claro" id="btn-maqueta" ${generada ? "disabled" : ""}
                  title="${generada ? "Solo en borrador: vuelve al paso 2 si necesitas cambiar el orden" : "Mide la cartilla con Word y adelanta preguntas que quepan en los huecos"}">
            Aprovechar el espacio</button>
          <small class="nota">Adelanta preguntas de la misma sección que quepan en el espacio que sobra al final de
            una columna. Cambia la numeración, nunca la sección ni los bloques. Tarda cerca de un minuto.</small>
          <p class="nota" id="msg-maqueta" role="status"></p>
        </div>
        <div class="bar-acciones" style="margin-bottom:0">
          <button type="button" class="boton" id="btn-generar" ${listo ? "" : "disabled"} title="${listo ? "" : "Primero completa todas las secciones"}">
            ${generada ? "Generar de nuevo" : "Generar Word y Excel"}</button>
          ${c.archivos.includes("docx") ? `<a class="boton claro" href="/api/cartillas/${c.id}/archivo/docx">Descargar Word</a>` : ""}
          ${c.archivos.includes("xlsx") ? `<a class="boton claro" href="/api/cartillas/${c.id}/archivo/xlsx">Descargar Excel</a>` : ""}
        </div>
        <p class="err" id="g-error" role="alert"></p>
        ${generada && c.archivos.length ? `<div class="paginas">
          ${c.paginas ? `<b>${c.paginas} página${c.paginas === 1 ? "" : "s"}</b> · ${c.faltan_paginas
              ? `faltan <b>${c.faltan_paginas}</b> para el múltiplo de 4 (${c.paginas + c.faltan_paginas}). El ajuste se hace en el Word: agrega bloques del cierre o un salto de página; nunca se quitan preguntas.`
              : "ya es múltiplo de 4: lista para imprimir tipo folleto."}`
            : `No se pudieron contar las páginas (Word no respondió). <button type="button" class="mini" id="btn-paginas">Contar páginas</button>`}
        </div>` : ""}
        ${generada && !c.archivos.length ? '<p class="err">Cambiaste el glosario después de generar: pulsa «Generar de nuevo» para descargar el Word y el Excel actualizados.</p>' : ""}
        ${generada && c.archivos.length ? '<p class="guardado">Cartilla generada. El Word es editable: puedes ajustar el logo, el vocabulario o el relleno, pero no cambies el orden de preguntas u opciones.</p>' : ""}
      </div>
    </div>
    <div>
      <h3 class="nota">Vista previa del cuadernillo</h3>
      <div id="previa" class="hoja-previa"><p class="nota">Armando la vista previa de las preguntas…</p></div>
    </div>
  </div>`;
}

async function cargarVistaPrevia() {
  const caja = $("#previa");
  if (caja) caja.innerHTML = `<p class="nota">Armando la vista previa de ${CART.elegidos} pregunta(s)…</p>`;
  const vp = await api(`/api/cartillas/${CART.id}/vista-previa`);
  $("#previa").innerHTML = vp.html || '<p class="nota">Sin ejercicios todavía.</p>';
}

document.addEventListener("click", async e => {
  if (e.target.closest("#btn-copiar-prompt") || e.target.closest("#btn-ver-prompt")) {
    const ver = !!e.target.closest("#btn-ver-prompt");
    const msg = $("#msg-prompt");
    try {
      if (!PROMPT) PROMPT = (await api("/api/prompt")).texto;
      const caja = $("#texto-prompt");
      caja.textContent = PROMPT;
      if (ver) { caja.hidden = !caja.hidden; msg.textContent = ""; return; }
      await navigator.clipboard.writeText(PROMPT);
      msg.textContent = `Copiado: ${PROMPT.length.toLocaleString("es-CO")} caracteres. Pégalo y detrás pega el simulacro.`;
    } catch (err) {
      // algunos navegadores no dejan copiar sin un gesto suyo: se muestra el texto YA SELECCIONADO,
      // para que baste con Ctrl+C. Son 22.000 caracteres: seleccionarlos a mano es un castigo.
      const caja = $("#texto-prompt");
      caja.hidden = false;
      const r = document.createRange();
      r.selectNodeContents(caja);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      caja.scrollIntoView({block: "nearest"});
      msg.textContent = "El texto quedó seleccionado abajo: pulsa Ctrl+C para copiarlo.";
    }
    return;
  }
  if (e.target.closest("#btn-volver")) { CART = null; SECCION = null; return simulacros(); }
  const paso = e.target.closest("[data-paso]");
  if (paso) { PASO = +paso.dataset.paso; CART = await api("/api/cartillas/" + CART.id); return pintarEditor(); }
  const mover = e.target.closest("[data-mover]");
  if (mover) {
    const [i, d] = mover.dataset.mover.split(",").map(Number);
    const secs = CART.secciones;
    [secs[i], secs[i + d]] = [secs[i + d], secs[i]];
    return guardarSecciones();
  }
  if (e.target.closest("#btn-guardar-sec")) return guardarSecciones();
  const quitarSec = e.target.closest("[data-quitar-sec]");
  if (quitarSec) return guardarSecciones(null, +quitarSec.dataset.quitarSec);
  if (e.target.closest("#btn-agregar-sec")) {
    const titulo = $("#ns-titulo").value.trim(), cantidad = +$("#ns-cantidad").value;
    if (!titulo || !(cantidad > 0)) { $("#sec-error").textContent = "La sección nueva necesita título y una cantidad de preguntas mayor que cero."; return; }
    const elegida = $("#ns-materia").value;
    const grupo = elegida.startsWith("grupo:") ? (OPC.grupos || []).find(g => g.nombre === elegida.slice(6)) : null;
    return guardarSecciones(grupo
      ? {titulo, materia: grupo.materias[0], materias: grupo.materias, submateria: null, cantidad, dificultad: "="}
      : {titulo, materia: elegida, submateria: $("#ns-sub").value || null, cantidad, dificultad: "="});
  }
  const agregar = e.target.closest("[data-agregar]");
  if (agregar) {
    try {
      const r = await api(`/api/cartillas/${CART.id}/items`, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({seccion: SECCION, ejercicio: +agregar.dataset.agregar})});
      CART = r.cartilla;
      pintarEditor();
    } catch (err) { alert(JSON.parse(err.message).detail || err.message); }
    return;
  }
  const quitar = e.target.closest("[data-quitar]");
  if (quitar) {
    const r = await api(`/api/cartillas/${CART.id}/items/${quitar.dataset.quitar}`, {method: "DELETE"});
    CART = r.cartilla;
    return pintarEditor();
  }
  const subir = e.target.closest("[data-subir]"), bajar = e.target.closest("[data-bajar]");
  if (subir || bajar) {
    const i = +(subir || bajar).dataset[subir ? "subir" : "bajar"], d = subir ? -1 : 1;
    const s = CART.secciones.find(x => x.id === SECCION);
    const ids = s.items.map(x => x.ejercicio_id);
    [ids[i], ids[i + d]] = [ids[i + d], ids[i]];
    try {
      CART = await api(`/api/cartillas/${CART.id}/secciones/${SECCION}/orden`, {method: "POST",
        headers: {"Content-Type": "application/json"}, body: JSON.stringify({orden: ids})});
      pintarEditor();
    } catch (err) { alert(JSON.parse(err.message).detail || err.message); }
    return;
  }
  const maq = e.target.closest("#btn-maqueta");
  if (maq) {
    maq.disabled = true;
    const msg = $("#msg-maqueta");
    msg.textContent = "Midiendo la cartilla con Word… esto tarda cerca de un minuto.";
    try {
      const r = await api(`/api/cartillas/${CART.id}/maquetacion`, {method: "POST"});
      CART = r.cartilla;
      pintarEditor();
      const caja = $("#msg-maqueta");
      caja.innerHTML = !r.ok ? esc(r.motivo || "No se pudo medir la cartilla.")
        : !r.mejoro ? `No hay nada que ganar: la cartilla ya aprovecha el espacio (${r.antes.paginas} páginas, se pierden ${Math.round(r.antes.perdido / 28.35 * 10) / 10} cm en total).`
        : `Listo: de <b>${r.antes.paginas}</b> a <b>${r.despues.paginas}</b> páginas · se adelantaron <b>${r.movidas.length}</b> pregunta(s): ${r.movidas.map(m => esc(m.codigo)).join(", ")}. Genera de nuevo para ver el resultado.`;
    } catch (err) {
      $("#msg-maqueta").textContent = JSON.parse(err.message).detail || err.message;
      maq.disabled = false;
    }
    return;
  }
  const pag = e.target.closest("#btn-paginas");
  if (pag) {
    pag.disabled = true;
    pag.textContent = "Contando…";
    try {
      const r = await api(`/api/cartillas/${CART.id}/paginas`, {method: "POST"});
      CART = r.cartilla;
      pintarEditor();
      if (!r.paginas) $("#g-error").textContent = "Word no respondió. Revisa que Microsoft Word esté instalado y vuelve a intentar.";
    } catch (err) { $("#g-error").textContent = JSON.parse(err.message).detail || err.message; pag.disabled = false; pag.textContent = "Contar páginas"; }
    return;
  }
  const gen = e.target.closest("#btn-generar");
  if (gen) {
    gen.disabled = true;
    $("#g-error").textContent = "";
    $("#g-archivos").textContent = "Generando el Word y el Excel, y contando las páginas…";
    try {
      const r = await api(`/api/cartillas/${CART.id}/generar`, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({nombre: $("#g-nombre").value})});
      CART = await api("/api/cartillas/" + CART.id);
      pintarEditor();
      $("#g-archivos").textContent = `Listo: ${r.docx} y ${r.xlsx} · ${r.preguntas} preguntas verificadas una por una.`
        + (r.paginas ? ` · ${r.paginas} páginas.` : "");
    } catch (err) {
      $("#g-error").textContent = JSON.parse(err.message).detail || err.message;
      $("#g-archivos").textContent = "";
      gen.disabled = false;
    }
    return;
  }
  const pest = e.target.closest(".pestanas-col button");
  if (pest) return cambiarPestana(pest.dataset.pest);
  if (e.target.closest("#p-quitar-imagen")) {
    try {
      CART = await api(`/api/cartillas/${CART.id}/imagen`, {method: "DELETE"});
      pintarEditor();
    } catch (err) { $("#p-msg").textContent = JSON.parse(err.message).detail || err.message; }
    return;
  }
  if (e.target.closest("#tem-todas")) { delete FILTROS.tematicas; return cargarCandidatos(); }
  if (e.target.closest("#tem-limpiar-busca")) { BUSCA_TEM = ""; return pintarTematicas(); }
  if (e.target.closest("[data-quitar-texto]")) { delete FILTROS.texto; return cargarCandidatos(); }
  const ir = e.target.closest("[data-ir]");
  if (ir) {                                   // el tema buscado está en otra sección: saltar allá sin perder la búsqueda
    SECCION = +ir.dataset.ir;
    VISTO = null;
    BUSCA_TEM = "";
    Object.keys(FILTROS).forEach(k => { if (k !== "texto" && k !== "orden") delete FILTROS[k]; });
    return pintarEditor();
  }
  const chip = e.target.closest("[data-filtro]");
  if (chip) {
    const k = chip.dataset.filtro, v = chip.dataset.valor;
    const lista = FILTROS[k] || [];
    FILTROS[k] = lista.includes(v) ? lista.filter(x => x !== v) : lista.concat(v);
    if (!FILTROS[k].length) delete FILTROS[k];
    return cargarCandidatos();
  }
  if (e.target.closest("[data-sin-usar]")) { FILTROS.sin_usar ? delete FILTROS.sin_usar : FILTROS.sin_usar = "1"; return cargarCandidatos(); }
  if (e.target.closest("[data-ocultar]")) { FILTROS.ocultar_excluidos ? delete FILTROS.ocultar_excluidos : FILTROS.ocultar_excluidos = "1"; return cargarCandidatos(); }
  if (e.target.closest("#c-limpiar")) { FILTROS = {}; return cargarCandidatos(); }
  const ver = e.target.closest("[data-ver]");
  if (ver) return verEjercicio(ver.dataset.ver);
  if (e.target.closest("#btn-auto")) {
    const b = e.target.closest("#btn-auto");
    b.disabled = true;
    try {
      const r = await api(`/api/cartillas/${CART.id}/secciones/${SECCION}/automatica`, {method: "POST",
        headers: {"Content-Type": "application/json"}, body: "{}"});
      CART = r.cartilla;
      pintarEditor();
      $("#msg-auto").textContent = r.mensaje;
    } catch (err) { alert(JSON.parse(err.message).detail || err.message); b.disabled = false; }
  }
});

document.addEventListener("focusout", e => {
  if (e.target.id === "p-titulo" && e.target.value.trim() !== (CART?.titulo_portada || "")) {
    guardarPortada({titulo: e.target.value});
  }
});

document.addEventListener("change", async e => {
  if (e.target.id === "sel-seccion") { SECCION = +e.target.value; FILTROS = {}; VISTO = null; BUSCA_TEM = ""; return pintarEditor(); }
  if (e.target.id === "ns-materia" || e.target.id === "ns-sub") {
    if (e.target.id === "ns-materia") {
      const grupo = e.target.value.startsWith("grupo:");
      $("#ns-sub").innerHTML = grupo ? '<option value="">(todas las de las materias del grupo)</option>'
                                     : opcionesSubmateria(e.target.value, CART.grado);
      $("#ns-sub").disabled = grupo;
    }
    const elegida = $("#ns-materia").value;
    $("#ns-titulo").value = (elegida.startsWith("grupo:") ? elegida.slice(6) : ($("#ns-sub").value || elegida)).toUpperCase();
    return;
  }
  if (e.target.id === "g-glosario") {
    const casilla = e.target;
    casilla.disabled = true;
    try {
      CART = await api(`/api/cartillas/${CART.id}/glosario`, {method: "PUT", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({incluir: casilla.checked})});
      pintarEditor();
    } catch (err) { casilla.checked = !casilla.checked; casilla.disabled = false; alert(JSON.parse(err.message).detail || err.message); }
    return;
  }
  if (e.target.id === "c-orden") { FILTROS.orden = e.target.value; return cargarCandidatos(); }
  if (e.target.name === "portada") return guardarPortada({portada: e.target.value});
  if (e.target.id === "p-imagen") {
    const archivo = e.target.files[0];
    if (!archivo) return;
    const cuerpo = new FormData();
    cuerpo.append("archivo", archivo);
    $("#p-msg").textContent = "Subiendo la imagen…";
    try {
      CART = await api(`/api/cartillas/${CART.id}/imagen`, {method: "POST", body: cuerpo});
      pintarEditor();
    } catch (err) { $("#p-msg").textContent = JSON.parse(err.message).detail || err.message; }
    return;
  }
  if (e.target.dataset?.cantidad) {
    const total = [...document.querySelectorAll("[data-cantidad]")].reduce((a, x) => a + (+x.value || 0), 0);
    const t = $("#sec-total");
    if (t) t.textContent = total;
  }
});
async function guardarPortada(cambios) {
  try {
    CART = await api(`/api/cartillas/${CART.id}/portada`, {method: "PUT",
      headers: {"Content-Type": "application/json"}, body: JSON.stringify(cambios)});
    pintarEditor();
  } catch (err) { alert(JSON.parse(err.message).detail || err.message); }
}

document.addEventListener("input", e => {
  if (e.target.id === "c-texto") {
    FILTROS.texto = e.target.value.trim() || undefined;
    if (!FILTROS.texto) delete FILTROS.texto;
    clearTimeout(temporizador);
    temporizador = setTimeout(cargarCandidatos, 300);
  }
  if (e.target.id === "p-titulo") return;      // el título se guarda al salir del campo
  if (e.target.id === "tem-busca") {
    BUSCA_TEM = e.target.value;
    pintarTematicas();
  }
});

async function guardarSecciones(nueva = null, quitar = null) {
  const secciones = CART.secciones.filter(s => s.id !== quitar).map(s => ({
    id: s.id, titulo: s.titulo, materia: s.materia, submateria: s.submateria,
    cantidad: +(document.querySelector(`[data-cantidad="${s.id}"]`)?.value ?? s.cantidad),
    dificultad: document.querySelector(`[data-dificultad="${s.id}"]`)?.value ?? s.dificultad,
  }));
  if (nueva) secciones.push(nueva);          // puede traer «materias» si es un grupo
  try {
    CART = await api(`/api/cartillas/${CART.id}/secciones`, {method: "PUT", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({secciones})});
    pintarEditor();
  } catch (err) {
    const el = $("#sec-error");
    if (el) el.textContent = JSON.parse(err.message).detail || err.message;
  }
}

/* ================================================================ formatos */
let formatosCargados = false;
async function cargarFormatos() {
  if (formatosCargados) return;
  const lista = await api("/api/formatos");
  const grupos = {};
  lista.forEach(f => (grupos[f.grupo] ??= []).push(f));
  $("#formatos").innerHTML = Object.entries(grupos).map(([g, fs]) => `
    <div class="grupo-formatos"><h2>${esc(g)}</h2><div class="fichas">
      ${fs.map(f => `<div class="ficha"><b>${esc(f.titulo)}</b><small>${esc(f.descripcion)}</small><code>${esc(f.nombre)}</code>
        <a class="boton" href="/formatos/${f.archivo}" download="${esc(f.nombre)}">Descargar Word</a></div>`).join("")}
    </div></div>`).join("");
  formatosCargados = true;
}

/* ================================================================ catálogos */
let catalogosCargados = false;
async function cargarCatalogos() {
  if (catalogosCargados) return;
  const c = await api("/api/catalogos");
  const tabla = (enc, filas) => `<div class="tabla-scroll"><table class="datos"><tr>${enc.map(e => `<th>${e}</th>`).join("")}</tr>${filas.join("")}</table></div>`;
  $("#catalogos").innerHTML = `
    <div class="cat"><h2>Grados</h2>${tabla(["Grado", "Código", "En la portada"], c.grados.map(g => `<tr><td>${esc(g.nombre)}</td><td class="mono">${g.codigo}</td><td>${esc(g.portada)}</td></tr>`))}</div>
    <div class="cat"><h2>Materias y submaterias</h2>${tabla(["Materia", "Código", "Prefijo", "Submaterias (código · prefijo)"], c.materias.map(m => `<tr>
      <td><span class="color" style="background:${m.color}"></span>${esc(m.nombre)}</td><td class="mono">${m.codigo || "—"}</td><td class="mono">${m.prefijo || "—"}</td>
      <td>${m.submaterias.map(s => `${esc(s.nombre)} <span class="mono">(${s.codigo} · ${s.prefijo})</span>`).join("<br>") || "—"}</td></tr>`))}</div>
    <div class="cat"><h2>Agrupaciones y partes</h2>${tabla(["Código", "Agrupación"], c.agrupaciones.map(a => `<tr><td class="mono">${a.codigo}</td><td>${esc(a.nombre)}</td></tr>`))}</div>
    <div class="cat"><h2>Tipos de material</h2>${tabla(["Código", "Tipo"], c.tipos.map(t => `<tr><td class="mono">${t.codigo}</td><td>${esc(t.nombre)}</td></tr>`))}</div>
    <div class="cat"><h2>Estructuras</h2><div class="estructuras">${c.estructuras.map(e => `<div class="estructura">
      <h3>${e.clave} · ${esc(e.nombre)}</h3>
      <div class="nota">Código de materia ${e.codigo_materia || "según la materia"} · ${e.editable ? "se arma en el momento" : e.total + " preguntas"}</div>
      <ol>${e.secciones.map(s => `<li><span>${esc(s.titulo)}${s.mezclada ? " <small>(mezclada)</small>" : ""}</span><span class="mono">${s.cantidad}</span></li>`).join("")}</ol></div>`).join("")}</div></div>
    <div class="cat"><h2>Plantillas de respuestas</h2>${tabla(["Plantilla", "140 posiciones"], c.plantillas.map(p => `<tr><td class="mono">${p.numero}</td><td class="secuencia">${p.secuencia.replace(/(.{10})/g, "$1 ")}</td></tr>`))}</div>
    <div class="cat"><h2>Excepciones de superíndice</h2><p class="nota">Escrituras que se aceptan aunque tengan una letra seguida de un número.</p><div class="etiquetas">${c.excepciones.map(e => `<span>${esc(e)}</span>`).join("")}</div></div>
    <div class="cat"><h2>Frases prohibidas</h2><p class="nota">Texto de trabajo que no puede quedar en un archivo de carga.</p><div class="etiquetas">${c.frases.map(f => `<span>${esc(f.frase)}${f.mayusculas ? " · solo en mayúsculas" : ""}</span>`).join("")}</div></div>`;
  catalogosCargados = true;
}

mostrar(location.hash.slice(1));
