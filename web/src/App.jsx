import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./lib/auth";
import Shell from "./components/Shell";
import Login from "./views/Login";
import Overview from "./views/Overview";
import Ask from "./views/Ask";
import Graph from "./views/Graph";
import Catalog from "./views/Catalog";
import Review from "./views/Review";
import Health from "./views/Health";
import About from "./views/About";

export default function App() {
  const { user } = useAuth();
  if (!user) return <Login />;

  const allowed = new Set(user.views || []);
  const guard = (key, element) => (allowed.has(key) ? element : <Navigate to="/" replace />);

  return (
    <Shell>
      <Routes>
        <Route path="/"        element={<Overview />} />
        <Route path="/ask"     element={guard("ask", <Ask />)} />
        <Route path="/graph"   element={guard("graph", <Graph />)} />
        <Route path="/catalog" element={guard("catalog", <Catalog />)} />
        <Route path="/review"  element={guard("review", <Review />)} />
        <Route path="/health"  element={guard("health", <Health />)} />
        <Route path="/about"   element={guard("about", <About />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
