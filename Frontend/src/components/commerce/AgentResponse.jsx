import { useEffect, useState } from "react";
import ProductCard from "../ProductCard";

const PAGE_SIZE = 10;
const CART_STORAGE_KEY = "agentcommerce-cart";
const CHAT_SESSION_ID_KEY = "agentcommerce-chat-session-id";

function readActiveSessionId() {
  return (
    sessionStorage.getItem(CHAT_SESSION_ID_KEY) ||
    localStorage.getItem(CHAT_SESSION_ID_KEY) ||
    ""
  );
}

function cartContainsProduct(productId) {
  try {
    const cart = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
    const activeSessionId = readActiveSessionId();
    return Array.isArray(cart) && cart.some(
      (item) =>
        item.chatSessionId === activeSessionId &&
        String(item.product_id) === String(productId)
    );
  } catch {
    return false;
  }
}

export default function AgentResponse({ data, onAction }) {

  const action =
    data?.action ||
    data?.final_action;

  const products =
    Array.isArray(data?.products)
      ? data.products
      : [];

  const offer =
    data?.offer || {};

  const offerAvailable = Boolean(
    offer &&
      (
        offer.final_price != null ||
        offer.amount != null ||
        offer.original_price != null
      )
  );

  const explicitProductDetail =
    action === "PRODUCT_SELECTED" ||
    action === "PRODUCT_DETAIL" ||
    action === "VIEW_PRODUCT" ||
    action === "select_product";

  const requestedProductId =
    data?.product_id ??
    data?.product?.product_id ??
    data?.product?.id ??
    data?.transaction?.product_id ??
    data?.offer?.product_id;

  const matchingProduct =
    requestedProductId != null &&
    products.length
      ? products.find(
          (product) =>
            String(
              product?.product_id ??
                product?.id
            ) ===
            String(requestedProductId)
        )
      : null;

  const selectedProduct =
    data?.product ||
    matchingProduct ||
    (
      products.length === 1
        ? products[0]
        : null
    ) ||
    (
      offerAvailable
        ? offer
        : null
    );

  if (action === "OFFER_ACCEPTED") {
    return <AcceptedOffer data={data} onAction={onAction} />;
  }

  if (action === "CONTEXT_REQUIRED") {
    return <ContextRequired data={data} onAction={onAction} />;
  }

  if (action === "PRICE_ABOVE_PRODUCT") {
    return <ListedPriceResponse data={data} onAction={onAction} />;
  }

  const shouldShowSingleProductDetail =
    explicitProductDetail &&
    Boolean(selectedProduct);

  const shouldShowProductList =
    products.length > 1 &&
    !explicitProductDetail;

  if (shouldShowSingleProductDetail) {
    return (
      <ProductDetail
        data={data}
        product={selectedProduct}
        onAction={onAction}
      />
    );
  }

  if (shouldShowProductList) {
    return (
      <ProductList
        products={products}
        data={data}
        onAction={onAction}
      />
    );
  }

  if (
    action ===
      "NEGOTIATION_AMOUNT_REQUIRED" ||
    action ===
      "NEGOTIATION_INPUT_REQUIRED"
  ) {
    return (
      <NegotiationInputRequired
        data={data}
        onAction={onAction}
      />
    );
  }

  if (action === "NUMERIC_INPUT_CLARIFICATION") {
    return (
      <NegotiationInputRequired
        data={data}
        onAction={onAction}
      />
    );
  }

  if (
    [
      "COUNTER_OFFER",
      "OFFER_CREATED",
      "OFFER_AVAILABLE",
      "OFFER_REQUESTED",
      "NEGOTIATE",
      "MAX_DISCOUNT_REACHED",
      "LIMITED_OFFER",
    ].includes(action) ||
    (
      offerAvailable &&
      [
        "RECOMMEND_PRODUCT",
        "PRODUCT_SELECTED",
      ].includes(action)
    )
  ) {
    return (
      <NegotiationResponse
        data={data}
        onAction={onAction}
      />
    );
  }

  if (
    action === "PAYMENT_PENDING" ||
    action === "CHECKOUT_READY" ||
    data?.checkout?.status ===
      "CHECKOUT_READY"
  ) {
    return (
      <CheckoutReady
        data={data}
        onAction={onAction}
      />
    );
  }

  if (
    action === "ORDER_CREATED" ||
    data?.order?.status ===
      "ORDER_CREATED" ||
    data?.order?.status ===
      "CONFIRMED"
  ) {
    return (
      <OrderSuccess
        data={data}
      />
    );
  }

  if (
    action === "RECOMMEND_PRODUCT" ||
    action === "OFFER_REQUESTED" ||
    products.length > 0
  ) {
    return (
      <ProductList
        products={Array.isArray(data?.products) ? data.products : products}
        data={data}
        onAction={onAction}
      />
    );
  }

  return (
    <p className="leading-6 text-[rgba(240,231,214,0.8)]">
      {
        data?.message ||
        data?.response ||
        "I'm ready. Tell me what you'd like to find."
      }
    </p>
  );
}


