import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const CART_STORAGE_KEY = "agentcommerce-cart";

function readCart() {
  try {
    const value = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export default function Cart() {
  const navigate = useNavigate();
  const [items, setItems] = useState(readCart);

  useEffect(() => {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    window.dispatchEvent(new Event("agentcommerce-cart-updated"));
  }, [items]);

  function updateQuantity(productId, change) {
    setItems((current) => current.map((item) => {
      if (String(item.product_id) !== String(productId)) {
        return item;
      }
      return {
        ...item,
        quantity: Math.min(10, Math.max(1, item.quantity + change)),
      };
    }));
  }

  function removeItem(productId) {
    setItems((current) => current.filter(
      (item) => String(item.product_id) !== String(productId)
    ));
  }

  const total = items.reduce(
    (sum, item) => sum + Number(item.final_price || item.price || 0) * item.quantity,
    0
  );

  function checkoutItem(item) {
    navigate("/checkout", {
      state: {
        cartItems: [item],
        chatSessionId: item.chatSessionId,
      },
    });
  }

  function checkoutAll() {
    navigate("/checkout", {
      state: {
        cartItems: items,
        chatSessionId: items[0]?.chatSessionId,
      },
    });
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-white sm:px-6">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-violet-400">Your cart</p>
            <h1 className="mt-2 text-3xl font-bold">Selected products</h1>
          </div>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            Continue shopping
          </button>
        </div>

        {!items.length ? (
          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center">
            <p className="text-slate-400">Your cart is empty.</p>
            <button
              type="button"
              onClick={() => navigate("/")}
              className="mt-5 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white hover:bg-violet-500"
            >
              Find products
            </button>
          </section>
        ) : (
          <div className="space-y-4">
            {items.map((item) => (
              <section
                key={item.product_id}
                className="flex flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-xs text-slate-500">category-{item.category || "Product"}</p>
                  <h2 className="mt-1 text-lg font-semibold">{item.name}</h2>
                  <p className="mt-2 text-sm text-slate-300">
                    ₹{Number(item.final_price || item.price || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })} each
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 rounded-xl border border-slate-700 px-3 py-2">
                    <button
                      type="button"
                      disabled={item.quantity <= 1}
                      onClick={() => updateQuantity(item.product_id, -1)}
                      className="text-lg text-slate-300 disabled:opacity-40"
                    >
                      -
                    </button>
                    <span className="min-w-[20px] text-center">{item.quantity}</span>
                    <button
                      type="button"
                      disabled={item.quantity >= 10}
                      onClick={() => updateQuantity(item.product_id, 1)}
                      className="text-lg text-slate-300 disabled:opacity-40"
                    >
                      +
                    </button>
                  </div>
                  <p className="min-w-[110px] text-right font-semibold">
                    ₹{(Number(item.final_price || item.price || 0) * item.quantity).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </p>
                  <button
                    type="button"
                    onClick={() => removeItem(item.product_id)}
                    className="text-sm text-rose-300 hover:text-rose-200"
                  >
                    Remove
                  </button>
                  <button
                    type="button"
                    onClick={() => checkoutItem(item)}
                    className="rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
                  >
                    Checkout
                  </button>
                </div>
              </section>
            ))}

            <section className="flex items-center justify-between border-t border-slate-800 pt-6">
              <span className="text-slate-400">Cart total</span>
              <div className="flex items-center gap-5">
                <span className="text-2xl font-bold">₹{total.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                <button
                  type="button"
                  onClick={checkoutAll}
                  className="rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500"
                >
                  Checkout all
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </main>
  );
}
