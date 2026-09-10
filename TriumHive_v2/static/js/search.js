/* search.js — TriumHive
   Búsqueda en tiempo real usando la API /api/buscar
*/

(function () {
  "use strict";

  const input = document.getElementById("input-busqueda");
  const contenedor = document.getElementById("resultados-busqueda");
  if (!input || !contenedor) return;

  let temporizador = null;

  input.addEventListener("input", function () {
    const termino = this.value.trim();
    clearTimeout(temporizador);

    if (termino.length < 2) {
      ocultarResultados();
      return;
    }

    temporizador = setTimeout(function () {
      buscar(termino);
    }, 250);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      ocultarResultados();
      this.blur();
    }
  });

  document.addEventListener("click", function (e) {
    if (!input.contains(e.target) && !contenedor.contains(e.target)) {
      ocultarResultados();
    }
  });

  function buscar(termino) {
    fetch("/api/buscar?q=" + encodeURIComponent(termino))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderizarResultados(data.resultados || []);
      })
      .catch(function () { ocultarResultados(); });
  }

  function renderizarResultados(resultados) {
    contenedor.innerHTML = "";

    if (resultados.length === 0) {
      contenedor.innerHTML = '<p class="buscador__vacio">Sin resultados para esa búsqueda.</p>';
      contenedor.classList.add("esta-visible");
      return;
    }

    resultados.forEach(function (r) {
      const a = document.createElement("a");
      a.href = r.url;
      a.className = "buscador__item";
      a.innerHTML = `
        <span style="font-size:1.1rem">${r.categoria_icono || "📌"}</span>
        <span>
          <strong>${escapeHtml(r.titulo)}</strong>
          <small>${escapeHtml(r.categoria)} · @${escapeHtml(r.autor)}</small>
        </span>`;
      contenedor.appendChild(a);
    });

    contenedor.classList.add("esta-visible");
  }

  function ocultarResultados() {
    contenedor.classList.remove("esta-visible");
    contenedor.innerHTML = "";
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

})();