/* ============================================================
   NEGOTIATION INPUT
   ============================================================ */

function NegotiationInputRequired({ data, onAction }) {
  const product = data?.product || data?.products?.[0] || {};
  const offer = data?.offer || {};
  const currentPrice = Number(
    offer.original_price ??
    product.price ??
    product.current_price ??
    data?.transaction?.original_price ??
    0
  );
  const step = currentPrice >= 1000 ? 100 : 50;
  const roundedTarget = Math.max(step, Math.ceil(currentPrice / step) * step);
  const roundedBudget = Math.max(
    step,
    Math.round(currentPrice / step) * step
  );
  const suggestions = currentPrice > 0
    ? [
        `₹${roundedTarget}`,
        `Rupees ${roundedBudget}`,
        `Discount of ${roundedBudget}`,
        "10% off",
      ]
    : ["10% off"];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold text-[#f0e7d6]">
          Let's find a price that works for you.
        </h3>

        <p className="mt-2 text-sm leading-6 text-[rgba(240,231,214,0.8)]">
          {
            data?.message ||
            "What price would you like to pay? You can give me a target price or tell me the discount you're looking for."
          }
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onAction?.("numeric_suggestion", suggestion)}
            className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-4 py-3 text-left text-sm text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)] hover:text-[#d9a353]"
          >
            {suggestion}
          </button>
        ))}
        <button
          type="button"
          onClick={() => onAction?.("close_negotiation", null, data)}
          className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-4 py-3 text-left text-sm text-[rgba(240,231,214,0.45)] transition-all duration-300 hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)] hover:text-[#d9a353]"
        >
          Close and discuss a different product
        </button>
      </div>

      <p className="text-xs text-[rgba(240,231,214,0.45)]">
        Just type your target in the message box below.
      </p>
    </div>
  );
}

function NegotiationSuggestions({ currentPrice, data, onAction }) {
  const step = currentPrice >= 1000 ? 100 : 50;
  const roundedTarget = Math.max(step, Math.ceil(currentPrice / step) * step);
  const roundedBudget = Math.max(step, Math.round(currentPrice / step) * step);
  const suggestions = currentPrice > 0
    ? [
        `₹${roundedTarget}`,
        `Rupees ${roundedBudget}`,
        `Discount of ${roundedBudget}`,
        "10% off",
      ]
    : ["10% off"];

  return (
    <div className="mt-4 grid gap-2 sm:grid-cols-2">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onAction?.("numeric_suggestion", suggestion, data)}
          className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-3 py-2.5 text-left text-sm text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)] hover:text-[#d9a353]"
        >
          {suggestion}
        </button>
      ))}
      <button
        type="button"
        onClick={() => onAction?.("close_negotiation", null, data)}
        className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-3 py-2.5 text-left text-sm text-[rgba(240,231,214,0.45)] transition-all duration-300 hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)] hover:text-[#d9a353]"
      >
        Close and discuss a different product
      </button>
    </div>
  );
}


/* ============================================================
   PRODUCT LIST
   ============================================================ */

