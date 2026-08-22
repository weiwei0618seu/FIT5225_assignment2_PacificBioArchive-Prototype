import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/">
          <span className="brand__mark" aria-hidden="true">P</span>
          <span><strong>Pacific</strong> BioArchive</span>
        </NavLink>
        <nav aria-label="Primary navigation">
          <NavLink to="/">Overview</NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/manage">Manage</NavLink>
        </nav>
        <div className="account">
          <span title={user?.username}>Signed in</span>
          <button className="button button--quiet" type="button" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
