(() => {
  const page = document.querySelector("[data-payment-page]");
  const payloadElement = document.getElementById("infinitepay-checkout-payload");
  if (!page || !payloadElement) return;

  const message = page.querySelector("[data-payment-message]");
  const retryButton = page.querySelector("[data-payment-retry]");
  const loader = page.querySelector(".payment-loader");
  const apiUrl = page.dataset.apiUrl;
  const payload = JSON.parse(payloadElement.textContent);

  const checkoutHostIsSafe = (url) => {
    try {
      const parsed = new URL(url);
      return parsed.protocol === "https:" && (
        parsed.hostname === "checkout.infinitepay.io" ||
        parsed.hostname === "checkout.infinitepay.com.br" ||
        parsed.hostname.endsWith(".checkout.infinitepay.io") ||
        parsed.hostname.endsWith(".checkout.infinitepay.com.br")
      );
    } catch (_) {
      return false;
    }
  };

  const openCheckout = async () => {
    retryButton.hidden = true;
    loader.hidden = false;
    message.textContent = "Conectando diretamente com a InfinitePay…";

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || !checkoutHostIsSafe(data.url)) {
        throw new Error(data.message || "Link de pagamento inválido.");
      }
      window.location.replace(data.url);
    } catch (error) {
      loader.hidden = true;
      retryButton.hidden = false;
      message.textContent = "Não foi possível abrir o pagamento. Confira sua internet e tente novamente.";
    }
  };

  retryButton.addEventListener("click", openCheckout);
  openCheckout();
})();
