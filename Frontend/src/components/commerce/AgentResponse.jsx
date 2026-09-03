import { useEffect, useState } from "react";
import ProductCard from "../ProductCard";

const PAGE_SIZE = 20;

export default function AgentResponse({ data, onAction }) {
  const action = data?.action || data?.final_action;
  const products = Array.isArray(data?.products) ? data.products : [];
  const offer = data?.offer || {};
  const offerAvailable = Boolean(
    offer &&
      (offer.final_price != null || offer.amount != null || offer.original_price != null)
  );

  const explicitProductDetail =
    action === "PRODUCT_SELECTED" ||
    action === "PRODUCT_DETAIL" ||
    action === "VIEW_PRODUCT" ||
    action === "select_product" ||
    Boolean(data?.product) ||
    (data?.product_id != null && products.length === 1);

  const requestedProductId =
    data?.product_id ??
    data?.transaction?.product_id ??
    data?.offer?.product_id;

  const matchingProduct =
    requestedProductId && products.length
      ? products.find(
          (product) =>
            Number(product?.product_id ?? product?.id) === Number(requestedProductId)
        )
      : null;

  const selectedProduct =
    data?.product ||
    matchingProduct ||
    (products.length ? products[0] : null) ||
    offer ||
    null;

  const shouldShowSingleProductDetail =
    explicitProductDetail ||
    (!products.length && Boolean(selectedProduct));

  if (shouldShowSingleProductDetail) {
    return <ProductDetail data={data} product={selectedProduct} onAction={onAction} />;
  }

  if (action === "NEGOTIATION_AMOUNT_REQUIRED") {
    return (
      <div className="space-y-3">
        <p className="leading-6 text-slate-300">
          {data?.message || "Tell me what discount percentage you want, and I will try to get you the best price."}
        </p>
        {products[0] && (
          <p className="text-xs text-slate-500">
            {products[0].name || `Product ${products[0].product_id}`} · ₹{Number(products[0].price || 0).toLocaleString("en-IN")}
          </p>
        )}
      </div>
    );
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
    return <ProductList products={products} data={data} onAction={onAction} />;
  }

  return <p className="text-slate-300">{data?.message || "I processed your request."}</p>;
}

function ProductList({ products, data, onAction }) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [products.length]);

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.innerHeight + window.scrollY;
      const scrollThreshold = document.body.offsetHeight - 180;

      if (scrollPosition >= scrollThreshold && visibleCount < products.length) {
        setVisibleCount((count) => Math.min(count + PAGE_SIZE, products.length));
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [visibleCount, products.length]);

  const visibleProducts = products.slice(0, visibleCount);
  const hasMore = visibleCount < products.length;

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-semibold text-white">
          I found some products for you.
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Showing {visibleProducts.length} of {products.length}. Scroll to load more.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {visibleProducts.map((product, index) => (
          <ProductCard
            key={product.product_id || product.id || index}
            product={product}
            data={data}
            onAction={onAction}
          />
        ))}
      </div>

      {hasMore && (
        <div className="flex justify-center pt-2">
          <button
            onClick={() => setVisibleCount((count) => Math.min(count + PAGE_SIZE, products.length))}
            className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
          >
            Load more products
          </button>
        </div>
      )}
    </div>
  );
}

function ProductDetail({ data, product, onAction }) {
  const productId =
    product?.product_id ??
    data?.product_id ??
    data?.transaction?.product_id ??
    data?.offer?.product_id;
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
  const currentProduct =
    data?.product ||
    data?.products?.find(
      (product) =>
        Number(product?.product_id ?? product?.id) === Number(data?.product_id ?? data?.transaction?.product_id ?? data?.offer?.product_id)
    ) ||
    data?.products?.[0] ||
    {};

  const product = {
    product_id: currentProduct.product_id ?? currentProduct.id ?? offer.product_id ?? data?.product_id ?? data?.transaction?.product_id,
    name: currentProduct.name || currentProduct.product_name || offer.name || data?.products?.[0]?.name || data?.products?.[0]?.product_name,
    category: currentProduct.category || currentProduct.category_name || offer.category || data?.products?.[0]?.category || data?.products?.[0]?.category_name,
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
