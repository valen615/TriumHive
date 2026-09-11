/* likes.js — TriumHive
   Maneja los "me gusta" asíncronos vía Fetch API (sin recargar la página).
*/

document.addEventListener("DOMContentLoaded", function () {
  inicializarBotonesLike();
});

function inicializarBotonesLike() {
  document.addEventListener("click", function (e) {
    const boton = e.target.closest(".boton-like");
    if (!boton) return;

    if (boton.dataset.requiereLogin === "true") {
      window.location.href = boton.dataset.loginUrl;
      return;
    }

    const postId = boton.dataset.postId;
    if (!postId) return;

    const url = `/post/${postId}/like`;
    const contadorSpan = boton.querySelector(".contador-likes");

    boton.disabled = true;

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": obtenerTokenCSRF(),
      },
    })
      .then(function (r) {
        if (!r.ok) throw new Error("Error " + r.status);
        return r.json();
      })
      .then(function (datos) {
        if (contadorSpan) contadorSpan.textContent = datos.total_likes;
        boton.classList.toggle("esta-activo", datos.dio_like);
        // Animación de pulso
        boton.classList.remove("animar");
        void boton.offsetWidth;
        boton.classList.add("animar");
      })
      .catch(function (err) {
        console.error("No se pudo procesar el like:", err);
      })
      .finally(function () {
        boton.disabled = false;
      });
  });
}

function obtenerTokenCSRF() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}
