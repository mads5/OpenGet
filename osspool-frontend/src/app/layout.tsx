import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Header } from "@/components/layout/header";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "OSSPool - Fund Open Source with Quadratic Funding",
  description:
    "Discover, rank, and fund critical open-source projects through quadratic funding pools.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Header />
        <main className="min-h-[calc(100vh-4rem)]">{children}</main>
        <footer className="border-t py-8">
          <div className="container text-center text-sm text-muted-foreground">
            OSSPool — Quadratic Funding for Open Source
          </div>
        </footer>
      </body>
    </html>
  );
}
