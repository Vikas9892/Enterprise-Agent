import type { Metadata } from "next";
import "./globals.css";
import SidebarNav from "@/components/layout/SidebarNav";
import TopHeader from "@/components/layout/TopHeader";

export const metadata: Metadata = {
  title: "Enterprise Agent Platform | Autonomous Agentic AI",
  description: "Next-generation enterprise agent orchestration, reflection loops, observability, and evaluation.",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <SidebarNav />
          <div className="main-viewport">
            <TopHeader />
            <main style={{ flex: 1, overflow: "hidden", position: "relative" }}>
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
