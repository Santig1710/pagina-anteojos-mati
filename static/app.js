const body = document.body;
const productData = JSON.parse(body.dataset.products || "[]");
const productsById = new Map(productData.map((product) => [String(product.id), product]));
const cart = new Map();
const currency = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 });
const productCards = [...document.querySelectorAll(".product-card")];
const companyFilter = document.querySelector("#companyFilter");
const brandFilter = document.querySelector("#brandFilter");
const searchInput = document.querySelector("#searchInput");
const noResults = document.querySelector("#noResults");
const drawer = document.querySelector("#cartDrawer");
const backdrop = document.querySelector("#drawerBackdrop");
const checkoutArea = document.querySelector("#checkoutArea");
const checkoutForm = document.querySelector("#checkoutForm");
const paymentMethods = ["Efectivo", "Transferencia", "Cheque"];
let selectedKind = "";

function applyFilters() {
  const company = companyFilter.value;
  const brand = brandFilter.value;
  const query = searchInput.value.trim().toLocaleLowerCase("es");
  let visible = 0;
  productCards.forEach((card) => {
    const matches = (!company || card.dataset.company === company)
      && (!brand || card.dataset.brand === brand)
      && (!selectedKind || card.dataset.kind === selectedKind)
      && (!query || card.dataset.search.includes(query));
    card.hidden = !matches;
    if (matches) visible += 1;
  });
  document.querySelector("#resultCount").textContent = `${visible} ${visible === 1 ? "modelo" : "modelos"}`;
  noResults.hidden = visible !== 0;
}

function syncBrands() {
  const company = companyFilter.value;
  [...brandFilter.options].forEach((option) => {
    option.hidden = Boolean(company && option.value && option.dataset.company !== company);
  });
  if (brandFilter.selectedOptions[0]?.hidden) brandFilter.value = "";
}

companyFilter.addEventListener("change", () => { syncBrands(); applyFilters(); });
brandFilter.addEventListener("change", applyFilters);
searchInput.addEventListener("input", applyFilters);
document.querySelectorAll(".type-option").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".type-option.is-selected")?.classList.remove("is-selected");
    button.classList.add("is-selected");
    selectedKind = button.dataset.kind;
    applyFilters();
  });
});
document.querySelectorAll("[data-company-pick]").forEach((button) => {
  button.addEventListener("click", () => {
    companyFilter.value = button.dataset.companyPick;
    syncBrands();
    applyFilters();
    document.querySelector("#coleccion").scrollIntoView({ behavior: "smooth" });
  });
});
document.querySelector("#clearFilters").addEventListener("click", () => {
  companyFilter.value = "";
  brandFilter.value = "";
  searchInput.value = "";
  selectedKind = "";
  document.querySelector(".type-option.is-selected")?.classList.remove("is-selected");
  document.querySelector('.type-option[data-kind=""]')?.classList.add("is-selected");
  syncBrands();
  applyFilters();
});

productCards.forEach((card) => {
  const input = card.querySelector(".quantity-control input");
  card.querySelectorAll(".qty-step").forEach((button) => {
    button.addEventListener("click", () => {
      const next = Number(input.value) + Number(button.dataset.step);
      input.value = Math.max(1, Math.min(Number(input.max), next));
    });
  });
  input.addEventListener("change", () => {
    input.value = Math.max(1, Math.min(Number(input.max), Number(input.value) || 1));
  });
  card.querySelector("[data-add]").addEventListener("click", () => {
    const id = card.dataset.productId;
    const current = cart.get(id) || 0;
    cart.set(id, Math.min(Number(card.dataset.stock), current + Number(input.value)));
    input.value = "1";
    renderCart();
    openCart();
  });
});

function renderPayments() {
  const container = document.querySelector("#paymentOptions");
  const active = [...container.querySelectorAll("input[type=checkbox]:checked")]
    .map((input) => input.value);
  container.innerHTML = paymentMethods.map((method) => {
    const checked = active.length ? active.includes(method) : method === "Efectivo";
    return `<label class="payment-option"><input type="checkbox" value="${method}" ${checked ? "checked" : ""}><span class="payment-check"></span><span>${method}</span><input class="payment-percent" type="number" min="1" max="100" value="${checked ? (active.length > 1 ? Math.floor(100 / active.length) : 100) : 0}" ${checked ? "" : "disabled"} aria-label="Porcentaje con ${method}"><span class="percent-symbol">%</span></label>`;
  }).join("");
  container.querySelectorAll("input").forEach((input) => input.addEventListener("change", (event) => {
    if (event.target.type === "checkbox") {
      if (!container.querySelector("input[type=checkbox]:checked")) event.target.checked = true;
      renderPayments();
    }
    updatePaymentTotal();
  }));
  updatePaymentTotal();
}

function getPayments() {
  return [...document.querySelectorAll(".payment-option")]
    .filter((row) => row.querySelector("input[type=checkbox]").checked)
    .map((row) => ({ method: row.querySelector("input[type=checkbox]").value, percent: Number(row.querySelector(".payment-percent").value) }));
}

