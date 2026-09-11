/* main.js — TriumHive
   Theme switcher + lightbox for post images
*/

(function () {
  "use strict";

  /* ============================================================
     TEMA (oscuro / claro) — persiste en localStorage
     ============================================================ */
  const html = document.documentElement;
  const botonTema = document.getElementById("boton-tema");

  function aplicarTema(tema) {
    html.dataset.tema = tema;
    if (botonTema) botonTema.textContent = tema === "oscuro" ? "☀️" : "🌙";
  }

  // Inicializar con el tema guardado o la preferencia del sistema
  const temaGuardado = localStorage.getItem("triumhive-tema");
  if (temaGuardado) {
    aplicarTema(temaGuardado);
  } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    aplicarTema("oscuro");
  }

  if (botonTema) {
    botonTema.addEventListener("click", function () {
      const actual = html.dataset.tema === "oscuro" ? "claro" : "oscuro";
      aplicarTema(actual);
      localStorage.setItem("triumhive-tema", actual);
    });
  }

  /* ============================================================
     LIGHTBOX para imágenes de posts
     ============================================================ */
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightbox-img");

  if (lightbox && lightboxImg) {
    // Abrir al hacer clic en cualquier imagen marcada
    document.addEventListener("click", function (e) {
      const img = e.target.closest("[data-lightbox='true']");
      if (img) {
        lightboxImg.src = img.src;
        lightboxImg.alt = img.alt || "Imagen";
        lightbox.classList.add("activo");
        document.body.style.overflow = "hidden";
      }
    });

    // Cerrar al hacer clic en el overlay o presionar Esc
    lightbox.addEventListener("click", function () {
      lightbox.classList.remove("activo");
      document.body.style.overflow = "";
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && lightbox.classList.contains("activo")) {
        lightbox.classList.remove("activo");
        document.body.style.overflow = "";
      }
    });
  }

  /* ============================================================
     AUTO-DISMISS de alertas flash tras 5 segundos
     ============================================================ */
  const alertas = document.querySelectorAll(".alerta");
  alertas.forEach(function (alerta) {
    setTimeout(function () {
      alerta.style.transition = "opacity 0.4s ease";
      alerta.style.opacity = "0";
      setTimeout(function () { alerta.remove(); }, 400);
    }, 5000);
  });

})();
