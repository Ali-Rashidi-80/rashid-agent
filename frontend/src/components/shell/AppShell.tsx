"use client";

import { useEffect } from "react";
import { useAgentStore } from "@/lib/agent-store";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { StatusBar } from "./StatusBar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const sidebarOpen = useAgentStore((s) => s.sidebarOpen);
  const setSidebarOpen = useAgentStore((s) => s.setSidebarOpen);
  const toggleSidebar = useAgentStore((s) => s.toggleSidebar);
  const cycleMode = useAgentStore((s) => s.cycleMode);
  const startNewChat = useAgentStore((s) => s.startNewChat);
  const setPanelFocus = useAgentStore((s) => s.setPanelFocus);

  useEffect(() => {
    useAgentStore.getState().hydrate();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable);

      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        startNewChat();
        return;
      }

      if (event.ctrlKey && !event.shiftKey && event.key.toLowerCase() === "b") {
        event.preventDefault();
        toggleSidebar();
        return;
      }

      if (event.ctrlKey && event.altKey && event.key === "1") {
        event.preventDefault();
        setPanelFocus("output");
        return;
      }

      if (event.ctrlKey && event.altKey && event.key === "2") {
        event.preventDefault();
        setPanelFocus("diff");
        return;
      }

      if (event.ctrlKey && event.altKey && event.key === "0") {
        event.preventDefault();
        setPanelFocus("split");
        return;
      }

      if (!typing && event.shiftKey && event.key === "Tab") {
        event.preventDefault();
        cycleMode();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [cycleMode, setPanelFocus, startNewChat, toggleSidebar]);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <TopBar onToggleSidebar={toggleSidebar} />
      <div className="flex min-h-0 flex-1">
        {sidebarOpen && (
          <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        )}
        <main className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</main>
      </div>
      <StatusBar />
    </div>
  );
}
