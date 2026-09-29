document.querySelectorAll(".notify-customer-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.classList.contains("confirm-cancel")) {
      const orderNumber = form.dataset.orderNumber;
      if (!window.confirm(`Deseja realmente cancelar o pedido #${orderNumber} e avisar o cliente?`)) {
        event.preventDefault();
        return;
      }
    }

    if (!event.defaultPrevented) {
      window.setTimeout(() => window.location.reload(), 1200);
    }
  });
});