function ProductList({
  products,
  data,
  onAction,
}) {

  const [visibleCount, setVisibleCount] =
    useState(PAGE_SIZE);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [products.length]);

  const visibleProducts =
    products.slice(
      0,
      visibleCount
    );

  const hasMore =
    visibleCount < products.length;

  function loadMore() {
    setVisibleCount(
      (count) =>
        Math.min(
          count + PAGE_SIZE,
          products.length
        )
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-semibold text-[#f0e7d6]">
          Here are a few options I found.
        </h3>

        <p className="mt-1 text-xs leading-5 text-[rgba(240,231,214,0.45)]">
          I found {products.length} matching options. Take a look below, and I can help you compare or negotiate any of them.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {visibleProducts.map(
          (product, index) => (
            <ProductCard
              key={
                product.product_id ||
                product.id ||
                index
              }
              product={product}
              data={data}
              onAction={onAction}
            />
          )
        )}
      </div>

      {hasMore && (
        <div className="flex justify-center pt-2">
          <button
            onClick={loadMore}
            className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-5 py-2.5 text-xs font-medium text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)] hover:text-[#d9a353]"
          >
            Show more options
          </button>
        </div>
      )}

      {!products.length && (
        <div className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] p-5 text-center">
          <p className="text-sm text-[rgba(240,231,214,0.45)]">
            I couldn't find a close match for that request.
          </p>

          <p className="mt-1 text-xs text-[rgba(240,231,214,0.45)]">
            Try changing the product type, budget, or other requirement.
          </p>
        </div>
      )}
    </div>
  );
}


/* ============================================================
   PRODUCT DETAIL
   ============================================================ */

