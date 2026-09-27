const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const productRows = [...document.querySelectorAll("[data-product]")];
const itemsInput = document.querySelector("#id_items_json");
const totalBox = document.querySelector("[data-order-total]");
const summaryBox = document.querySelector("[data-summary-lines]");
const orderForm = document.querySelector("[data-order-form]");
const dateSelect = document.querySelector("[data-date-select]");
const dateInput = document.querySelector("#id_pickup_date");
const slotSelect = document.querySelector("#id_pickup_slot");
const slotsNode = document.querySelector("#pickup-slots-data");
const slotsByDate = slotsNode ? JSON.parse(slotsNode.textContent) : {};

function selectedItems() {
  return productRows
    .map((row) => ({
      product_id: Number(row.dataset.id),
      name: row.dataset.name,
      price: Number(row.dataset.price.replace(",", ".")),
      quantity: Number(row.querySelector("[data-quantity]").value),
    }))
    .filter((item) => item.quantity > 0);
}

function renderSummary() {
  const items = selectedItems();
  const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  itemsInput.value = JSON.stringify(items.map(({ product_id, quantity }) => ({ product_id, quantity })));
  totalBox.textContent = money.format(total);
  summaryBox.innerHTML = items.length
    ? items.map((item) => `<div><span>${item.quantity}x ${item.name}</span><strong>${money.format(item.price * item.quantity)}</strong></div>`).join("")
    : '<p class="empty-summary">Escolha seus cookies para ver o resumo.</p>';
}

productRows.forEach((row) => {
  const quantity = row.querySelector("[data-quantity]");
  row.querySelector("[data-plus]").addEventListener("click", () => {
    quantity.value = Math.min(Number(quantity.value) + 1, 100);
    renderSummary();
  });
  row.querySelector("[data-minus]").addEventListener("click", () => {
    quantity.value = Math.max(Number(quantity.value) - 1, 0);
    renderSummary();
  });
});

if (dateSelect && slotSelect) {
  const updateSlots = () => {
    const slots = slotsByDate[dateSelect.value] || [];
    dateInput.value = dateSelect.value;
    slotSelect.innerHTML = '<option value="">Escolha o horário e local</option>' + slots
      .map((slot) => `<option value="${slot.id}">${slot.label}</option>`)
      .join("");
    slotSelect.disabled = !slots.length;
  };
  dateSelect.addEventListener("change", updateSlots);
  updateSlots();
}

orderForm?.addEventListener("submit", (event) => {
  renderSummary();
  if (!selectedItems().length) {
    event.preventDefault();
    alert("Escolha pelo menos um cookie antes de finalizar.");
  }
});

renderSummary();
