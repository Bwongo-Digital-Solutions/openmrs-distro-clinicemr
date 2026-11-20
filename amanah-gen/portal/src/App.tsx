import { useEffect, useMemo, useState } from "react";
import Keycloak from "keycloak-js";
import {
  Activity, ArrowRight, BookOpenCheck, CalendarDays, CheckCircle2,
  ChevronRight, ClipboardList, FileCheck2, FileHeart, HeartHandshake,
  Home, LogOut, Menu, MessageCircleHeart, ShieldCheck, Stethoscope,
  UserRound, Users, X
} from "lucide-react";

type Config = { url: string; realm: string; clientId: string };
type Section = { id: string; label: string; icon: typeof Home; description: string; status: string };
type Role = "individual" | "clinician" | "counsellor" | "reviewer";

const sections: Record<Role, Section[]> = {
  individual: [
    { id: "overview", label: "Overview", icon: Home, description: "Your AMANAH GEN home", status: "Available" },
    { id: "screening", label: "Screening", icon: ClipboardList, description: "Understand the screening process and your requests", status: "Coming soon" },
    { id: "results", label: "My results", icon: FileHeart, description: "Access results after clinical review and release", status: "Coming soon" },
    { id: "sharing", label: "Privacy & sharing", icon: ShieldCheck, description: "Manage purpose-specific sharing permissions", status: "Coming soon" },
    { id: "counselling", label: "Counselling", icon: HeartHandshake, description: "Find support from a qualified genetic counsellor", status: "Coming soon" }
  ],
  clinician: [
    { id: "overview", label: "Overview", icon: Home, description: "Clinical work overview", status: "Available" },
    { id: "screening", label: "Screening requests", icon: ClipboardList, description: "Review screening workflows", status: "Coming soon" },
    { id: "results", label: "Result review", icon: FileCheck2, description: "Review results before any patient release", status: "Coming soon" },
    { id: "referrals", label: "Referrals", icon: Users, description: "Coordinate specialist referrals", status: "Coming soon" }
  ],
  counsellor: [
    { id: "overview", label: "Overview", icon: Home, description: "Counselling work overview", status: "Available" },
    { id: "referrals", label: "Referral queue", icon: Users, description: "Review assigned counselling referrals", status: "Coming soon" },
    { id: "appointments", label: "Appointments", icon: CalendarDays, description: "Manage counselling appointments", status: "Coming soon" },
    { id: "followups", label: "Follow-ups", icon: MessageCircleHeart, description: "Coordinate agreed follow-up", status: "Coming soon" }
  ],
  reviewer: [
    { id: "overview", label: "Overview", icon: Home, description: "Knowledge governance overview", status: "Available" },
    { id: "documents", label: "Knowledge registry", icon: BookOpenCheck, description: "Review educational source documents", status: "Coming soon" },
    { id: "audit", label: "Audit history", icon: ShieldCheck, description: "Inspect reviewer-attributed events", status: "Coming soon" }
  ]
};

const roleLabels: Record<Role, string> = {
  individual: "Individual",
  clinician: "Clinician",
  counsellor: "Genetic counsellor",
  reviewer: "Knowledge reviewer"
};

const roleFor = (roles: string[]): Role => {
  if (roles.includes("AMANAH_GEN_ADMIN")) return "reviewer";
  if (roles.includes("AMANAH_GEN_COUNSELLOR")) return "counsellor";
  if (roles.includes("AMANAH_GEN_CLINICIAN")) return "clinician";
  return "individual";
};

const iconForRole = (role: Role) => role === "clinician" ? Stethoscope : role === "counsellor" ? HeartHandshake : role === "reviewer" ? BookOpenCheck : UserRound;