function updatePaymentTotal() {
  const total = getPayments().reduce((sum, payment) => sum + payment.percent, 0);
  const label = document.querySelector("#paymentTotal");
  label.textContent = `Porcentaje asignado: ${total}%`;
  label.classList.toggle("is-invalid", total !== 100);
  document.querySelector("#checkoutButton").disabled = total !== 100;
}

function renderCart() {
  const count = [...cart.values()].reduce((sum, quantity) => sum + quantity, 0);
  document.querySelector("#cartCount").textContent = count;
  document.querySelector("#drawerCount").textContent = `(${count})`;
  document.querySelector("#checkoutArea").hidden = count === 0;
  document.querySelector("#cartLines").innerHTML = count === 0
    ? '<div class="cart-empty"><span>◌</span><p>Tu pedido empieza con una buena elección.</p><button type="button" class="text-link" id="continueShopping">Ver colección ↗</button></div>'
    : [...cart.entries()].map(([id, quantity]) => {
      const product = productsById.get(id);
      const lineTotal = product.price * quantity;
      const imageUrl = product.image.startsWith("http") ? product.image : `/static/uploads/${product.image}`;
      return `<article class="cart-line"><div class="cart-line-image">${product.image ? `<img src="${imageUrl}" alt="">` : "LU"}</div><div class="cart-line-details"><p>${product.brand_name}</p><h3>${product.name}</h3><span>${currency.format(product.price)} / unidad</span><div class="cart-line-controls"><button type="button" data-cart-change="${id}" data-delta="-1" aria-label="Restar">−</button><span>${quantity}</span><button type="button" data-cart-change="${id}" data-delta="1" aria-label="Sumar">+</button><button type="button" class="remove-line" data-remove="${id}">Quitar</button></div></div><strong>${currency.format(lineTotal)}</strong></article>`;
    }).join("");
  const total = [...cart.entries()].reduce((sum, [id, quantity]) => sum + productsById.get(id).price * quantity, 0);
  document.querySelector("#cartTotal").textContent = currency.format(total);
  document.querySelectorAll("[data-cart-change]").forEach((button) => button.addEventListener("click", () => {
    const { cartChange: id, delta } = button.dataset;
    const product = productsById.get(id);
    const next = (cart.get(id) || 0) + Number(delta);
    if (next < 1) cart.delete(id);
    else cart.set(id, Math.min(product.stock, next));
    renderCart();
  }));
  document.querySelectorAll("[data-remove]").forEach((button) => button.addEventListener("click", () => {
    cart.delete(button.dataset.remove);
    renderCart();
  }));
  document.querySelector("#continueShopping")?.addEventListener("click", closeCart);
  renderPayments();
}

function openCart() {
  drawer.classList.add("is-open");
  backdrop.classList.add("is-open");
  drawer.setAttribute("aria-hidden", "false");
  document.body.classList.add("drawer-open");
}

function closeCart() {
  drawer.classList.remove("is-open");
  backdrop.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("drawer-open");
}

document.querySelector("#cartTrigger").addEventListener("click", openCart);
document.querySelector("#closeCart").addEventListener("click", closeCart);
backdrop.addEventListener("click", closeCart);
document.querySelector("#finishOrder").addEventListener("click", () => {
  document.querySelector("#orderSuccess").hidden = true;
  checkoutForm.hidden = false;
  closeCart();
});

checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = document.querySelector("#checkoutError");
  error.hidden = true;
  const payments = getPayments();
  if (payments.reduce((sum, payment) => sum + payment.percent, 0) !== 100) {
    error.textContent = "Los porcentajes de pago deben sumar 100%.";
    error.hidden = false;
    return;
  }
  const button = document.querySelector("#checkoutButton");
  button.disabled = true;
  try {
    const response = await fetch("/order", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content },
      body: JSON.stringify({
        buyer_name: checkoutForm.elements.buyer_name.value,
        buyer_phone: checkoutForm.elements.buyer_phone.value,
        items: [...cart.entries()].map(([id, quantity]) => ({ id: Number(id), quantity })),
        payments,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "No se pudo crear el pedido.");
    document.querySelector("#orderCode").textContent = result.order_id;
    document.querySelector("#whatsappLink").href = result.whatsapp_url;
    document.querySelector("#orderSuccess").hidden = false;
    checkoutForm.hidden = true;
    cart.clear();
    renderCart();
    document.querySelector("#orderSuccess").hidden = false;
    window.open(result.whatsapp_url, "_blank", "noopener");
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  } finally {
    button.disabled = false;
  }
});

const slides = [...document.querySelectorAll(".hero-slide")];
if (slides.length > 1) {
  let activeSlide = 0;
  window.setInterval(() => {
    slides[activeSlide].classList.remove("is-active");
    activeSlide = (activeSlide + 1) % slides.length;
    slides[activeSlide].classList.add("is-active");
    document.querySelector("#heroCurrent").textContent = String(activeSlide + 1).padStart(2, "0");
  }, 5200);
}

syncBrands();
renderCart();