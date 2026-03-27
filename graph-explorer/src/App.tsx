import { Routes, Route, Link } from "react-router-dom";
import SigmaGraph from "./v1-sigma/SigmaGraph";
import FlowGraph from "./v2-reactflow/FlowGraph";

function Landing() {
  return (
    <div className="landing">
      <h1>Graph Explorer</h1>
      <p>
        Interactive visualization of the Hungarian Political Argument Knowledge
        Graph. Explore topics, parties, and their argumentative relationships.
      </p>
      <div className="landing-links">
        <Link to="/v1">Sigma.js (Force-directed)</Link>
        <Link to="/v2">React Flow (Hierarchical)</Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/v1" element={<SigmaGraph />} />
      <Route path="/v2" element={<FlowGraph />} />
    </Routes>
  );
}