export default function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [keycloak, setKeycloak] = useState<Keycloak | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState("overview");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const response = await fetch("/amanah/portal/config.json", { cache: "no-store" });
        if (!response.ok) throw new Error("Portal identity configuration is unavailable.");
        const cfg = await response.json() as Config;
        if (!cfg.url || !cfg.realm || !cfg.clientId) throw new Error("Portal identity configuration is incomplete.");
        if (!alive) return;
        setConfig(cfg);
        const client = new Keycloak(cfg);
        const authenticated = await client.init({
          onLoad: "login-required",
          pkceMethod: "S256",
          checkLoginIframe: false,
          responseMode: "query"
        });
        if (!alive) return;
        if (!authenticated) throw new Error("Sign-in was not completed.");
        setKeycloak(client);
        setReady(true);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "Unable to initialise secure sign-in.");
      }
    })();
    return () => { alive = false; };
  }, []);

  const roles = useMemo(() => {
    const parsed = keycloak?.tokenParsed as { realm_access?: { roles?: string[] }; preferred_username?: string; name?: string } | undefined;
    return parsed?.realm_access?.roles ?? [];
  }, [keycloak, ready]);
  const role = roleFor(roles);
  const items = sections[role];
  const current = items.find(item => item.id === active) ?? items[0];
  const user = (keycloak?.tokenParsed as { name?: string; preferred_username?: string } | undefined);
  const displayName = user?.name || user?.preferred_username || "Signed-in user";
  const canUseAI = roles.includes("AMANAH_GEN_AI_USER");

  async function logout() {
    if (!keycloak) return;
    await keycloak.logout({ redirectUri: window.location.origin + "/amanah/portal/" });
  }

  if (error) return <main className="auth-state"><div className="auth-card"><div className="brand-mark">A</div><p className="eyebrow">SECURE ACCESS</p><h1>Sign-in unavailable</h1><p>{error}</p><p className="muted">Contact your AMANAH GEN administrator. Do not share passwords or access tokens.</p><button className="button primary" onClick={() => window.location.reload()}>Try again</button></div></main>;
  if (!ready || !keycloak || !config) return <main className="auth-state"><div className="auth-card"><div className="brand-mark">A</div><p className="eyebrow">AMANAH GEN</p><h1>Preparing your secure workspace</h1><p className="muted">Connecting to the identity provider…</p><div className="loader" /></div></main>;

  const RoleIcon = iconForRole(role);
  return <div className="app-shell">
    {mobileOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={mobileOpen ? "sidebar open" : "sidebar"}>
      <div className="brand"><div className="brand-mark">A</div><div><strong>AMANAH GEN</strong><span>Genetic health intelligence</span></div><button className="icon-button close-nav" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={18}/></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{items.map(item => { const Icon = item.icon; return <button key={item.id} className={active === item.id ? "nav-item selected" : "nav-item"} onClick={() => { setActive(item.id); setMobileOpen(false); }}><Icon size={18}/><span>{item.label}</span>{item.status !== "Available" && <span className="nav-dot" />}</button>; })}</nav>
      <div className="sidebar-bottom"><div className="privacy-note"><ShieldCheck size={17}/><div><strong>Privacy matters</strong><span>Your information is protected by access controls.</span></div></div><div className="profile"><div className="avatar"><RoleIcon size={17}/></div><div className="profile-copy"><strong>{displayName}</strong><span>{roleLabels[role]}</span></div><button className="icon-button" aria-label="Sign out" onClick={logout}><LogOut size={17}/></button></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><button className="icon-button menu-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={20}/></button><div className="breadcrumb">AMANAH GEN <ChevronRight size={14}/> <span>{current.label}</span></div><div className="topbar-right"><span className="secure-pill"><span/> Secure session</span><button className="text-button" onClick={logout}>Sign out <LogOut size={15}/></button></div></header>
      <div className="content">
        <section className="welcome"><div><p className="eyebrow">{roleLabels[role].toUpperCase()} WORKSPACE</p><h1>{active === "overview" ? "Your health. Your choices." : current.label}</h1><p>{active === "overview" ? "A secure place to understand, coordinate and navigate genetic health services." : current.description}</p></div><div className="welcome-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><Activity size={42}/></div></section>

        {active === "overview" ? <>
          <div className="section-heading"><div><h2>Workspace overview</h2><p>Tools and services available to your role</p></div><span className="status-chip"><CheckCircle2 size={14}/> Identity verified</span></div>
          <div className="card-grid">{items.filter(x => x.id !== "overview").map(item => { const Icon = item.icon; return <button className="feature-card" key={item.id} onClick={() => setActive(item.id)}><div className="feature-top"><div className="feature-icon"><Icon size={20}/></div><span className={item.status === "Available" ? "availability live" : "availability"}>{item.status}</span></div><h3>{item.label}</h3><p>{item.description}</p><span className="card-link">{item.status === "Available" ? "Open workspace" : "View planned screen"} <ArrowRight size={15}/></span></button>; })}</div>
          <section className="notice-panel"><div className="notice-icon"><ShieldCheck size={20}/></div><div><h3>Privacy and clinical safeguards</h3><p>Individual records remain separate. Sharing requires explicit permission from each person. Results must be reviewed by an authorised clinician before release.</p></div></section>
          <section className="bottom-grid"><div className="info-card"><div className="info-icon"><FileCheck2 size={18}/></div><div><h3>Clinical review comes first</h3><p>AI explanations are not diagnoses and do not replace qualified genetic counselling.</p></div></div><div className="info-card"><div className="info-icon"><HeartHandshake size={18}/></div><div><h3>Human support</h3><p>Genetic counselling and care navigation are central to the service.</p></div></div></section>
          {canUseAI && <div className="ai-note"><BookOpenCheck size={17}/><span>Your account has the educational AI access role. AI chat remains disabled by deployment policy.</span></div>}
        </> : <section className="coming-panel"><div className="coming-icon"><current.icon size={26}/></div><p className="eyebrow">WORKFLOW NOT YET CONNECTED</p><h2>{current.label}</h2><p>{current.description}. This screen is a navigation placeholder until its backend workflow, consent controls, audit events and role permissions have been implemented and reviewed.</p><div className="coming-status"><span className="status-dot"/> Planned — not operational</div><div className="coming-foot"><ShieldCheck size={16}/> No patient records are loaded or changed from this screen.</div></section>}
      </div>
      <footer className="footer"><span>AMANAH GEN</span><span>Understand your genetic health. Make informed choices. Protect what matters.</span><span>Secure workspace</span></footer>
    </main>
  </div>;
}