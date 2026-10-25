import { Link, NavLink, Outlet, ScrollRestoration } from "react-router";
import { useAuth } from "../auth/AuthProvider";

export function Layout() {
  const { me, signOut } = useAuth();
  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="site-nav">
        <div className="wrap nav-inner">
          <Link className="brand" to="/" aria-label="varuna home">varuna</Link>
          <nav className="nav-links" aria-label="Primary">
            <NavLink to="/" end>Latest</NavLink>
            <NavLink to="/creators">Creators</NavLink>
            <NavLink to="/method">Method</NavLink>
            <NavLink to="/transparency">Transparency</NavLink>
          </nav>
          <div className="nav-actions">
            {me?.email && (
              <span className="nav-user">
                {me.is_admin && <Link to="/admin/logs" className="underline">Logs</Link>}
                {me.is_admin && <Link to="/admin/records" className="underline">Records</Link>}
                <span title={me.email}>{me.email.split("@")[0]}</span>
                <button type="button" onClick={() => void signOut()}>Sign out</button>
              </span>
            )}
            <Link className="btn btn-primary btn-sm" to="/check">Check a reel</Link>
          </div>
        </div>
      </header>
      <main id="main">
        <Outlet />
      </main>
      <footer className="site-foot invert">
        <div className="wrap foot-inner">
          <div>
            <span className="brand">varuna</span>
            <p className="tagline">Question before you believe.</p>
          </div>
          <nav className="foot-links" aria-label="Footer">
            <Link to="/method">Methodology</Link>
            <Link to="/transparency">Transparency</Link>
            <Link to="/method#sources">Source rankings</Link>
            <Link to="/creators">Creators</Link>
            <Link to="/check">Check a reel</Link>
          </nav>
          <p className="foot-note">
            varuna fact checker checks claims, not people. Every verdict shows its sources, and verdicts expire so
            fast-moving claims get checked again.
          </p>
        </div>
        <div className="foot-mark" aria-hidden="true">varuna</div>
      </footer>
      <ScrollRestoration />
    </>
  );
}
