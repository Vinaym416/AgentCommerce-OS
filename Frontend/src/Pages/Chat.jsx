
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createCommerceSocket, getChatSession } from "../lib/api";
import AgentResponse from "../components/commerce/AgentResponse";

const CUSTOMER_ID = 5176;
const CHAT_STORAGE_KEY = "agentcommerce-chat-session";
const CHAT_SESSION_ID_KEY = "agentcommerce-chat-session-id";
const CART_STORAGE_KEY = "agentcommerce-cart";

function readCartCount() {
  try {
    const cart = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
    return Array.isArray(cart)
      ? cart.reduce((total, item) => total + Math.max(1, Number(item.quantity || 1)), 0)
      : 0;
  } catch {
    return 0;
  }
}

const WELCOME_MESSAGE = {
  role: "assistant",
  type: "welcome",
  text:
    "Hi! I’m your AgentCommerce shopping agent. What are you looking for today? I can help you find products, compare options, negotiate the price, and get you ready to checkout.",
};

export default function Chat() {
  const navigate = useNavigate();
  const { sessionId: routeSessionId } = useParams();

  const messagesEndRef = useRef(null);
  const socketRef = useRef(null);
  const pendingRequestRef = useRef(null);

  const initialSession = (() => {
    const navigation = performance.getEntriesByType("navigation")[0];

    /*
     * A browser reload should start with the current server session
     * when the route contains a session id.
     *
     * For a normal /commerce/chat route, reload starts a fresh local
     * conversation instead of showing stale demo messages.
     */
    if (!routeSessionId && navigation?.type === "reload") {
      sessionStorage.removeItem(CHAT_STORAGE_KEY);
      sessionStorage.removeItem(CHAT_SESSION_ID_KEY);
      localStorage.removeItem(CHAT_SESSION_ID_KEY);
      return null;
    }

    try {
      return JSON.parse(
        sessionStorage.getItem(CHAT_STORAGE_KEY) || "null"
      );
    } catch {
      sessionStorage.removeItem(CHAT_STORAGE_KEY);
      return null;
    }
  })();

  const [messages, setMessages] = useState(
    initialSession?.messages?.length
      ? initialSession.messages
      : [WELCOME_MESSAGE]
  );

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [socketReady, setSocketReady] = useState(false);
  const [cartCount, setCartCount] = useState(() => readCartCount());

  useEffect(() => {
    const refreshCartCount = () => setCartCount(readCartCount());
    window.addEventListener("agentcommerce-cart-updated", refreshCartCount);
    window.addEventListener("storage", refreshCartCount);
    return () => {
      window.removeEventListener("agentcommerce-cart-updated", refreshCartCount);
      window.removeEventListener("storage", refreshCartCount);
    };
  }, []);

  /*
   * This stores the currently selected product / transaction.
   *
   * Example:
   *
   * {
   *   product_id: 397,
   *   transaction_id: "txn_..."
   * }
   *
   * It is intentionally kept separately from messages so the next
   * conversational action knows which product the user is talking about.
   */
  const [negotiationContext, setNegotiationContext] = useState(
    initialSession?.negotiationContext || {}
  );

  const [sessionId] = useState(() => {
    if (routeSessionId) {
      localStorage.setItem(CHAT_SESSION_ID_KEY, routeSessionId);
      sessionStorage.setItem(CHAT_SESSION_ID_KEY, routeSessionId);

      return routeSessionId;
    }

    const storedSessionId =
      sessionStorage.getItem(CHAT_SESSION_ID_KEY) ||
      localStorage.getItem(CHAT_SESSION_ID_KEY);

    if (storedSessionId) {
      return storedSessionId;
    }

    const created = crypto.randomUUID();

    localStorage.setItem(CHAT_SESSION_ID_KEY, created);
    sessionStorage.setItem(CHAT_SESSION_ID_KEY, created);

    return created;
  });

  /*
   * Restore the server-side conversation when a session already exists.
   */
  useEffect(() => {
    let active = true;

    if (!routeSessionId) {
      return undefined;
    }

    getChatSession(sessionId)
      .then((session) => {
        if (!active) {
          return;
        }

        if (
          Array.isArray(session?.messages) &&
          session.messages.length
        ) {
          setMessages(session.messages);
          setNegotiationContext(session.context || {});
        }
      })
      .catch(() => {
        /*
         * A new session may not have a server-side record yet.
         * Browser session storage is enough until the first message
         * is successfully processed.
         */
      });

    return () => {
      active = false;
    };
  }, [routeSessionId, sessionId]);

  /*
   * Persist the visible conversation locally.
   */
  useEffect(() => {
    sessionStorage.setItem(
      CHAT_STORAGE_KEY,
      JSON.stringify({
        messages,
        negotiationContext,
      })
    );
  }, [messages, negotiationContext]);

  /*
   * Create one WebSocket connection for the entire chat.
   *
   * The connection itself is an external system, so it is explicitly
   * closed when the component is removed.
   */
  useEffect(() => {
    let active = true;

    const socket = createCommerceSocket({
      onOpen: () => {
        if (active) {
          setSocketReady(true);
        }
      },

      onClose: () => {
        if (active) {
          setSocketReady(false);
        }
      },

      onError: () => {
        if (active) {
          setSocketReady(false);
        }
      },
    });

    socketRef.current = socket;

    return () => {
      active = false;

      if (pendingRequestRef.current) {
        pendingRequestRef.current.reject(
          new Error("Chat connection was closed.")
        );

        pendingRequestRef.current = null;
      }

      socket.close();
      socketRef.current = null;
    };
  }, []);

  /*
   * Keep the latest assistant message visible.
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading]);

  const suggestions = [
    "Find me a smartphone under ₹25,000",
    "Find me running shoes under ₹3,000",
    "Show me the best deal available",
  ];

  /*
   * Send one conversational request through the existing WebSocket.
   *
   * Important:
   * We do not create a new WebSocket for every message.
   * We also make sure only one request is waiting at a time.
   */
  async function handleSend(message = input, context = {}) {
    const text = message.trim();

    if (!text) {
      return;
    }

    if (loading) {
      return;
    }

    const startsNewSearch = isNewCatalogSearch(text);
    const requestContext = startsNewSearch
      ? context
      : { ...negotiationContext, ...context };

    if (startsNewSearch) {
      setNegotiationContext({});
    }

    if (/^\d+(?:[.,]\d+)?$/.test(text.replace(/\s/g, ""))) {
      setInput("");
      setMessages((prev) => [
        ...prev,
        {
          role: "user",
          text,
        },
        {
          role: "assistant",
          text: "Please specify what this number means.",
          data: {
            action: "NUMERIC_INPUT_CLARIFICATION",
            message: "Please specify what this number means. Try one of the examples below.",
          },
        },
      ]);
      return;
    }

    const socket = socketRef.current;

    if (
      !socketReady ||
      !socket ||
      socket.readyState !== WebSocket.OPEN
    ) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            "I’m reconnecting to the shopping service. Give me a moment and try that again.",
          error: true,
        },
      ]);

      if (!routeSessionId) {
        navigate(`/commerce/chat/session/${sessionId}`, { replace: true });
      }

      return;
    }

    setInput("");

    /*
     * Add the user's actual words to the conversation.
     */
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text,
      },
    ]);

    setLoading(true);

    try {
      const response = await sendSocketMessage({
        message: text,
        session_id: sessionId,
        customer_id: CUSTOMER_ID,

        /*
         * Existing context comes first.
         * Explicit action context wins over old context.
         */
        ...requestContext,

        /*
         * Payment is never executed directly from the conversation.
         * Checkout handles the actual payment flow.
         */
        execute_payment: false,
      });

      /*
       * Resolve the product that the backend is currently talking about.
       */
      const responseProductId =
        response?.product_id ??
        response?.product?.product_id ??
        response?.product?.id ??
        response?.offer?.product_id ??
        response?.transaction?.product_id ??
        response?.products?.[0]?.product_id ??
        response?.products?.[0]?.id;

      const responseTransactionId =
        response?.offer?.transaction_id ??
        response?.transaction?.transaction_id ??
        response?.transaction_id;

      /*
       * If the backend asks the user for a negotiation amount,
       * remember the selected product.
       */
      if (
        [
          "NEGOTIATION_AMOUNT_REQUIRED",
          "NEGOTIATION_INPUT_REQUIRED",
        ].includes(response?.action) &&
        responseProductId != null
      ) {
        setNegotiationContext({
          product_id: responseProductId,

          ...(responseTransactionId
            ? {
                transaction_id: responseTransactionId,
              }
            : {}),
        });
      }

      /*
       * Once a real offer exists, keep the transaction/product available
       * until checkout. Do not randomly replace the context.
       */
      else if (
        response?.offer &&
        (response?.offer?.product_id != null ||
          responseProductId != null)
      ) {
        setNegotiationContext({
          product_id:
            response?.offer?.product_id ??
            responseProductId,

          ...(responseTransactionId
            ? {
                transaction_id: responseTransactionId,
              }
            : {}),
        });
      }

      /*
       * Product recommendation without an active negotiation should
       * not create a fake negotiation state.
       */
      else if (
        response?.action === "RECOMMEND_PRODUCT" &&
        responseProductId != null
      ) {
        setNegotiationContext({});
      }

      /*
       * The backend response is stored as one assistant message.
       *
       * AgentResponse decides how to visually render:
       * - product results
       * - product detail
       * - negotiation
       * - checkout
       * - order confirmation
       */
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
            "I couldn’t complete that request right now. Please try again.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function isNewCatalogSearch(text) {
    const normalized = text.toLowerCase().replace(/\s+/g, " ").trim();
    const phraseMatch = [
      "best deal",
      "show me",
      "find me",
      "find a",
      "find the",
      "looking for",
      "recommend",
      "more options",
      "other products",
      "different product",
      "something cheap",
      "cheapest",
      "budget-friendly",
    ].some((phrase) => normalized.includes(phrase));
    const budgetMatch = /\b(?:under|below|less than|within|budget)\b\s*(?:inr|rs|₹)?\s*[0-9]/i.test(normalized);
    const optionCountMatch = /\b(?:show|give|find|list)\s+(?:me\s+)?\d+\s+(?:options?|products?|items?)\b/i.test(normalized);
    return phraseMatch || budgetMatch || optionCountMatch;
  }

  /*
   * Promise wrapper around the shared WebSocket.
   *
   * This keeps the message handling predictable and prevents a
   * previous request from accidentally consuming a later response.
   */
  function sendSocketMessage(payload) {
    return new Promise((resolve, reject) => {
      const socket = socketRef.current;

      if (
        !socket ||
        socket.readyState !== WebSocket.OPEN
      ) {
        reject(new Error("Chat connection is not available."));
        return;
      }

      const previousRequest = pendingRequestRef.current;

      if (previousRequest) {
        previousRequest.reject(
          new Error("Another chat request is already being processed.")
        );

        pendingRequestRef.current = null;
      }

      const handleMessage = (event) => {
        try {
          const response = JSON.parse(event.data);

          pendingRequestRef.current = null;

          if (response?.success === false) {
            reject(
              new Error(
                response?.error ||
                  response?.message ||
                  "Chat request failed."
              )
            );

            return;
          }

          resolve(response);
        } catch {
          pendingRequestRef.current = null;

          reject(
            new Error(
              "The chat server returned an invalid response."
            )
          );
        }
      };

      const handleError = () => {
        pendingRequestRef.current = null;

        reject(
          new Error("Chat connection failed.")
        );
      };

      socket.addEventListener(
        "message",
        handleMessage,
        { once: true }
      );

      socket.addEventListener(
        "error",
        handleError,
        { once: true }
      );

      pendingRequestRef.current = {
        resolve,
        reject,
      };

      socket.send(JSON.stringify(payload));
    });
  }

  /*
   * Resolve the product involved in a button action.
   */
  function resolveCurrentProduct(product, data) {
    const productId =
      product?.product_id ??
      product?.id ??
      data?.product_id ??
      data?.product?.product_id ??
      data?.product?.id ??
      data?.transaction?.product_id ??
      data?.offer?.product_id;

    if (productId == null) {
      return null;
    }

    if (
      product &&
      (product.product_id != null ||
        product.id != null)
    ) {
      return product;
    }

    if (
      data?.product &&
      (data.product.product_id != null ||
        data.product.id != null)
    ) {
      return data.product;
    }

    const products = Array.isArray(data?.products)
      ? data.products
      : [];

    return (
      products.find(
        (candidate) =>
          String(
            candidate?.product_id ??
              candidate?.id
          ) === String(productId)
      ) ||
      products[0] ||
      {
        product_id: productId,
      }
    );
  }

  /*
   * Handle actions generated by ProductCard / AgentResponse.
   */
  function handleAction(action, product, data) {
    if (action === "add_to_cart") {
      addToCart(product, data);
      return;
    }

    if (action === "remove_from_cart") {
      try {
        const stored = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
        const nextCart = Array.isArray(stored)
          ? stored.filter((item) => String(item.product_id) !== String(product?.product_id))
          : [];
        localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(nextCart));
        window.dispatchEvent(new Event("agentcommerce-cart-updated"));
      } catch {
        localStorage.removeItem(CART_STORAGE_KEY);
      }
      return;
    }

    if (action === "close_negotiation") {
      handleSend(
        "I would like to discuss a different product.",
        {
          button_action: "close_negotiation",
          product_id: null,
          transaction_id: null,
          negotiation_requested: false,
        }
      );
      return;
    }

    if (action === "numeric_suggestion") {
      handleSend(product, negotiationContext);
      return;
    }

    const currentProduct =
      resolveCurrentProduct(product, data);

    const productId =
      currentProduct?.product_id ??
      currentProduct?.id ??
      data?.product_id ??
      data?.product?.product_id ??
      data?.product?.id ??
      data?.transaction?.product_id ??
      data?.offer?.product_id;

    const transactionId =
      data?.offer?.transaction_id ??
      data?.transaction?.transaction_id ??
      data?.transaction_id ??
      negotiationContext?.transaction_id;

    const transactionProductId =
      data?.offer?.product_id ??
      data?.transaction?.product_id ??
      data?.product_id ??
      negotiationContext?.product_id;
    const productTransactionId =
      transactionProductId != null &&
      productId != null &&
      String(transactionProductId) === String(productId)
        ? transactionId
        : undefined;

    if (productId == null) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            "I couldn’t identify that product. Please choose a product from the results and I’ll help you from there.",
          error: true,
        },
      ]);

      return;
    }

    /*
     * USER SELECTS / VIEWS PRODUCT
     *
     * This does NOT send "I want this product" to the backend.
     *
     * That was one of the causes of the repeated conversational
     * messages. Viewing a product should simply show its details.
     */
    if (action === "select_product") {
      setNegotiationContext({
        product_id: productId,
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text:
            "Sure. Here’s a closer look at that product.",
          data: {
            ...data,

            action: "VIEW_PRODUCT",

            product: currentProduct,

            product_id: productId,

            message:
              "Sure. Here’s a closer look at that product.",
          },
        },
      ]);

      return;
    }

    /*
     * USER WANTS TO NEGOTIATE.
     *
     * This is a natural conversational sentence rather than
     * exposing an internal action name to the user.
     */
    if (action === "negotiate") {
      sendNegotiationRequest(productId, productTransactionId);

      return;
    }

    /*
     * USER ACCEPTS THE OFFER.
     *
     * Acceptance does not immediately charge the user.
     * It moves them to the secure checkout page.
     */
    if (action === "accept_offer") {
      const offer = data?.offer || {};

      const acceptedPrice =
        offer?.final_price ??
        offer?.amount ??
        offer?.price;

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Offer accepted.",
          data: {
            ...data,
            action: "OFFER_ACCEPTED",
            final_action: "OFFER_ACCEPTED",
            message: "Offer accepted.",
            product: currentProduct,
            offer: {
              ...offer,
              product_id: offer?.product_id ?? productId,
              ...(acceptedPrice != null ? { final_price: acceptedPrice } : {}),
            },
          },
        },
      ]);

      return;
    }

    /*
     * USER WANTS TO TRY AGAIN.
     */
    if (action === "negotiate_again" || action === "negotiate") {
      sendNegotiationRequest(productId, productTransactionId);

      return;
    }

    /*
     * CHECKOUT.
     */
    if (action === "proceed_to_payment") {
      navigate("/checkout", {
        state: {
          transactionId,
          productId,
          quantity: Math.max(1, Number(product?.quantity ?? data?.quantity ?? 1)),
          chatSessionId: sessionId,
          commerceData: data,
        },
      });

      return;
    }

    /*
     * DIRECT BUY AT THE CURRENT LISTED PRICE.
     */
    if (action === "buy_now") {
      addToCart(
        { ...currentProduct, quantity: product?.quantity ?? 1 },
        data
      );
    }
  }

  function addToCart(product, data) {
    let cart = [];
    try {
      const stored = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
      cart = Array.isArray(stored) ? stored : [];
    } catch {
      cart = [];
    }

    const item = {
      product_id: product?.product_id ?? product?.id ?? data?.offer?.product_id,
      name: product?.name || product?.product_name || "Selected product",
      category: product?.category || product?.category_name,
      price: Number(product?.price ?? product?.original_price ?? 0),
      final_price: Number(product?.final_price ?? product?.price ?? 0),
      quantity: Math.min(10, Math.max(1, Number(product?.quantity ?? 1))),
      transaction_id: data?.offer?.transaction_id ?? data?.transaction?.transaction_id,
      chatSessionId: sessionId,
      commerceData: data,
    };
    const existing = cart.find(
      (candidate) => String(candidate.product_id) === String(item.product_id)
    );
    const nextCart = existing
      ? cart.map((candidate) => candidate === existing
          ? { ...candidate, quantity: Math.min(10, candidate.quantity + item.quantity) }
          : candidate)
      : [...cart, item];
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(nextCart));
    window.dispatchEvent(new Event("agentcommerce-cart-updated"));
  }

  function sendNegotiationRequest(productId, transactionId) {
    const context = {
      product_id: productId,
      negotiation_requested: true,
      button_action: "negotiate",
      ...(transactionId ? { transaction_id: transactionId } : {}),
    };

    setNegotiationContext(context);
    handleSend("That’s a little higher than I was hoping for. Can you try one more time?", context);
  }

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      handleSend();
    }
  }

  /*
   * Start a genuinely new conversation.
   */
  function resetChat() {
    const newSessionId = crypto.randomUUID();

    setMessages([WELCOME_MESSAGE]);
    setInput("");
    setNegotiationContext({});
    setLoading(false);

    sessionStorage.removeItem(
      CHAT_STORAGE_KEY
    );

    localStorage.setItem(
      CHAT_SESSION_ID_KEY,
      newSessionId
    );

    sessionStorage.setItem(
      CHAT_SESSION_ID_KEY,
      newSessionId
    );

    navigate(
      "/commerce/chat/session/" +
        newSessionId
    );
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
              Discover · Compare · Negotiate · Buy
            </p>

          </div>

          <div className="hidden rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-400 sm:block">
            Customer #{CUSTOMER_ID}
          </div>

          {cartCount > 0 && (
            <button
              type="button"
              onClick={() => navigate("/cart")}
              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-300 transition hover:bg-emerald-500/20"
            >
              Go to cart ({cartCount})
            </button>
          )}

        </header>

        {/* CHAT */}
        <div className="flex-1 overflow-y-auto">

          <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">

            {messages.map((message, index) => (
              <Message
                key={`${sessionId}-${index}`}
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
                      I’m checking that for you...
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
                  onClick={() =>
                    handleSend(suggestion)
                  }
                  disabled={loading || !socketReady}
                  className="rounded-xl border border-slate-800 bg-slate-900 p-3 text-left text-xs text-slate-400 transition hover:border-violet-500/40 hover:bg-slate-800 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
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
                placeholder={
                  socketReady
                    ? "Ask me to find, compare, negotiate, or buy..."
                    : "Connecting to your shopping agent..."
                }
                rows={1}
                disabled={!socketReady}
                className="w-full resize-none bg-transparent px-5 py-4 pr-14 text-sm text-white outline-none placeholder:text-slate-500 disabled:cursor-not-allowed"
              />

              <button
                onClick={() => handleSend()}
                disabled={
                  !input.trim() ||
                  loading ||
                  !socketReady
                }
                className="absolute bottom-2 right-2 flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-500"
              >
                ↑
              </button>

            </div>

            <div className="mt-2 flex items-center justify-center gap-2">

              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  socketReady
                    ? "bg-emerald-400"
                    : "bg-amber-400"
                }`}
              />

              <p className="text-center text-[11px] text-slate-600">

                {socketReady
                  ? "Your agent can discover products, negotiate offers and prepare secure checkout."
                  : "Connecting to AgentCommerce..."}

              </p>

            </div>

          </div>

        </div>

      </main>

    </div>
  );
}


/* MESSAGE */

function Message({ message, onAction }) {

  const isUser =
    message.role === "user";

  return (
    <div
      className={`mb-8 flex gap-4 ${
        isUser
          ? "justify-end"
          : ""
      }`}
    >

      {!isUser && (
        <AgentAvatar />
      )}

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

      <span>
        {name}
      </span>

      <span className="text-emerald-400">
        Ready
      </span>

    </div>
  );

}

