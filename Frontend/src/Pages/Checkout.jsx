
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { API_BASE_URL } from "../lib/api";

export default function Checkout() {
  const location = useLocation();
  const transactionId = location.state?.transactionId;
  const [loading, setLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [paymentResponse, setPaymentResponse] = useState(null);
  const [session, setSession] = useState(null);

  useEffect(() => {
    const loadSession = async () => {
      try {
        setSessionLoading(true);
        const query = transactionId
          ? `?transaction_id=${encodeURIComponent(transactionId)}`
          : "";
        const response = await fetch(`${API_BASE_URL}/commerce/session/5176${query}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.detail || "Unable to load checkout session.");
        }

        setSession(data);
      } catch (error) {
        console.error("Session Error:", error);
        setStatus(error.message || "Unable to load AI-negotiated offer.");
      } finally {
        setSessionLoading(false);
      }
    };

    loadSession();
  }, []);

  const product = session?.product || { product_id: 453, name: "Premium Product" };
  const customer = session?.customer || { customer_id: 5176 };
  const originalPrice = Number(session?.original_price ?? 784.23);
  const discountPercent = Number(session?.discount ?? 10);
  const finalPrice = Number(session?.final_price ?? 705.81);
  const discountAmount = Number(session?.discount_amount ?? originalPrice - finalPrice);

  const handlePayment = async () => {
    if (!session) {
      setStatus("Checkout session is still loading.");
      return;
    }

    try {
      setLoading(true);
      setStatus("");
      setPaymentResponse(null);

      // ------------------------------------------------------
      // 1. ASK BACKEND TO CREATE RAZORPAY ORDER
      // ------------------------------------------------------

      const response = await fetch(
        `${API_BASE_URL}/commerce/create-payment-order`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            customer_id: customer.customer_id,
            transaction_id: transactionId || session.transaction_id,
            product_id: product.product_id,
            product_price: originalPrice,
            discount_percent: discountPercent,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data?.detail ||
            data?.message ||
            "Unable to create payment order."
        );
      }

      const transactionId = data.transactionId || session.transaction_id;
      if (!transactionId) {
        throw new Error(
          "Server did not return transaction_id. Payment cannot proceed securely."
        );
      }
      
      console.log("Transaction ID:", transactionId);

      // ------------------------------------------------------
      // 2. CHECK RAZORPAY SDK
      // ------------------------------------------------------

      if (!window.Razorpay) {
        throw new Error("Razorpay Checkout SDK is not loaded.");
      }

      // ------------------------------------------------------
      // 3. RAZORPAY CHECKOUT OPTIONS
      // ------------------------------------------------------

      const options = {
        key: data.keyId,

        amount: data.amount,

        currency: data.currency,

        name: "AgentCommerce OS",

        description: "AI Agentic Commerce Purchase",

        order_id: data.orderId,

        // ======================================================
        // PAYMENT SUCCESS HANDLER
        // ======================================================
        // SECURITY: Send ONLY transaction_id for verification
        // Never send product pricing data to server
        // ======================================================

        handler: async function (paymentResponse) {
          console.log(
            "Razorpay Payment Response:",
            paymentResponse
          );

          try {
            const verifyResponse = await fetch(
              `${API_BASE_URL}/commerce/verify-payment`,
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  // ================================================
                  // SECURITY: Send transaction_id and payment details only.
                  // Backend resolves the real Razorpay order_id from MongoDB.
                  // ================================================
                  transaction_id: transactionId,
                  razorpay_payment_id: paymentResponse.razorpay_payment_id,
                  razorpay_signature: paymentResponse.razorpay_signature,
                }),
              }
            );

            const verifyData = await verifyResponse.json();

            if (!verifyResponse.ok) {
              throw new Error(
                verifyData?.detail?.message ||
                  verifyData?.detail ||
                  "Payment verification failed."
              );
            }

            setPaymentResponse(verifyData);

            if (verifyData?.final_action === "ORDER_CREATED") {
              setStatus("Payment verified. Order created successfully.");
            } else {
              setStatus("Payment completed. Verification pending...");
            }

            setLoading(false);
          } catch (error) {
            console.error("Verification Error:", error);
            setStatus(error.message || "Payment verification failed.");
            setLoading(false);
          }
        },

        // ----------------------------------------------------
        // PREFILL
        // ----------------------------------------------------

        prefill: {
          name: customer.name || "AgentCommerce Customer",
          email: "customer@example.com",
          contact: "9999999999",
        },

        // ----------------------------------------------------
        // NOTES
        // ----------------------------------------------------

        notes: {
          customer_id: String(customer.customer_id),
          product_id: String(product.product_id),
          source: "AgentCommerce OS",
        },

        // ----------------------------------------------------
        // THEME
        // ----------------------------------------------------

        theme: {
          color: "#6366f1",
        },

        // ----------------------------------------------------
        // MODAL
        // ----------------------------------------------------

        modal: {
          ondismiss: function () {
            setLoading(false);
            setStatus("Payment window closed.");
          },
        },
      };

      // ------------------------------------------------------
      // 4. CREATE RAZORPAY INSTANCE
      // ------------------------------------------------------

      const razorpay = new window.Razorpay(options);

      razorpay.on("payment.failed", function (response) {
        console.error("Razorpay Payment Failed:", response.error);
        setStatus(
          response.error?.description || "Payment failed. Please try again."
        );
        setLoading(false);
      });

      razorpay.open();

    } catch (error) {
      console.error("Checkout Error:", error);

      setStatus(
        error.message ||
          "Something went wrong while starting checkout."
      );

      setLoading(false);
    }
  };

  if (sessionLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <div className="text-lg text-slate-300">Loading your AI-negotiated offer...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* ----------------------------------------------------
          HEADER
      ---------------------------------------------------- */}

      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">

          <div>
            <h1 className="text-xl font-bold tracking-tight">AgentCommerce OS</h1>
            <p className="text-xs text-slate-400">AI-Powered Agentic Commerce</p>
          </div>

          <div className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-2 text-xs font-medium text-emerald-400">
            Razorpay Test Mode
          </div>

        </div>
      </header>

      {/* ----------------------------------------------------
          MAIN
      ---------------------------------------------------- */}

      <main className="mx-auto flex max-w-6xl items-center justify-center px-6 py-16">

        <div className="grid w-full max-w-5xl gap-8 lg:grid-cols-[1.4fr_0.8fr]">

          {/* ==================================================
              PRODUCT CARD
          ================================================== */}

          <section className="rounded-3xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl backdrop-blur">

            {/* AI BADGE */}

            <div className="mb-8 flex items-center gap-3">

              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-500/20 text-xl">
                ✨
              </div>

              <div>
                <p className="text-sm font-semibold text-indigo-400">AI Negotiated Offer</p>
                <p className="text-xs text-slate-500">Personalized by AgentCommerce OS</p>
              </div>

            </div>

            {/* PRODUCT */}

            <div className="mb-10">
              <p className="mb-2 text-xs font-medium uppercase tracking-widest text-slate-500">
                Product #{product.product_id}
              </p>
              <h2 className="text-4xl font-bold tracking-tight">{product.name}</h2>
              <p className="mt-4 max-w-xl leading-7 text-slate-400">
                Your AI commerce agent negotiated a personalized price for this purchase.
              </p>

            </div>

            {/* PRICE */}

            <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-6">

              <div className="flex items-center justify-between">

                <span className="text-slate-400">
                  Original price
                </span>

                <span className="text-slate-300 line-through">
                  ₹784.23
                </span>

              </div>

              <div className="mt-4 flex items-center justify-between">
                <span className="text-slate-400">AI discount</span>
                <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-sm font-semibold text-emerald-400">
                  {discountPercent}% OFF
                </span>

              </div>

              <div className="my-5 border-t border-white/10" />

              <div className="flex items-end justify-between">

                <div>
                  <p className="text-sm text-slate-500">
                    Final price
                  </p>

                  <p className="mt-1 text-4xl font-bold">
                    ₹705.81
                  </p>
                </div>
                <span className="mb-1 text-sm text-slate-500">INR</span>
              </div>

            </div>

            {/* CUSTOMER */}

            <div className="mt-6 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-500/20 font-semibold text-indigo-300">
                V
              </div>

              <div>
                <p className="text-sm font-medium">Customer #{customer.customer_id}</p>
                <p className="text-xs text-slate-500">Personalized checkout</p>
              </div>

            </div>

          </section>

          {/* ==================================================
              PAYMENT CARD
          ================================================== */}

          <section className="flex flex-col rounded-3xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl backdrop-blur">

            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Secure Checkout</p>
              <h2 className="mt-2 text-2xl font-bold">Complete your purchase</h2>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                You will be redirected to Razorpay&apos;s secure payment interface.
              </p>

            </div>

            {/* ORDER SUMMARY */}

            <div className="mt-8 space-y-4">

              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Product</span>
                <span>#{product.product_id}</span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-slate-400">
                  Quantity
                </span>

                <span>
                  1
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Discount</span>
                <span className="text-emerald-400">- ₹{discountAmount.toFixed(2)}</span>
              </div>

              <div className="border-t border-white/10 pt-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Total</span>
                  <span className="text-2xl font-bold">₹{finalPrice.toFixed(2)}</span>
                </div>

              </div>
            </div>

            {/* PAYMENT BUTTON */}

            <div className="mt-auto pt-10">

              <button
                onClick={handlePayment}
                disabled={loading}
                className="w-full rounded-2xl bg-indigo-500 px-6 py-4 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:bg-indigo-400 hover:shadow-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Creating Secure Order..." : `Pay ₹${finalPrice.toFixed(2)}`}
              </button>

              {/* STATUS */}

              {status && (
                <div
                  className={`mt-4 rounded-xl border p-4 text-sm ${
                    status.toLowerCase().includes("failed")
                      ? "border-red-400/20 bg-red-400/10 text-red-300"
                      : "border-amber-400/20 bg-amber-400/10 text-amber-300"
                  }`}
                >
                  {status}
                </div>
              )}

              {/* SECURITY */}

              <div className="mt-5 flex items-center justify-center gap-2 text-xs text-slate-500">
                <span>🔒</span>
                <span>Secured by Razorpay Test Mode</span>
              </div>

            </div>

          </section>

        </div>

      </main>

      {/* ----------------------------------------------------
          PAYMENT RESPONSE DEBUG
          Remove this before final submission.
      ---------------------------------------------------- */}

      {paymentResponse && (
        <div className="mx-auto mb-10 max-w-5xl px-6">

          <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/5 p-6">

            <p className="mb-3 text-sm font-semibold text-emerald-400">
              Razorpay Response Received
            </p>

            <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-400">
              {JSON.stringify(
                paymentResponse,
                null,
                2
              )}
            </pre>

          </div>

        </div>
      )}

    </div>
  );
}

