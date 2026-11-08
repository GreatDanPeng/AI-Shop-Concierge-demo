import { useEffect, useId, useRef, useState } from "react";
import { Icon, type IconName } from "./icons";

export type SidebarItem = { id: string; label: string; icon: IconName; count?: number };
export type SidebarGroup = { id: string; label: string; items: SidebarItem[] };

export type SidebarProps = {
  groups: SidebarGroup[];
  activeId: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  drawerOpen: boolean; // narrow screens: the sidebar slides in as a drawer
  onDrawerClose: () => void;
  onSelect: (id: string) => void;
};

function GroupSection({ group, collapsed, activeId, onPick }: {
  group: SidebarGroup; collapsed: boolean; activeId: string; onPick: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const listId = useId();
  // Collapsed to icons: every item stays visible, the accordion headers step aside.
  const showItems = collapsed || open;
  return (
    <section className="sidebar-group">
      {!collapsed && (
        <button type="button" className="sidebar-group-toggle" aria-expanded={open} aria-controls={listId} onClick={() => setOpen(!open)}>
          <Icon name={open ? "chevron-down" : "chevron-right"} size={16} />
          <span>{group.label}</span>
        </button>
      )}
      <ul id={listId} className="sidebar-list">
        {showItems && group.items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={item.id === activeId ? "sidebar-item sidebar-item--active" : "sidebar-item"}
              aria-current={item.id === activeId ? "page" : undefined}
              title={collapsed ? item.label : undefined}
              onClick={() => onPick(item.id)}
            >
              <Icon name={item.icon} />
              <span className={collapsed ? "sidebar-label sr-only" : "sidebar-label"}>{item.label}</span>
              {!collapsed && item.count !== undefined && <span className="sidebar-count">{item.count}</span>}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Sidebar({ groups, activeId, collapsed, onToggleCollapsed, drawerOpen, onDrawerClose, onSelect }: SidebarProps) {
  const classes = ["sidebar", collapsed && "sidebar--collapsed", drawerOpen && "sidebar--drawer-open"].filter(Boolean).join(" ");
  const navRef = useRef<HTMLElement>(null);

  // When the drawer opens, the keyboard focus moves into it (onto the page you are on).
  useEffect(() => {
    if (!drawerOpen) return;
    const nav = navRef.current;
    (nav?.querySelector<HTMLElement>('[aria-current="page"]') ?? nav?.querySelector<HTMLElement>("button"))?.focus();
  }, [drawerOpen]);

  // Escape closes an open drawer wherever the focus happens to be.
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onDrawerClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawerOpen, onDrawerClose]);
  function pick(id: string) {
    onSelect(id);
    if (drawerOpen) onDrawerClose(); // on a phone, choosing something puts the drawer away
  }

  return (
    <>
      {drawerOpen && <div className="sidebar-backdrop" data-testid="sidebar-backdrop" aria-hidden="true" onClick={onDrawerClose} />}
      <nav ref={navRef} className={classes} aria-label="Main">
        <button
          type="button"
          className="sidebar-collapse"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={onToggleCollapsed}
        >
          <Icon name={collapsed ? "chevron-right" : "chevron-left"} />
          {!collapsed && <span>Collapse</span>}
        </button>
        {groups.map((group) => (
          <GroupSection key={group.id} group={group} collapsed={collapsed} activeId={activeId} onPick={pick} />
        ))}
      </nav>
    </>
  );
}
