/**
 * likes.js
 * --------
 * Dos responsabilidades independientes en un mismo archivo de interacción
 * "social" ligera:
 *   1. Sistema de "me gusta" asíncrono vía Fetch API (sin recargar la página).
 *   2. Modo claro/oscuro persistente usando LocalStorage.
 */

document.addEventListener("DOMContentLoaded", () => {
  inicializarModoOscuro();
  inicializarBotonesLike();
});

/* =========================================================
 *  MODO OSCURO / CLARO
 * ========================================================= */
function inicializarModoOscuro() {
  const CLAVE_ALMACENAMIENTO = "triumphare-tema";
  const raiz = document.documentElement;
  const boton = document.getElementById("boton-tema");

  const temaGuardado = localStorage.getItem(CLAVE_ALMACENAMIENTO);
  const prefiereOscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const temaInicial = temaGuardado || (prefiereOscuro ? "oscuro" : "claro");

  aplicarTema(temaInicial);

  if (boton) {
    boton.addEventListener("click", () => {
      const temaActual = raiz.getAttribute("data-tema") === "oscuro" ? "oscuro" : "claro";
      const nuevoTema = temaActual === "oscuro" ? "claro" : "oscuro";
      aplicarTema(nuevoTema);
      localStorage.setItem(CLAVE_ALMACENAMIENTO, nuevoTema);
    });
  }

  function aplicarTema(tema) {
    if (tema === "oscuro") {
      raiz.setAttribute("data-tema", "oscuro");
      if (boton) boton.textContent = "☀️";
    } else {
      raiz.removeAttribute("data-tema");
      if (boton) boton.textContent = "🌙";
    }
  }
}

/* =========================================================
 *  LIKES ASÍNCRONOS
 * ========================================================= */
function inicializarBotonesLike() {
  const botones = document.querySelectorAll(".boton-like");

  botones.forEach((boton) => {
    boton.addEventListener("click", async () => {
      // Si el usuario no ha iniciado sesión, el botón lleva data-requiere-login
      // y simplemente redirige al login en vez de intentar la petición.
      if (boton.dataset.requiereLogin === "true") {
        window.location.href = boton.dataset.loginUrl;
        return;
      }

      const postId = boton.dataset.postId;
      const url = `/post/${postId}/like`;
      const contadorSpan = boton.querySelector(".contador-likes");

      boton.disabled = true;

      try {
        const respuesta = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": obtenerTokenCSRF(),
          },
        });

        if (!respuesta.ok) {
          throw new Error(`Error del servidor: ${respuesta.status}`);
        }

        const datos = await respuesta.json();

        if (contadorSpan) contadorSpan.textContent = datos.total_likes;
        boton.classList.toggle("esta-activo", datos.dio_like);

        // Pequeña animación de "pulso" en el ícono al dar like
        boton.classList.remove("animar");
        void boton.offsetWidth; // fuerza reflow para poder reiniciar la animación
        boton.classList.add("animar");
      } catch (error) {
        console.error("No se pudo procesar el like:", error);
        mostrarErrorTemporal(boton);
      } finally {
        boton.disabled = false;
      }
    });
  });
}

/** Lee el token CSRF incrustado en el <meta> de base.html */
function obtenerTokenCSRF() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

/** Feedback visual simple si la petición de like falla (ej. sin conexión) */
function mostrarErrorTemporal(boton) {
  const textoOriginal = boton.title;
  boton.title = "No se pudo registrar el like. Intenta de nuevo.";
  setTimeout(() => { boton.title = textoOriginal || ""; }, 3000);
}