function ProductDetail({
  data,
  product,
  onAction,
}) {
  const [quantity, setQuantity] = useState(
    Math.min(10, Math.max(1, Number(product?.quantity || 1)))
  );

  const productId =
    product?.product_id ??
    product?.id ??
    data?.product_id ??
    data?.transaction?.product_id ??
    data?.offer?.product_id;

  const offer =
    data?.offer || {};

  const price = Number(
    product?.final_price ??
    product?.price ??
    product?.current_price ??
    offer.final_price ??
    offer.amount ??
    offer.original_price ??
    0
  );

  const stock =
    product?.stock ??
    product?.inventory ??
    product?.quantity ??
    product?.available_quantity;

  const category =
    product?.category ??
    product?.category_name ??
    product?.categoryName;

  const productName =
    product?.name ??
    product?.product_name ??
    `Product ${productId}`;

  const [inCart, setInCart] = useState(() => cartContainsProduct(productId));

  function handleBuyAction() {
    if (inCart) {
      onAction?.("remove_from_cart", { product_id: productId }, data);
      setInCart(false);
      return;
    }

    onAction?.("add_to_cart", { ...product, quantity, price }, data);
    setInCart(true);
  }

  return (
    <div className="max-w-2xl space-y-5">
      <div>
        <p className="leading-6 text-[rgba(240,231,214,0.8)]">
          {
            data?.message ||
            "Sure. Here's a closer look at that product."
          }
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] transition-all duration-300">
        <div className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[#d9a353]">
                Product details
              </p>

              <h3 className="mt-2 text-xl font-semibold text-[#f0e7d6]">
                {productName}
              </h3>

              {category && (
                <p className="mt-1 text-xs text-[rgba(240,231,214,0.45)]">
                  {category}
                </p>
              )}
            </div>

            {stock != null && (
              <span className="rounded-full border border-[#d9a353]/20 bg-[rgba(217,163,83,0.15)] px-3 py-1 text-[11px] font-medium text-[#d9a353]">
                {Number(stock) > 0
                  ? "In stock"
                  : "Out of stock"}
              </span>
            )}
          </div>

          <div className="mt-6">
            <p className="text-xs text-[rgba(240,231,214,0.45)]">
              Current price
            </p>

            <p className="mt-1 text-3xl font-bold text-[#f0e7d6]">
              ₹
              {price.toLocaleString(
                "en-IN",
                {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                }
              )}
            </p>
          </div>

          <div className="mt-5 flex items-center justify-between rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] px-3 py-2">
            <span className="text-xs text-[rgba(240,231,214,0.45)]">Quantity</span>
            <div className="flex items-center gap-3">
              <button
                type="button"
                disabled={quantity <= 1}
                onClick={() => setQuantity((value) => Math.max(1, value - 1))}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(240,231,214,0.16)] text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353] disabled:cursor-not-allowed disabled:opacity-40"
              >
                -
              </button>
              <span className="min-w-[24px] text-center text-sm font-medium text-[#f0e7d6]">
                {quantity}
              </span>
              <button
                type="button"
                disabled={quantity >= 10}
                onClick={() => setQuantity((value) => Math.min(10, value + 1))}
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(240,231,214,0.16)] text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353] disabled:cursor-not-allowed disabled:opacity-40"
              >
                +
              </button>
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] p-4">
            <p className="text-xs font-medium text-[rgba(240,231,214,0.45)]">
              What would you like to do?
            </p>

            <p className="mt-1 text-xs leading-5 text-[rgba(240,231,214,0.45)]">
              You can buy it at the current price, or I can try to get you a better deal.
            </p>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <button
              onClick={() =>
                onAction?.(
                  "negotiate",
                  { ...product, quantity },
                  data
                )
              }
              className="rounded-lg border border-[#d9a353]/30 bg-[rgba(217,163,83,0.15)] px-4 py-3 text-sm font-medium text-[#d9a353] transition-all duration-300 hover:bg-[rgba(217,163,83,0.25)]"
            >
              Negotiate Price
            </button>

            <button
              onClick={handleBuyAction}
              className={`rounded-lg px-4 py-3 text-sm font-medium text-[#0e0b08] transition-all duration-300 ${
                inCart
                  ? "border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] text-[rgba(240,231,214,0.8)] hover:border-[#d9a353] hover:text-[#d9a353]"
                  : "bg-[#d9a353] hover:bg-[#f0e7d6]"
              }`}
            >
              {inCart
                ? "Remove from cart"
                : `Buy at ₹${price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


/* ============================================================
   NEGOTIATION RESPONSE
   ============================================================ */

function NegotiationResponse({
  data,
  onAction,
}) {

  const offer =
    data?.offer || {};

  const currentProduct =
    data?.product ||
    data?.products?.find(
      (product) =>
        String(
          product?.product_id ??
            product?.id
        ) ===
        String(
          data?.product_id ??
            data?.transaction?.product_id ??
            data?.offer?.product_id
        )
    ) ||
    data?.products?.[0] ||
    {};

  const product = {
    product_id:
      currentProduct.product_id ??
      currentProduct.id ??
      offer.product_id ??
      data?.product_id ??
      data?.transaction?.product_id,

    name:
      currentProduct.name ??
      currentProduct.product_name ??
      offer.name ??
      "Selected product",

    category:
      currentProduct.category ??
      currentProduct.category_name ??
      offer.category,
  };

  const original = Number(
    offer.original_price ??
    currentProduct.price ??
    currentProduct.current_price ??
    data?.original_price ??
    0
  );

  const negotiated = Number(
    offer.final_price ??
    offer.amount ??
    offer.price ??
    original
  );

  const discountAmount =
    Math.max(
      0,
      original - negotiated
    );

  const discountPercentage =
    original > 0
      ? (
          (discountAmount /
            original) *
          100
        )
      : 0;

  const requestedTarget =
    offer.requested_price ??
    offer.target_price ??
    data?.target_price ??
    data?.requested_price;

  const targetDiscount =
    offer.requested_discount_percentage ??
    data?.requested_discount_percentage;

  const offerReason =
    offer.reason ??
    offer.explanation ??
    data?.reason;

  const targetWasNotReached =
    requestedTarget != null &&
    negotiated > Number(
      requestedTarget
    );

  const targetDiscountNotReached =
    targetDiscount != null &&
    discountPercentage <
      Number(targetDiscount);

  const limitedOffer =
    targetWasNotReached ||
    targetDiscountNotReached ||
    actionIndicatesLimit(data?.action);

  const maximumDiscount = Number(
    offer.maximum_discount_percent ??
    data?.policy?.maximum_discount_percent ??
    20
  );

  const offeredDiscount = Number(
    offer.discount_percent ?? discountPercentage
  );

  const maximumReached =
    data?.action === "MAX_DISCOUNT_REACHED" ||
    offer.is_final_offer === true ||
    offeredDiscount >= maximumDiscount ||
    (
      offer.negotiation_round != null &&
      offer.max_negotiation_rounds != null &&
      Number(offer.negotiation_round) >= Number(offer.max_negotiation_rounds)
    );
  const finalOffer = data?.final_offer === true;

  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[rgba(217,163,83,0.15)] text-[#d9a353]">
            ✦
          </div>

          <h3 className="font-semibold text-[#f0e7d6]">
            I found a better price for you.
          </h3>
        </div>

        <p className="mt-2 text-xs leading-5 text-[rgba(240,231,214,0.45)]">
          I checked the available offer against the merchant's pricing limits.
        </p>
      </div>

      <div className="rounded-lg border border-[#d9a353]/30 bg-[rgba(217,163,83,0.05)] p-5 transition-all duration-300">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-[rgba(240,231,214,0.45)]">
              Your offer
            </p>

            <p className="mt-1 font-medium text-[#f0e7d6]">
              {product.name}
            </p>
          </div>

          {discountPercentage > 0 && (
            <span className="rounded-full border border-[#d9a353]/20 bg-[rgba(217,163,83,0.15)] px-3 py-1 text-[11px] font-semibold text-[#d9a353]">
              {discountPercentage.toFixed(1)}% off
            </span>
          )}
        </div>

        <div className="mt-6">
          <p className="text-sm text-[rgba(240,231,214,0.45)] line-through">
            ₹
            {original.toLocaleString(
              "en-IN",
              {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              }
            )}
          </p>

          <p className="mt-1 text-3xl font-bold text-[#f0e7d6]">
            ₹
            {negotiated.toLocaleString(
              "en-IN",
              {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              }
            )}
          </p>

          {discountAmount > 0 && (
            <p className="mt-2 text-xs text-[#d9a353]">
              You save ₹
              {discountAmount.toLocaleString(
                "en-IN",
                {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                }
              )}
            </p>
          )}
        </div>

        {requestedTarget != null && (
          <div className="mt-5 rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] p-4">
            <p className="text-xs text-[rgba(240,231,214,0.45)]">
              Your target
            </p>

            <p className="mt-1 text-sm font-medium text-[#f0e7d6]">
              ₹
              {Number(
                requestedTarget
              ).toLocaleString(
                "en-IN",
                {
                  maximumFractionDigits: 2,
                }
              )}
            </p>
          </div>
        )}

        {targetDiscount != null && (
          <div className="mt-3 rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] p-4">
            <p className="text-xs text-[rgba(240,231,214,0.45)]">
              Requested discount
            </p>

            <p className="mt-1 text-sm font-medium text-[#f0e7d6]">
              {Number(
                targetDiscount
              ).toFixed(1)}
              % off
            </p>
          </div>
        )}

        {limitedOffer && (
          <div className="mt-5 rounded-lg border border-[#d9a353]/20 bg-[rgba(217,163,83,0.15)] p-4">
            <p className="text-xs font-medium text-[#d9a353]">
              This is the best price I can offer.
            </p>

            <p className="mt-1 text-xs leading-5 text-[rgba(240,231,214,0.45)]">
              {offerReason ||
                "The merchant's pricing policy does not allow me to go lower than this."}
            </p>
          </div>
        )}

        {!limitedOffer &&
          offerReason && (
            <div className="mt-5 rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] p-4">
              <p className="text-xs font-medium text-[rgba(240,231,214,0.45)]">
                Why this offer?
              </p>

              <p className="mt-1 text-xs leading-5 text-[rgba(240,231,214,0.45)]">
                {offerReason}
              </p>
            </div>
          )}

        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          <button
            onClick={() =>
              onAction?.(
                "accept_offer",
                product,
                data
              )
            }
            className="rounded-lg bg-[#d9a353] px-4 py-3 text-sm font-semibold text-[#0e0b08] transition-all duration-300 hover:bg-[#f0e7d6]"
          >
            Accept & continue
          </button>

          {!maximumReached && !finalOffer && (
            <button
              onClick={() =>
                onAction?.(
                  "negotiate",
                  product,
                  data
                )
              }
              className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-4 py-3 text-sm font-medium text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353]"
            >
              Try again
            </button>
          )}

          {finalOffer && (
            <button
              type="button"
              onClick={() => onAction?.("close_negotiation", null, data)}
              className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] px-4 py-3 text-sm font-medium text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353]"
            >
              Close and discuss a different product
            </button>
          )}
        </div>

        {maximumReached && !finalOffer && (
          <div className="mt-4 rounded-lg border border-[#d9a353]/20 bg-[rgba(217,163,83,0.08)] p-4">
            <p className="text-sm font-medium text-[#d9a353]">
              I have completed the automatic negotiation rounds.
            </p>
            <p className="mt-1 text-xs leading-5 text-[rgba(240,231,214,0.65)]">
              Enter the discount or price you are looking in the same format as shown below . I will check it and return the best possible price or a counter-offer based on the merchant policy.
            </p>
            <NegotiationSuggestions
              currentPrice={original}
              data={data}
              onAction={onAction}
            />
          </div>
        )}

        <p className="mt-3 text-center text-[11px] text-[rgba(240,231,214,0.45)]">
          Accepting this offer will take you to secure checkout. You won't be charged from this chat screen.
        </p>
      </div>
    </div>
  );
}

function AcceptedOffer({ data, onAction }) {
  const [quantity, setQuantity] = useState(
    Math.max(1, Number(data?.offer?.quantity ?? data?.product?.quantity ?? 1))
  );
  const offer = data?.offer || {};
  const product = data?.product || {};
  const finalPrice = Number(
    offer.final_price ?? offer.amount ?? offer.price ?? 0
  );
  const productId = offer.product_id ?? product.product_id ?? data?.product_id;
  const [inCart, setInCart] = useState(() => cartContainsProduct(productId));
  const totalPrice = finalPrice * quantity;
  const suggestions = [
    ...(Array.isArray(data?.suggested_products) ? data.suggested_products : []),
    ...(Array.isArray(data?.products) ? data.products : []),
  ]
    .filter((candidate) => {
      const candidateId = candidate?.product_id ?? candidate?.id;
      return (
        String(candidateId) !== String(productId) &&
        candidateId != null
      );
    })
    .sort(
      (left, right) =>
        Number(right?.product_score ?? right?.match_score ?? 0) -
        Number(left?.product_score ?? left?.match_score ?? 0)
    )
    .filter(
      (candidate, index, all) =>
        all.findIndex(
          (item) => String(item?.product_id ?? item?.id) === String(candidate?.product_id ?? candidate?.id)
        ) === index
    )
    .slice(0, 1);

  const suggestion = suggestions[0];
  const suggestionName =
    suggestion?.name ||
    suggestion?.product_name ||
    `Product ${suggestion?.product_id ?? suggestion?.id}`;
  const suggestionPrice = suggestion?.price ?? suggestion?.current_price;
  const suggestionIsUpsell = Number(suggestionPrice ?? 0) > finalPrice;

  function addAcceptedOfferToCart() {
    if (inCart) {
      onAction?.("remove_from_cart", { product_id: productId }, data);
      setInCart(false);
      return;
    }
    onAction?.(
      "add_to_cart",
      {
        ...product,
        ...offer,
        product_id: productId,
        name: offer.name || product.name,
        category: offer.category || product.category,
        final_price: finalPrice,
        quantity,
      },
      data
    );
    setInCart(true);
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold text-[#f0e7d6]">Offer accepted</h3>
        <p className="mt-2 text-sm text-[rgba(240,231,214,0.8)]">
          {offer.name || product.name || `Product ${productId}`}
        </p>
      </div>

      <div className="rounded-lg border border-[#d9a353]/20 bg-[rgba(217,163,83,0.05)] p-5 transition-all duration-300">
        <p className="text-3xl font-bold text-[#f0e7d6]">
          ₹{finalPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
        </p>

        <div className="mt-5 flex items-center justify-between rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] px-3 py-2">
          <span className="text-xs text-[rgba(240,231,214,0.45)]">Quantity</span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={quantity <= 1}
              onClick={() => setQuantity((value) => Math.max(1, value - 1))}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(240,231,214,0.16)] text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353] disabled:cursor-not-allowed disabled:opacity-40"
            >
              -
            </button>
            <span className="min-w-[24px] text-center text-sm font-medium text-[#f0e7d6]">{quantity}</span>
            <button
              type="button"
              disabled={quantity >= 10}
              onClick={() => setQuantity((value) => Math.min(10, value + 1))}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(240,231,214,0.16)] text-[rgba(240,231,214,0.8)] transition-all duration-300 hover:border-[#d9a353] hover:text-[#d9a353] disabled:cursor-not-allowed disabled:opacity-40"
            >
              +
            </button>
          </div>
        </div>

        <p className="mt-3 text-sm text-[rgba(240,231,214,0.8)]">
          Total: <span className="font-semibold text-[#f0e7d6]">₹{totalPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
        </p>

        {suggestion && (
          <div className="mt-5 rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] p-4">
            <p className="text-xs font-medium text-[rgba(240,231,214,0.45)]">
              You might also like
            </p>
            <p className="mt-2 text-sm leading-6 text-[rgba(240,231,214,0.8)]">
              {suggestionIsUpsell
                ? `You might also want ${suggestionName}. It's slightly more expensive, but it has a higher match score.`
                : `Since you're buying ${product.name || `Product ${productId}`}, I found another item that pairs well with it.`}
            </p>
            <button
              type="button"
              onClick={() => onAction?.("select_product", suggestion, { ...data, product: suggestion })}
              className="mt-3 w-full rounded-lg border border-[rgba(240,231,214,0.16)] p-3 text-left transition-all duration-300 hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)]"
            >
              <p className="text-sm font-medium text-[#f0e7d6]">{suggestionName}</p>
              {suggestionPrice != null && (
                <p className="mt-2 text-sm text-[rgba(240,231,214,0.8)]">
                  ₹{Number(suggestionPrice).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                </p>
              )}
            </button>
          </div>
        )}

        <button
          onClick={addAcceptedOfferToCart}
          className={`mt-5 w-full rounded-lg px-4 py-3 text-sm font-semibold text-[#0e0b08] transition-all duration-300 ${
            inCart
              ? "border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] text-[rgba(240,231,214,0.8)] hover:border-[#d9a353] hover:text-[#d9a353]"
              : "bg-[#d9a353] hover:bg-[#f0e7d6]"
          }`}
        >
          {inCart ? "Remove from cart" : "Accept and add to cart"}
        </button>
      </div>
    </div>
  );
}


