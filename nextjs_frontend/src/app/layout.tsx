import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Auth App',
  description: 'Authentication application with OAuth support',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <script 
          src="https://js.hcaptcha.com/1/api.js" 
          async 
          defer
        ></script>
      </head>
      <body>{children}</body>
    </html>
  );
}