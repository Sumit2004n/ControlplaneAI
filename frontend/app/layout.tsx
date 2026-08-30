import type { Metadata } from "next";

import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import { AppProvider } from "@/lib/context";

import "./globals.css";

export const metadata: Metadata = {
  title: "ControlPlane.ai — Enterprise AI Governance",
  description: "Runtime risk control plane for enterprise AI (Round 2 prototype).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">{children}</main>
            </div>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
