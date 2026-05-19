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
          src="https://www.google.com/recaptcha/api.js?onload=onRecaptchaLoad&render=explicit"
          async
          defer
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              window.onRecaptchaLoad = function() {
                console.log('reCAPTCHA loaded');
              };
            `,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}