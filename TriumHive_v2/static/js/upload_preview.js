/* upload_preview.js — TriumHive
   Vista previa de archivos seleccionados antes de enviar el formulario.
*/

(function () {
  "use strict";

  const MAX_ARCHIVOS = 5;
  const MAX_MB = 10;

  function formatearTamanio(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function esImagen(tipo) {
    return tipo && tipo.startsWith("image/");
  }

  function inicializarUpload(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (!input || !preview) return;

    input.addEventListener("change", function () {
      preview.innerHTML = "";
      const archivos = Array.from(this.files).slice(0, MAX_ARCHIVOS);

      archivos.forEach(function (archivo) {
        if (archivo.size > MAX_MB * 1024 * 1024) {
          const warn = document.createElement("div");
          warn.className = "error-campo";
          warn.textContent = `⚠ "${archivo.name}" supera los ${MAX_MB} MB y será ignorado.`;
          preview.appendChild(warn);
          return;
        }

        const item = document.createElement("div");
        item.className = "preview-item";

        if (esImagen(archivo.type)) {
          const reader = new FileReader();
          reader.onload = function (e) {
            const img = document.createElement("img");
            img.src = e.target.result;
            img.alt = archivo.name;
            item.appendChild(img);
          };
          reader.readAsDataURL(archivo);
        } else {
          const ext = archivo.name.split(".").pop().toUpperCase();
          item.innerHTML = `<span style="font-size:1.3rem">${iconoExt(ext)}</span><span style="font-size:0.6rem;padding:2px">${ext}<br>${formatearTamanio(archivo.size)}</span>`;
        }

        preview.appendChild(item);
      });
    });
  }

  function iconoExt(ext) {
    const mapa = { PDF: "📄", DOCX: "📝", DOC: "📝", XLSX: "📊", XLS: "📊", ZIP: "🗜️", TXT: "📃" };
    return mapa[ext] || "📎";
  }

  // Post form
  inicializarUpload("input-adjuntos", "preview-archivos");

  // Avatar (perfil) — muestra previsualización inline
  const inputAvatar = document.getElementById("input-avatar");
  const zonaAvatar = document.getElementById("zona-avatar");
  if (inputAvatar && zonaAvatar) {
    inputAvatar.addEventListener("change", function () {
      const f = this.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = function (e) {
        // Insertar/actualizar la imagen del avatar grande si existe
        const avatarGrande = document.querySelector(".avatar-grande");
        if (avatarGrande) {
          avatarGrande.innerHTML = `<img src="${e.target.result}" alt="Vista previa" style="width:100%;height:100%;object-fit:cover">`;
        }
        // Actualizar el fondo de la zona
        zonaAvatar.querySelector(".zona-upload__texto").textContent = `✅ ${f.name}`;
      };
      reader.readAsDataURL(f);
    });
  }

  // Drag & drop visual para la zona de upload
  document.querySelectorAll(".zona-upload").forEach(function (zona) {
    zona.addEventListener("dragover", function (e) {
      e.preventDefault();
      zona.classList.add("drag-over");
    });
    zona.addEventListener("dragleave", function () {
      zona.classList.remove("drag-over");
    });
    zona.addEventListener("drop", function (e) {
      zona.classList.remove("drag-over");
      const input = zona.querySelector("input[type='file']");
      if (input) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event("change"));
      }
    });
  });

})();
