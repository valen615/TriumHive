/**
 * search.js
 * ---------
 * Búsqueda en tiempo real (sin recargar la página) sobre el título de
 * las publicaciones, consultando el endpoint /api/buscar de app.py.
 * Aplica "debounce" para no disparar una petición por cada tecla.
 */

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("input-busqueda");
  const contenedorResultados = document.getElementById("resultados-busqueda");

  if (!input || !contenedorResultados) return;

  let temporizador = null;
  const RETRASO_MS = 300;

  input.addEventListener("input", () => {
    const termino = input.value.trim();

    clearTimeout(temporizador);

    if (termino.length < 2) {
      ocultarResultados();
      return;
    }

    temporizador = setTimeout(() => buscar(termino), RETRASO_MS);
  });

  // Cierra el desplegable si el usuario hace clic fuera del buscador
  document.addEventListener("click", (evento) => {
    if (!evento.target.closest(".buscador")) {
      ocultarResultados();
    }
  });

  // Permite navegar los resultados y cerrarlos con la tecla Escape
  input.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") ocultarResultados();
  });

  async function buscar(termino) {
    try {
      const respuesta = await fetch(`/api/buscar?q=${encodeURIComponent(termino)}`);
      if (!respuesta.ok) throw new Error("Fallo en la búsqueda");

      const datos = await respuesta.json();
      renderizarResultados(datos.resultados, termino);
    } catch (error) {
      console.error("Error al buscar publicaciones:", error);
      ocultarResultados();
    }
  }

  function renderizarResultados(resultados, termino) {
    contenedorResultados.innerHTML = "";

    if (resultados.length === 0) {
      const vacio = document.createElement("div");
      vacio.className = "buscador__vacio";
      vacio.textContent = `Sin resultados para "${termino}"`;
      contenedorResultados.appendChild(vacio);
    } else {
      resultados.forEach((post) => {
        const enlace = document.createElement("a");
        enlace.className = "buscador__item";
        enlace.href = post.url;
        enlace.innerHTML = `
          <strong>${escaparHTML(post.titulo)}</strong>
          <small>${escaparHTML(post.categoria)} · por ${escaparHTML(post.autor)}</small>
        `;
        contenedorResultados.appendChild(enlace);
      });
    }

    mostrarResultados();
  }

  function mostrarResultados() {
    contenedorResultados.classList.add("esta-visible");
  }

  function ocultarResultados() {
    contenedorResultados.classList.remove("esta-visible");
  }

  /** Evita inyección de HTML al insertar texto proveniente del servidor */
  function escaparHTML(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
  }
});
