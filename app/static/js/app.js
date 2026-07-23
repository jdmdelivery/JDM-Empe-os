(() => {
  const root = document.documentElement;
  root.setAttribute("data-theme", "dark");
  document.body.setAttribute("data-theme", "dark");

  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", (event) => {
      const message = el.getAttribute("data-confirm") || "¿Confirmar acción?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
})();