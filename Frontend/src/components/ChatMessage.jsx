function ChatMessage({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`chat-row ${
        isUser ? "chat-row-user" : "chat-row-agent"
      }`}
    >
      <div
        className={`chat-bubble ${
          isUser
            ? "chat-bubble-user"
            : "chat-bubble-agent"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}

export default ChatMessage;