/* ============================================================
   CHECKOUT READY
   ============================================================ */

function CheckoutReady({
  data,
  onAction,
}) {

  const offer =
    data?.offer || {};

  const finalPrice =
    offer.final_price ??
    offer.amount ??
    offer.price;

  const productName =
    data?.product?.name ??
    data?.product?.product_name ??
    offer.name ??
    "Your selected product";

  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[rgba(217,163,83,0.15)] text-[#d9a353]">
            ✓
          </div>

          <h3 className="font-semibold text-[#f0e7d6]">
            Your deal is ready.
          </h3>
        </div>

        <p className="mt-2 text-sm leading-6 text-[rgba(240,231,214,0.8)]">
          The price has been approved and you can continue to secure checkout.
        </p>
      </div>

      <div className="rounded-lg border border-[#d9a353]/20 bg-[rgba(217,163,83,0.05)] p-5 transition-all duration-300">
        <p className="text-xs text-[rgba(240,231,214,0.45)]">
          Ready to checkout
        </p>

        <p className="mt-2 font-medium text-[#f0e7d6]">
          {productName}
        </p>

        {finalPrice != null && (
          <p className="mt-3 text-2xl font-bold text-[#d9a353]">
            ₹
            {Number(
              finalPrice
            ).toLocaleString(
              "en-IN",
              {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              }
            )}
          </p>
        )}

        <button
          onClick={() =>
            onAction?.(
              "proceed_to_payment",
              data?.offer,
              data
            )
          }
          className="mt-5 w-full rounded-lg bg-[#d9a353] px-4 py-3 text-sm font-semibold text-[#0e0b08] transition-all duration-300 hover:bg-[#f0e7d6]"
        >
          Continue to secure checkout
        </button>
      </div>
    </div>
  );
}


