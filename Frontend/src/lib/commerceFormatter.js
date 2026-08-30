export function formatCommerceResponse(data) {
  if (!data) {
    return {
      text: "I couldn't process that request. Please try again.",
      type: "error",
    };
  }

  const action = data.action || data.final_action;
  const message = data.message;

  switch (action) {
    case "RECOMMEND_PRODUCT":
      return {
        action,
        type: "recommendation",
        text: message || "I found some products that match what you're looking for.",
      };

    case "COUNTER_OFFER":
      return {
        action,
        type: "counter_offer",
        text: message || "I checked the available offer and negotiated a better price for you.",
      };

    case "OFFER_CREATED":
    case "OFFER_AVAILABLE":
    case "OFFER_REQUESTED":
      return {
        action,
        type: "offer",
        text: message || "I've prepared an offer based on your request.",
      };

    case "PAYMENT_PENDING":
    case "CHECKOUT_READY":
      return {
        action,
        type: "checkout",
        text: message || "Your offer has been accepted. Your checkout is ready.",
      };

    case "ORDER_CREATED":
      return {
        action,
        type: "order",
        text: message || "Payment was confirmed and your order has been created successfully.",
      };

    default:
      return {
        action,
        type: "general",
        text:
          data.message ||
          data.response ||
          "I've processed your request.",
      };
  }
}