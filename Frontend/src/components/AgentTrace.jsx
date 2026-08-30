function AgentTrace({ trace = [] }) {
  if (!trace.length) return null;

  return (
    <div className="agent-trace">

      <div className="trace-title">
        Agent activity
      </div>

      <div className="trace-list">

        {trace.map((step, index) => (
          <div
            key={`${step}-${index}`}
            className="trace-step"
          >
            <span className="trace-dot" />

            <span>
              {step
                .replaceAll("_", " ")
                .toLowerCase()
                .replace(/\b\w/g, c => c.toUpperCase())}
            </span>
          </div>
        ))}

      </div>

    </div>
  );
}

export default AgentTrace;