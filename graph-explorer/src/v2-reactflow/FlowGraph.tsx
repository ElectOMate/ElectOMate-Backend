import { Link } from "react-router-dom";

export default function FlowGraph() {
  return (
    <div className="placeholder">
      <h2>React Flow Visualization</h2>
      <p>Coming in Step 05 of the prompt trail.</p>
      <Link to="/" className="back-link" style={{ position: "static" }}>
        Back to Home
      </Link>
    </div>
  );
}
