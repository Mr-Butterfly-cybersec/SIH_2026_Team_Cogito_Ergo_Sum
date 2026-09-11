import type { Metadata, Viewport } from "next";

import { Providers } from "./providers";
import "./globals.css";

const DESCRIPTION =
  "Cyber risk quantification and security-investment optimization: from CVE to rupee impact to optimal security spend.";

export const metadata: Metadata = {
  title: "CRQ Decision Engine — SIH26105",
  description: DESCRIPTION,
  applicationName: "CRQ Decision Engine",
  openGraph: {
    title: "CRQ Decision Engine — from CVE to ₹ impact to optimal security spend",
    description: DESCRIPTION,
    type: "website",
  },
  twitter: { card: "summary_large_image", description: DESCRIPTION },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Matches the dashboard background, so mobile browser chrome blends with the page
  // instead of framing it in white.
  themeColor: "#05070d",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
