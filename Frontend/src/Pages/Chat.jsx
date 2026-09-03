import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { sendCommerceMessage } from "../lib/api";
import AgentResponse from "../components/commerce/AgentResponse";

const CUSTOMER_ID = 5176;

const WELCOME_MESSAGE = {
  role: "assistant",
  type: "welcome",
  text:
    "Hi! I’m your AgentCommerce shopping agent. Tell me what you’re looking for and I’ll find the best option for you.",
};

export default function Chat() {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [negotiationContext, setNegotiationContext] = useState({});

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const suggestions = [
    "Find me a smartphone under ₹25,000",
    "Find me running shoes under ₹3,000",
    "Show me the best deal available",
  ];

  async function handleSend(message = input, context = {}) {
    const text = message.trim();

    if (!text || loading) return;

    setInput("");

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text,
      },
    ]);

    setLoading(true);

    try {
      const response = await sendCommerceMessage({
        message: text,
        customer_id: CUSTOMER_ID,

        ...negotiationContext,
        ...context,

        execute_payment: false,
      });

      const responseProductId =
        response?.product_id ??
        response?.offer?.product_id ??
        response?.transaction?.product_id ??
        response?.products?.[0]?.product_id;
      const responseTransactionId =
        response?.offer?.transaction_id ??
        response?.transaction?.transaction_id;

      if (response?.action === "NEGOTIATION_AMOUNT_REQUIRED" && responseProductId != null) {
        setNegotiationContext({
          product_id: responseProductId,
          ...(responseTransactionId ? { transaction_id: responseTransactionId } : {}),
        });
      } else if (response?.offer || response?.transaction) {
        setNegotiationContext({});
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            response?.message ||
            response?.response ||
            "I found some options for you.",
          data: response,
        },
      ]);
    } catch (error) {
      console.error("Commerce error:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            "I couldn't complete that request right now. Please try again.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleAction(action, product, data) {
    const transactionId =
      data?.offer?.transaction_id ||
      data?.transaction?.transaction_id;

    const currentProduct =
      product && (product.product_id || product.id)
        ? product
        : data?.product && (data.product.product_id || data.product.id)
          ? data.product
          : data?.products?.find(
              (candidate) =>
                Number(candidate?.product_id ?? candidate?.id) === Number(data?.product_id ?? data?.transaction?.product_id ?? data?.offer?.product_id)
            ) ||
            data?.products?.[0] ||
            null;

    const productId =
      currentProduct?.product_id ??
      currentProduct?.id ??
      data?.product_id ??
      data?.transaction?.product_id ??
      data?.offer?.product_id;

    /*
     * USER SELECTS PRODUCT
     */
    if (action === "select_product") {
      setNegotiationContext({ product_id: productId });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Great choice. Here is the product details.",
          data: {
            ...data,
            action: "VIEW_PRODUCT",
            product: product,
            product_id: productId,
            transaction: transactionId
              ? {
                  transaction_id: transactionId,
                  product_id: productId,
                }
              : undefined,
            message: "Great choice. Here's the product you're interested in.",
          },
        },
      ]);

      return;
    }

    /*
     * USER WANTS NEGOTIATION
     */
    if (action === "negotiate") {
      handleSend(
        "Can you negotiate a better price for me?",
        {
          product_id: productId,
          transaction_id: transactionId,
        }
      );

      return;
    }

    /*
     * USER ACCEPTS NEGOTIATED OFFER
     */
    if (action === "accept_offer") {
      navigate("/checkout", {
        state: {
          transactionId,
          productId,
          commerceData: data,
        },
      });

      return;
    }

    /*
     * USER WANTS ANOTHER NEGOTIATION
     */
    if (action === "negotiate_again") {
      handleSend(
        "Try negotiating a better price again.",
        {
          product_id: productId,
          transaction_id: transactionId,
        }
      );

      return;
    }

    /*
     * CHECKOUT
     */
    if (action === "proceed_to_payment") {
      navigate("/checkout", {
        state: {
          transactionId,
          productId,
          commerceData: data,
        },
      });

      return;
    }

    /*
     * DIRECT BUY
     */
    if (action === "buy_now") {
      navigate("/checkout", {
        state: {
          transactionId,
          productId,
          commerceData: data,
        },
      });
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  function resetChat() {
    setMessages([WELCOME_MESSAGE]);
    setInput("");
    setNegotiationContext({});
  }

  return (
    <div className="flex h-screen bg-slate-950 text-white">

      {/* SIDEBAR */}
      <aside className="hidden w-72 flex-col border-r border-slate-800 bg-slate-950 lg:flex">

        <div className="border-b border-slate-800 px-5 py-5">

          <div className="flex items-center gap-3">

            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 font-bold">
              A
            </div>

            <div>
              <h1 className="font-semibold">
                AgentCommerce
              </h1>

              <p className="text-xs text-slate-500">
                Autonomous Commerce OS
              </p>
            </div>

          </div>

        </div>

        <div className="flex-1 px-4 py-5">

          <button
            onClick={resetChat}
            className="mb-6 flex w-full items-center gap-3 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-medium transition hover:bg-slate-800"
          >
            <span className="text-lg">＋</span>
            New conversation
          </button>

          <p className="mb-3 px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent
          </p>

          <div className="space-y-1">

            <button className="w-full rounded-lg bg-slate-900 px-3 py-3 text-left text-sm text-slate-300">
              Smartphone shopping
            </button>

            <button className="w-full rounded-lg px-3 py-3 text-left text-sm text-slate-400 transition hover:bg-slate-900">
              Best deal negotiation
            </button>

            <button className="w-full rounded-lg px-3 py-3 text-left text-sm text-slate-400 transition hover:bg-slate-900">
              Running shoes
            </button>

          </div>

        </div>

        {/* AGENT STATUS */}
        <div className="border-t border-slate-800 p-4">

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

            <div className="mb-3 flex items-center justify-between">

              <span className="text-sm font-medium">
                Agent Status
              </span>

              <span className="flex items-center gap-2 text-xs text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Online
              </span>

            </div>

            <div className="space-y-2 text-xs text-slate-500">

              <StatusRow
                name="Buyer Agent"
              />

              <StatusRow
                name="Negotiation Agent"
              />

              <StatusRow
                name="Payment Agent"
              />

            </div>

          </div>

        </div>

      </aside>

      {/* MAIN */}
      <main className="flex min-w-0 flex-1 flex-col">

        {/* HEADER */}
        <header className="flex h-16 items-center justify-between border-b border-slate-800 px-5 lg:px-8">

          <div>

            <h2 className="font-semibold">
              Shopping Assistant
            </h2>

            <p className="text-xs text-slate-500">
              Discover · Negotiate · Buy
            </p>

          </div>

          <div className="hidden rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-400 sm:block">
            Customer #{CUSTOMER_ID}
          </div>

        </header>

        {/* CHAT */}
        <div className="flex-1 overflow-y-auto">

          <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">

            {messages.map((message, index) => (
              <Message
                key={index}
                message={message}
                onAction={handleAction}
              />
            ))}

            <div ref={messagesEndRef} />

            {loading && (
              <div className="mb-8 flex gap-4">

                <AgentAvatar />

                <div className="rounded-2xl rounded-tl-md border border-slate-800 bg-slate-900 px-5 py-4">

                  <div className="flex items-center gap-2">

                    <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400" />

                    <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:150ms]" />

                    <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:300ms]" />

                    <span className="ml-2 text-xs text-slate-500">
                      Agent is working...
                    </span>

                  </div>

                </div>

              </div>
            )}

          </div>

        </div>

        {/* SUGGESTIONS */}
        {messages.length === 1 && (

          <div className="mx-auto w-full max-w-5xl px-4 pb-3 sm:px-6">

            <div className="grid gap-2 sm:grid-cols-3">

              {suggestions.map((suggestion) => (

                <button
                  key={suggestion}
                  onClick={() => handleSend(suggestion)}
                  className="rounded-xl border border-slate-800 bg-slate-900 p-3 text-left text-xs text-slate-400 transition hover:border-violet-500/40 hover:bg-slate-800 hover:text-slate-200"
                >
                  {suggestion}
                </button>

              ))}

            </div>

          </div>

        )}

        {/* INPUT */}
        <div className="border-t border-slate-800 bg-slate-950 p-4">

          <div className="mx-auto max-w-5xl">

            <div className="relative rounded-2xl border border-slate-700 bg-slate-900 shadow-xl focus-within:border-violet-500/60">

              <textarea
                value={input}
                onChange={(event) =>
                  setInput(event.target.value)
                }
                onKeyDown={handleKeyDown}
                placeholder="Ask me to find, compare, negotiate, or buy..."
                rows={1}
                className="w-full resize-none bg-transparent px-5 py-4 pr-14 text-sm text-white outline-none placeholder:text-slate-500"
              />

              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="absolute bottom-2 right-2 flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
              >
                ↑
              </button>

            </div>

            <p className="mt-2 text-center text-[11px] text-slate-600">
              Your agent can discover products, negotiate offers and prepare secure checkout.
            </p>

          </div>

        </div>

      </main>

    </div>
  );
}


/* MESSAGE */

function Message({ message, onAction }) {

  const isUser = message.role === "user";

  return (
    <div
      className={`mb-8 flex gap-4 ${
        isUser ? "justify-end" : ""
      }`}
    >

      {!isUser && <AgentAvatar />}

      <div
        className={`max-w-4xl rounded-2xl px-5 py-4 text-sm leading-6 ${
          isUser
            ? "max-w-xl rounded-tr-md bg-violet-600 text-white"
            : "w-full rounded-tl-md border border-slate-800 bg-slate-900 text-slate-300"
        }`}
      >

        {isUser ? (
          message.text
        ) : message.data ? (
          <AgentResponse
            data={message.data}
            onAction={onAction}
          />
        ) : (
          message.text
        )}

      </div>

    </div>
  );
}


/* PRODUCT/AGENT AVATAR */

function AgentAvatar() {

  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-violet-500/30 bg-violet-500/10 text-violet-300">
      ✦
    </div>
  );

}


/* STATUS */

function StatusRow({ name }) {

  return (
    <div className="flex justify-between">

      <span>{name}</span>

      <span className="text-emerald-400">
        Ready
      </span>

    </div>
  );

}