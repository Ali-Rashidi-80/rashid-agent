"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { StatusBar } from "./StatusBar";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <TopBar onToggleSidebar={() => setSidebarOpen((open) => !open)} />
      <div className="flex min-h-0 flex-1">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          className={cn(!sidebarOpen && "hidden lg:flex")}
        />
        <main className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</main>
      </div>
      <StatusBar />
    </div>
  );
}
