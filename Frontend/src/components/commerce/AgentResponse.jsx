import ProductCard from "../ProductCard";

export default function AgentResponse({ data, onAction }) {
  const action = data?.action || data?.final_action;
  const products = data?.products || [];
  const offer = data?.offer || {};
  const offerAvailable = Boolean(
    offer &&
      (offer.final_price != null || offer.amount != null || offer.original_price != null)
  );
  const selectedProduct = data?.product || offer || products[0];
  const isSelectedProduct = Boolean(
    selectedProduct &&
      data?.transaction?.product_id &&
      Number(data.transaction.product_id) === Number(selectedProduct.product_id)
  );

  if (
    action === "PRODUCT_SELECTED" ||
    action === "PRODUCT_DETAIL" ||
    (action === "RECOMMEND_PRODUCT" && isSelectedProduct)
  ) {
    return <ProductDetail data={data} product={selectedProduct} onAction={onAction} />;
  }

  if (
    [
      "COUNTER_OFFER",
      "OFFER_CREATED",
      "OFFER_AVAILABLE",
      "OFFER_REQUESTED",
      "NEGOTIATE",
      "LIMITED_OFFER",
    ].includes(action) ||
    (offerAvailable && ["RECOMMEND_PRODUCT", "PRODUCT_SELECTED"].includes(action))
  ) {
    return <NegotiationResponse data={data} onAction={onAction} />;
  }

  if (
    action === "PAYMENT_PENDING" ||
    action === "CHECKOUT_READY" ||
    data?.checkout?.status === "CHECKOUT_READY"
  ) {
    return <CheckoutReady data={data} onAction={onAction} />;
  }

  if (
    action === "ORDER_CREATED" ||
    data?.order?.status === "ORDER_CREATED" ||
    data?.order?.status === "CONFIRMED"
  ) {
    return <OrderSuccess data={data} />;
  }

  if (
    action === "RECOMMEND_PRODUCT" ||
    action === "OFFER_REQUESTED" ||
    products.length > 0
  ) {
    return (
      <div className="space-y-5">
          <div>
            <h3 className="text-base font-semibold text-white">
              I found some products for you.
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Compare the options below or choose one and I'll help you negotiate the price.
            </p>
          </div>
        <div className="grid gap-4 md:grid-cols-2">
          {products.map((product, index) => (
            <ProductCard
              key={product.product_id || product.id || index}
              product={product}
              data={data}
              onAction={onAction}
            />
          ))}
        </div>
      </div>
    );
  }

  return <p className="text-slate-300">{data?.message || "I processed your request."}</p>;
}

function ProductDetail({ data, product, onAction }) {
  const productId = product?.product_id || data?.offer?.product_id;
  const offer = data?.offer || {};
  const price = Number(
    product?.final_price ??
    product?.price ??
    product?.current_price ??
    offer.final_price ??
    offer.amount ??
    offer.original_price ??
    0
  );

  return (
    <div className="max-w-xl space-y-4">
      <p className="leading-6 text-slate-300">
        {data?.message || "Great choice. Here's the product you're interested in."}
      </p>
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
        <p className="text-xs text-slate-500">Selected product</p>
        <h3 className="mt-1 text-lg font-semibold text-white">
          {product?.name || product?.product_name || `Product ${productId}`}
        </h3>
        <p className="mt-3 text-2xl font-bold text-white">
          ₹{price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
        </p>
        <div className="mt-5 grid grid-cols-2 gap-2">
          <button
            onClick={() => onAction?.("negotiate", product, data)}
            className="rounded-xl border border-violet-500/40 bg-violet-500/10 px-4 py-3 text-sm font-medium text-violet-300 hover:bg-violet-500/20"
          >
            Negotiate Price
          </button>
          <button
            onClick={() => onAction?.("buy_now", product, data)}
            className="rounded-xl bg-violet-600 px-4 py-3 text-sm font-medium text-white hover:bg-violet-500"
          >
            Buy Now
          </button>
        </div>
      </div>
    </div>
  );
}

function NegotiationResponse({ data, onAction }) {
  const offer = data?.offer || {};
  const product = {
    product_id: offer.product_id || data?.products?.[0]?.product_id,
    name: offer.name || data?.products?.[0]?.name || data?.products?.[0]?.product_name,
    category: offer.category || data?.products?.[0]?.category || data?.products?.[0]?.category_name,
  };
  const original = Number(offer.original_price ?? data?.products?.[0]?.price ?? data?.products?.[0]?.current_price ?? 0);
  const negotiated = Number(offer.final_price ?? offer.amount ?? original);
  return (
    <div className="space-y-4">
        <div>
          <h3 className="font-semibold text-white">✦ I negotiated a better price for you.</h3>
          <p className="mt-1 text-xs text-slate-500">Here's the offer I was able to secure.</p>
        </div>
      <div className="rounded-2xl border border-violet-500/30 bg-violet-500/5 p-5">
        <p className="text-xs text-slate-500">Negotiated offer</p>
        <p className="mt-2 font-medium text-white">{product.name || `Product ${product.product_id}`}</p>
        <p className="mt-3 text-sm text-slate-400 line-through">₹{original.toLocaleString("en-IN")}</p>
        <p className="text-2xl font-bold text-white">₹{negotiated.toLocaleString("en-IN")}</p>
        <div className="mt-5 grid grid-cols-2 gap-2">
          <button onClick={() => onAction?.("accept_offer", product, data)} className="rounded-xl bg-emerald-600 px-4 py-3 text-xs font-semibold text-white hover:bg-emerald-500">Accept Offer</button>
          <button onClick={() => onAction?.("negotiate_again", product, data)} className="rounded-xl border border-slate-700 px-4 py-3 text-xs text-slate-300 hover:bg-slate-800">Negotiate Again</button>
        </div>
      </div>
    </div>
  );
}

function CheckoutReady({ data, onAction }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-semibold text-white">Your deal is ready.</h3>
        <p className="mt-1 text-xs text-slate-500">The negotiated price has been locked for checkout.</p>
      </div>
      <button onClick={() => onAction?.("proceed_to_payment", data?.offer, data)} className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white hover:bg-emerald-500">Proceed to payment</button>
    </div>
  );
}

function OrderSuccess({ data }) {
  return (
    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-2xl text-emerald-400">✓</div>
      <h3 className="mt-4 text-lg font-semibold text-white">Payment successful</h3>
      <p className="mt-2 text-sm text-slate-400">Your order has been confirmed.</p>
      {data?.order?.order_id && <p className="mt-4 text-xs text-slate-500">Order {data.order.order_id}</p>}
    </div>
  );
}
