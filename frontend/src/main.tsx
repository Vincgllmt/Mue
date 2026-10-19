import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import "./styles.css";
import AuditPage from "./pages/AuditPage";
import HomePage from "./pages/HomePage";
import NewOfferPage from "./pages/NewOfferPage";
import OfferPage from "./pages/OfferPage";
import ProfilePage from "./pages/ProfilePage";

function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <NavLink to="/" className="brand">🐍 Mue</NavLink>
        <nav>
          <NavLink to="/" end>Candidatures</NavLink>
          <NavLink to="/offers/new">Nouvelle offre</NavLink>
          <NavLink to="/profile">Profil</NavLink>
          <NavLink to="/audit">Audit</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/offers/new" element={<NewOfferPage />} />
          <Route path="/offers/:id" element={<OfferPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/audit/:id" element={<AuditPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