/* ============================================================
   ORDER SUCCESS
   ============================================================ */

function OrderSuccess({ data }) {

  const orderId =
    data?.order?.order_id ??
    data?.order?.id;

  return (
    <div className="rounded-lg border border-[#d9a353]/20 bg-[rgba(217,163,83,0.05)] p-6 text-center transition-all duration-300">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[rgba(217,163,83,0.15)] text-2xl text-[#d9a353]">
        ✓
      </div>

      <h3 className="mt-4 text-lg font-semibold text-[#f0e7d6]">
        Your order is confirmed.
      </h3>

      <p className="mt-2 text-sm leading-6 text-[rgba(240,231,214,0.8)]">
        Payment was verified and your order has been successfully created.
      </p>

      {orderId && (
        <div className="mt-5 rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#0e0b08] px-4 py-3">
          <p className="text-[11px] uppercase tracking-wide text-[rgba(240,231,214,0.45)]">
            Order
          </p>

          <p className="mt-1 text-xs font-medium text-[rgba(240,231,214,0.8)]">
            {orderId}
          </p>
        </div>
      )}
    </div>
  );
}


/* ============================================================
   HELPERS
   ============================================================ */

function actionIndicatesLimit(action) {
  return [
    "MAX_DISCOUNT_REACHED",
    "LIMITED_OFFER",
  ].includes(action);
}

function ContextRequired({ data, onAction }) {
  const [selectedContext, setSelectedContext] = useState({});
  const missingContext = data?.customer_intent?.missing_context || [];
  const categories = [
    "Category 0",
    "Category 1",
    "Category 2",
    "Category 3",
    "Category 4",
    "Category 5",
    "Category 6",
    "Category 7",
  ];
  const budgets = [
    "Under ₹500",
    "Under ₹1,000",
    "Under ₹2,500",
    "Under ₹5,000",
    "Under ₹25,000",
  ];
  const urgencies = ["Low", "Medium", "High"];

  function selectOption(type, option) {
    const nextContext = {
      ...selectedContext,
      [type]: option,
    };
    setSelectedContext(nextContext);

    if (missingContext.every((field) => nextContext[field])) {
      onAction?.("context_complete", nextContext, data);
    }
  }

  function optionGroup(type, label, options) {
    return (
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[#d9a353]">
          {label}
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => selectOption(type, option)}
              className={`rounded-lg border px-3 py-2.5 text-left text-sm transition-all duration-300 ${
                selectedContext[type] === option
                  ? "border-[#d9a353] bg-[rgba(217,163,83,0.2)] text-[#d9a353]"
                  : "border-[rgba(240,231,214,0.16)] bg-[#14100b] text-[rgba(240,231,214,0.8)] hover:border-[#d9a353] hover:bg-[rgba(217,163,83,0.15)] hover:text-[#d9a353]"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <p className="leading-6 text-[rgba(240,231,214,0.8)]">
        {data?.message || "Tell me a few details so I can find the right products."}
      </p>

      {missingContext.includes("category") && optionGroup("category", "Product category", categories)}
      {missingContext.includes("budget") && optionGroup("budget", "Budget", budgets)}
      {missingContext.includes("urgency") && optionGroup("urgency", "Purchase urgency", urgencies)}

      <p className="text-xs text-[rgba(240,231,214,0.45)]">
        Selected {missingContext.filter((field) => selectedContext[field]).length} of {missingContext.length}. Choose all options to search.
      </p>
    </div>
  );
}

function ListedPriceResponse({ data, onAction }) {
  const product = data?.products?.[0] || data?.product || {};
  const productId = product.product_id ?? product.id ?? data?.product_id;
  const price = Number(
    product.price ?? product.current_price ?? data?.offer?.original_price ?? 0
  );
  const name = product.name || product.product_name || `Product ${productId}`;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold text-[#f0e7d6]">
          This product already costs less than your target.
        </h3>
        <p className="mt-2 text-sm leading-6 text-[rgba(240,231,214,0.8)]">
          The real current price for {name} is shown below. No discount is needed.
        </p>
      </div>

      <div className="rounded-lg border border-[rgba(240,231,214,0.16)] bg-[#14100b] p-5">
        <p className="text-xs text-[rgba(240,231,214,0.45)]">Current price</p>
        <p className="mt-1 text-3xl font-bold text-[#f0e7d6]">
          ₹{price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
        </p>
        <button
          type="button"
          onClick={() => onAction?.("add_to_cart", { ...product, price }, data)}
          className="mt-5 w-full rounded-lg bg-[#d9a353] px-4 py-3 text-sm font-semibold text-[#0e0b08] transition-all duration-300 hover:bg-[#f0e7d6]"
        >
          Buy at current price
        </button>
      </div>
    </div>
  );
}